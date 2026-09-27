"""Stable, user-facing references for internal business records."""

from datetime import datetime
import hashlib


def friendly_reference(prefix: str, occurred_at: datetime | None, internal_id: str | None) -> str:
    date_part = occurred_at.strftime("%Y%m%d") if occurred_at else "UNDATED"
    digest = hashlib.sha256((internal_id or "unknown").encode("utf-8")).hexdigest()[:6].upper()
    return f"{prefix}-{date_part}-{digest}"


def training_record_reference(occurred_at: datetime | None, internal_id: str | None) -> str:
    return friendly_reference("TR", occurred_at, internal_id)


def report_reference(occurred_at: datetime | None, internal_id: str | None) -> str:
    return friendly_reference("DR", occurred_at, internal_id)
