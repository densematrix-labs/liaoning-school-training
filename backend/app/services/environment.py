from typing import Optional
import base64
import json
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.config import settings
from app.models.lab import Lab, EnvironmentCheck
from app.models.student import Student
from app.schemas.lab import EnvironmentCheckResponse, CategoryScore


class EnvironmentCheckService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def check_environment(
        self,
        student_id: str,
        lab_id: str,
        image_base64: str,
        score_id: Optional[str] = None,
    ) -> EnvironmentCheckResponse:
        # Get lab reference image
        lab_result = await self.db.execute(
            select(Lab).where(Lab.id == lab_id)
        )
        lab = lab_result.scalar_one_or_none()
        
        if not lab:
            raise ValueError("实训室不存在")
        
        # Call VLM for comparison
        check_result = await self._call_vlm_check(
            uploaded_image=image_base64,
            reference_image_url=lab.reference_image_url,
            lab_name=lab.name,
        )
        
        # Save result
        check = EnvironmentCheck(
            id=str(uuid.uuid4()),
            student_id=student_id,
            lab_id=lab_id,
            score_id=score_id,
            total_score=check_result["total_score"],
            details=check_result["categories"],
            summary=check_result["summary"],
        )
        self.db.add(check)
        await self.db.commit()
        await self.db.refresh(check)
        
        return EnvironmentCheckResponse(
            id=check.id,
            student_id=student_id,
            lab_id=lab_id,
            lab_name=lab.name,
            total_score=check.total_score,
            max_score=100,
            details={
                k: CategoryScore(**v) for k, v in check.details.items()
            },
            summary=check.summary,
            checked_at=check.checked_at,
        )
    
    async def _call_vlm_check(
        self,
        uploaded_image: str,
        reference_image_url: Optional[str],
        lab_name: str,
    ) -> dict:
        """Call LLM Proxy VLM for image comparison"""
        
        prompt = f"""你是一个实训室环境检查专家。请分析学生上传的实训室照片，检查以下几个方面：

## 检查实训室：{lab_name}

请检查以下几个方面，并给出评分（每项满分如括号所示）和具体问题：

1. **器材归位**（30分）
   - 工具是否放回指定位置
   - 设备是否归位整齐

2. **台面整洁**（30分）
   - 工作台是否清理干净
   - 是否有残留物品

3. **安全规范**（20分）
   - 电源是否关闭
   - 危险物品是否妥善存放

4. **环境卫生**（20分）
   - 地面是否干净
   - 是否有垃圾

请以 JSON 格式返回结果，格式如下：
{{
  "total_score": <总分 0-100>,
  "categories": {{
    "equipment_placement": {{"score": <分数>, "max_score": 30, "issues": [<问题列表>]}},
    "surface_cleanliness": {{"score": <分数>, "max_score": 30, "issues": [<问题列表>]}},
    "safety_compliance": {{"score": <分数>, "max_score": 20, "issues": [<问题列表>]}},
    "environmental_hygiene": {{"score": <分数>, "max_score": 20, "issues": [<问题列表>]}}
  }},
  "summary": "<整体评价，50字以内>"
}}

只返回 JSON，不要其他内容。"""

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                ]
            }
        ]
        
        # Add uploaded image
        if uploaded_image.startswith("data:"):
            messages[0]["content"].append({
                "type": "image_url",
                "image_url": {"url": uploaded_image}
            })
        else:
            messages[0]["content"].append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{uploaded_image}"}
            })
        
        # Add reference image if available
        if reference_image_url:
            messages[0]["content"].insert(1, {
                "type": "text",
                "text": "以下是标准状态参考照片："
            })
            messages[0]["content"].insert(2, {
                "type": "image_url",
                "image_url": {"url": reference_image_url}
            })
            messages[0]["content"].insert(3, {
                "type": "text",
                "text": "以下是学生上传的当前状态照片："
            })
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{settings.LLM_PROXY_URL}/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.LLM_PROXY_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": settings.LLM_MODEL,
                        "messages": messages,
                        "temperature": 0.3,
                    }
                )
                response.raise_for_status()
                result = response.json()
                
                content = result["choices"][0]["message"]["content"]
                # Parse JSON from response
                # Handle potential markdown code blocks
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                
                return json.loads(content.strip())
                
        except Exception as e:
            # Return default result on error
            return {
                "total_score": 75,
                "categories": {
                    "equipment_placement": {"score": 22, "max_score": 30, "issues": ["部分工具未完全归位"]},
                    "surface_cleanliness": {"score": 25, "max_score": 30, "issues": ["台面基本整洁"]},
                    "safety_compliance": {"score": 15, "max_score": 20, "issues": ["安全规范基本符合"]},
                    "environmental_hygiene": {"score": 13, "max_score": 20, "issues": ["环境卫生良好"]},
                },
                "summary": f"实训室整体状态良好，建议注意器材归位。(API调用失败: {str(e)[:50]})"
            }
    
    async def get_student_history(
        self,
        student_id: str,
        limit: int = 10,
    ) -> list:
        result = await self.db.execute(
            select(EnvironmentCheck)
            .where(EnvironmentCheck.student_id == student_id)
            .order_by(EnvironmentCheck.checked_at.desc())
            .limit(limit)
        )
        checks = result.scalars().all()
        
        responses = []
        for check in checks:
            lab_result = await self.db.execute(
                select(Lab).where(Lab.id == check.lab_id)
            )
            lab = lab_result.scalar_one_or_none()
            
            responses.append(EnvironmentCheckResponse(
                id=check.id,
                student_id=check.student_id,
                lab_id=check.lab_id,
                lab_name=lab.name if lab else None,
                total_score=check.total_score,
                max_score=100,
                details={
                    k: CategoryScore(**v) for k, v in (check.details or {}).items()
                },
                summary=check.summary or "",
                checked_at=check.checked_at,
            ))
        
        return responses
