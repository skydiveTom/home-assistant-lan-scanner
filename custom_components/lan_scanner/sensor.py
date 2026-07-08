"""Sensor platform for LAN Scanner."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTR_DEVICES, DOMAIN
from .coordinator import LanScannerCoordinator
from .helpers import LanScannerDeviceEntity, async_update_device_name
from .models import NetworkDevice


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up LAN Scanner sensors."""
    coordinator: LanScannerCoordinator = entry.runtime_data

    entities: list[SensorEntity] = [LanScannerSummarySensor(coordinator, entry)]

    for device in coordinator.devices.values():
        entities.extend(_create_sensor_entities(coordinator, device))

    @callback
    def _async_add_device(mac: str, device: NetworkDevice) -> None:
        async_update_device_name(hass, device)
        async_add_entities(_create_sensor_entities(coordinator, device))

    coordinator.register_new_device_callback(_async_add_device)
    async_add_entities(entities)


def _create_sensor_entities(
    coordinator: LanScannerCoordinator,
    device: NetworkDevice,
) -> list[SensorEntity]:
    """Create sensor entities for a single device."""
    return [
        LanScannerDeviceIpSensor(coordinator, device),
        LanScannerDeviceLastSeenSensor(coordinator, device),
        LanScannerDeviceVendorSensor(coordinator, device),
    ]


class LanScannerSummarySensor(CoordinatorEntity[LanScannerCoordinator], SensorEntity):
    """Sensor showing the total number of discovered devices."""

    _attr_translation_key = "summary"
    _attr_icon = "mdi:lan"

    def __init__(
        self,
        coordinator: LanScannerCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the summary sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_summary"
        self._attr_name = "LAN Scanner"

    @property
    def native_value(self) -> int:
        """Return the number of discovered devices."""
        return len(self.coordinator.devices)

    @property
    def extra_state_attributes(self) -> dict:
        """Return all discovered devices as attributes."""
        return {
            ATTR_DEVICES: [
                device.as_dict() for device in self.coordinator.devices.values()
            ]
        }


class LanScannerDeviceIpSensor(LanScannerDeviceEntity, SensorEntity):
    """Sensor for a device's current IP address."""

    _attr_translation_key = "ip"
    _attr_icon = "mdi:ip-network"

    def __init__(
        self,
        coordinator: LanScannerCoordinator,
        device: NetworkDevice,
    ) -> None:
        """Initialize the IP sensor."""
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{device.mac}_ip"

    @property
    def native_value(self) -> str | None:
        """Return the device IP address."""
        if dev := self.device:
            return dev.ip
        return None


class LanScannerDeviceLastSeenSensor(LanScannerDeviceEntity, SensorEntity):
    """Sensor for when a device was last seen."""

    _attr_translation_key = "last_seen"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:clock-outline"

    def __init__(
        self,
        coordinator: LanScannerCoordinator,
        device: NetworkDevice,
    ) -> None:
        """Initialize the last seen sensor."""
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{device.mac}_last_seen"

    @property
    def native_value(self):
        """Return the last seen timestamp."""
        if dev := self.device:
            return dev.last_seen
        return None


class LanScannerDeviceVendorSensor(LanScannerDeviceEntity, SensorEntity):
    """Sensor for a device's vendor."""

    _attr_translation_key = "vendor"
    _attr_icon = "mdi:factory"

    def __init__(
        self,
        coordinator: LanScannerCoordinator,
        device: NetworkDevice,
    ) -> None:
        """Initialize the vendor sensor."""
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{device.mac}_vendor"

    @property
    def native_value(self) -> str | None:
        """Return the device vendor."""
        if dev := self.device:
            return dev.vendor
        return None

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional device attributes."""
        if dev := self.device:
            return {
                "hostname": dev.hostname,
                "open_ports": dev.open_ports,
                "is_camera": dev.is_camera,
                "has_rtsp": dev.has_rtsp,
                "is_rtsp_camera_only": dev.is_rtsp_camera_only,
            }
        return {}
