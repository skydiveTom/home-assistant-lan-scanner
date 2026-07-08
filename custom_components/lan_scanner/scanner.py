"""Network scanning logic for LAN Scanner."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

import aiooui
from aiodiscover import DiscoverHosts

from .const import COMMON_PORTS, PORT_SCAN_CONCURRENCY, PORT_SCAN_TIMEOUT
from .models import NetworkDevice, ScanResult

_LOGGER = logging.getLogger(__name__)


def normalize_mac(mac: str) -> str:
    """Normalize a MAC address to lowercase colon-separated format."""
    cleaned = mac.replace("-", ":").replace(".", "").lower()
    if len(cleaned) == 12 and ":" not in mac:
        return ":".join(cleaned[i : i + 2] for i in range(0, 12, 2))
    return cleaned


def resolve_device_name(
    mac: str,
    hostname: str | None,
    vendor: str | None,
    ip: str,
    mac_names: dict[str, str],
) -> str:
    """Resolve the best display name for a device."""
    if mac in mac_names:
        return mac_names[mac]
    if hostname and hostname != ip:
        return hostname
    vendor_label = vendor or "Unknown"
    return f"{vendor_label} {mac[-8:]}"


class NetworkScanner:
    """Scans the local network using ARP discovery and optional port scanning."""

    def __init__(
        self,
        local_ip: str | None,
        scan_ports: bool,
    ) -> None:
        """Initialize the scanner."""
        self._local_ip = local_ip
        self._scan_ports = scan_ports

    async def async_scan(self, mac_names: dict[str, str]) -> ScanResult:
        """Perform a full network scan."""
        result = ScanResult(scanned_at=datetime.now(timezone.utc))
        hosts = await self._async_discover_hosts()

        if self._scan_ports and hosts:
            port_results = await self._async_scan_ports(
                [host["ip"] for host in hosts if host.get("ip")]
            )
        else:
            port_results = {}

        for host in hosts:
            ip = host.get("ip")
            raw_mac = host.get("macaddress")
            if not ip or not raw_mac:
                continue

            mac = normalize_mac(raw_mac)
            hostname = host.get("hostname")
            vendor = aiooui.get_vendor(mac)
            open_ports = port_results.get(ip, [])
            is_rtsp_camera_only = open_ports == [554]
            has_rtsp = 554 in open_ports

            result.devices[mac] = NetworkDevice(
                mac=mac,
                ip=ip,
                hostname=hostname,
                vendor=vendor,
                friendly_name=resolve_device_name(
                    mac, hostname, vendor, ip, mac_names
                ),
                open_ports=open_ports,
                is_rtsp_camera_only=is_rtsp_camera_only,
                has_rtsp=has_rtsp,
                last_seen=result.scanned_at,
            )

        _LOGGER.debug("Scan found %d devices", len(result.devices))
        return result

    async def _async_discover_hosts(self) -> list[dict]:
        """Discover hosts on the network via ARP."""
        try:
            kwargs: dict = {}
            if self._local_ip:
                kwargs["local_ip"] = self._local_ip
            async with DiscoverHosts(**kwargs) as discover:
                hosts = await discover.async_discover()
            return hosts or []
        except Exception as err:
            _LOGGER.error("ARP discovery failed: %s", err)
            return []

    async def _async_scan_ports(self, ips: list[str]) -> dict[str, list[int]]:
        """Scan common ports on all discovered hosts."""
        semaphore = asyncio.Semaphore(PORT_SCAN_CONCURRENCY)
        results: dict[str, list[int]] = {}

        async def scan_host(ip: str) -> None:
            open_ports: list[int] = []
            for port in COMMON_PORTS:
                if await self._async_is_port_open(ip, port, semaphore):
                    open_ports.append(port)
            if open_ports:
                results[ip] = sorted(open_ports)

        await asyncio.gather(*(scan_host(ip) for ip in ips))
        return results

    async def _async_is_port_open(
        self, ip: str, port: int, semaphore: asyncio.Semaphore
    ) -> bool:
        """Check if a TCP port is open on a host."""
        async with semaphore:
            try:
                _, writer = await asyncio.wait_for(
                    asyncio.open_connection(ip, port),
                    timeout=PORT_SCAN_TIMEOUT,
                )
                writer.close()
                await writer.wait_closed()
                return True
            except (TimeoutError, OSError, asyncio.CancelledError):
                return False
