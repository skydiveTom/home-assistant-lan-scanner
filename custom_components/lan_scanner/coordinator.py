"""Data update coordinator for LAN Scanner."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING, Any, Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_EXTRA_IPS,
    CONF_LOCAL_IP,
    CONF_MAC_NAMES,
    CONF_SCAN_INTERVAL,
    CONF_SCAN_PORTS,
    CONF_SUBNET,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SCAN_PORTS,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)
from .models import NetworkDevice, ScanResult
from .scanner import NetworkScanner

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)


class LanScannerCoordinator(DataUpdateCoordinator[ScanResult]):
    """Coordinator that periodically scans the local network."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.config_entry = entry
        options = entry.options
        scan_interval = options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        scan_interval = max(scan_interval, MIN_SCAN_INTERVAL)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

        self._new_device_callbacks: list[Callable[[str, NetworkDevice], None]] = []
        self._known_macs: set[str] = set()

    @property
    def mac_names(self) -> dict[str, str]:
        """Return MAC to friendly name mappings."""
        return dict(self.config_entry.options.get(CONF_MAC_NAMES, {}))

    @property
    def devices(self) -> dict[str, NetworkDevice]:
        """Return discovered devices from the latest scan."""
        if self.data is None:
            return {}
        return self.data.devices

    def register_new_device_callback(
        self, callback_func: Callable[[str, NetworkDevice], None]
    ) -> None:
        """Register a callback for newly discovered devices."""
        self._new_device_callbacks.append(callback_func)

    async def _async_update_data(self) -> ScanResult:
        """Fetch data from the network scanner."""
        options = self.config_entry.options
        local_ip = self.config_entry.data.get(CONF_LOCAL_IP) or None
        subnet = self.config_entry.data.get(CONF_SUBNET) or None
        scan_ports = options.get(CONF_SCAN_PORTS, DEFAULT_SCAN_PORTS)
        extra_ips = options.get(CONF_EXTRA_IPS, [])

        scanner = NetworkScanner(
            local_ip=local_ip,
            subnet=subnet,
            scan_ports=scan_ports,
            extra_ips=extra_ips,
        )

        try:
            result = await scanner.async_scan(self.mac_names)
        except Exception as err:
            raise UpdateFailed(f"Network scan failed: {err}") from err

        self._notify_new_devices(result.devices)
        self._async_update_device_registry(result.devices)
        return result

    @callback
    def _async_update_device_registry(
        self, devices: dict[str, NetworkDevice]
    ) -> None:
        """Update device registry entries with current names."""
        from .helpers import async_update_device_name

        for device in devices.values():
            async_update_device_name(self.hass, device)

    def _notify_new_devices(self, devices: dict[str, NetworkDevice]) -> None:
        """Notify listeners about newly discovered devices."""
        for mac, device in devices.items():
            if mac not in self._known_macs:
                self._known_macs.add(mac)
                for callback_func in self._new_device_callbacks:
                    callback_func(mac, device)

    @callback
    def async_set_device_name(self, mac: str, name: str) -> None:
        """Set a friendly name for a device by MAC address."""
        mac_names = dict(self.mac_names)
        mac_names[mac] = name
        self.hass.config_entries.async_update_entry(
            self.config_entry,
            options={**self.config_entry.options, CONF_MAC_NAMES: mac_names},
        )

    def update_scan_interval(self) -> None:
        """Update the coordinator scan interval from config options."""
        scan_interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        scan_interval = max(scan_interval, MIN_SCAN_INTERVAL)
        self.update_interval = timedelta(seconds=scan_interval)
