"""School foundation data: typed validation, row-isolated import and soft disable."""
import csv
import io
import json
import math
import uuid
from datetime import datetime
from sqlalchemy import select

from app.models.user import User, UserRole
from app.models.student import Major, Class, Student
from app.models.lab import Lab
from app.models.ability import MajorAbility, SubAbility
from app.models.training import TrainingProject
from app.models.operations import ConfigurationVersion
from app.services.production_data import setting, put_setting
from app.services.audit import record_audit
from app.services.auth import AuthService

CATALOG = {
    "accounts": (User, ["username","name","role"], ["username","name","role"]),
    "majors": (Major,["code","name","description"],["code","name"]),
    "classes": (Class,["name","major_id","teacher_id","year"],["name","major_id","year"]),
    "students": (Student,["user_id","student_no","name","major_id","class_id","enrollment_year"],["user_id","student_no","name","major_id","class_id","enrollment_year"]),
    "labs": (Lab,["name","building","floor","capacity","reference_image_url"],["name"]),
    "abilities": (MajorAbility,["name","description","weight","graduation_threshold","display_order"],["name"]),
    "sub-abilities": (SubAbility,["major_ability_id","name","description","weight"],["major_ability_id","name"]),
    "projects": (TrainingProject,["name","major_id","lab_id","duration","steps","scoring_rules","ability_mapping"],["name","major_id"]),
}


def as_dict(item, fields):
    result = {key:getattr(item,key) for key in ["id"]+fields}
    for key,value in list(result.items()):
        if hasattr(value,"value"):
            result[key] = value.value
    return result


async def save_item(db, kind, data, actor, item_id=None):
    if kind not in CATALOG:
        raise ValueError("不支持的数据类型")
    model, fields, required = CATALOG[kind]
    allowed = set(fields) | {"id","enabled","password","code","oidc_subject","oidc_issuer"}
    if set(data)-allowed:
        raise ValueError("未知字段："+",".join(sorted(set(data)-allowed)))
    item = await db.get(model, item_id) if item_id else None
    if item_id and not item:
        raise ValueError("记录不存在")
    before = as_dict(item,fields) if item else None
    values = {key:data[key] for key in fields if key in data}
    merged = {**(before or {}),**values}
    if any(merged.get(key) is None or merged.get(key)=="" for key in required):
        raise ValueError("缺少必填项："+",".join(required))
    for key in ["year","enrollment_year","floor","capacity","duration"]:
        if key in values and values[key] not in (None,""):
            values[key] = int(values[key])
            if not -10 <= values[key] <= 10000:
                raise ValueError(f"{key} 超出范围")
    for key in ["weight","graduation_threshold","display_order"]:
        if key in values:
            values[key] = float(values[key])
            if not math.isfinite(values[key]) or values[key]<0 or (key=="graduation_threshold" and values[key]>1):
                raise ValueError(f"{key} 超出范围")
    foreign = {"major_id":Major,"class_id":Class,"teacher_id":User,"user_id":User,"lab_id":Lab,"major_ability_id":MajorAbility}
    for key, cls in foreign.items():
        if merged.get(key) and not await db.get(cls,merged[key]):
            raise ValueError(f"关联对象不存在：{key}")
    if kind == "accounts":
        values["role"] = UserRole(merged["role"])
        if not item and len(str(data.get("password",""))) < 12:
            raise ValueError("初始密码至少 12 位")
        if data.get("password"):
            if len(data["password"])<12:
                raise ValueError("密码至少 12 位")
            values["password_hash"] = AuthService.get_password_hash(data["password"])
    if kind == "students":
        user, cls = await db.get(User,merged["user_id"]), await db.get(Class,merged["class_id"])
        if user.role != UserRole.STUDENT or cls.major_id != merged["major_id"]:
            raise ValueError("学生账号角色或班级专业不匹配")
    for unique in {"accounts":["username"],"majors":["code"],"students":["student_no","user_id"]}.get(kind,[]):
        match = (await db.execute(select(model.id).where(getattr(model,unique)==merged[unique]))).scalar_one_or_none()
        if match and match != item_id:
            raise ValueError(f"{unique} 已存在；请使用原 ID 更新")
    if kind=="projects":
        for key, default in [("steps",[]),("scoring_rules",{}),("ability_mapping",{})]:
            if key in values and isinstance(values[key],str):
                values[key] = json.loads(values[key])
            merged[key] = values.get(key,merged.get(key) or default)
        if not isinstance(merged["steps"],list) or not isinstance(merged["ability_mapping"],dict) or not isinstance(merged["scoring_rules"],dict):
            raise ValueError("步骤、规则和映射结构错误")
        steps = merged["steps"]
        ids = [str(step.get("id", "")) for step in steps]
        if steps and (not all(ids) or len(set(ids)) != len(ids)):
            raise ValueError("步骤编号不能为空或重复")
        if set(merged["ability_mapping"])-set(ids):
            raise ValueError("映射引用未知步骤")
        for refs in merged["ability_mapping"].values():
            if not isinstance(refs,list):
                raise ValueError("能力映射必须为数组")
            for sub_id in refs:
                if not await db.get(SubAbility,sub_id):
                    raise ValueError("映射引用不存在的子能力")
        if steps:
            from app.services.production_data import score_steps
            temporary = TrainingProject(steps=steps,ability_mapping=merged["ability_mapping"],scoring_rules=merged["scoring_rules"])
            _,_,maximum,_ = score_steps(temporary,{str(s["id"]):True for s in steps if s.get("enabled",True)})
            values["max_score"] = maximum
        rules = dict(merged["scoring_rules"])
        if rules.get("repeat_mode","all") not in {"all","latest","highest","average"}:
            raise ValueError("重复计分模式必须为 all/latest/highest/average")
        rules["version"] = int((item.scoring_rules or {}).get("version",0) if item else 0)+1
        values["scoring_rules"] = rules
    if item is None:
        item = model(id=str(uuid.uuid4()),**values)
        db.add(item)
    else:
        for key,value in values.items():
            setattr(item,key,value)
    await db.flush()
    state = await setting(db,f"state:{kind}:{item.id}",{})
    if "enabled" in data:
        from app.services.production_data import truth
        state["enabled"] = truth(data["enabled"])
    if "code" in data:
        state["code"] = str(data["code"])
    await put_setting(db,f"state:{kind}:{item.id}",state,actor.id)
    if kind=="accounts" and ("enabled" in data or "password" in data or "role" in data):
        from app.services.account_security import revoke
        await revoke(db,item.id,state.get("enabled",True))
    if kind=="accounts" and data.get("oidc_subject") and data.get("oidc_issuer"):
        import hashlib
        key = "oidc_identity:"+hashlib.sha256(f'{data["oidc_issuer"]}|{data["oidc_subject"]}'.encode()).hexdigest()
        bound = await setting(db,key)
        if bound and bound["user_id"] != item.id:
            raise ValueError("该统一认证身份已绑定其他账号")
        await put_setting(db,key,{"user_id":item.id},actor.id)
    after = as_dict(item,fields)
    version = int((await setting(db,f"version:{kind}:{item.id}",{})).get("version",0))+1
    await put_setting(db,f"version:{kind}:{item.id}",{"version":version},actor.id)
    db.add(ConfigurationVersion(object_type=kind,object_id=item.id,version=version,before=before,after=after,changed_by=actor.id))
    await record_audit(db,actor_id=actor.id,actor_name=actor.name,action="update" if before else "create",object_type=kind,object_id=item.id,
                       before=before,after={**after,**state})
    return {**after,**state}


def parse_upload(filename, content):
    if len(content)>20*1024*1024:
        raise ValueError("文件大小超过 20MB")
    if filename.lower().endswith(".csv"):
        rows = list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))
    elif filename.lower().endswith(".xlsx"):
        import zipfile
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            if sum(info.file_size for info in archive.infolist())>100*1024*1024:
                raise ValueError("表格解压后过大")
        from openpyxl import load_workbook
        book = load_workbook(io.BytesIO(content),read_only=True,data_only=True)
        source = iter(book.active.values)
        fields = [str(x or "") for x in next(source)]
        rows = []
        for row in source:
            rows.append(dict(zip(fields,[v.isoformat() if isinstance(v,datetime) else v for v in row])))
            if len(rows)>5000:
                break
        book.close()
    else:
        raise ValueError("仅支持 UTF-8 CSV 或 XLSX")
    if not rows or len(rows)>5000:
        raise ValueError("单次文件须包含 1—5000 条记录")
    return rows
