#!/usr/bin/env python3
"""
NordicTrack Treadmill Bluetooth Reader
Connects to NordicTrack treadmill and reads pace and incline data

This script works on Raspberry Pi with BlueZ
"""

import sys
import asyncio
import struct
from datetime import datetime

try:
    from bleak import BleakClient, BleakScanner
except ImportError:
    print("Required library not found. Install with:")
    print("pip install bleak")
    sys.exit(1)

# Common NordicTrack/iFit FTMS (Fitness Machine Service) UUIDs
FTMS_SERVICE_UUID = "00001826-0000-1000-8000-00805f9b34fb"
TREADMILL_DATA_UUID = "00002acd-0000-1000-8000-00805f9b34fb"  # Treadmill Data
INDOOR_BIKE_DATA_UUID = "00002ad2-0000-1000-8000-00805f9b34fb"  # Indoor Bike Data
FITNESS_MACHINE_CONTROL_POINT_UUID = "00002ad9-0000-1000-8000-00805f9b34fb"
FITNESS_MACHINE_STATUS_UUID = "00002ada-0000-1000-8000-00805f9b34fb"
FITNESS_MACHINE_FEATURE_UUID = "00002acc-0000-1000-8000-00805f9b34fb"

# Alternative proprietary NordicTrack UUIDs (may vary by model)
NORDICTRACK_SERVICE_UUID = "6e40fff0-b5a3-f393-e0a9-e50e24dcca9e"


class NordicTrackTreadmill:
    """NordicTrack Treadmill BLE Client"""
    
    def __init__(self):
        self.client = None
        self.device = None
        self.speed_kmh = 0.0
        self.incline_percent = 0.0
        self.distance_m = 0.0
        self.connected = False
        
    async def scan_for_treadmill(self, timeout=10.0):
        """Scan for NordicTrack treadmill"""
        print(f"🔍 Scanning for NordicTrack treadmill ({timeout}s)...")
        
        devices = await BleakScanner.discover(timeout=timeout)
        
        # Look for devices with NordicTrack, iFit, or FTMS in the name
        treadmill_keywords = ['nordictrack', 'nordic', 'ifit', 'treadmill', 'ftms']
        
        found_devices = []
        for device in devices:
            name = device.name or ""
            name_lower = name.lower()
            
            # Check if device name contains any treadmill keywords
            if any(keyword in name_lower for keyword in treadmill_keywords):
                found_devices.append(device)
                print(f"  ✓ Found: {device.name} ({device.address})")
        
        if not found_devices:
            print("\n⚠️  No NordicTrack treadmill found")
            print("Showing all devices for reference:")
            for device in devices:
                if device.name:
                    print(f"  - {device.name} ({device.address})")
            return None
        
        # Return the first found device
        return found_devices[0]
    
    async def connect(self, device_address=None):
        """Connect to treadmill"""
        if not device_address:
            self.device = await self.scan_for_treadmill()
            if not self.device:
                return False
        else:
            print(f"🔗 Connecting to {device_address}...")
            self.device = device_address
        
        try:
            self.client = BleakClient(self.device)
            await self.client.connect()
            self.connected = True
            
            print(f"✅ Connected to {self.device.name if hasattr(self.device, 'name') else self.device}")
            
            # Discover services
            await self._discover_services()
            
            return True
            
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    async def _discover_services(self):
        """Discover and print available services and characteristics"""
        print("\n📋 Discovering services...")
        
        services = self.client.services
        
        for service in services:
            print(f"\n🔷 Service: {service.uuid}")
            if service.description:
                print(f"   Description: {service.description}")
            
            for char in service.characteristics:
                print(f"  └─ Characteristic: {char.uuid}")
                print(f"     Properties: {char.properties}")
                if char.description:
                    print(f"     Description: {char.description}")
    
    def _parse_treadmill_data(self, data: bytearray):
        """
        Parse FTMS Treadmill Data characteristic
        Based on Bluetooth FTMS specification
        """
        if len(data) < 3:
            return
        
        # Parse flags (first 2 bytes, little-endian)
        flags = struct.unpack('<H', data[0:2])[0]
        
        offset = 2
        
        # Bit 0: More data flag
        # Bit 1: Average Speed present
        instantaneous_speed_present = flags & 0x01
        
        try:
            # Instantaneous Speed (uint16, km/h with 0.01 resolution)
            if instantaneous_speed_present and len(data) >= offset + 2:
                speed_raw = struct.unpack('<H', data[offset:offset+2])[0]
                self.speed_kmh = speed_raw * 0.01
                offset += 2
            
            # Average Speed (if present)
            if (flags & 0x02) and len(data) >= offset + 2:
                offset += 2
            
            # Total Distance (uint24, meters with 1m resolution)
            if (flags & 0x04) and len(data) >= offset + 3:
                distance_bytes = data[offset:offset+3] + b'\x00'  # Pad to 4 bytes
                self.distance_m = struct.unpack('<I', distance_bytes)[0]
                offset += 3
            
            # Inclination (sint16, percentage with 0.1 resolution)
            if (flags & 0x08) and len(data) >= offset + 2:
                incline_raw = struct.unpack('<h', data[offset:offset+2])[0]
                self.incline_percent = incline_raw * 0.1
                offset += 2
            
            # Ramp Angle Setting (sint16, degrees with 0.1 resolution)
            if (flags & 0x10) and len(data) >= offset + 2:
                offset += 2
            
            # Remaining fields...
            
        except Exception as e:
            print(f"⚠️  Parse error: {e}")
    
    def _notification_handler(self, sender, data: bytearray):
        """Handle notifications from treadmill"""
        self._parse_treadmill_data(data)
        
        # Print current stats
        pace_min_per_km = (60 / self.speed_kmh) if self.speed_kmh > 0 else 0
        pace_min = int(pace_min_per_km)
        pace_sec = int((pace_min_per_km - pace_min) * 60)
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] 🏃 Speed: {self.speed_kmh:5.1f} km/h | "
              f"Pace: {pace_min}:{pace_sec:02d} min/km | "
              f"Incline: {self.incline_percent:4.1f}% | "
              f"Distance: {self.distance_m:6.0f}m")
    
    async def start_notifications(self):
        """Subscribe to treadmill data notifications"""
        print("\n📡 Subscribing to treadmill data...\n")
        
        # Try FTMS Treadmill Data characteristic
        try:
            await self.client.start_notify(
                TREADMILL_DATA_UUID,
                self._notification_handler
            )
            print("✅ Subscribed to Treadmill Data")
            return True
        except Exception as e:
            print(f"⚠️  Could not subscribe to Treadmill Data: {e}")
        
        # Try Indoor Bike Data as fallback (some treadmills use this)
        try:
            await self.client.start_notify(
                INDOOR_BIKE_DATA_UUID,
                self._notification_handler
            )
            print("✅ Subscribed to Indoor Bike Data")
            return True
        except Exception as e:
            print(f"⚠️  Could not subscribe to Indoor Bike Data: {e}")
        
        print("❌ Could not subscribe to any data characteristic")
        return False
    
    async def disconnect(self):
        """Disconnect from treadmill"""
        if self.client and self.connected:
            await self.client.disconnect()
            self.connected = False
            print("\n✅ Disconnected from treadmill")


async def main():
    print("=" * 60)
    print("  NordicTrack Treadmill Bluetooth Reader")
    print("=" * 60)
    
    treadmill = NordicTrackTreadmill()
    
    # Connect to treadmill
    # You can specify an address like: await treadmill.connect("XX:XX:XX:XX:XX:XX")
    connected = await treadmill.connect()
    
    if not connected:
        print("\n❌ Failed to connect to treadmill")
        print("\nTroubleshooting:")
        print("1. Make sure your treadmill's Bluetooth is enabled")
        print("2. Check that you're not already connected from another device")
        print("3. Try power cycling the treadmill")
        print("4. Move closer to the treadmill")
        return
    
    # Start receiving data
    subscribed = await treadmill.start_notifications()
    
    if not subscribed:
        await treadmill.disconnect()
        return
    
    print("\n" + "=" * 60)
    print("📊 Receiving treadmill data...")
    print("Press Ctrl+C to stop")
    print("=" * 60 + "\n")
    
    try:
        # Keep running and receiving notifications
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Stopping...")
    finally:
        await treadmill.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
