"""Support for Home Maintenance platform."""

import logging
from datetime import datetime
from typing import cast

from homeassistant.components.binary_sensor import DOMAIN as PLATFORM
from homeassistant.components.sensor import DOMAIN as SENSOR_PLATFORM
from homeassistant.components.tag.const import EVENT_TAG_SCANNED
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, ServiceCall, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_registry import RegistryEntry  # noqa: TC002
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util

from . import const
from .notifications import HomeMaintenanceNotificationManager
from .panel import (
    async_register_panel,
    async_unregister_panel,
)
from .store import TaskStore
from .websocket import async_register_websockets

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = const.CONFIG_SCHEMA


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:  # noqa: ARG001
    """Track states and offer events for sensors."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the Home Maintenance config entry."""

    @callback
    def handle_tag_scanned_event(event: Event) -> None:
        """Handle when a tag is scanned."""
        tag_id = event.data.get("tag_id")  # Actually tag UUID

        store = hass.data[const.DOMAIN].get("store")
        tasks = store.get_by_tag_uuid(tag_id)
        if not tasks:
            return

        _LOGGER.debug("Tag scanned: %s", tag_id)

        for task in tasks:
            task_id = task["id"]
            store.update_last_performed(task_id)

    # Initialize and load stored tasks
    task_store = TaskStore(hass)
    await task_store.async_load()

    # Register Device
    device_registry = dr.async_get(hass)
    device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(const.DOMAIN, const.DEVICE_KEY)},
        name=const.NAME,
        model=const.NAME,
        sw_version=const.VERSION,
        manufacturer=const.MANUFACTURER,
    )

    hass.data.setdefault(const.DOMAIN, {})
    hass.data[const.DOMAIN] = {
        "add_entities": None,
        "entry_id": entry.entry_id,
        "device_id": device.id,
        "store": task_store,
        "entities": {},
    }

    await hass.config_entries.async_forward_entry_setups(
        entry, [PLATFORM, SENSOR_PLATFORM]
    )

    # Register the panel (frontend)
    await async_register_panel(hass, entry)

    # Websocket support
    await async_register_websockets(hass)

    # Register custom services
    register_services(hass)

    notification_manager = HomeMaintenanceNotificationManager(hass)
    await notification_manager.async_setup()
    hass.data[const.DOMAIN]["notification_manager"] = notification_manager

    # Register event listener for tag scanned
    unsub = hass.bus.async_listen(EVENT_TAG_SCANNED, handle_tag_scanned_event)
    hass.data[const.DOMAIN]["unsub_tag_scanned"] = unsub

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Home Maintenance config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, [PLATFORM, SENSOR_PLATFORM]
    )
    if not unload_ok:
        return False

    if "unsub_tag_scanned" in hass.data[const.DOMAIN]:
        hass.data[const.DOMAIN]["unsub_tag_scanned"]()
    if "notification_manager" in hass.data[const.DOMAIN]:
        await hass.data[const.DOMAIN]["notification_manager"].async_unload()

    async_unregister_panel(hass)
    hass.data.pop(const.DOMAIN, None)
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle reload of a config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:  # noqa: ARG001
    """Remove Home Maintenance config entry."""
    async_unregister_panel(hass)
    del hass.data[const.DOMAIN]


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:  # noqa: ARG001
    """Handle migration of config entry."""
    return True


@callback
def register_services(hass: HomeAssistant) -> None:
    """Register services used by home maintenance component."""

    def resolve_task_id(service_data: dict) -> str:
        """Resolve a task reference from task_id or entity_id."""
        if service_data.get("task_id"):
            return service_data["task_id"]

        entity_registry = er.async_get(hass)
        entry = cast("RegistryEntry", entity_registry.async_get(service_data["entity_id"]))
        if entry is None:
            msg = f"Entity not found: {service_data['entity_id']}"
            raise ValueError(msg)
        return entry.unique_id

    def parse_performed_date(performed_date_str: str | None) -> datetime | None:
        """Parse an optional performed date string."""
        if performed_date_str is None:
            return None

        parsed_date = dt_util.parse_date(performed_date_str)
        if parsed_date is None:
            msg = f"Could not parse performed_date: {performed_date_str}"
            raise ValueError(msg)
        combined_date = datetime.combine(parsed_date, datetime.min.time())
        return dt_util.as_local(combined_date)

    async def async_srv_reset(call: ServiceCall) -> None:
        task_id = resolve_task_id(call.data)
        store = hass.data[const.DOMAIN].get("store")
        store.update_last_performed(task_id, parse_performed_date(call.data.get("performed_date")))

    async def async_srv_complete_task(call: ServiceCall) -> None:
        task_id = resolve_task_id(call.data)
        store = hass.data[const.DOMAIN].get("store")
        store.update_last_performed(task_id, parse_performed_date(call.data.get("performed_date")))

    async def async_srv_snooze_task(call: ServiceCall) -> None:
        task_id = resolve_task_id(call.data)
        notification_manager = hass.data[const.DOMAIN]["notification_manager"]
        await notification_manager.async_snooze_task(task_id, call.data["days"])

    async def async_srv_send_task_notification(call: ServiceCall) -> None:
        task_id = resolve_task_id(call.data)
        notification_manager = hass.data[const.DOMAIN]["notification_manager"]
        await notification_manager.async_send_notification(task_id, force=True)

    if not hass.services.has_service(const.DOMAIN, const.SERVICE_RESET):
        hass.services.async_register(
            const.DOMAIN,
            const.SERVICE_RESET,
            async_srv_reset,
            schema=const.SERVICE_RESET_SCHEMA,
        )
    if not hass.services.has_service(const.DOMAIN, const.SERVICE_COMPLETE_TASK):
        hass.services.async_register(
            const.DOMAIN,
            const.SERVICE_COMPLETE_TASK,
            async_srv_complete_task,
            schema=const.SERVICE_COMPLETE_TASK_SCHEMA,
        )
    if not hass.services.has_service(const.DOMAIN, const.SERVICE_SNOOZE_TASK):
        hass.services.async_register(
            const.DOMAIN,
            const.SERVICE_SNOOZE_TASK,
            async_srv_snooze_task,
            schema=const.SERVICE_SNOOZE_TASK_SCHEMA,
        )
    if not hass.services.has_service(
        const.DOMAIN, const.SERVICE_SEND_TASK_NOTIFICATION
    ):
        hass.services.async_register(
            const.DOMAIN,
            const.SERVICE_SEND_TASK_NOTIFICATION,
            async_srv_send_task_notification,
            schema=const.SERVICE_SEND_TASK_NOTIFICATION_SCHEMA,
        )
