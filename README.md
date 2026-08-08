# 🦊 KALI-FOX

> One-command, self-healing RTL8188EUS driver installer & Monitor Mode setup for the TP-Link TL-WN722N V2/V3 Wi-Fi adapter on Kali Linux.

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

To stop background network interference, set `wlan0` to Monitor Mode, and run `wifite`:

```bash
sudo python3 install_rtl8188eus.py --fix-monitor
sudo wifite -i wlan0 --kill
```

### Manual Commands (Optional)

```bash
# 1. Stop interfering network services
sudo airmon-ng check kill

# 2. Enable Monitor Mode on interface
sudo ip link set wlan0 down
sudo iw dev wlan0 set type monitor
sudo ip link set wlan0 up

# 3. Test Packet Injection
sudo aireplay-ng --test wlan0
```

---

## 🧹 Auto-Cleaning Engine

Upon successful driver installation, KALI-FOX automatically cleans up temporary build files, cloned directories, and unnecessary installer caches to keep your system lean and compact.

---

## 📜 Credits & Author Rights

This project utilizes driver source patches and DKMS module definitions maintained by the open-source community:

- **aircrack-ng**: [rtl8188eus repository](https://github.com/aircrack-ng/rtl8188eus)
- **gglluukk**: [rtl8188eus Linux 6.8+/7.0+ patches](https://github.com/gglluukk/rtl8188eus)
- **lwfinger**: [rtl8188eu driver maintenance](https://github.com/lwfinger/rtl8188eu)

*All original driver copyrights and license rights belong to their respective authors.*

---

## 📄 License

[MIT License](LICENSE) — Created with ❤️ by [cid-moosa](https://github.com/cid-moosa)
