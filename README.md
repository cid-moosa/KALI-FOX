# 🦊 KALI-FOX

> One-command installer for the TP-Link TL-WN722N V2/V3 Wi-Fi adapter (Realtek RTL8188EUS) on Kali Linux — with animated TUI, ASCII art, and auto-reboot.

[![License: MIT](https://img.shields.io/badge/License-MIT-brightgreen.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform: Kali Linux](https://img.shields.io/badge/Platform-Kali%20Linux-557C94.svg)](https://www.kali.org/)
[![GitHub Release](https://img.shields.io/github/v/release/cid-moosa/KALI-FOX)](https://github.com/cid-moosa/KALI-FOX/releases)
[![GitHub issues](https://img.shields.io/github/issues/cid-moosa/KALI-FOX)](https://github.com/cid-moosa/KALI-FOX/issues)

---

## The Problem

The TP-Link TL-WN722N V2/V3 doesn't work out-of-the-box on Kali Linux — the bundled `r8188eu` driver conflicts with the adapter's RTL8188EUS chipset. Fixing it manually means hunting down repos, blacklisting modules, and compiling kernel drivers by hand.

**KALI-FOX does all of that in one command — fully automated, zero prompts.**

## Features

- 🎨 **Animated TUI** — ASCII art banner, globe-spin download animation, animated fox mascot, typewriter system info, phase progress bar
- 🔧 **Fully automated** — installs deps, blacklists the broken driver, clones, patches, compiles, loads, and reboots
- 🛡️ **Kernel 7.x compatible** — auto-patches the Makefile `EXTRA_CFLAGS` for newer kernels
- 📟 **Degrades gracefully** — works with plain text if `rich` is missing or stdout is piped
- 🔄 **Auto-reboot** — 10-second countdown after success (Ctrl+C to cancel)
- 🧱 **Idempotent** — safe to re-run; skips steps that are already done

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

| Phase | Step | Action |
|:-----:|------|--------|
| 1/6 | **Dependencies** | `apt-get update` + install `build-essential`, `libelf-dev`, `linux-headers`, `bc`, `dkms`, `git` |
| 2/6 | **Unload** | `rmmod r8188eu` (non-critical if not loaded) |
| 3/6 | **Blacklist** | Write `blacklist r8188eu` → `/etc/modprobe.d/realtek.conf` |
| 4/6 | **Clone** | `git clone --depth=1` the [aircrack-ng/rtl8188eus](https://github.com/aircrack-ng/rtl8188eus) repo |
| 5/6 | **Compile** | Patch Makefile for kernel compat, then `make` + `make install` |
| 6/6 | **Load** | `depmod -a` + `modprobe 8188eu` |
| ✓ | **Reboot** | Auto-reboot countdown (Ctrl+C to cancel) |

## TUI Animations

The script includes animations ported from [PIPY-FOX](https://github.com/cid-moosa/PIPY-FOX):

- **Animated ASCII banner** — line-by-line reveal of the KALI-FOX and adapter model logos
- **Globe spin** 🌍🌎🌏 — during download phase
- **Fox mascot** — happy 😊 on success, sad 😢 on failure, working ⚙️ during compilation
- **Phase progress bar** — `[████░░]` shows overall progress
- **Typewriter effect** — system info printed character by character
- **Disclaimer panel** — styled warning box before installation begins
- **Variety spinners** — different spinner styles per step (`dots`, `earth`, `bouncingBar`, `arrow3`, etc.)

All animations respect `NO_COLOR`, `isatty()`, and missing `rich` — degrades to plain text automatically.

## Requirements

- **OS:** Kali Linux (Debian-based)
- **Python:** 3.10+
- **Privileges:** Must run as root (`sudo`)
- **Hardware:** TP-Link TL-WN722N V2 or V3 (RTL8188EUS chipset)

## Tech Stack

- Python 3 (stdlib: `subprocess`, `os`, `signal`, `shutil`, `atexit`, `time`, `itertools`)
- [`rich`](https://github.com/Textualize/rich) (optional — animated TUI, Live rendering, tables, panels)
- [aircrack-ng/rtl8188eus](https://github.com/aircrack-ng/rtl8188eus) (driver source)

## Related

- [PIPY-FOX](https://github.com/cid-moosa/PIPY-FOX) — Same adapter driver installer for Parrot OS (different driver, different approach)

## License

[MIT](LICENSE)

---

<p align="center">
  Made by <a href="https://github.com/cid-moosa">cid-moosa</a>
</p>
