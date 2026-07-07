"""Helpers for task date and notification calculations."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from dateutil.relativedelta import relativedelta
from homeassistant.util import dt as dt_util

from .const import TASK_DEFAULTS


def normalize_task_data(task_data: dict[str, Any]) -> dict[str, Any]:
    """Return a task payload with additive defaults applied."""
    normalized = dict(TASK_DEFAULTS)
    normalized.update(task_data)

    notify_days_before_due = normalized.get("notify_days_before_due")
    if notify_days_before_due in ("", None):
        normalized["notify_days_before_due"] = None
    elif notify_days_before_due is not None:
        normalized["notify_days_before_due"] = int(notify_days_before_due)

    for key in (
        "notification_url",
        "notification_target",
        "tag_id",
        "icon",
        "snooze_until",
        "last_notification_kind",
        "last_notification_date",
    ):
        if normalized.get(key) == "":
            normalized[key] = None

    normalized["notifications_enabled"] = bool(
        normalized.get("notifications_enabled", False)
    )
    normalized["notify_when"] = normalized.get("notify_when") or "due_and_overdue"
    return normalized


def _as_local_start_of_day(value: datetime) -> datetime:
    """Normalize a datetime to local midnight."""
    return dt_util.as_local(value).replace(hour=0, minute=0, second=0, microsecond=0)


def parse_local_datetime(value: str | None) -> datetime | None:
    """Parse an ISO datetime and convert it to local time."""
    if not value:
        return None

    parsed = dt_util.parse_datetime(value)
    if parsed is None:
        return None

    if parsed.tzinfo is None:
        parsed = dt_util.as_utc(parsed)

    return dt_util.as_local(parsed)


def calculate_next_due(task: dict[str, Any]) -> datetime | None:
    """Calculate the next due datetime for a task."""
    last = parse_local_datetime(task.get("last_performed"))
    if last is None:
        return None

    interval_value = int(task["interval_value"])
    interval_type = task["interval_type"]
    last = _as_local_start_of_day(last)

    if interval_type == "days":
        return last + timedelta(days=interval_value)
    if interval_type == "weeks":
        return last + timedelta(weeks=interval_value)
    if interval_type == "months":
        return last + relativedelta(months=interval_value)

    return last


def get_task_due_details(
    task: dict[str, Any], now: datetime | None = None
) -> dict[str, Any]:
    """Return due metadata for a task."""
    now = now or dt_util.now()
    today = _as_local_start_of_day(now)
    next_due = calculate_next_due(task)
    snooze_until = parse_local_datetime(task.get("snooze_until"))
    is_snoozed = bool(snooze_until and _as_local_start_of_day(snooze_until) >= today)

    if next_due is None:
        return {
            "next_due": None,
            "days_until_due": None,
            "status": "unknown",
            "is_due": True,
            "is_overdue": False,
            "is_snoozed": is_snoozed,
            "snooze_until": snooze_until,
        }

    due_day = _as_local_start_of_day(next_due)
    delta_days = (due_day.date() - today.date()).days
    status = "not_due"
    if delta_days == 0:
        status = "due"
    elif delta_days < 0:
        status = "overdue"

    return {
        "next_due": due_day,
        "days_until_due": delta_days,
        "status": status,
        "is_due": delta_days <= 0,
        "is_overdue": delta_days < 0,
        "is_snoozed": is_snoozed,
        "snooze_until": snooze_until,
    }
