from datetime import timezone
from zoneinfo import ZoneInfo


def utc_boundary(value):
    """API date filters: explicit offset preferred, campus local if omitted."""
    if value is None:
        return None
    if value.tzinfo is None:
        value=value.replace(tzinfo=ZoneInfo('Asia/Shanghai'))
    return value.astimezone(timezone.utc).replace(tzinfo=None)
