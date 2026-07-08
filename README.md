# LAN Scanner — Home Assistant Integration

Custom integration for Home Assistant that scans your local network, discovers devices (IP, MAC, hostname, vendor), detects WiFi cameras with only port 554 open (RTSP), and lets you assign persistent friendly names by MAC address.

## Features

- **ARP network scan** — discovers all active devices on your LAN
- **Device details** — IP, MAC, hostname, vendor (OUI lookup)
- **RTSP camera detection** — identifies cameras with only port 554 open
- **MAC-based naming** — assign custom names that persist across IP changes
- **Device trackers** — optional presence tracking per device
- **Summary sensor** — total device count with full device list in attributes
- **Polish UI** — full Polish translations included

## Requirements

- Home Assistant OS (recommended) or Home Assistant Container on Linux
- Network interface with ARP access (`NET_RAW` capability — available on HA OS)
- Local network in a single subnet (VLAN isolation may block discovery)

## Installation

### Via HACS (recommended)

1. Add this repository as a [custom repository](https://hacs.xyz/docs/faq/custom_repositories/) in HACS (category: **Integration**)
2. Install **LAN Scanner** — choose version **v1.0.0** if prompted
3. Restart Home Assistant
4. Go to **Settings → Devices & services → Add integration → LAN Scanner**

#### HACS troubleshooting

If you see `The version fd9393a ... can not be used with HACS`, HACS cached an old commit from before `hacs.json` was added. Fix:

1. **HACS** → **Integrations** → remove **LAN Scanner** if present (⋮ → Delete)
2. **HACS** → **⋮** → **Custom repositories** → remove `skydiveTom/home-assistant-lan-scanner`
3. **HACS** → **⋮** → **Clear cache** (or restart Home Assistant)
4. Re-add the custom repository and install again — select **v1.0.0** or latest **main**

### Manual installation

Copy the `custom_components/lan_scanner` folder to `/config/custom_components/lan_scanner` on your Home Assistant instance and restart.

## Configuration

On first setup you will configure:

| Option | Description | Default |
|---|---|---|
| Local IP | IP of the HA network interface to scan from | Auto-detected |
| Subnet | Network range in CIDR notation | Auto `/24` |
| Scan interval | Seconds between scans (min 300) | 900 (15 min) |
| Scan ports | Enable port scanning for RTSP detection | Enabled |
| Device trackers | Create presence trackers for devices | Enabled |

### Assigning device names

After the first scan:

1. Go to **Settings → Devices & services → LAN Scanner → Configure**
2. Choose **Device names (MAC)**
3. Add MAC address and friendly name

Or use the service:

```yaml
service: lan_scanner.set_device_name
data:
  mac: "aa:bb:cc:dd:ee:ff"
  name: "Garden Camera"
```

### Manual scan

```yaml
service: lan_scanner.scan
```

## Entities

Each discovered device (by MAC) creates:

| Entity | Type | Description |
|---|---|---|
| IP address | sensor | Current IP (updates on DHCP change) |
| Last seen | sensor | Timestamp of last scan detection |
| Vendor | sensor | Manufacturer from OUI database |
| RTSP camera | binary_sensor | `on` if only port 554 is open |
| Presence | device_tracker | `home` / `not_home` (if enabled) |

A summary sensor **LAN Scanner** shows total device count with a `devices` attribute containing the full list.

## RTSP camera detection

The integration scans these common ports:

`21, 22, 23, 53, 80, 135, 139, 443, 445, 554, 1883, 8000, 8080, 8443, 8554`

Classification:
- **RTSP camera only** — port 554 is the only open port
- **Has RTSP** — port 554 open along with other ports (e.g. web UI on 80)

## Limitations

- Devices in deep sleep may not respond to ARP probes
- VLAN / AP client isolation prevents cross-segment scanning
- Port scanning generates network traffic — use intervals ≥ 15 minutes on `/24` networks
- Cameras with a web interface on port 80 won't be classified as "RTSP only"
- Devices without a MAC address cannot be persistently identified

## Development

```
home-assistant-lan-scanner/
└── custom_components/
    └── lan_scanner/
```

## License

MIT
