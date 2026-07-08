"""Options flow for LAN Scanner."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_MAC_NAMES,
    CONF_SCAN_INTERVAL,
    CONF_SCAN_PORTS,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SCAN_PORTS,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)
from .scanner import normalize_mac


class LanScannerOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for LAN Scanner."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show options menu."""
        if user_input is not None:
            next_step = user_input["menu"]
            if next_step == "settings":
                return await self.async_step_settings()
            return await self.async_step_mac_names()

        return self.async_show_menu(
            step_id="init",
            menu_options={
                "settings": "Scan settings",
                "mac_names": "Device names (MAC)",
            },
        )

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle scan settings."""
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={
                    **self._config_entry.options,
                    CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
                    CONF_SCAN_PORTS: user_input[CONF_SCAN_PORTS],
                },
            )

        options = self._config_entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL)),
                vol.Required(
                    CONF_SCAN_PORTS,
                    default=options.get(CONF_SCAN_PORTS, DEFAULT_SCAN_PORTS),
                ): bool,
            }
        )

        return self.async_show_form(step_id="settings", data_schema=schema)

    async def async_step_mac_names(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage MAC address friendly names."""
        errors: dict[str, str] = {}
        mac_names: dict[str, str] = dict(
            self._config_entry.options.get(CONF_MAC_NAMES, {})
        )

        if user_input is not None:
            action = user_input.get("action", "add")
            if action == "add":
                try:
                    mac = normalize_mac(user_input["mac"])
                    name = user_input["name"].strip()
                    if not name:
                        errors["name"] = "name_required"
                    else:
                        mac_names[mac] = name
                        return self.async_create_entry(
                            title="",
                            data={
                                **self._config_entry.options,
                                CONF_MAC_NAMES: mac_names,
                            },
                        )
                except (ValueError, TypeError):
                    errors["mac"] = "invalid_mac"
            elif action == "remove" and user_input.get("mac_to_remove"):
                mac = normalize_mac(user_input["mac_to_remove"])
                mac_names.pop(mac, None)
                return self.async_create_entry(
                    title="",
                    data={
                        **self._config_entry.options,
                        CONF_MAC_NAMES: mac_names,
                    },
                )

        coordinator = self.hass.data.get(DOMAIN, {}).get(
            self._config_entry.entry_id
        )
        known_macs: list[str] = []
        if coordinator and coordinator.devices:
            known_macs = sorted(coordinator.devices.keys())

        remove_options = {mac: mac_names.get(mac, mac) for mac in mac_names}

        schema_dict: dict = {
            vol.Required("action", default="add"): vol.In(
                {"add": "Add / update name", "remove": "Remove name"}
            ),
            vol.Optional("mac"): str,
            vol.Optional("name"): str,
        }
        if remove_options:
            schema_dict[vol.Optional("mac_to_remove")] = vol.In(remove_options)

        schema = vol.Schema(schema_dict)

        saved_names = "\n".join(
            f"{mac} → {name}" for mac, name in mac_names.items()
        ) or "No custom names saved."
        known_devices = "\n".join(
            f"{mac} → {mac_names.get(mac, '(unnamed)')}"
            for mac in (known_macs or list(mac_names.keys()))
        ) or "No devices discovered yet."

        return self.async_show_form(
            step_id="mac_names",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "known_devices": known_devices,
                "saved_names": saved_names,
            },
        )
