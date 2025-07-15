import asyncio
import time
from ble_central import BLE_Central

def controls_callback(data):
    print(data)

async def main_task():
    ble = BLE_Central("PicoW_BLE")
    tasks = [
        asyncio.create_task(ble.characteristic_listener(ble.controls_characteristic, controls_callback)),
        asyncio.create_task(ble.connection_task())
    ]
    await asyncio.gather(*tasks)

def run():
    asyncio.run(main_task())