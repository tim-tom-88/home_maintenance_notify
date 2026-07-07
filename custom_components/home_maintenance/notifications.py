"""Notification helpers for Home Maintenance."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.util import dt as dt_util

from . import const
from .task_utils import get_task_due_details

_LOGGER = logging.getLogger(__name__)
MOBILE_APP_ACTION_EVENT = "mobile_app_notification_action"


class HomeMaintenanceNotificationManager:
    """Drive task notifications and mobile notification actions."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the notification manager."""
        self.hass = hass
        self._remove_store_listener = None
        self._remove_time_listener = None
        self._remove_action_listener = None

    async def async_setup(self) -> None:
        """Set up listeners."""
        store = self.hass.data[const.DOMAIN]["store"]
        self._remove_store_listener = store.async_add_listener(self._handle_task_change)
        self._remove_time_listener = async_track_time_change(
            self.hass, self._handle_task_change, hour=0, minute=5, second=0
        )
        self._remove_action_listener = self.hass.bus.async_listen(
            MOBILE_APP_ACTION_EVENT, self._handle_mobile_action
        )
        await self.async_process_notifications()

    async def async_unload(self) -> None:
        """Tear down listeners."""
        for remove_listener in (
            self._remove_store_listener,
            self._remove_time_listener,
            self._remove_action_listener,
        ):
            if remove_listener is not None:
                remove_listener()

    @callback
    def _handle_task_change(self, *_args) -> None:
        """Queue notification processing."""
        self.hass.async_create_task(self.async_process_notifications())

    async def async_process_notifications(self) -> None:
        """Send any notifications that are currently due."""
        store = self.hass.data[const.DOMAIN]["store"]
        for task in store.get_all():
            await self.async_send_notification(task["id"])

    async def async_send_notification(
        self, task_id: str, force: bool = False
    ) -> bool:
        """Send a task notification if applicable."""
        store = self.hass.data[const.DOMAIN]["store"]
        task = store.get(task_id)
        if not task:
            return False

        if not task.get("notifications_enabled") and not force:
            return False

        due_details = get_task_due_details(task)
        notification_kind = self._get_notification_kind(task, due_details)
        if notification_kind is None and not force:
            return False

        if due_details["is_snoozed"] and not force:
            return False

        today = dt_util.now().date().isoformat()
        if (
            not force
            and task.get("last_notification_date") == today
            and task.get("last_notification_kind") == notification_kind
        ):
            return False

        domain, service = self._resolve_notification_service(
            task.get("notification_target")
        )
        message = self._build_message(task, due_details, notification_kind)
        data = self._build_notification_payload(task)

        await self.hass.services.async_call(
            domain,
            service,
            {
                "title": task["title"],
                "message": message,
                "data": data,
            },
            blocking=True,
        )

        store.update_notification_state(
            task_id,
            {
                "last_notification_kind": notification_kind or "manual",
                "last_notification_date": today,
            },
        )
        return True

    async def async_snooze_task(self, task_id: str, days: int) -> None:
        """Snooze a task's notifications."""
        snooze_until = (
            dt_util.now().replace(hour=0, minute=0, second=0, microsecond=0)
            + timedelta(days=days)
        ).isoformat()
        store = self.hass.data[const.DOMAIN]["store"]
        store.update_notification_state(
            task_id,
            {
                "snooze_until": snooze_until,
                "last_notification_kind": None,
                "last_notification_date": None,
            },
        )

    async def _handle_mobile_action(self, event: Event) -> None:
        """Handle actionable notification events."""
        action = event.data.get("action")
        if not isinstance(action, str):
            return

        if action.startswith(f"{const.NOTIFICATION_ACTION_COMPLETE}::"):
            task_id = action.split("::", 1)[1]
            self.hass.data[const.DOMAIN]["store"].update_last_performed(task_id)
            return

        if action.startswith(f"{const.NOTIFICATION_ACTION_SNOOZE}::"):
            task_id = action.split("::", 1)[1]
            await self.async_snooze_task(task_id, const.DEFAULT_SNOOZE_DAYS)

    def _get_notification_kind(
        self, task: dict[str, Any], due_details: dict[str, Any]
    ) -> str | None:
        """Determine whether a notification should be emitted."""
        notify_days_before_due = task.get("notify_days_before_due")
        if (
            notify_days_before_due is not None
            and due_details["days_until_due"] == notify_days_before_due
        ):
            return "due_soon"

        notify_when = task.get("notify_when", "due_and_overdue")
        if due_details["status"] == "due" and notify_when in ("due", "due_and_overdue"):
            return "due"
        if due_details["status"] == "overdue" and notify_when in (
            "overdue",
            "due_and_overdue",
        ):
            return "overdue"
        return None

    def _resolve_notification_service(self, value: str | None) -> tuple[str, str]:
        """Resolve a service target into domain/service parts."""
        if not value:
            return ("notify", "notify")
        if "." in value:
            domain, service = value.split(".", 1)
            return (domain, service)
        return ("notify", value)

    def _build_message(
        self,
        task: dict[str, Any],
        due_details: dict[str, Any],
        notification_kind: str | None,
    ) -> str:
        """Build notification copy."""
        if notification_kind == "due_soon":
            return (
                f"{task['title']} is due in "
                f"{due_details['days_until_due']} day(s)."
            )
        if notification_kind == "overdue":
            return f"{task['title']} is overdue."
        if notification_kind == "manual":
            return f"{task['title']} notification sent."
        return f"{task['title']} is due today."

    def _build_notification_payload(self, task: dict[str, Any]) -> dict[str, Any]:
        """Build the mobile notification action payload."""
        actions = [
            {
                "action": f"{const.NOTIFICATION_ACTION_COMPLETE}::{task['id']}",
                "title": "Mark complete",
            },
            {
                "action": f"{const.NOTIFICATION_ACTION_SNOOZE}::{task['id']}",
                "title": "Snooze",
            },
        ]
        if task.get("notification_url"):
            actions.append(
                {
                    "action": "URI",
                    "title": "Open",
                    "uri": task["notification_url"],
                }
            )

        return {
            "tag": f"{const.DOMAIN}_{task['id']}",
            "actions": actions,
            "url": task.get("notification_url"),
        }
