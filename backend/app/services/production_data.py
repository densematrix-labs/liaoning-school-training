"""Validated ingestion of real training records; never fabricates step outcomes."""
import asyncio
import hashlib
import json
import math
import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.training import TrainingProject, TrainingRecord, Score
from app.models.student import Student
from app.models.operations import SystemSetting
from app.models.workflow import MockSyncTask, MockSyncException, TaskStatus, EnvironmentTask
from app.services.audit import record_audit


def truth(value):
    if isinstance(value, bool):
        return value
    if value in (1, "1", "true", "TRUE", "pass", "passed", "通过"):
        return True
    if value in (0, "0", "false", "FALSE", "fail", "failed", "未通过"):
        return False
    raise ValueError("步骤状态必须是明确的通过/未通过")


def score_steps(project, raw):
    if isinstance(raw, str):
        raw = json.loads(raw)
    if isinstance(raw, list):
        ids = [str(item.get("step_id") or item.get("id") or "") for item in raw]
        if not all(ids) or len(ids) != len(set(ids)):
            raise ValueError("步骤标识缺失或重复")
        raw = dict(zip(ids, raw))
    if not isinstance(raw, dict):
        raise ValueError("steps 必须为逐步骤 JSON 对象或数组")
    steps = [step for step in (project.steps or []) if step.get("enabled", True)]
    expected = {str(step.get("id", "")) for step in steps}
    if not steps or "" in expected or len(expected) != len(steps):
        raise ValueError("评分规则没有有效且唯一的步骤")
    if set(raw) != expected:
        raise ValueError("源步骤与评分规则不一致；缺少或未知步骤不得生成成绩")
    details, total, maximum, failed = {}, 0.0, 0.0, set()
    for step in steps:
        sid = str(step["id"])
        source = raw[sid]
        source = source if isinstance(source, dict) else {"passed": source}
        passed = truth(source.get("passed"))
        weight = float(step.get("weight", 1))
        full = float(step.get("score", 0)) * weight
        fail = float(step.get("failed_score", 0)) * weight
        if not all(math.isfinite(x) for x in (full, fail, weight)) or full <= 0 or not 0 <= fail <= full:
            raise ValueError("评分规则分值/权重不合法")
        related = list((project.ability_mapping or {}).get(sid) or step.get("abilities") or [])
        value = full if passed else fail
        if not passed:
            failed.update(related)
        details[sid] = {
            "passed": passed, "source_status": "通过" if passed else "未通过",
            "score": round(value, 6), "max_score": round(full, 6), "deduction": round(full-value, 6),
            "reason": source.get("reason"), "related_abilities": related, "step_name": step.get("name", sid),
            "applied_rule": {"passed_score": full, "failed_score": fail, "weight": weight,
                             "rule_version": (project.scoring_rules or {}).get("version", 1)},
        }
        total += value
        maximum += full
    return details, round(total, 2), round(maximum, 2), sorted(failed)


async def setting(db, key, default=None):
    item = await db.get(SystemSetting, key)
    return item.value if item else default


async def put_setting(db, key, value, actor=None):
    item = await db.get(SystemSetting, key)
    if item:
        item.value, item.updated_by = value, actor
    else:
        db.add(SystemSetting(key=key, value=value, updated_by=actor))
    await db.flush()


async def enabled(db, kind, identifier):
    state = await setting(db, f"state:{kind}:{identifier}", {})
    return state.get("enabled", True)


class ProductionIngest:
    def __init__(self, db):
        self.db = db

    async def run(self, rows, *, actor_id, source="school", actor_name=None):
        rows = list(rows)
        task = MockSyncTask(id=str(uuid.uuid4()), status=TaskStatus.RUNNING, read_count=len(rows),
                            success_count=0, skipped_count=0, error_count=0, created_by=actor_id,
                            started_at=datetime.utcnow(), completed_at=None)
        self.db.add(task)
        await self.db.flush()
        affected = set()
        for index, raw in enumerate(rows, 2):
            try:
                async with self.db.begin_nested():
                    source_id = str(raw.get("source_record_id", "")).strip()
                    if not source_id or not raw.get("completed_at") or not raw.get("student_no") or not raw.get("project_code"):
                        raise ValueError("缺少源标识、完成时间、学号或项目编码")
                    timestamp = datetime.fromisoformat(str(raw["completed_at"]).replace("Z", "+00:00"))
                    # Naive source timestamps are Asia/Shanghai unless source mapping provides an offset.
                    if timestamp.tzinfo:
                        timestamp = timestamp.astimezone(timezone.utc).replace(tzinfo=None)
                    external_id = "src:" + hashlib.sha256(f"{source}:{source_id}".encode()).hexdigest()
                    previous = (await self.db.execute(select(TrainingRecord).where(TrainingRecord.external_id == external_id))).scalar_one_or_none()
                    fingerprint = hashlib.sha256(json.dumps(raw, sort_keys=True, default=str, ensure_ascii=False).encode()).hexdigest()
                    if previous:
                        evidence = await setting(self.db, f"source:{previous.id}", {})
                        if evidence.get("fingerprint") != fingerprint:
                            raise ValueError("源记录已存在但内容改变；需人工确认修订，不自动覆盖历史")
                        task.skipped_count += 1
                        continue
                    student = (await self.db.execute(select(Student).where(Student.student_no == str(raw["student_no"])))).scalar_one_or_none()
                    projects = list((await self.db.execute(select(TrainingProject))).scalars())
                    matched = [p for p in projects if str((p.scoring_rules or {}).get("code") or p.id) == str(raw["project_code"])]
                    if not student or len(matched) != 1:
                        raise ValueError("学号或唯一项目编码无法匹配")
                    project = matched[0]
                    if not await enabled(self.db, "students", student.id) or not await enabled(self.db, "projects", project.id):
                        raise ValueError("学生或实训项目已停用")
                    details, total, maximum, failed = score_steps(project, raw.get("steps"))
                    record = TrainingRecord(id=str(uuid.uuid4()), external_id=external_id, student_id=student.id,
                                            project_id=project.id, steps_data={k:{"passed":v["passed"],"reason":v["reason"]} for k,v in details.items()}, completed_at=timestamp)
                    self.db.add(record)
                    await self.db.flush()
                    score = Score(id=str(uuid.uuid4()), student_id=student.id, project_id=project.id, record_id=record.id,
                                  total_score=total, max_score=maximum, details=details, failed_abilities=failed, calculated_at=timestamp)
                    self.db.add(score)
                    await put_setting(self.db, f"source:{record.id}", {"source":source,"source_record_id":source_id,
                                      "batch_id":task.id,"fingerprint":fingerprint,"completed_at":str(raw["completed_at"]),
                                      "rules":project.scoring_rules,"mapping":project.ability_mapping,"steps":project.steps}, actor_id)
                    await self.db.flush()
                    if raw.get("environment_image") and project.lab_id:
                        from app.services.environment import EnvironmentCheckService
                        EnvironmentCheckService._validate_image_source(raw["environment_image"])
                        self.db.add(EnvironmentTask(id=str(uuid.uuid4()), student_id=student.id, lab_id=project.lab_id,
                                                    score_id=score.id, image_data=raw["environment_image"], status=TaskStatus.PENDING, created_by=actor_id))
                task.success_count += 1
                affected.add(student.id)
            except (ValueError, TypeError, KeyError, IntegrityError) as exc:
                task.error_count += 1
                self.db.add(MockSyncException(task_id=task.id, row_number=index, source_record_id=str(raw.get("source_record_id", ""))[:100],
                                             reason=str(exc)[:400] if not isinstance(exc, IntegrityError) else "唯一性或关联校验失败",
                                             raw_data=raw))
        task.status, task.completed_at = TaskStatus.COMPLETED, datetime.utcnow()
        await record_audit(self.db, actor_id=actor_id, actor_name=actor_name, action="real_data_sync", object_type="sync_task", object_id=task.id,
                           after={"source":source,"read":task.read_count,"success":task.success_count,"skipped":task.skipped_count,"errors":task.error_count})
        await self.db.commit()
        from app.services.ability import AbilityService
        for student_id in affected:
            try:
                await AbilityService(self.db).recalculate_profile(student_id)
            except Exception:
                await self.db.rollback()
                await put_setting(self.db, f"recalculate:{student_id}", {"status":"failed","batch_id":task.id})
                await self.db.commit()
        return task


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,63}", value):
        raise ValueError("数据库表名/字段名只能使用标准标识符")
    return "`" + value + "`"


def read_mysql(config, credentials, cursor=None):
    """Source table/view: one completed training session per row, JSON steps column.

    No arbitrary SQL is accepted. A school DBA may provide a read-only view for
    normalized vendor schemas. Cursor is (updated_at, immutable unique id).
    """
    import pymysql
    columns = config["fields"]
    required = {"source_record_id", "student_no", "project_code", "completed_at", "steps", "updated_at"}
    if not required.issubset(columns):
        raise ValueError("字段映射缺少必填字段")
    projection = ",".join(f"{identifier(columns[key])} AS {identifier(key)}" for key in sorted(required))
    table = identifier(config["table"])
    updated, unique = identifier(columns["updated_at"]), identifier(columns["source_record_id"])
    limit = min(max(int(config.get("batch_size", 1000)), 1), 5000)
    query, args = f"SELECT {projection} FROM {table}", []
    if cursor:
        query += f" WHERE ({updated} > %s OR ({updated} = %s AND {unique} > %s))"
        args += [cursor[0], cursor[0], cursor[1]]
    query += f" ORDER BY {updated}, {unique} LIMIT %s"
    args.append(limit)
    connection = pymysql.connect(host=credentials["host"], port=int(credentials.get("port",3306)),
        user=credentials["user"], password=credentials["password"], database=credentials["database"],
        connect_timeout=10, read_timeout=30, write_timeout=10, charset="utf8mb4", autocommit=False,
        cursorclass=pymysql.cursors.DictCursor, **({"ssl": {"ca":credentials["ssl_ca"]}} if credentials.get("ssl_ca") else {}))
    try:
        with connection.cursor() as db:
            db.execute("SET TRANSACTION READ ONLY")
            db.execute("START TRANSACTION WITH CONSISTENT SNAPSHOT")
            db.execute(query, args)
            rows = db.fetchall()
        connection.rollback()
        return [{key: value.isoformat() if isinstance(value, datetime) else value for key,value in row.items()} for row in rows]
    finally:
        connection.close()
