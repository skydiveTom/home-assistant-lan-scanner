"""Data models for LAN Scanner."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class NetworkDevice:
    """Represents a device discovered on the local network."""

    mac: str
    ip: str
    hostname: str | None
    vendor: str | None
    friendly_name: str
    open_ports: list[int] = field(default_factory=list)
    is_rtsp_camera_only: bool = False
    has_rtsp: bool = False
    last_seen: datetime | None = None

    def as_dict(self) -> dict:
        """Return a serializable representation for sensor attributes."""
        return {
            "mac": self.mac,
            "ip": self.ip,
            "hostname": self.hostname,
            "vendor": self.vendor,
            "friendly_name": self.friendly_name,
            "open_ports": self.open_ports,
            "is_rtsp_camera_only": self.is_rtsp_camera_only,
            "has_rtsp": self.has_rtsp,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
        }


@dataclass
class ScanResult:
    """Result of a full network scan."""

    devices: dict[str, NetworkDevice] = field(default_factory=dict)
    scanned_at: datetime | None = None
