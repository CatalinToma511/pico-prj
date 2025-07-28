import asyncio
import time
from ble_central import BLE_Central
from car import Car

async def main_task():
    ble = BLE_Central("PicoW_BLE")
    my_car = Car(2,3,9,5)
    tasks = [
        asyncio.create_task(ble.characteristic_listener(ble.controls_characteristic, my_car.process_data)),
        asyncio.create_task(ble.connection_task()),
        asyncio.create_task(ble.blink_task())
    ]
    await asyncio.gather(*tasks) # type: ignore

def run():
    asyncio.run(main_task())