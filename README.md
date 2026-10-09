# router

Python and systemd unit that builds a LAN bridge and attaches it to a WAN interface on Linux.

`router.service` owns the LAN side. It does not use `hostapd.service` or `dnsmasq.service`. It starts `hostapd` and `dnsmasq` itself and writes their configs under `/run/router`. NetworkManager keeps the WAN interface and gets an address from the ISP by DHCP. Every other interface in this config is expected to be unmanaged in NetworkManager so `ip`, `hostapd`, and `dnsmasq` are the only writers on those devices.

## Layout

Installed copy lives at `/opt/router`. This tree is the source of those files. The unit runs as `User=root` and `Group=router`, and `dnsmasq` is started with `-g router`, so that group must exist.

| File | Role |
|---|---|
| `service.py` | CLI. Parses `--start`, `--stop`, `--restart`, `--reload` and builds a `Router`. |
| `router.py` | Creates the bridge, restores the firewall, generates and runs `dnsmasq` and `hostapd`. |
| `helpers.py` | Config load, interface and address checks, `rfkill`, interface delete. Imported by `router.py`, `service.py`, and `wifi.py`. |
| `wifi.py` | Queries running `hostapd` instances through `hostapd_cli` (`stas`, `signals`). |
| `config.json` | Interface map, DHCP instance, and AP instances. |
| `router.service` | Oneshot unit. `RemainAfterExit=true`. |
| `firewall.ipt` | Static `iptables-restore` ruleset. |
| `dnsmasq-dhcp0.append` | Extra `dnsmasq` lines appended to the generated config. |
| `hostapd-ap0.append` | Not in this tree. `config.json` expects it at `/opt/router/hostapd-ap0.append`. |
| `hostapd-ap1.append` | Not in this tree. `config.json` expects it at `/opt/router/hostapd-ap1.append`. |

Runtime files (`dnsmasq-*.conf`, `dnsmasq-*.pid`, `hostapd-*.conf`, `hostapd-*.pid`) are created in `/run/router` by `RuntimeDirectory=router` (`RuntimeDirectoryMode=0770`). `wifi.py` also points `hostapd_cli` at that directory (`-p /run/router`), so the hostapd append files need a control interface there.

## What the unit does

`router.service` starts after `network-online.target` and `NetworkManager.service`. It conflicts with `wpa_supplicant.service` and `hostapd.service` so those units do not take the radios. It does not enable or talk to `dnsmasq.service`.

`ExecStart` runs:

```
/opt/router/service.py --start --config /opt/router/config.json
```

`Start()` order:

1. Bridge, unless `--no-bridges`. For each enabled `type: bridge` interface, delete it if it already exists, create it with the configured MAC, bring it down, enslave `type: lan` members (down, master, up, promisc on), bring the bridge up, set STP, and add the bridge address. Wi-Fi members are not enslaved here. `hostapd` joins them with `bridge=`. Then set `net.ipv4.ip_forward=1`. A failed `ip` or `sysctl` step raises and aborts start.
2. Firewall. `iptables-restore /opt/router/firewall.ipt`. Not gated by the `--no-*` flags. Stop does not flush this ruleset.
3. `dnsmasq`, unless `--no-dnsmasq` or the bridge step returned failure. Write `/run/router/dnsmasq-<name>.conf` (interface, router and DNS options, DHCP range, domain records, then the append file), test it with `dnsmasq --test`, and start `dnsmasq -g router` with a pid file.
4. `hostapd`, unless `--no-hostapd` or the bridge or `dnsmasq` step returned failure. `rfkill unblock all` once, write `/run/router/hostapd-<name>.conf` (`interface`, `bridge`, then the append file), and start `hostapd -dd -K -t -B` with a pid file.

The WAN interface is listed in `config.json` and is not configured by this code. `helpers.LoadConfig` requires the named devices to exist and match `hwaddr`, and rejects a second `type: wan` interface.

`ExecStop` kills `dnsmasq` and `hostapd` from their pid files, unlinks those pid and conf files, `rfkill block all` once per hostapd instance, detaches LAN slaves (down, nomaster, promisc off), flushes and deletes the bridge, and sets `net.ipv4.ip_forward=0`. It does not flush the iptables ruleset.

`ExecReload` sends `SIGHUP` to each running `dnsmasq` from its pid file. The hostapd loop reads the generated conf file, not the pid file, so that `SIGHUP` only goes out if the conf contents are numeric. The unit is `Type=oneshot`, so systemd does not supervise the child daemons after `service.py` exits.

## Current config

`br0` is `192.168.1.1/24`, STP off, metric 55. Members: `lan0`, `lan1`, `lan2`, `lan3`, `wlan0`, `wlan1`. Only the `lan*` members are enslaved by `router.py`.

`dhcp0` listens on `br0`, serves `192.168.1.10`–`192.168.1.100`, lease 3600 seconds, domain `lan`. Generated options also set the router and DNS server to `192.168.1.1` and a host record for `/etc/hostname`. The append file sets group `router`, the resolver to OpenDNS (`208.67.220.220`, `208.67.222.222`), and `no-resolv`.

`ap0` is `wlan0` on `br0`. `ap1` is `wlan1` on `br0`. SSID, channel, and passphrase live in the hostapd append files, which are not in this tree.

`firewall.ipt` defaults INPUT and FORWARD to DROP and OUTPUT to ACCEPT. It masquerades `192.168.1.0/24` out `wan0`, accepts DHCP and DNS on `br0`, accepts SSH, SMB, and a few other TCP ports from the LAN, and drops `192.168.1.2`, `192.168.1.3`, `192.168.1.4`, and `192.168.1.31` toward the WAN.

## Commands

```
service.py --start   --config /opt/router/config.json
service.py --stop    --config /opt/router/config.json
service.py --restart --config /opt/router/config.json
service.py --reload  --config /opt/router/config.json
```

Optional flags: `--no-bridges` (`-B`), `--no-dnsmasq` (`-D`), `--no-hostapd` (`-H`). Default config path is `config.json` next to `service.py`.

Station list from the running APs (`hostapd_cli -p /run/router`):

```
wifi.py --config /opt/router/config.json stas
wifi.py --config /opt/router/config.json signals
```

systemd:

```
systemctl start router.service
systemctl stop router.service
systemctl reload router.service
```

## NetworkManager

Leave `wan0` managed so DHCP to the ISP keeps working. Ignore `lan0`–`lan3`, `wlan0`, `wlan1`, and `br0` in the NetworkManager config. If NetworkManager also writes those interfaces, it will fight `router.service`.
