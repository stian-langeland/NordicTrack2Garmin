# NordicTrack2Garmin

Connect your NordicTrack treadmill to your Garmin watch via a Raspberry Pi acting as a Bluetooth footpod sensor.

## 🎯 Overview

This project provides two main tools:

1. **BLE Pace Sensor** - Simulates a Bluetooth footpod that Garmin watches can connect to
2. **NordicTrack Reader** - Reads speed and incline data from NordicTrack treadmills via Bluetooth

Together, these tools allow you to bridge your NordicTrack treadmill data to your Garmin watch for accurate indoor running metrics.

## 📋 Features

- ✅ **Real-time data transmission** to Garmin watches
- ✅ **FTMS protocol support** for NordicTrack treadmills
- ✅ **Customizable pace and cadence** settings
- ✅ **Distance tracking** with automatic reset
- ✅ **Incline monitoring** from treadmill
- ✅ **Raspberry Pi optimized** for reliable BLE peripheral mode

## 🛠️ Hardware Requirements

- **Raspberry Pi** (3, 4, Zero W, or newer) with Bluetooth
- **NordicTrack treadmill** with Bluetooth/iFit capability
- **Garmin watch** with footpod sensor support

## 🚀 Quick Start

### On Raspberry Pi

1. **Install system dependencies:**
```bash
sudo apt-get update
sudo apt-get install -y python3-dbus python3-gi bluez python3-pip
```

2. **Clone the repository:**
```bash
git clone https://github.com/stian-langeland/NordicTrack2Garmin.git
cd NordicTrack2Garmin
```

3. **Run the BLE Pace Sensor:**
```bash
sudo python3 ble_pace_sensor_rpi.py
```

4. **Connect your Garmin watch:**
   - Start a Run/Walk activity on your watch
   - Swipe down → Sensors & Accessories → Add New
   - Select "Foot Pod"
   - Look for "Footpod" and select it

### Reading NordicTrack Data (Optional)

To read data directly from your NordicTrack treadmill:

1. **Install bleak:**
```bash
pip3 install bleak
```

2. **Run the reader:**
```bash
python3 nordictrack_reader.py
```

This will scan for and connect to your treadmill, displaying real-time speed, pace, incline, and distance.

## 📁 Project Structure

```
NordicTrack2Garmin/
├── ble_pace_sensor_rpi.py    # BLE footpod sensor for Raspberry Pi
├── nordictrack_reader.py      # NordicTrack treadmill Bluetooth reader
├── requirements_rpi.txt       # System dependencies list
├── README_RASPBERRY_PI.md     # Detailed Raspberry Pi setup guide
├── venv_control.sh            # Virtual environment helper script
└── push_to_github.sh          # GitHub repository setup helper
```

## ⚙️ Configuration

### Adjust Pace and Cadence

Edit the constants in `ble_pace_sensor_rpi.py`:

```python
PACE_KMH = 10.0      # Speed in km/h (10 km/h = 6:00 min/km pace)
CADENCE_RPM = 85     # Steps per minute
```

### Auto-start on Boot

To run the sensor automatically when your Raspberry Pi boots:

1. Create a systemd service:
```bash
sudo nano /etc/systemd/system/footpod.service
```

2. Add the following content:
```ini
[Unit]
Description=BLE Footpod Sensor for Garmin
After=bluetooth.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/pi/NordicTrack2Garmin
ExecStart=/usr/bin/python3 /home/pi/NordicTrack2Garmin/ble_pace_sensor_rpi.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

3. Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable footpod.service
sudo systemctl start footpod.service
```

## 📖 Documentation

- **[Raspberry Pi Setup Guide](README_RASPBERRY_PI.md)** - Detailed installation and configuration instructions
- **[System Requirements](requirements_rpi.txt)** - Complete list of dependencies

## 🔧 Troubleshooting

### Garmin Watch Can't Find Sensor

- Ensure you're **in an activity** when searching for sensors
- Keep devices within 10 feet during pairing
- Restart Bluetooth on your watch
- Try running `sudo systemctl restart bluetooth` on the Pi

### NordicTrack Connection Issues

- Make sure the treadmill's Bluetooth is enabled
- Disconnect from any other devices (phone apps, etc.)
- Move the Raspberry Pi closer to the treadmill
- Power cycle the treadmill

### BLE Adapter Not Found

```bash
# Check Bluetooth status
sudo systemctl status bluetooth

# Restart Bluetooth
sudo systemctl restart bluetooth

# Verify adapter
hciconfig
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is open source and available under the MIT License.

## 🙏 Acknowledgments

- Uses the Bluetooth FTMS (Fitness Machine Service) standard
- Built with Python's BlueZ D-Bus API for Raspberry Pi
- Compatible with standard Garmin ANT+ footpod protocol

## 📧 Contact

For issues or questions, please open an issue on GitHub.

---

**Note:** This project is designed for Raspberry Pi. macOS has limited BLE peripheral support and may not work reliably with Garmin watches.
