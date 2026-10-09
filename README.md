# router

Python and systemd unit that builds a LAN bridge and attaches it to a WAN interface on Linux.

`router.service` owns the LAN side. It does not use `hostapd.service` or `dnsmasq.service`. It starts `hostapd` and `dnsmasq` itself and writes their configs under `/run/router`. NetworkManager keeps the WAN interface and gets an address from the ISP by DHCP. Every other interface in this config is expected to be unmanaged in NetworkManager so `ip`, `hostapd`, and `dnsmasq` are the only writers on those devices.

## Layout

Installed copy lives at `/opt/router`. This tree is the source of those files.

| File | Role |
|---|---|
| `service.py` | CLI. Parses `--start`, `--stop`, `--restart`, `--reload` and builds a `Router`. |
| `router.py` | Creates the bridge, restores the firewall, generates and runs `dnsmasq` and `hostapd`. |
| `config.json` | Interface map, DHCP instance, and AP instances. |
| `router.service` | Oneshot unit. `RemainAfterExit=yes`. |
| `firewall.ipt` | Static `iptables-restore` ruleset. |
| `dnsmasq-dhcp0.append` | Extra `dnsmasq` lines appended to the generated config. |
| `hostapd-ap0.append` | 2.4 GHz AP settings appended to the generated config. |
| `hostapd-ap1.append` | 5 GHz AP settings appended to the generated config. |
| `wifi.py` | Unused stub. |

`router.py` and `service.py` import `helpers`, which is not in this tree. Runtime files (`*.conf`, `*.pid`) are created in `/run/router` by `RuntimeDirectory=router`.

## What the unit does

`router.service` starts after `network-online.target` and `NetworkManager.service`. It conflicts with `wpa_supplicant.service` and `hostapd.service` so those units do not take the radios.

`ExecStart` runs:

```
/opt/router/service.py --start --config /opt/router/config.json
```

`Start()` order:

1. Bridge. For each enabled `type: bridge` interface, create it with the configured MAC, enslave `type: lan` members (down, master, up, promisc on), set STP, and add the bridge address. Wi-Fi members are not enslaved here. `hostapd` joins them with `bridge=`. Then set `net.ipv4.ip_forward=1`.
2. Firewall. `iptables-restore /opt/router/firewall.ipt`.
3. `dnsmasq`. Write `/run/router/dnsmasq-<name>.conf`, test it, and start `dnsmasq -g router` with a pid file. Skipped if the bridge step failed.
4. `hostapd`. `rfkill unblock all` once, write `/run/router/hostapd-<name>.conf`, and start `hostapd -B` with a pid file. Skipped if the bridge or `dnsmasq` step failed.

The WAN interface is listed in `config.json` and is not configured by this code.

`ExecStop` kills `dnsmasq` and `hostapd` from their pid files, detaches LAN slaves, deletes the bridge, and sets `net.ipv4.ip_forward=0`. It does not flush the iptables ruleset.

`ExecReload` sends `SIGHUP` to each running `dnsmasq`. The unit is `Type=oneshot`, so systemd does not supervise the child daemons after `service.py` exits.

## Current config

`br0` is `192.168.1.1/24`, STP off, metric 55. Members: `lan0`, `lan1`, `lan2`, `lan3`, `wlan0`, `wlan1`.

`dhcp0` listens on `br0`, serves `192.168.1.10`–`192.168.1.100`, lease 3600 seconds, domain `lan`. The append file sets the resolver to OpenDNS and disables reading `/etc/resolv.conf`.

`ap0` is `wlan0` on `br0` (2.4 GHz). `ap1` is `wlan1` on `br0` (5 GHz). SSIDs, channels, and passphrases are in the hostapd append files.

`firewall.ipt` defaults INPUT and FORWARD to DROP and OUTPUT to ACCEPT. It masquerades `192.168.1.0/24` out `wan0`, accepts DHCP and DNS on `br0`, and drops a few LAN hosts toward the WAN.

## Commands

```
service.py --start   --config /opt/router/config.json
service.py --stop    --config /opt/router/config.json
service.py --restart --config /opt/router/config.json
service.py --reload  --config /opt/router/config.json
```

Optional flags: `--no-bridge`, `--no-dnsmasq`, `--no-hostapd`.

systemd:

```
systemctl start router.service
systemctl stop router.service
systemctl reload router.service
```

## NetworkManager

Leave `wan0` managed so DHCP to the ISP keeps working. Ignore `lan0`–`lan3`, `wlan0`, `wlan1`, and `br0` in the NetworkManager config. If NetworkManager also writes those interfaces, it will fight `router.service`.
