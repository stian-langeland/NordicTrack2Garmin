#!/usr/bin/env python3
"""
Bluetooth Low Energy Pace Sensor for Garmin Watch - Raspberry Pi Version
Uses BlueZ D-Bus API for proper BLE peripheral advertising
"""

import struct
import time
import sys
import signal
from threading import Thread

try:
    import dbus
    import dbus.service
    import dbus.mainloop.glib
    from gi.repository import GLib
except ImportError:
    print("Required libraries not found. Install with:")
    print("sudo apt-get install python3-dbus python3-gi")
    print("pip install PyGObject")
    sys.exit(1)

# Bluetooth SIG assigned UUIDs for Running Speed and Cadence Service
RSC_SERVICE_UUID = "00001814-0000-1000-8000-00805f9b34fb"
RSC_MEASUREMENT_UUID = "00002a53-0000-1000-8000-00805f9b34fb"
RSC_FEATURE_UUID = "00002a54-0000-1000-8000-00805f9b34fb"

# Constant pace settings (adjustable)
PACE_KMH = 10.0  # Speed in km/h
CADENCE_RPM = 85  # Steps per minute

# BlueZ D-Bus constants
BLUEZ_SERVICE_NAME = 'org.bluez'
GATT_MANAGER_IFACE = 'org.bluez.GattManager1'
DBUS_OM_IFACE = 'org.freedesktop.DBus.ObjectManager'
DBUS_PROP_IFACE = 'org.freedesktop.DBus.Properties'
GATT_SERVICE_IFACE = 'org.bluez.GattService1'
GATT_CHRC_IFACE = 'org.bluez.GattCharacteristic1'
GATT_DESC_IFACE = 'org.bluez.GattDescriptor1'
LE_ADVERTISING_MANAGER_IFACE = 'org.bluez.LEAdvertisingManager1'
LE_ADVERTISEMENT_IFACE = 'org.bluez.LEAdvertisement1'


class Application(dbus.service.Object):
    """
    org.bluez.GattApplication1 interface implementation
    """
    def __init__(self, bus):
        self.path = '/'
        self.services = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_service(self, service):
        self.services.append(service)

    @dbus.service.method(DBUS_OM_IFACE, out_signature='a{oa{sa{sv}}}')
    def GetManagedObjects(self):
        response = {}
        for service in self.services:
            response[service.get_path()] = service.get_properties()
            chrcs = service.get_characteristics()
            for chrc in chrcs:
                response[chrc.get_path()] = chrc.get_properties()
                descs = chrc.get_descriptors()
                for desc in descs:
                    response[desc.get_path()] = desc.get_properties()
        return response


class Service(dbus.service.Object):
    """
    org.bluez.GattService1 interface implementation
    """
    PATH_BASE = '/org/bluez/footpod/service'

    def __init__(self, bus, index, uuid, primary):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.uuid = uuid
        self.primary = primary
        self.characteristics = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
            GATT_SERVICE_IFACE: {
                'UUID': self.uuid,
                'Primary': self.primary,
                'Characteristics': dbus.Array(
                    self.get_characteristic_paths(),
                    signature='o')
            }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_characteristic(self, characteristic):
        self.characteristics.append(characteristic)

    def get_characteristic_paths(self):
        result = []
        for chrc in self.characteristics:
            result.append(chrc.get_path())
        return result

    def get_characteristics(self):
        return self.characteristics

    @dbus.service.method(DBUS_PROP_IFACE,
                         in_signature='s',
                         out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_SERVICE_IFACE:
            raise InvalidArgsException()
        return self.get_properties()[GATT_SERVICE_IFACE]


class Characteristic(dbus.service.Object):
    """
    org.bluez.GattCharacteristic1 interface implementation
    """
    def __init__(self, bus, index, uuid, flags, service):
        self.path = service.path + '/char' + str(index)
        self.bus = bus
        self.uuid = uuid
        self.service = service
        self.flags = flags
        self.descriptors = []
        self.value = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
            GATT_CHRC_IFACE: {
                'Service': self.service.get_path(),
                'UUID': self.uuid,
                'Flags': self.flags,
                'Descriptors': dbus.Array(
                    self.get_descriptor_paths(),
                    signature='o')
            }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_descriptor(self, descriptor):
        self.descriptors.append(descriptor)

    def get_descriptor_paths(self):
        result = []
        for desc in self.descriptors:
            result.append(desc.get_path())
        return result

    def get_descriptors(self):
        return self.descriptors

    @dbus.service.method(DBUS_PROP_IFACE,
                         in_signature='s',
                         out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_CHRC_IFACE:
            raise InvalidArgsException()
        return self.get_properties()[GATT_CHRC_IFACE]

    @dbus.service.method(GATT_CHRC_IFACE,
                        in_signature='a{sv}',
                        out_signature='ay')
    def ReadValue(self, options):
        return self.value

    @dbus.service.method(GATT_CHRC_IFACE, in_signature='aya{sv}')
    def WriteValue(self, value, options):
        self.value = value

    @dbus.service.method(GATT_CHRC_IFACE)
    def StartNotify(self):
        if self.notifying:
            return
        self.notifying = True

    @dbus.service.method(GATT_CHRC_IFACE)
    def StopNotify(self):
        if not self.notifying:
            return
        self.notifying = False

    @dbus.service.signal(DBUS_PROP_IFACE,
                         signature='sa{sv}as')
    def PropertiesChanged(self, interface, changed, invalidated):
        pass


class RSCMeasurementCharacteristic(Characteristic):
    """
    RSC Measurement Characteristic - provides speed and cadence data
    """
    def __init__(self, bus, index, service, pace_sensor):
        Characteristic.__init__(
            self, bus, index,
            RSC_MEASUREMENT_UUID,
            ['notify'],
            service)
        self.notifying = False
        self.pace_sensor = pace_sensor

    def update_measurement(self):
        """Update the characteristic value with new measurement"""
        if not self.notifying:
            return

        measurement = self.pace_sensor.get_measurement()
        self.value = dbus.Array(measurement, signature='y')
        
        self.PropertiesChanged(
            GATT_CHRC_IFACE,
            {'Value': self.value}, [])

    def StartNotify(self):
        if self.notifying:
            return
        self.notifying = True
        print("✅ Garmin watch connected and receiving data!")

    def StopNotify(self):
        if not self.notifying:
            return
        self.notifying = False
        print("⚠️  Watch disconnected")


class RSCFeatureCharacteristic(Characteristic):
    """
    RSC Feature Characteristic - describes sensor capabilities
    """
    def __init__(self, bus, index, service):
        Characteristic.__init__(
            self, bus, index,
            RSC_FEATURE_UUID,
            ['read'],
            service)
        # Features: stride length, total distance, walking/running status
        features = 0b00000111
        self.value = dbus.Array(struct.pack('<H', features), signature='y')


class RSCService(Service):
    """
    Running Speed and Cadence Service
    """
    def __init__(self, bus, index, pace_sensor):
        Service.__init__(self, bus, index, RSC_SERVICE_UUID, True)
        
        # Add RSC Feature characteristic
        self.add_characteristic(RSCFeatureCharacteristic(bus, 0, self))
        
        # Add RSC Measurement characteristic
        self.measurement_chrc = RSCMeasurementCharacteristic(bus, 1, self, pace_sensor)
        self.add_characteristic(self.measurement_chrc)


class Advertisement(dbus.service.Object):
    """
    LE Advertisement
    """
    PATH_BASE = '/org/bluez/footpod/advertisement'

    def __init__(self, bus, index, advertising_type):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.ad_type = advertising_type
        self.service_uuids = []
        self.manufacturer_data = {}
        self.solicit_uuids = []
        self.service_data = {}
        self.local_name = 'Footpod'
        self.include_tx_power = False
        self.data = None
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        properties = dict()
        properties['Type'] = self.ad_type
        if self.service_uuids:
            properties['ServiceUUIDs'] = dbus.Array(self.service_uuids, signature='s')
        if self.solicit_uuids:
            properties['SolicitUUIDs'] = dbus.Array(self.solicit_uuids, signature='s')
        if self.manufacturer_data:
            properties['ManufacturerData'] = dbus.Dictionary(
                self.manufacturer_data, signature='qv')
        if self.service_data:
            properties['ServiceData'] = dbus.Dictionary(self.service_data, signature='sv')
        if self.local_name:
            properties['LocalName'] = dbus.String(self.local_name)
        if self.include_tx_power:
            properties['IncludeTxPower'] = dbus.Boolean(self.include_tx_power)
        if self.data:
            properties['Data'] = dbus.Dictionary(self.data, signature='yv')
        return {LE_ADVERTISEMENT_IFACE: properties}

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_service_uuid(self, uuid):
        if uuid not in self.service_uuids:
            self.service_uuids.append(uuid)

    @dbus.service.method(DBUS_PROP_IFACE,
                         in_signature='s',
                         out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != LE_ADVERTISEMENT_IFACE:
            raise InvalidArgsException()
        return self.get_properties()[LE_ADVERTISEMENT_IFACE]

    @dbus.service.method(LE_ADVERTISEMENT_IFACE,
                         in_signature='',
                         out_signature='')
    def Release(self):
        print('Advertisement released')


class PaceSensor:
    """Pace sensor data calculator"""
    def __init__(self, pace_kmh, cadence_rpm):
        self.pace_kmh = pace_kmh
        self.cadence_rpm = cadence_rpm
        self.speed_mps = pace_kmh / 3.6
        self.stride_length_m = (self.speed_mps / (cadence_rpm / 60.0)) if cadence_rpm > 0 else 0
        self.total_distance_m = 0
        self.last_update_time = time.time()

    def get_measurement(self):
        """Generate RSC measurement data"""
        # Update distance
        current_time = time.time()
        time_delta = current_time - self.last_update_time
        self.total_distance_m += self.speed_mps * time_delta
        self.last_update_time = current_time

        # Build measurement packet
        flags = 0b00000111  # Stride length present, total distance present, running
        speed_encoded = int(self.speed_mps * 256)
        cadence_encoded = self.cadence_rpm
        stride_length_encoded = int(self.stride_length_m * 100)
        total_distance_encoded = int(self.total_distance_m * 10)

        measurement = struct.pack(
            '<BHBHI',
            flags,
            speed_encoded,
            cadence_encoded,
            stride_length_encoded,
            total_distance_encoded
        )

        # Periodic status update
        if int(self.total_distance_m) % 100 < 2:
            print(f"📊 Distance: {self.total_distance_m:.1f}m | "
                  f"Speed: {self.pace_kmh:.1f} km/h | "
                  f"Cadence: {self.cadence_rpm} RPM")

        return measurement


def find_adapter(bus):
    """Find the Bluetooth adapter"""
    remote_om = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, '/'),
                                DBUS_OM_IFACE)
    objects = remote_om.GetManagedObjects()

    for o, props in objects.items():
        if GATT_MANAGER_IFACE in props.keys():
            return o

    return None


def main():
    print("=" * 60)
    print("  Bluetooth Footpod Sensor for Garmin Watch")
    print("  Raspberry Pi Version")
    print("=" * 60)

    # Initialize D-Bus
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()

    # Find adapter
    adapter_path = find_adapter(bus)
    if not adapter_path:
        print('❌ BLE adapter not found!')
        sys.exit(1)

    print(f"📡 Using adapter: {adapter_path}")

    # Create pace sensor
    pace_sensor = PaceSensor(PACE_KMH, CADENCE_RPM)

    # Create GATT application
    app = Application(bus)
    service = RSCService(bus, 0, pace_sensor)
    app.add_service(service)

    # Register GATT application
    service_manager = dbus.Interface(
        bus.get_object(BLUEZ_SERVICE_NAME, adapter_path),
        GATT_MANAGER_IFACE)

    # Create advertisement
    adv = Advertisement(bus, 0, 'peripheral')
    adv.add_service_uuid(RSC_SERVICE_UUID)
    adv.local_name = 'Footpod'

    # Register advertisement
    ad_manager = dbus.Interface(
        bus.get_object(BLUEZ_SERVICE_NAME, adapter_path),
        LE_ADVERTISING_MANAGER_IFACE)

    mainloop = GLib.MainLoop()

    def update_measurement():
        """Periodic update of measurement data"""
        service.measurement_chrc.update_measurement()
        return True  # Continue the timer

    # Register GATT and advertising
    try:
        service_manager.RegisterApplication(app.get_path(), {},
                                            reply_handler=lambda: None,
                                            error_handler=lambda error: print(f'❌ Failed to register app: {error}'))
        
        ad_manager.RegisterAdvertisement(adv.get_path(), {},
                                         reply_handler=lambda: None,
                                         error_handler=lambda error: print(f'❌ Failed to register advertisement: {error}'))

        print("\n" + "="*60)
        print("🏃 BLE Footpod Sensor Started!")
        print("="*60)
        print(f"📍 Device Name: Footpod")
        print(f"⚡ Speed: {pace_sensor.pace_kmh:.1f} km/h ({pace_sensor.speed_mps:.2f} m/s)")
        print(f"👟 Cadence: {pace_sensor.cadence_rpm} RPM")
        print(f"📏 Stride Length: {pace_sensor.stride_length_m:.2f} m")
        print(f"⏱️  Pace: {60 / pace_sensor.pace_kmh:.2f} min/km")
        print(f"\n🔵 Broadcasting RSC Service: {RSC_SERVICE_UUID}")
        print("\n" + "="*60)
        print("📱 CONNECTING YOUR GARMIN WATCH:")
        print("="*60)
        print("1. Start a Run/Walk activity on your watch")
        print("2. Swipe down → Sensors & Accessories → Add New")
        print("3. Select 'Foot Pod'")
        print("4. Look for 'Footpod' and select it")
        print("\n💡 Keep devices within 10 feet during pairing")
        print("="*60)
        print("\n⏸️  Press Ctrl+C to stop\n")

        # Update measurement every second
        GLib.timeout_add_seconds(1, update_measurement)

        # Handle Ctrl+C
        def signal_handler(sig, frame):
            print("\n\n⏹️  Stopping pace sensor...")
            mainloop.quit()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        mainloop.run()

    except Exception as e:
        print(f"❌ Error: {e}")
        mainloop.quit()

    print("✅ Pace sensor stopped")


if __name__ == '__main__':
    main()
