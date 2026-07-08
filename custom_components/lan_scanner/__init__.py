"""The LAN Scanner integration."""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, PLATFORMS, SERVICE_SCAN, SERVICE_SET_DEVICE_NAME
from .coordinator import LanScannerCoordinator
from .scanner import normalize_mac

_LOGGER = logging.getLogger(__name__)

type LanScannerConfigEntry = ConfigEntry[LanScannerCoordinator]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the LAN Scanner integration."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: LanScannerConfigEntry) -> bool:
    """Set up LAN Scanner from a config entry."""
    coordinator = LanScannerCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _async_register_services(hass)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: LanScannerConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: LanScannerConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


async def _async_update_listener(
    hass: HomeAssistant, entry: LanScannerConfigEntry
) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


def _async_register_services(hass: HomeAssistant) -> None:
    """Register integration services."""
    if hass.services.has_service(DOMAIN, SERVICE_SCAN):
        return

    async def handle_scan(call: ServiceCall) -> None:
        """Trigger an immediate network scan."""
        for coordinator in hass.data.get(DOMAIN, {}).values():
            await coordinator.async_request_refresh()

    async def handle_set_device_name(call: ServiceCall) -> None:
        """Assign a friendly name to a device by MAC address."""
        mac = normalize_mac(call.data["mac"])
        name = call.data["name"].strip()
        if not name:
            return

        for coordinator in hass.data.get(DOMAIN, {}).values():
            coordinator.async_set_device_name(mac, name)

        for coordinator in hass.data.get(DOMAIN, {}).values():
            await coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        SERVICE_SCAN,
        handle_scan,
        schema=vol.Schema({}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_DEVICE_NAME,
        handle_set_device_name,
        schema=vol.Schema(
            {
                vol.Required("mac"): cv.string,
                vol.Required("name"): cv.string,
            }
        ),
    )
