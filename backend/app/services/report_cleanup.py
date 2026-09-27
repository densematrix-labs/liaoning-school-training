"""Admin-only, recoverable cleanup for legacy generic diagnostic reports."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.report import DiagnosticReport, LEGACY_GENERIC_REPORT_TITLES
from app.models.student import Student
from app.models.workflow import ReportTask


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


async def legacy_report_cleanup_plan(db: AsyncSession) -> dict:
    rows = list((await db.execute(
        select(DiagnosticReport, Student.name)
        .join(Student, Student.id == DiagnosticReport.student_id)
        .where(DiagnosticReport.title.in_(LEGACY_GENERIC_REPORT_TITLES))
        .order_by(DiagnosticReport.generated_at.desc(), DiagnosticReport.id.desc())
    )).all())
    latest_report = (await db.execute(
        select(DiagnosticReport)
        .order_by(DiagnosticReport.generated_at.desc(), DiagnosticReport.id.desc())
        .limit(1)
    )).scalar_one_or_none()
    preserved_id = (
        latest_report.id
        if latest_report and (latest_report.title or "").strip() in LEGACY_GENERIC_REPORT_TITLES
        else None
    )
    records = [
        {
            "id": report.id,
            "student_id": report.student_id,
            "student_name": student_name,
            "title": report.title,
            "created_at": _iso(report.generated_at),
            "preserved_as_latest": report.id == preserved_id,
        }
        for report, student_name in rows
    ]
    new_format_count = (await db.execute(
        select(func.count())
        .select_from(DiagnosticReport)
        .where(DiagnosticReport.title.not_in(LEGACY_GENERIC_REPORT_TITLES))
    )).scalar() or 0
    latest_new = (await db.execute(
        select(DiagnosticReport, Student.name)
        .join(Student, Student.id == DiagnosticReport.student_id)
        .where(DiagnosticReport.title.not_in(LEGACY_GENERIC_REPORT_TITLES))
        .order_by(DiagnosticReport.generated_at.desc(), DiagnosticReport.id.desc())
        .limit(1)
    )).first()
    return {
        "matched_count": len(records),
        "delete_count": sum(not item["preserved_as_latest"] for item in records),
        "preserved_count": sum(item["preserved_as_latest"] for item in records),
        "records": records,
        "new_format_count": new_format_count,
        "latest_new_format": (
            {
                "id": latest_new[0].id,
                "student_id": latest_new[0].student_id,
                "student_name": latest_new[1],
                "title": latest_new[0].title,
                "created_at": _iso(latest_new[0].generated_at),
            }
            if latest_new
            else None
        ),
    }


def _full_report_json(report: DiagnosticReport) -> dict:
    return {
        "id": report.id,
        "student_id": report.student_id,
        "report_type": report.report_type.value,
        "title": report.title,
        "content": report.content,
        "content_html": report.content_html,
        "pdf_url": report.pdf_url,
        "score_id": report.score_id,
        "generated_at": _iso(report.generated_at),
    }


async def execute_legacy_report_cleanup(db: AsyncSession) -> dict:
    plan = await legacy_report_cleanup_plan(db)
    delete_ids = [item["id"] for item in plan["records"] if not item["preserved_as_latest"]]
    if not delete_ids:
        return {**plan, "deleted_count": 0, "backup": None, "remaining_legacy_count": plan["matched_count"]}

    reports = list((await db.execute(
        select(DiagnosticReport)
        .where(DiagnosticReport.id.in_(delete_ids))
        .order_by(DiagnosticReport.generated_at, DiagnosticReport.id)
    )).scalars().all())
    linked_tasks = list((await db.execute(
        select(ReportTask.id, ReportTask.report_id).where(ReportTask.report_id.in_(delete_ids))
    )).all())

    backup_dir = Path(settings.REPORT_BACKUP_DIR).expanduser().resolve()
    backup_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(backup_dir, 0o700)
    created_at = datetime.now(timezone.utc)
    filename = f"legacy-diagnostic-reports-{created_at.strftime('%Y%m%dT%H%M%SZ')}.json"
    target = backup_dir / filename
    temporary = target.with_suffix(".json.tmp")
    payload = {
        "format": "liaoning-school-training/diagnostic-report-backup-v1",
        "created_at": created_at.isoformat(),
        "reason": "精确清理历史泛化标题诊断报告",
        "legacy_titles": sorted(LEGACY_GENERIC_REPORT_TITLES),
        "reports": [_full_report_json(report) for report in reports],
        "linked_report_tasks": [
            {"task_id": task_id, "report_id": report_id} for task_id, report_id in linked_tasks
        ],
    }
    with temporary.open("x", encoding="utf-8") as file:
        os.chmod(temporary, 0o600)
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.flush()
        os.fsync(file.fileno())
    os.replace(temporary, target)
    os.chmod(target, 0o600)
    backup_sha256 = hashlib.sha256(target.read_bytes()).hexdigest()

    if linked_tasks:
        await db.execute(
            update(ReportTask).where(ReportTask.report_id.in_(delete_ids)).values(report_id=None)
        )
    await db.execute(delete(DiagnosticReport).where(DiagnosticReport.id.in_(delete_ids)))
    await db.commit()

    remaining = (await db.execute(
        select(func.count())
        .select_from(DiagnosticReport)
        .where(DiagnosticReport.title.in_(LEGACY_GENERIC_REPORT_TITLES))
    )).scalar() or 0
    new_format_count = (await db.execute(
        select(func.count())
        .select_from(DiagnosticReport)
        .where(DiagnosticReport.title.not_in(LEGACY_GENERIC_REPORT_TITLES))
    )).scalar() or 0
    return {
        **plan,
        "deleted_count": len(delete_ids),
        "backup": {
            "filename": filename,
            "created_at": created_at.isoformat(),
            "record_count": len(reports),
            "sha256": backup_sha256,
        },
        "remaining_legacy_count": remaining,
        "new_format_count": new_format_count,
    }
