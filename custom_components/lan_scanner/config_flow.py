"""Config flow for LAN Scanner."""

from __future__ import annotations

import ipaddress
import logging
import socket
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import (
    CONF_LOCAL_IP,
    CONF_MAC_NAMES,
    CONF_SCAN_INTERVAL,
    CONF_SCAN_PORTS,
    CONF_SUBNET,
    CONF_TRACK_DEVICES,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SCAN_PORTS,
    DEFAULT_TRACK_DEVICES,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)
from .options_flow import LanScannerOptionsFlowHandler

_LOGGER = logging.getLogger(__name__)


def _get_default_local_ip() -> str:
    """Detect the default local IPv4 address."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "192.168.1.1"
    finally:
        sock.close()


def _validate_subnet(subnet: str) -> str:
    """Validate and normalize a CIDR subnet string."""
    network = ipaddress.ip_network(subnet.strip(), strict=False)
    return str(network)


def _validate_local_ip(local_ip: str) -> str:
    """Validate a local IPv4 address."""
    return str(ipaddress.ip_address(local_ip.strip()))


class LanScannerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for LAN Scanner."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> LanScannerOptionsFlowHandler:
        """Get the options flow for this handler."""
        return LanScannerOptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                local_ip = _validate_local_ip(user_input[CONF_LOCAL_IP])
                subnet = _validate_subnet(
                    user_input.get(CONF_SUBNET)
                    or str(
                        ipaddress.ip_network(f"{local_ip}/24", strict=False)
                    )
                )
                scan_interval = int(user_input[CONF_SCAN_INTERVAL])
                if scan_interval < MIN_SCAN_INTERVAL:
                    errors[CONF_SCAN_INTERVAL] = "scan_interval_too_low"
                else:
                    return self.async_create_entry(
                        title=f"LAN Scanner ({local_ip})",
                        data={
                            CONF_LOCAL_IP: local_ip,
                            CONF_SUBNET: subnet,
                            CONF_TRACK_DEVICES: user_input[CONF_TRACK_DEVICES],
                        },
                        options={
                            CONF_SCAN_INTERVAL: scan_interval,
                            CONF_SCAN_PORTS: user_input[CONF_SCAN_PORTS],
                            CONF_MAC_NAMES: {},
                        },
                    )
            except ValueError:
                errors["base"] = "invalid_network"

        default_ip = _get_default_local_ip()
        try:
            default_subnet = str(
                ipaddress.ip_network(f"{default_ip}/24", strict=False)
            )
        except ValueError:
            default_subnet = "192.168.1.0/24"

        schema = vol.Schema(
            {
                vol.Required(CONF_LOCAL_IP, default=default_ip): str,
                vol.Optional(CONF_SUBNET, default=default_subnet): str,
                vol.Required(
                    CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                ): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL)),
                vol.Required(
                    CONF_SCAN_PORTS, default=DEFAULT_SCAN_PORTS
                ): bool,
                vol.Required(
                    CONF_TRACK_DEVICES, default=DEFAULT_TRACK_DEVICES
                ): bool,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )
