# 🦊 KALI-FOX

> One-command, self-healing installer for the TP-Link TL-WN722N V2/V3 Wi-Fi adapter (Realtek RTL8188EUS) on Kali Linux — fully automated, animated TUI, zero user input.

[![License: MIT](https://img.shields.io/badge/License-MIT-brightgreen.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform: Kali Linux](https://img.shields.io/badge/Platform-Kali%20Linux-557C94.svg)](https://www.kali.org/)
[![GitHub Release](https://img.shields.io/github/v/release/cid-moosa/KALI-FOX)](https://github.com/cid-moosa/KALI-FOX/releases)
[![GitHub issues](https://img.shields.io/github/issues/cid-moosa/KALI-FOX)](https://github.com/cid-moosa/KALI-FOX/issues)

---

## The Problem

The TP-Link TL-WN722N V2/V3 doesn't work out-of-the-box on Kali Linux — the bundled `r8188eu` driver conflicts with the adapter's RTL8188EUS chipset. Fixing it manually means hunting down repos, blacklisting modules, compiling kernel drivers, and debugging build failures.

**KALI-FOX does all of that in one command — and auto-repairs any errors it encounters.**

## Features

- 🔧 **Self-Healing** — every step has multiple fallback strategies; errors are auto-repaired, not just reported
- 🎨 **Animated TUI** — ASCII art banner, globe spin, fox mascot (happy/sad/working/repairing), typewriter, phase progress bar
- ⚡ **Fully Automated** — zero prompts, zero user input from start to reboot
- 🛡️ **5 Compilation Strategies** — KCFLAGS → CFLAGS_MODULE → header symlinks → DKMS make target → manual DKMS registration
- 📡 **Clone Fallbacks** — git clone → full clone → wget tarball → curl tarball
- 🔄 **Auto-Reboot** — 10-second countdown after success (Ctrl+C to cancel)
- 📟 **Degrades Gracefully** — plain text output if `rich` is missing or stdout is piped

## Quickstart

```bash
git clone https://github.com/cid-moosa/KALI-FOX.git
cd KALI-FOX
sudo python3 install_rtl8188eus.py
```

> **Tip:** For the animated TUI experience, install `rich` first:
> ```bash
> apt install python3-rich   # or: pip install rich
> ```

## What It Does

| Phase | Step | Action | Auto-Repair |
|:-----:|------|--------|-------------|
| 1/6 | **Dependencies** | `apt update` + install 7 packages | `dpkg --configure`, `apt install -f`, individual package install |
| 2/6 | **Unload** | `rmmod r8188eu` | Force-unload with `rmmod -f` |
| 3/6 | **Blacklist** | Write to `/etc/modprobe.d/realtek.conf` | Recreate directory + file |
| 4/6 | **Clone** | `git clone --depth=1` | Full clone → wget tarball → curl tarball |
| 5/6 | **Compile** | Patch Makefile + `make` + `make install` | 5 strategies (see below) |
| 6/6 | **Load** | `depmod -a` + `modprobe 8188eu` | Find `.ko` file + `insmod` directly |
| ✓ | **Reboot** | Auto-reboot in 10s | Ctrl+C to cancel |

### Compilation Strategies (Step 5)

If one fails, the next is tried automatically:

1. **KCFLAGS** — passes `-I<include>` via `KCFLAGS` (additive, doesn't override Makefile)
2. **CFLAGS_MODULE** — passes via `CFLAGS_MODULE` (alternative kbuild variable)
3. **Header Symlinks** — symlinks all `.h` files from `include/` directly into `core/`, `hal/`, `os_dep/`
4. **DKMS make target** — runs `make dkms-install`
5. **Manual DKMS** — copies source to `/usr/src/`, generates `dkms.conf`, runs `dkms add/build/install`

## TUI Animations

| Animation | Description |
|---|---|
| ASCII banner reveal | Line-by-line animated logo + adapter model |
| Globe spin 🌍🌎🌏 | During download phase |
| Fox mascot | 4 variants: happy ✓, sad ✗, working ⚙, repairing 🔧 |
| Repair animation | Wrench/gear icon cycle during auto-fix |
| Phase progress bar | `[████░░] Phase 3/6 (50%)` |
| Typewriter | System info printed character by character |
| Variety spinners | Different spinner per step |
| Auto-reboot countdown | 10s countdown with Ctrl+C cancel |

All animations respect `NO_COLOR`, `isatty()`, and missing `rich`.

## Requirements

- **OS:** Kali Linux (Debian-based)
- **Python:** 3.10+
- **Privileges:** Must run as root (`sudo`)
- **Hardware:** TP-Link TL-WN722N V2 or V3 (RTL8188EUS chipset)

## Enable Monitor Mode & Test Packet Injection

After installing the driver and rebooting, plug in your TP-Link TL-WN722N V2/V3 adapter and run:

1. **Identify your wireless interface name:**
   ```bash
   iwconfig
   ```

2. **Kill conflicting processes and set monitor mode (assuming interface `wlan0`):**
   ```bash
   sudo ifconfig wlan0 down
   sudo airmon-ng check kill
   sudo iwconfig wlan0 mode monitor
   sudo ifconfig wlan0 up
   ```

3. **Verify monitor mode:**
   ```bash
   iwconfig
   ```
   The output for `wlan0` should display `Mode:Monitor`.

4. **Test packet injection:**
   ```bash
   sudo aireplay-ng --test wlan0
   ```
   If successful, `aireplay-ng` will show packet injection responses from nearby access points.

## Related

- [PIPY-FOX](https://github.com/cid-moosa/PIPY-FOX) — Same adapter installer for Parrot OS

## License

[MIT](LICENSE)

---

<p align="center">
  Made by <a href="https://github.com/cid-moosa">cid-moosa</a>
</p>
