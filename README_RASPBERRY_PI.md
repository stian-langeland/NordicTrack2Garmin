# Bluetooth Pace Sensor for Garmin Watch - Raspberry Pi Setup Guide

## Requirements
- Raspberry Pi (any model with Bluetooth: Pi 3, 4, Zero W, etc.)
- Raspberry Pi OS (Raspbian)
- Python 3.7+

## Installation Steps

### 1. Update System
```bash
sudo apt-get update
sudo apt-get upgrade -y
```

### 2. Install Dependencies
```bash
sudo apt-get install -y python3-dbus python3-gi bluez
```

### 3. Transfer the Script
Copy `ble_pace_sensor_rpi.py` to your Raspberry Pi. You can use:
- USB drive
- SCP: `scp ble_pace_sensor_rpi.py pi@raspberrypi.local:~/`
- Git clone this repository

### 4. Make Script Executable
```bash
chmod +x ble_pace_sensor_rpi.py
```

### 5. Run the Script
```bash
sudo python3 ble_pace_sensor_rpi.py
```

**Note:** `sudo` is required because BlueZ needs root access for BLE peripheral mode.

## Connecting Your Garmin Watch

1. **Start a Run or Walk activity** on your Garmin watch
2. Swipe down or press UP to access the activity menu
3. Select **Sensors & Accessories** → **Add New**
4. Choose **Foot Pod**
5. Wait for "Footpod" to appear and select it
6. The script will display "✅ Garmin watch connected!" when paired

## Configuration

Edit these values in `ble_pace_sensor_rpi.py` to change the pace/cadence:

```python
PACE_KMH = 10.0      # Speed in km/h (10 km/h = 6:00 min/km pace)
CADENCE_RPM = 85     # Steps per minute
```

## Running at Startup (Optional)

To automatically start the sensor on boot:

### 1. Create a systemd service
```bash
sudo nano /etc/systemd/system/footpod.service
```

### 2. Add this content:
```ini
[Unit]
Description=BLE Footpod Sensor for Garmin
After=bluetooth.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/pi
ExecStart=/usr/bin/python3 /home/pi/ble_pace_sensor_rpi.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 3. Enable and start the service
```bash
sudo systemctl daemon-reload
sudo systemctl enable footpod.service
sudo systemctl start footpod.service
```

### 4. Check status
```bash
sudo systemctl status footpod.service
```

## Troubleshooting

### "BLE adapter not found"
- Check Bluetooth is enabled: `sudo systemctl status bluetooth`
- Enable if needed: `sudo systemctl start bluetooth`
- Verify adapter exists: `hciconfig`

### "Failed to register application"
- Make sure no other BLE peripheral services are running
- Restart Bluetooth: `sudo systemctl restart bluetooth`
- Try rebooting the Pi

### Watch Can't Find Sensor
- Make sure you're IN an activity when searching
- Keep devices within 10 feet during pairing
- Restart Bluetooth on your watch
- Try restarting the script

### Check Logs
```bash
# If using systemd service:
sudo journalctl -u footpod.service -f

# Or check BlueZ logs:
sudo journalctl -u bluetooth -f
```

## Stopping the Sensor

Press `Ctrl+C` in the terminal, or if running as a service:
```bash
sudo systemctl stop footpod.service
```

## Advantages of Raspberry Pi vs macOS

- ✅ Proper BLE peripheral advertising with service UUIDs
- ✅ Better compatibility with fitness devices
- ✅ More stable long-term operation
- ✅ Can run headless (no monitor needed)
- ✅ Low power consumption (especially Pi Zero W)

## Notes

- The Raspberry Pi will appear as "Footpod" to your Garmin watch
- The sensor transmits data continuously when connected
- Distance resets when the script restarts
- You can adjust pace and cadence in the script and restart
