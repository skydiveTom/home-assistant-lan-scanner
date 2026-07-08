"""Shared helpers for LAN Scanner entities."""

from __future__ import annotations

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import LanScannerCoordinator
from .models import NetworkDevice
from .scanner import is_pseudo_mac


def get_device_info(device: NetworkDevice) -> DeviceInfo:
    """Build DeviceInfo for a discovered network device."""
    connections: set[tuple[str, str]] = set()
    if not is_pseudo_mac(device.mac):
        connections.add((dr.CONNECTION_NETWORK_MAC, device.mac))

    return DeviceInfo(
        identifiers={(DOMAIN, device.mac)},
        name=device.friendly_name,
        manufacturer=device.vendor,
        model="IP Camera" if device.is_camera else None,
        connections=connections or None,
    )


class LanScannerDeviceEntity(CoordinatorEntity[LanScannerCoordinator]):
    """Base class for per-device LAN Scanner entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: LanScannerCoordinator,
        device: NetworkDevice,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._mac = device.mac
        self._attr_device_info = get_device_info(device)

    @property
    def device(self) -> NetworkDevice | None:
        """Return the current device data."""
        return self.coordinator.devices.get(self._mac)

    @property
    def available(self) -> bool:
        """Return True if the device was seen in the last scan."""
        return self.device is not None


@callback
def async_update_device_name(
    hass: HomeAssistant,
    device: NetworkDevice,
) -> None:
    """Update the device registry name when friendly name changes."""
    device_registry = dr.async_get(hass)
    if entry := device_registry.async_get_device(
        identifiers={(DOMAIN, device.mac)}
    ):
        device_registry.async_update_device(
            entry.id,
            name=device.friendly_name,
            manufacturer=device.vendor,
        )
