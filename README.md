# 🦊 KALI-FOX

**KALI-FOX** is a single-file Python 3 CLI automation script built for **Kali Linux** (Recommended OS: **Kali Linux**).  
It automates installing drivers for **TP-Link USB Wi-Fi adapters (V2 / V3)** (Realtek RTL8188EUS chipset).

The main goal of this automation is to install drivers that allow **monitor mode** and **packet injection** *where the driver and chipset support those features*.

> ⚠️ KALI-FOX does **not** create, modify, or own any drivers.  
> It only automates the installation process.  
> All rights, original copyrights, and responsibility for the drivers belong to their original authors (**aircrack-ng**, **gglluukk**, **lwfinger**).

---

## What this project does

- Uses **one Python file** (`install_rtl8188eus.py`)
- Runs fully in the terminal (CLI with Rich TUI animations)
- Installs official Kali DKMS drivers & upstream patches automatically
- Blacklists incompatible stock drivers (`r8188eu` & `rtl8xxxu`)
- Auto-repairs build warnings and API mismatches on modern Kali kernels (6.8+ / 7.0+)
- Deletes temporary build files and installer caches after installation
- Includes `--fix-monitor` tool to automatically configure Monitor Mode & Wifite

---

## Supported models

This project targets **TP-Link TL-WN722N V2 / V3** (Realtek RTL8188EUS chipset).

Some newer revisions of the same models use the **same Realtek chipset** and behave exactly like V2 / V3.  
If your adapter uses the same chipset, it will usually work the same way.

> V1 adapters use Atheros AR9271, are plug-and-play, and are **not** targeted by this project.

---

## Requirements

- Kali Linux *(Recommended OS)*
- Python **3.8 or newer**
- Root / `sudo` access
- Internet connection (to download drivers & dependencies)

---

## Installation & Usage (Step-by-Step)

### STEP 1: Plug in the adapter and verify detection

Open a terminal and run:
```bash
lsusb
```

### STEP 2: Clone the repository

```bash
git clone https://github.com/cid-moosa/KALI-FOX.git
cd KALI-FOX
```

### STEP 3: Run KALI-FOX

```bash
sudo python3 install_rtl8188eus.py
```

### STEP 4: Enable Monitor Mode & Run Wifite (Optional)

```bash
sudo python3 install_rtl8188eus.py --fix-monitor
sudo wifite -i wlan0 --kill
```

### STEP 5: Reboot

```bash
sudo reboot
```

---

## Author & Credits

- Created with ❤️ by **[cid-moosa](https://github.com/cid-moosa)**
- Driver Source Credits & Author Rights: [aircrack-ng](https://github.com/aircrack-ng/rtl8188eus) · [gglluukk](https://github.com/gglluukk/rtl8188eus) · [lwfinger](https://github.com/lwfinger/rtl8188eu)
- License: [MIT License](LICENSE)
