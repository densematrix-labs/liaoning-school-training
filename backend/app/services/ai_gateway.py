"""Bounded provider requests with a local transmission audit (no raw payload)."""
import hashlib
import json
import os
import time
from datetime import datetime

import httpx
from app.config import settings


def bounded_vision_payload(messages):
    import base64, copy, io
    from PIL import Image
    payload=copy.deepcopy(messages)
    for message in payload:
        if not isinstance(message.get('content'),list):
            continue
        for item in message['content']:
            if item.get('type')!='image_url':
                continue
            source=item.get('image_url',{}).get('url','')
            if not source.startswith('data:image/') or len(source)<400000:
                continue
            data=base64.b64decode(source.split(',',1)[1],validate=True)
            image=Image.open(io.BytesIO(data));image.load()
            if image.width*image.height>25000000:
                raise ValueError('图片尺寸超出支持范围')
            image=image.convert('RGB');image.thumbnail((1000,1000),Image.Resampling.LANCZOS)
            output=io.BytesIO()
            for quality in [86,76,66,56]:
                output=io.BytesIO();image.save(output,format='JPEG',quality=quality,optimize=True)
                if len(output.getvalue())<350000:break
            item['image_url']['url']='data:image/jpeg;base64,'+base64.b64encode(output.getvalue()).decode()
    return payload


async def completion(messages, *, vision=False, db=None):
    from app.services.audit import record_audit
    if vision:
        messages=bounded_vision_payload(messages)
    routes=[{"url":settings.LLM_BASE_URL,"key":settings.LLM_API_KEY,
             "model":settings.VLM_MODEL if vision else settings.LLM_MODEL}]
    # Optional operator-only failover configuration. Never exposed via an API.
    for route in json.loads(os.getenv("AI_FALLBACK_ROUTES","[]")):
        routes.append({"url":route["url"],"key":os.getenv(route["key_env"],""),
                       "model":route["vision_model"] if vision else route["model"]})
    digest=hashlib.sha256(json.dumps(messages,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    # Image comparisons may need longer than text-only calls. Keep the
    # operator-configurable budget bounded rather than disabling timeouts.
    budget=max(5,min(120,settings.VLM_TIMEOUT_SECONDS)) if vision else 50
    deadline=time.monotonic()+budget
    failures=[]
    for route in routes:
        if not route["key"]:
            continue
        if not route["url"].startswith("https://") and not os.getenv("ALLOW_LOCAL_AI_HTTP","") == "true":
            raise RuntimeError("AI 接口必须使用 HTTPS；校内本地模型需管理员明确启用 HTTP")
        remaining=deadline-time.monotonic()
        if remaining<=0:
            break
        try:
            timeout=httpx.Timeout(remaining,connect=min(5,remaining))
            async with httpx.AsyncClient(timeout=timeout,follow_redirects=False) as client:
                response=await client.post(route["url"].rstrip("/")+"/chat/completions",
                    headers={"Authorization":"Bearer "+route["key"]},
                    json={"model":route["model"],"messages":messages,"temperature":0.2,"response_format":{"type":"json_object"}})
                response.raise_for_status()
                body=response.json()
                content=body["choices"][0]["message"]["content"]
                data=json.loads(content)
                if not isinstance(data,dict):
                    raise ValueError("AI JSON must be an object")
            if db:
                await record_audit(db,actor_id=None,actor_name="AI 服务",action="ai_call",object_type="model",object_id=route["model"],
                    after={"payload_sha256":digest,"model":route["model"],"vision":vision,"usage":body.get("usage",{}),"generated_at":datetime.utcnow().isoformat()})
                await db.commit()
            return data,route["model"]
        except (httpx.HTTPError,ValueError,KeyError,TypeError) as exc:
            failures.append(type(exc).__name__)
    if db:
        await record_audit(db,actor_id=None,actor_name="AI 服务",action="ai_call",object_type="model",result="failed",
            reason=",".join(failures) or "not_configured",after={"payload_sha256":digest,"vision":vision})
        await db.commit()
    if any('Timeout' in failure for failure in failures):
        raise RuntimeError('AI 服务超时（' + ','.join(failures) + '）；未生成检查结果，失败任务保留，可重新提交或联系教师人工处理')
    raise RuntimeError("AI 服务未配置、不可达或未返回有效结构化结果；原始业务数据不受影响")


def validate_report(data, facts):
    sections=["overview","score_analysis","weaknesses","environment","suggestions","training_plan"]
    if set(sections)-set(data) or not isinstance(data.get("evidence"),list):
        raise ValueError("AI 报告缺少六类内容或证据引用")
    if any(not isinstance(data[key],str) or not data[key].strip() for key in sections):
        raise ValueError("AI 报告章节内容为空")
    if not data["evidence"]:
        raise ValueError("AI 报告未引用任何事实")
    for evidence in data["evidence"]:
        if not isinstance(evidence,dict) or evidence.get("key") not in facts or evidence.get("value") != facts[evidence["key"]]:
            raise ValueError("AI 报告引用数值与结构化数据不一致，需要重新生成或人工核查")
    import re
    numbers={str(x) for x in facts.values() if isinstance(x,(int,float)) and not isinstance(x,bool)}
    numbers|={str(float(x)) for x in numbers}|{str(int(float(x))) for x in numbers if float(x).is_integer()}
    for key in sections[:4]:
        # These are factual sections, not recommendation durations or goals.
        factual_text=re.sub(r'(?<![A-Za-z0-9])[56]S(?![A-Za-z0-9])','现场整理规范',data[key])
        for number in re.findall(r"(?<![A-Za-z])\d+(?:\.\d+)?",factual_text):
            if number not in numbers:
                raise ValueError("AI 事实章节出现无证据数字，需要人工核查")
    labels=["诊断结论","成绩与步骤分析","薄弱能力","环境规范情况","改进建议","训练建议"]
    content = "\n\n".join("## "+label+"\n"+data[key] for key,label in zip(sections,labels))
    causes=data.get('possible_causes')
    if causes is not None:
        if not isinstance(causes,str) or not causes.strip():
            raise ValueError('可能原因内容为空')
        content += '\n\n## 可能原因\n'+causes
    return content + '\n\n## 处理状态\n已生成。'
