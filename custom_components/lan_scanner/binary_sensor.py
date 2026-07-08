"""Binary sensor platform for LAN Scanner."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import LanScannerCoordinator
from .helpers import LanScannerDeviceEntity
from .models import NetworkDevice


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up LAN Scanner binary sensors."""
    coordinator: LanScannerCoordinator = entry.runtime_data

    entities: list[BinarySensorEntity] = [
        LanScannerCameraBinarySensor(coordinator, device)
        for device in coordinator.devices.values()
    ]

    @callback
    def _async_add_device(mac: str, device: NetworkDevice) -> None:
        async_add_entities([LanScannerCameraBinarySensor(coordinator, device)])

    coordinator.register_new_device_callback(_async_add_device)
    async_add_entities(entities)


class LanScannerCameraBinarySensor(LanScannerDeviceEntity, BinarySensorEntity):
    """Binary sensor indicating an RTSP/IP camera."""

    _attr_translation_key = "rtsp_camera"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_icon = "mdi:cctv"

    def __init__(
        self,
        coordinator: LanScannerCoordinator,
        device: NetworkDevice,
    ) -> None:
        """Initialize the camera binary sensor."""
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{device.mac}_camera"

    @property
    def is_on(self) -> bool | None:
        """Return True if the device is an IP camera (RTSP port open)."""
        if dev := self.device:
            return dev.is_camera
        return False

    @property
    def extra_state_attributes(self) -> dict:
        """Return camera-related attributes."""
        if dev := self.device:
            return {
                "has_rtsp": dev.has_rtsp,
                "is_rtsp_camera_only": dev.is_rtsp_camera_only,
                "open_ports": dev.open_ports,
            }
        return {}
