import machine
import sys
import aioble
import bluetooth
import machine
import uasyncio as asyncio
import utime

from micropython import const
from car import Car

my_car = Car(2, 3, 7, 5)


def uid():
    """ Return the unique id of the device as a string """
    return "{:02x}{:02x}{:02x}{:02x}{:02x}{:02x}{:02x}{:02x}".format(*machine.unique_id())


# constants
MANUFACTURER_ID = const(0x02A29)
MODEL_NUMBER_ID = const(0x2A24)
SERIAL_NUMBER_ID = const(0x2A25)
HARDWARE_REVISION_ID = const(0x2A26)
BLE_VERSION_ID = const(0x2A28)

_DEVICE_INFO_UUID = bluetooth.UUID(0xFFFF) # Device Information
_GENERIC = bluetooth.UUID(0x1848)
_MOVING_UUID = bluetooth.UUID(0x2A70)
_LIGHTS_UUID = bluetooth.UUID(0x2A71)
_ROBOT = bluetooth.UUID(0x1800)

_BLE_APPEARANCE_GENERIC_REMOTE_CONTROL = const(384)

ADV_INTERVAL_MS = 25_000

# Create Service for device info 
device_info = aioble.Service(_DEVICE_INFO_UUID)
# Create Characteristic for device info
aioble.Characteristic(device_info, bluetooth.UUID(MANUFACTURER_ID), read=True, initial="Eu")
aioble.Characteristic(device_info, bluetooth.UUID(MODEL_NUMBER_ID), read=True, initial="1.0")
aioble.Characteristic(device_info, bluetooth.UUID(SERIAL_NUMBER_ID), read=True, initial=uid())
aioble.Characteristic(device_info, bluetooth.UUID(HARDWARE_REVISION_ID), read=True, initial=sys.version)
aioble.Characteristic(device_info, bluetooth.UUID(BLE_VERSION_ID), read=True, initial="1.0")

# Create Service for random things
remote_service = aioble.Service(_GENERIC)
# Create Chracteristic for random things
moving_characteristic = aioble.Characteristic(
    remote_service, _MOVING_UUID, write = True, read=True, notify=True, capture=True, initial="0")
lights_characteristic = aioble.Characteristic(
    remote_service, _LIGHTS_UUID, write = True, read=True, notify=True, capture=True, initial="0")

# Registering all Services
print("Registering services")
aioble.register_services(remote_service, device_info)

connected = False
connection = None



# Task to process lights characteristic data 
async def listen_moving_characteristic_task():
    while True:
        data  = (await moving_characteristic.written())[1].decode('utf-8')
        for c in data:
            print(c, end='')
        print('')
        my_car.process_moving_data(data)



async def connection_task():
    """ Task to handle the connection """
    global connected, connection
    while True:
        print("Waiting for connection")
        connected = False
        connection = await aioble.advertise(ADV_INTERVAL_MS,
                                            name="Masinuta",
                                            appearance=_BLE_APPEARANCE_GENERIC_REMOTE_CONTROL,
                                            services=[_ROBOT])
        connected = True
        print("Connection from, ", connection.device)

        await connection.disconnected(timeout_ms = None)
        print("disconnected")


async def main():
    tasks = [
        asyncio.create_task(listen_moving_characteristic_task()),
        asyncio.create_task(connection_task()),
    ]
    await asyncio.gather(*tasks)

asyncio.run(main())