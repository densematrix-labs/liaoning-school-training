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
    "labs": (Lab,["name","building","floor","capacity","reference_image_url","equipment","status"],["name"]),
    "abilities": (MajorAbility,["name","description","pass_score","display_order","icon"],["name"]),
    "sub-abilities": (SubAbility,["major_ability_id","name","description","full_score"],["major_ability_id","name"]),
    "projects": (TrainingProject,["name","major_id","lab_id","duration","steps","scoring_rules","ability_mapping"],["name","major_id"]),
}


def as_dict(item, fields):
    result = {key:getattr(item,key) for key in ["id"]+fields}
    for key,value in list(result.items()):
        if hasattr(value,"value"):
            result[key] = value.value
    return result


async def save_item(db, kind, data, actor, item_id=None):
    data=dict(data)
    # Legacy admin endpoints translate old storage fields; current catalog exposes only points.
    if kind=='abilities':
        if float(data.get('weight',0))<0:raise ValueError('分值不能为负数')
        data.pop('weight',None)
        if 'graduation_threshold' in data:data['pass_score']=float(data.pop('graduation_threshold'))*100
    elif kind=='sub-abilities' and 'weight' in data:
        data['full_score']=data.pop('weight')
    if kind not in CATALOG:
        raise ValueError("不支持的数据类型")
    model, fields, required = CATALOG[kind]
    allowed = set(fields) | {"id","enabled","password","code","description","oidc_subject","oidc_issuer"}
    if set(data)-allowed:
        raise ValueError("未知字段："+",".join(sorted(set(data)-allowed)))
    item = await db.get(model, item_id) if item_id else None
    if item_id and not item:
        raise ValueError("记录不存在")
    if kind == "accounts" and item_id == actor.id:
        from app.services.production_data import truth
        if ("enabled" in data and not truth(data["enabled"])) or data.get("role", "admin") != "admin":
            raise ValueError("不能停用或降级当前管理员账号")
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
    for key in ["weight","graduation_threshold","display_order","full_score","pass_score"]:
        if key in values:
            values[key] = float(values[key])
            if not math.isfinite(values[key]) or values[key]<0 or (key=="graduation_threshold" and values[key]>1):
                raise ValueError(f"{key} 超出范围")
    if "full_score" in values and values["full_score"] <= 0:
        raise ValueError("子能力满分必须大于零")
    if "pass_score" in values and values["pass_score"] > 100:
        raise ValueError("达标分必须在0到100之间")
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
    if kind == 'labs' and 'equipment' in values:
        equipment = values['equipment']
        if isinstance(equipment, str):
            equipment = json.loads(equipment)
        if not isinstance(equipment, list) or any(not isinstance(x, str) for x in equipment):
            raise ValueError('设备清单必须为设备名称列表')
        values['equipment'] = [x.strip() for x in equipment if x.strip()]
    if kind == 'labs' and 'status' in values:
        from app.models.lab import LabStatus
        try:
            values['status']=LabStatus(values['status'])
        except ValueError as exc:
            raise ValueError('实训室状态仅支持 available / in_use / maintenance') from exc
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
        if merged['scoring_rules'].get('scoring_mode', 'absolute') != 'absolute':
            raise ValueError('仅支持绝对分值计分')
        if any(float(step.get('weight', 1)) != 1 for step in merged['steps']):
            raise ValueError('请配置步骤绝对分值，不配置步骤权重')
        merged['scoring_rules'] = {k:v for k,v in merged['scoring_rules'].items() if k not in {'total_score','decay','time_decay'}}
        merged['scoring_rules']['scoring_mode'] = 'absolute'
        steps = merged["steps"]
        ids = [str(step.get("id", "")) for step in steps]
        if steps and (not all(ids) or len(set(ids)) != len(ids)):
            raise ValueError("步骤编号不能为空或重复")
        if set(merged["ability_mapping"])-set(ids):
            raise ValueError("映射引用未知步骤")
        for refs in merged["ability_mapping"].values():
            if not isinstance(refs,list):
                raise ValueError("能力映射必须为数组")
            if len(refs) != len(set(refs)):
                raise ValueError('同一步骤不能重复关联同一子能力')
            for sub_id in refs:
                if not await db.get(SubAbility,sub_id):
                    raise ValueError("映射引用不存在的子能力")
        from app.services.mapping_points import validate_mapping_points
        merged['scoring_rules']['ability_mapping_points'] = validate_mapping_points(
            merged['ability_mapping'], merged['scoring_rules'].get('ability_mapping_points', {}))
        if any(step.get("enabled",True) for step in steps):
            from app.services.production_data import score_steps
            temporary = TrainingProject(steps=steps,ability_mapping=merged["ability_mapping"],scoring_rules={**merged["scoring_rules"],"enabled":True})
            _,_,maximum,_ = score_steps(temporary,{str(s["id"]):True for s in steps if s.get("enabled",True)})
            values["max_score"] = maximum
        rules = dict(merged["scoring_rules"])
        if "code" in data:
            rules["code"] = str(data["code"])
        if rules.get("code"):
            projects = (await db.execute(select(TrainingProject))).scalars().all()
            if any(p.id != item_id and (p.scoring_rules or {}).get("code")==rules["code"] for p in projects):
                raise ValueError("实训项目编码已存在")
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
    if kind == "projects" and "description" in data:
        state["description"] = str(data["description"])
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


async def ability_hierarchy(db):
    """Read configured parents/children, including disabled nodes and inherited thresholds."""
    from app.models.operations import SystemSetting
    states = {row.key: row.value for row in (await db.execute(
        select(SystemSetting).where(SystemSetting.key.like('state:%'))
    )).scalars()}
    parents = (await db.execute(select(MajorAbility).order_by(MajorAbility.display_order, MajorAbility.id))).scalars().all()
    children = (await db.execute(select(SubAbility).order_by(SubAbility.id))).scalars().all()
    result = []
    for parent in parents:
        state = states.get(f'state:abilities:{parent.id}', {})
        row = {**as_dict(parent, CATALOG['abilities'][1]), **state,
               'level': 1, 'level_name': '一级 · 大类能力',
               'enabled': state.get('enabled', True), 'threshold_source': '本级配置', 'children': []}
        for child in children:
            if child.major_ability_id != parent.id:
                continue
            child_state = states.get(f'state:sub-abilities:{child.id}', {})
            row['children'].append({**as_dict(child, CATALOG['sub-abilities'][1]), **child_state,
                'level': 2, 'level_name': '二级 · 子能力',
                'parent_name': parent.name, 'parent_code': state.get('code'),
                'enabled': child_state.get('enabled', True),
                'effective_enabled': child_state.get('enabled', True) and row['enabled']})
        result.append(row)
    return {'items':result,'active_dimensions':sum(row['enabled'] for row in result)}


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
