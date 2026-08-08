# 🦊 KALI-FOX

> One-command RTL8188EUS driver installer & Monitor Mode setup for TP-Link TL-WN722N V2/V3 on Kali Linux.

---

## ⚡ Quickstart

Open your Kali Linux terminal and run:

```bash
git clone https://github.com/cid-moosa/KALI-FOX.git
cd KALI-FOX
sudo python3 install_rtl8188eus.py
```

---

## 📡 Enable Monitor Mode & Run Wifite

To stop background network interference, enable Monitor Mode on `wlan0`, and launch `wifite`:

```bash
sudo python3 install_rtl8188eus.py --fix-monitor
sudo wifite -i wlan0 --kill
```

### Manual Commands (Optional)

```bash
# 1. Kill interfering processes
sudo airmon-ng check kill

# 2. Set Monitor Mode
sudo ip link set wlan0 down
sudo iw dev wlan0 set type monitor
sudo ip link set wlan0 up

# 3. Test Packet Injection
sudo aireplay-ng --test wlan0
```

---

## 💡 Troubleshooting

- **VMware / VirtualBox Users:** Ensure your TP-Link USB adapter is passed through to the Kali Linux VM in your VM USB settings (**USB 2.0 / 3.0**).

---

<p align="center">
  Made with ❤️ by <a href="https://github.com/cid-moosa">cid-moosa</a>
</p>
