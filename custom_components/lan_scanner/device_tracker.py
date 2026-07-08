"""Device tracker platform for LAN Scanner."""

from __future__ import annotations

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_TRACK_DEVICES, DOMAIN
from .coordinator import LanScannerCoordinator
from .helpers import LanScannerDeviceEntity
from .models import NetworkDevice


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up LAN Scanner device trackers."""
    if not entry.data.get(CONF_TRACK_DEVICES, True):
        return

    coordinator: LanScannerCoordinator = entry.runtime_data

    entities: list[TrackerEntity] = []
    for mac, device in coordinator.devices.items():
        entities.append(LanScannerDeviceTracker(coordinator, device))

    @callback
    def _async_add_device(mac: str, device: NetworkDevice) -> None:
        async_add_entities([LanScannerDeviceTracker(coordinator, device)])

    coordinator.register_new_device_callback(_async_add_device)
    async_add_entities(entities)


class LanScannerDeviceTracker(LanScannerDeviceEntity, TrackerEntity):
    """Device tracker for a discovered network device."""

    _attr_translation_key = "presence"
    _attr_source_type = SourceType.ROUTER

    def __init__(
        self,
        coordinator: LanScannerCoordinator,
        device: NetworkDevice,
    ) -> None:
        """Initialize the device tracker."""
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{device.mac}_tracker"
        self._attr_name = None

    @property
    def is_connected(self) -> bool:
        """Return True if the device is currently on the network."""
        return self.device is not None

    @property
    def ip_address(self) -> str | None:
        """Return the device IP address."""
        if dev := self.device:
            return dev.ip
        return None

    @property
    def mac_address(self) -> str:
        """Return the device MAC address."""
        return self._mac

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional tracker attributes."""
        if dev := self.device:
            return {
                "hostname": dev.hostname,
                "vendor": dev.vendor,
                "open_ports": dev.open_ports,
                "is_camera": dev.is_camera,
                "has_rtsp": dev.has_rtsp,
                "is_rtsp_camera_only": dev.is_rtsp_camera_only,
            }
        return {}
