# 🦊 KALI-FOX

> One-command installer for the TP-Link TL-WN722N V2/V3 Wi-Fi adapter (Realtek RTL8188EUS) on Kali Linux.

[![License: MIT](https://img.shields.io/badge/License-MIT-brightgreen.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform: Kali Linux](https://img.shields.io/badge/Platform-Kali%20Linux-557C94.svg)](https://www.kali.org/)
[![GitHub issues](https://img.shields.io/github/issues/cid-moosa/KALI-FOX)](https://github.com/cid-moosa/KALI-FOX/issues)

---

## The Problem

The TP-Link TL-WN722N V2/V3 doesn't work out-of-the-box on Kali Linux — the bundled `r8188eu` driver conflicts with the adapter's RTL8188EUS chipset. Fixing it manually means hunting down repos, blacklisting modules, and compiling kernel drivers by hand.

**KALI-FOX does all of that in one command.**

## Features

- 🔧 **Fully automated** — installs dependencies, blacklists the broken driver, clones, compiles, and loads the correct module
- 🎨 **Polished TUI** — animated spinners, color-coded output, and a summary table via the `rich` library
- 📟 **Degrades gracefully** — works with plain text if `rich` is missing or stdout is piped
- 🛡️ **Safe** — checks for root, validates every step, cleans up temp files on exit or Ctrl+C
- 🧱 **Idempotent** — safe to re-run; skips steps that are already done (e.g. blacklist already present)

## Quickstart

```bash
# SSH into your Kali box or open a terminal, then:
git clone https://github.com/cid-moosa/KALI-FOX.git
cd KALI-FOX
sudo python3 install_rtl8188eus.py
```

> **Tip:** For the best experience, install `rich` first:
> ```bash
> apt install python3-rich   # or: pip install rich
> ```

## What It Does

| Step | Action |
|------|--------|
| 1 | Updates apt & installs `build-essential`, `libelf-dev`, `linux-headers`, `bc`, `dkms`, `git` |
| 2 | Unloads the conflicting `r8188eu` kernel module |
| 3 | Blacklists `r8188eu` in `/etc/modprobe.d/realtek.conf` |
| 4 | Clones the [aircrack-ng/rtl8188eus](https://github.com/aircrack-ng/rtl8188eus) driver source |
| 5 | Compiles and installs the driver via `make` / `make install` |
| 6 | Runs `depmod -a` and loads the new `8188eu` module |

## Requirements

- **OS:** Kali Linux (Debian-based)
- **Python:** 3.10+
- **Privileges:** Must run as root (`sudo`)
- **Hardware:** TP-Link TL-WN722N V2 or V3 (RTL8188EUS chipset)

## Tech Stack

- Python 3 (stdlib: `subprocess`, `os`, `signal`, `shutil`, `atexit`)
- [`rich`](https://github.com/Textualize/rich) (optional — TUI spinners, tables, color)
- [aircrack-ng/rtl8188eus](https://github.com/aircrack-ng/rtl8188eus) (driver source)

## License

[MIT](LICENSE)

---

<p align="center">
  Made by <a href="https://github.com/cid-moosa">cid-moosa</a>
</p>
