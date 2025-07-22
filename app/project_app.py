import asyncio
import time
from ble_central import BLE_Central
from car import Car

def controls_callback(data):
    print(data)

async def main_task():
    ble = BLE_Central("PicoW_BLE")
    global my_car
    my_car = Car(2,3,7,5)
    tasks = [
        asyncio.create_task(ble.characteristic_listener(ble.controls_characteristic, controls_callback)),
        asyncio.create_task(ble.connection_task())
    ]
    await asyncio.gather(*tasks) # type: ignore

def run():
    asyncio.run(main_task())