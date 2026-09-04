from typing import Optional
import base64
import json
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.config import settings
from app.models.lab import Lab, EnvironmentCheck
from app.models.user import User
from app.models.workflow import EnvironmentReview, EnvironmentTask, TaskStatus
from app.database import AsyncSessionLocal
from app.models.student import Student
from app.schemas.lab import CategoryScore, EnvironmentCheckResponse, EnvironmentReviewRequest, EnvironmentTaskResponse


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
            uploaded_image_url=(
                image_base64 if image_base64.startswith("data:") else f"data:image/jpeg;base64,{image_base64}"
            ),
            total_score=check_result["total_score"],
            details={
                **check_result["categories"],
                "__suggestions__": check_result.get("suggestions", []),
            },
            summary=check_result["summary"],
        )
        self.db.add(check)
        await self.db.commit()
        await self.db.refresh(check)
        
        return await self._to_response(check, lab)

    async def create_task(
        self,
        student_id: str,
        lab_id: str,
        image_base64: str,
        score_id: Optional[str],
        created_by: str,
    ) -> EnvironmentTaskResponse:
        if not image_base64.startswith(("data:image/jpeg", "data:image/png", "data:image/webp")):
            raise ValueError("仅支持 JPG、PNG 或 WebP 图片")
        if len(image_base64) > 14_000_000:
            raise ValueError("图片不得超过 10MB")
        try:
            metadata, payload = image_base64.split(",", 1)
            if ";base64" not in metadata or not base64.b64decode(payload, validate=True):
                raise ValueError
        except (ValueError, base64.binascii.Error) as exc:
            raise ValueError("图片内容无效，请重新选择文件") from exc
        lab = (await self.db.execute(select(Lab.id).where(Lab.id == lab_id))).scalar_one_or_none()
        if not lab:
            raise ValueError("实训室不存在")
        student = (await self.db.execute(select(Student.id).where(Student.id == student_id))).scalar_one_or_none()
        if not student:
            raise ValueError("学生不存在")
        task = EnvironmentTask(
            id=str(uuid.uuid4()),
            student_id=student_id,
            lab_id=lab_id,
            score_id=score_id,
            image_data=image_base64,
            status=TaskStatus.PENDING,
            created_by=created_by,
        )
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        return await self.get_task(task.id)

    async def get_task(self, task_id: str) -> Optional[EnvironmentTaskResponse]:
        task = (await self.db.execute(select(EnvironmentTask).where(EnvironmentTask.id == task_id))).scalar_one_or_none()
        if not task:
            return None
        result = await self.get_check(task.check_id) if task.check_id else None
        return EnvironmentTaskResponse(
            id=task.id,
            student_id=task.student_id,
            lab_id=task.lab_id,
            score_id=task.score_id,
            status=task.status.value,
            check_id=task.check_id,
            error_message=task.error_message,
            created_at=task.created_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
            result=result,
        )
    
    async def _call_vlm_check(
        self,
        uploaded_image: str,
        reference_image_url: Optional[str],
        lab_name: str,
    ) -> dict:
        """Call the configured multimodal provider for image comparison."""
        
        prompt = f"""你是一个实训室环境检查专家。请分析教师上传的实训室照片，检查以下几个方面：

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
    "summary": "<整体评价，50字以内>",
    "suggestions": ["<针对可见问题的具体处置建议>"]
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
                "text": "以下是教师上传的当前状态照片："
            })

        if reference_image_url and reference_image_url.startswith("/"):
            messages[0]["content"][2]["image_url"]["url"] = (
                f"{settings.PUBLIC_BASE_URL.rstrip('/')}{reference_image_url}"
            )

        if not settings.LLM_API_KEY:
            raise RuntimeError(f"{settings.LLM_PROVIDER} 未配置，无法执行真实环境检查")

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{settings.LLM_BASE_URL.rstrip('/')}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.LLM_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": settings.VLM_MODEL,
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
                
        except (httpx.HTTPError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"{settings.LLM_PROVIDER} 环境检查调用失败") from exc
    
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
            
            responses.append(await self._to_response(check, lab))
        
        return responses

    async def get_check(self, check_id: str) -> Optional[EnvironmentCheckResponse]:
        check = (await self.db.execute(
            select(EnvironmentCheck).where(EnvironmentCheck.id == check_id)
        )).scalar_one_or_none()
        if not check:
            return None
        lab = (await self.db.execute(select(Lab).where(Lab.id == check.lab_id))).scalar_one_or_none()
        return await self._to_response(check, lab)

    async def review_check(
        self,
        check_id: str,
        reviewer_id: str,
        data: EnvironmentReviewRequest,
    ) -> EnvironmentCheckResponse:
        if data.status not in {"confirmed", "modified", "rejected"}:
            raise ValueError("复核状态仅支持 confirmed、modified 或 rejected")
        check = (await self.db.execute(
            select(EnvironmentCheck).where(EnvironmentCheck.id == check_id)
        )).scalar_one_or_none()
        if not check:
            raise ValueError("环境检查记录不存在")
        review = (await self.db.execute(
            select(EnvironmentReview).where(EnvironmentReview.check_id == check_id)
        )).scalar_one_or_none()
        if not review:
            review = EnvironmentReview(
                id=str(uuid.uuid4()),
                check_id=check_id,
                reviewer_id=reviewer_id,
                status=data.status,
            )
            self.db.add(review)
        review.reviewer_id = reviewer_id
        review.status = data.status
        review.reviewed_details = data.reviewed_details or check.details
        review.reviewed_summary = data.reviewed_summary or check.summary
        review.note = data.note
        await self.db.commit()
        lab = (await self.db.execute(select(Lab).where(Lab.id == check.lab_id))).scalar_one_or_none()
        return await self._to_response(check, lab)

    async def _to_response(self, check: EnvironmentCheck, lab: Optional[Lab]) -> EnvironmentCheckResponse:
        review = (await self.db.execute(
            select(EnvironmentReview).where(EnvironmentReview.check_id == check.id)
        )).scalar_one_or_none()
        reviewer_name = None
        if review:
            reviewer = (await self.db.execute(select(User).where(User.id == review.reviewer_id))).scalar_one_or_none()
            reviewer_name = reviewer.name if reviewer else None
        return EnvironmentCheckResponse(
            id=check.id,
            student_id=check.student_id,
            lab_id=check.lab_id,
            lab_name=lab.name if lab else None,
            total_score=check.total_score,
            max_score=100,
            details={k: CategoryScore(**v) for k, v in (check.details or {}).items() if k != "__suggestions__"},
            summary=check.summary or "",
            suggestions=(check.details or {}).get("__suggestions__", []),
            checked_at=check.checked_at,
            uploaded_image_url=check.uploaded_image_url,
            reference_image_url=lab.reference_image_url if lab else None,
            review_status=review.status if review else None,
            reviewed_details=review.reviewed_details if review else None,
            reviewed_summary=review.reviewed_summary if review else None,
            review_note=review.note if review else None,
            reviewer_name=reviewer_name,
            reviewed_at=review.reviewed_at if review else None,
        )


async def process_environment_task(task_id: str) -> None:
    from datetime import datetime

    async with AsyncSessionLocal() as db:
        task = (await db.execute(select(EnvironmentTask).where(EnvironmentTask.id == task_id))).scalar_one_or_none()
        if not task:
            return
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        task.error_message = None
        await db.commit()
        try:
            result = await EnvironmentCheckService(db).check_environment(
                student_id=task.student_id,
                lab_id=task.lab_id,
                image_base64=task.image_data,
                score_id=task.score_id,
            )
            task = (await db.execute(select(EnvironmentTask).where(EnvironmentTask.id == task_id))).scalar_one()
            task.status = TaskStatus.COMPLETED
            task.check_id = result.id
            task.image_data = "已转存至环境检查记录"
            task.completed_at = datetime.utcnow()
            await db.commit()
        except Exception as exc:
            await db.rollback()
            task = (await db.execute(select(EnvironmentTask).where(EnvironmentTask.id == task_id))).scalar_one_or_none()
            if task:
                task.status = TaskStatus.FAILED
                task.error_message = str(exc)[:1000]
                task.completed_at = datetime.utcnow()
                await db.commit()
