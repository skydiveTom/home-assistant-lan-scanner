"""Network scanning logic for LAN Scanner."""

from __future__ import annotations

import asyncio
import ipaddress
import logging
from datetime import datetime, timezone

import aiooui
from aiodiscover import DiscoverHosts

from .const import (
    COMMON_PORTS,
    PORT_SCAN_CONCURRENCY,
    PORT_SCAN_TIMEOUT,
    RTSP_PORT,
    RTSP_PORTS,
    RTSP_SCAN_TIMEOUT,
)
from .models import NetworkDevice, ScanResult

_LOGGER = logging.getLogger(__name__)


def normalize_mac(mac: str) -> str:
    """Normalize a MAC address to lowercase colon-separated format."""
    cleaned = mac.replace("-", ":").replace(".", "").lower()
    if len(cleaned) == 12 and ":" not in mac:
        return ":".join(cleaned[i : i + 2] for i in range(0, 12, 2))
    return cleaned


def ip_to_pseudo_mac(ip: str) -> str:
    """Create a stable identifier for devices without a MAC address."""
    return f"ip-{ip.replace('.', '-')}"


def is_pseudo_mac(mac: str) -> bool:
    """Return True if the identifier is IP-based rather than a real MAC."""
    return mac.startswith("ip-")


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
    if is_pseudo_mac(mac):
        if vendor:
            return f"{vendor} {ip}"
        return f"Device {ip}"
    vendor_label = vendor or "Unknown"
    return f"{vendor_label} {mac[-8:]}"


class NetworkScanner:
    """Scans the local network using ARP discovery and optional port scanning."""

    def __init__(
        self,
        local_ip: str | None,
        subnet: str | None,
        scan_ports: bool,
        extra_ips: list[str] | None = None,
    ) -> None:
        """Initialize the scanner."""
        self._local_ip = local_ip
        self._subnet = subnet
        self._scan_ports = scan_ports
        self._extra_ips = extra_ips or []

    async def async_scan(self, mac_names: dict[str, str]) -> ScanResult:
        """Perform a full network scan."""
        result = ScanResult(scanned_at=datetime.now(timezone.utc))
        hosts = await self._async_discover_hosts()
        arp_by_ip: dict[str, dict] = {
            host["ip"]: host for host in hosts if host.get("ip")
        }

        subnet_ips = self._get_subnet_hosts()
        scan_targets = set(subnet_ips) | set(arp_by_ip) | set(self._extra_ips)

        port_results: dict[str, list[int]] = {}
        if self._scan_ports and scan_targets:
            rtsp_hits = await self._async_scan_rtsp_ports(scan_targets)
            scan_targets |= rtsp_hits
            port_results = await self._async_scan_ports(sorted(scan_targets))
            _LOGGER.info(
                "Port scan: %d hosts checked, %d with open ports, %d RTSP",
                len(scan_targets),
                len(port_results),
                sum(1 for ports in port_results.values() if RTSP_PORT in ports),
            )

        processed_ips: set[str] = set()

        for host in hosts:
            ip = host.get("ip")
            raw_mac = host.get("macaddress")
            if not ip or not raw_mac:
                continue

            processed_ips.add(ip)
            mac = normalize_mac(raw_mac)
            result.devices[mac] = self._build_device(
                mac=mac,
                ip=ip,
                hostname=host.get("hostname"),
                open_ports=port_results.get(ip, []),
                mac_names=mac_names,
                scanned_at=result.scanned_at,
            )

        for ip, open_ports in port_results.items():
            if ip in processed_ips:
                continue

            mac = await self._async_resolve_mac(ip) or ip_to_pseudo_mac(ip)
            hostname = await self._async_resolve_hostname(ip)
            result.devices[mac] = self._build_device(
                mac=mac,
                ip=ip,
                hostname=hostname,
                open_ports=open_ports,
                mac_names=mac_names,
                scanned_at=result.scanned_at,
            )

        for ip in self._extra_ips:
            if ip in processed_ips or ip in port_results:
                continue
            if not self._scan_ports:
                continue
            open_ports = await self._async_scan_ports([ip])
            ports = open_ports.get(ip, [])
            if not ports:
                _LOGGER.debug("Extra IP %s has no open monitored ports", ip)
                continue
            mac = await self._async_resolve_mac(ip) or ip_to_pseudo_mac(ip)
            result.devices[mac] = self._build_device(
                mac=mac,
                ip=ip,
                hostname=await self._async_resolve_hostname(ip),
                open_ports=ports,
                mac_names=mac_names,
                scanned_at=result.scanned_at,
            )

        _LOGGER.info(
            "Scan complete: %d devices (subnet=%s, ARP=%d)",
            len(result.devices),
            self._subnet or "auto",
            len(arp_by_ip),
        )
        return result

    def _build_device(
        self,
        mac: str,
        ip: str,
        hostname: str | None,
        open_ports: list[int],
        mac_names: dict[str, str],
        scanned_at: datetime,
    ) -> NetworkDevice:
        """Build a NetworkDevice from scan data."""
        vendor = None if is_pseudo_mac(mac) else aiooui.get_vendor(mac)
        is_rtsp_camera_only = open_ports == [RTSP_PORT]
        has_rtsp = RTSP_PORT in open_ports

        return NetworkDevice(
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
            last_seen=scanned_at,
        )

    def _get_subnet_hosts(self) -> list[str]:
        """Return all host IPs in the configured subnet."""
        if not self._subnet:
            return []
        try:
            network = ipaddress.ip_network(self._subnet, strict=False)
            return [str(ip) for ip in network.hosts()]
        except ValueError:
            _LOGGER.warning("Invalid subnet configured: %s", self._subnet)
            return []

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

    async def _async_scan_rtsp_ports(self, ips: set[str]) -> set[str]:
        """Quickly scan RTSP ports across many hosts."""
        semaphore = asyncio.Semaphore(PORT_SCAN_CONCURRENCY)
        hits: set[str] = set()

        async def probe(ip: str) -> None:
            for port in RTSP_PORTS:
                if await self._async_is_port_open(
                    ip, port, semaphore, timeout=RTSP_SCAN_TIMEOUT
                ):
                    hits.add(ip)
                    return

        await asyncio.gather(*(probe(ip) for ip in ips))
        return hits

    async def _async_scan_ports(self, ips: list[str]) -> dict[str, list[int]]:
        """Scan common ports on all target hosts."""
        semaphore = asyncio.Semaphore(PORT_SCAN_CONCURRENCY)
        results: dict[str, list[int]] = {}

        async def scan_host(ip: str) -> None:
            open_ports: list[int] = []
            ports_to_check = list(COMMON_PORTS)
            if RTSP_PORT not in ports_to_check:
                ports_to_check.append(RTSP_PORT)
            for port in ports_to_check:
                timeout = RTSP_SCAN_TIMEOUT if port in RTSP_PORTS else PORT_SCAN_TIMEOUT
                if await self._async_is_port_open(ip, port, semaphore, timeout):
                    open_ports.append(port)
            if open_ports:
                results[ip] = sorted(set(open_ports))

        await asyncio.gather(*(scan_host(ip) for ip in ips))
        return results

    async def _async_is_port_open(
        self,
        ip: str,
        port: int,
        semaphore: asyncio.Semaphore,
        timeout: float = PORT_SCAN_TIMEOUT,
    ) -> bool:
        """Check if a TCP port is open on a host."""
        async with semaphore:
            try:
                _, writer = await asyncio.wait_for(
                    asyncio.open_connection(ip, port),
                    timeout=timeout,
                )
                writer.close()
                await writer.wait_closed()
                return True
            except (TimeoutError, OSError, asyncio.CancelledError):
                return False

    async def _async_resolve_mac(self, ip: str) -> str | None:
        """Try to resolve MAC address for an IP (uses ARP cache after probing)."""

        def lookup() -> str | None:
            try:
                from getmac import get_mac_address as getmac_lookup

                mac = getmac_lookup(ip=ip)
                if mac:
                    return normalize_mac(mac)
            except Exception as err:
                _LOGGER.debug("MAC lookup failed for %s: %s", ip, err)
            return None

        return await asyncio.get_running_loop().run_in_executor(None, lookup)

    async def _async_resolve_hostname(self, ip: str) -> str | None:
        """Resolve hostname for an IP address."""

        def lookup() -> str | None:
            try:
                import socket

                host, _, _ = socket.gethostbyaddr(ip)
                return host if host and host != ip else None
            except OSError:
                return None

        return await asyncio.get_running_loop().run_in_executor(None, lookup)
