from datetime import UTC, datetime


def now():
    return datetime.now(UTC).replace(tzinfo=None)


def iso(value):
    return value.replace(tzinfo=UTC).isoformat(timespec='seconds') if value else None
