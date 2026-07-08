"""Constants for the LAN Scanner integration."""

DOMAIN = "lan_scanner"

CONF_SUBNET = "subnet"
CONF_LOCAL_IP = "local_ip"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_SCAN_PORTS = "scan_ports"
CONF_TRACK_DEVICES = "track_devices"
CONF_MAC_NAMES = "mac_names"
CONF_EXTRA_IPS = "extra_ips"

DEFAULT_SCAN_INTERVAL = 900
MIN_SCAN_INTERVAL = 300
DEFAULT_SCAN_PORTS = True
DEFAULT_TRACK_DEVICES = True

RTSP_PORT = 554
RTSP_PORTS = [554, 8554]
RTSP_SCAN_TIMEOUT = 2.0

COMMON_PORTS = [
    21,
    22,
    23,
    53,
    80,
    135,
    139,
    443,
    445,
    554,
    1883,
    8000,
    8080,
    8443,
    8554,
]

PORT_SCAN_TIMEOUT = 0.5
PORT_SCAN_CONCURRENCY = 50

PLATFORMS = ["sensor", "binary_sensor", "device_tracker"]

SERVICE_SCAN = "scan"
SERVICE_SET_DEVICE_NAME = "set_device_name"

ATTR_DEVICES = "devices"
ATTR_MAC = "mac"
ATTR_IP = "ip"
ATTR_HOSTNAME = "hostname"
ATTR_VENDOR = "vendor"
ATTR_OPEN_PORTS = "open_ports"
ATTR_HAS_RTSP = "has_rtsp"
ATTR_IS_RTSP_CAMERA_ONLY = "is_rtsp_camera_only"
ATTR_LAST_SEEN = "last_seen"
ATTR_FRIENDLY_NAME = "friendly_name"
