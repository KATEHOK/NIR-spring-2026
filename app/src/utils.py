from datetime import datetime, timezone


def datetime_utcnow(naive: bool = True) -> datetime:
    """Вернет now (aware или naive)"""
    now_aware = datetime.now(timezone.utc)
    return now_aware.replace(tzinfo=None) if naive else now_aware