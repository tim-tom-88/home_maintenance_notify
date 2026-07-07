"""Support summary sensors for Home Maintenance."""

from __future__ import annotations

from collections.abc import Callable

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_change

from . import const
from .task_utils import get_task_due_details


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,  # noqa: ARG001
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Home Maintenance summary sensors."""
    device_id = hass.data[const.DOMAIN].get("device_id")
    async_add_entities(
        [
            HomeMaintenanceSummarySensor(hass, device_id, "due_count"),
            HomeMaintenanceSummarySensor(hass, device_id, "overdue_count"),
            HomeMaintenanceSummarySensor(hass, device_id, "next_due_task"),
        ]
    )


class HomeMaintenanceSummarySensor(SensorEntity):
    """Summary sensor backed by the task store."""

    def __init__(self, hass: HomeAssistant, device_id: str, sensor_type: str) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self._device_id = device_id
        self._sensor_type = sensor_type
        self._remove_listener: Callable[[], None] | None = None
        self._remove_time_listener: Callable[[], None] | None = None
        self._attr_unique_id = f"{const.DOMAIN}_{sensor_type}"
        self._attr_name = {
            "due_count": "Home Maintenance Due Tasks",
            "overdue_count": "Home Maintenance Overdue Tasks",
            "next_due_task": "Home Maintenance Next Due Task",
        }[sensor_type]
        self._update_state()

    @property
    def device_info(self) -> DeviceInfo | None:
        """Return device information for this sensor."""
        return DeviceInfo(
            identifiers={(const.DOMAIN, const.DEVICE_KEY)},
            name=const.NAME,
            model=const.NAME,
            sw_version=const.VERSION,
            manufacturer=const.MANUFACTURER,
        )

    def _update_state(self) -> None:
        """Recompute the current summary."""
        store = self.hass.data[const.DOMAIN]["store"]
        tasks = store.get_all()
        details = [(task, get_task_due_details(task)) for task in tasks]

        due_count = sum(1 for _, detail in details if detail["status"] == "due")
        overdue_count = sum(1 for _, detail in details if detail["status"] == "overdue")
        next_due_candidates = [
            (task, detail)
            for task, detail in details
            if detail["next_due"] is not None
        ]
        next_due_candidates.sort(key=lambda item: item[1]["next_due"])

        if self._sensor_type == "due_count":
            self._attr_native_value = due_count
            self._attr_extra_state_attributes = {"overdue_count": overdue_count}
            return

        if self._sensor_type == "overdue_count":
            self._attr_native_value = overdue_count
            self._attr_extra_state_attributes = {"due_count": due_count}
            return

        if not next_due_candidates:
            self._attr_native_value = "None"
            self._attr_extra_state_attributes = {}
            return

        task, detail = next_due_candidates[0]
        self._attr_native_value = task["title"]
        self._attr_extra_state_attributes = {
            "task_id": task["id"],
            "next_due": detail["next_due"].isoformat(),
            "days_until_due": detail["days_until_due"],
            "due_status": detail["status"],
        }

    async def async_added_to_hass(self) -> None:
        """Subscribe to store and daily refreshes."""
        store = self.hass.data[const.DOMAIN]["store"]
        self._remove_listener = store.async_add_listener(self._handle_store_update)
        self._remove_time_listener = async_track_time_change(
            self.hass, self._handle_store_update, hour=0, minute=5, second=0
        )

    async def async_will_remove_from_hass(self) -> None:
        """Remove subscriptions."""
        if self._remove_listener is not None:
            self._remove_listener()
        if self._remove_time_listener is not None:
            self._remove_time_listener()

    def _handle_store_update(self, *_args) -> None:
        """Handle state recalculation triggers."""
        self._update_state()
        self.async_schedule_update_ha_state()

    async def async_update(self) -> None:
        """Refresh summary state."""
        self._update_state()
