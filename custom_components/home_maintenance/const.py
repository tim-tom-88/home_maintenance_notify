"""Constants for the Home Maintenance integration."""

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import config_validation as cv

VERSION = "1.6.0"
NAME = "Home Maintenance"
MANUFACTURER = "@TJPoorman"

DOMAIN = "home_maintenance"

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

PANEL_FILENAME = "panel/main.js"
PANEL_URL = "home-maintenance"
PANEL_API_PATH = "/home_maintenance_static"
PANEL_API_URL = PANEL_API_PATH + "/main.js"
PANEL_TITLE = NAME
PANEL_ICON = "mdi:hammer-wrench"
PANEL_NAME = "home-maintenance-panel"

DEVICE_KEY = "home_maintenance_hub"

SERVICE_RESET = "reset_last_performed"
SERVICE_COMPLETE_TASK = "complete_task"
SERVICE_SNOOZE_TASK = "snooze_task"
SERVICE_SEND_TASK_NOTIFICATION = "send_task_notification"
NOTIFICATION_ACTION_COMPLETE = "HOME_MAINTENANCE_COMPLETE"
NOTIFICATION_ACTION_SNOOZE = "HOME_MAINTENANCE_SNOOZE"
DEFAULT_SNOOZE_DAYS = 1

TASK_DEFAULTS = {
    "notifications_enabled": False,
    "notification_url": None,
    "notify_when": "due_and_overdue",
    "notify_days_before_due": None,
    "notification_target": None,
    "snooze_until": None,
    "last_notification_kind": None,
    "last_notification_date": None,
}

SERVICE_RESET_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Optional("performed_date"): cv.string,
    }
)
TASK_REFERENCE_SCHEMA = vol.Schema(
    vol.Any(
        {
            vol.Required("task_id"): cv.string,
            vol.Optional("entity_id"): cv.entity_id,
        },
        {
            vol.Required("entity_id"): cv.entity_id,
            vol.Optional("task_id"): cv.string,
        },
    )
)
SERVICE_COMPLETE_TASK_SCHEMA = vol.Schema(
    vol.Any(
        {
            vol.Required("task_id"): cv.string,
            vol.Optional("entity_id"): cv.entity_id,
            vol.Optional("performed_date"): cv.string,
        },
        {
            vol.Required("entity_id"): cv.entity_id,
            vol.Optional("task_id"): cv.string,
            vol.Optional("performed_date"): cv.string,
        },
    )
)
SERVICE_SNOOZE_TASK_SCHEMA = vol.Schema(
    vol.Any(
        {
            vol.Required("task_id"): cv.string,
            vol.Optional("entity_id"): cv.entity_id,
            vol.Optional("days", default=DEFAULT_SNOOZE_DAYS): vol.All(
                vol.Coerce(int), vol.Range(min=1)
            ),
        },
        {
            vol.Required("entity_id"): cv.entity_id,
            vol.Optional("task_id"): cv.string,
            vol.Optional("days", default=DEFAULT_SNOOZE_DAYS): vol.All(
                vol.Coerce(int), vol.Range(min=1)
            ),
        },
    )
)
SERVICE_SEND_TASK_NOTIFICATION_SCHEMA = TASK_REFERENCE_SCHEMA

CONFIG_STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional("admin_only", default=True): cv.boolean,
        vol.Optional("sidebar_title", default=PANEL_TITLE): cv.string,
    }
)


def get_options_schema(config_entry: ConfigEntry) -> vol.Schema:
    """Return the schema for get options."""
    return vol.Schema(
        {
            vol.Optional(
                "admin_only",
                default=config_entry.options.get(
                    "admin_only", config_entry.data.get("admin_only", True)
                ),
            ): cv.boolean,
            vol.Optional(
                "sidebar_title",
                default=config_entry.options.get(
                    "sidebar_title",
                    config_entry.data.get("sidebar_title", PANEL_TITLE),
                ),
            ): cv.string,
        }
    )
