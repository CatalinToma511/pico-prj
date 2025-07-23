import asyncio
import time
from ble_central import BLE_Central
from car import Car

def controls_callback(data):
    # for b in data:
    #     print(b, ' ')
    global my_car
    spd = data[0] - data[1]
    if spd != 0:
        my_car.led.on()
    else:
        my_car.led.off()

    if spd >= 0:
        my_car.motor.set_direction(1)
    else:
        my_car.motor.set_direction(-1)

        # speed
    my_car.motor.set_speed(int(abs(spd)/255 * 100))
        
    # steering
    my_car.steering.set_steering_position(data[2] - 128)


async def main_task():
    ble = BLE_Central("PicoW_BLE")
    global my_car
    my_car = Car(2,3,8,5)
    tasks = [
        asyncio.create_task(ble.characteristic_listener(ble.controls_characteristic, controls_callback)),
        asyncio.create_task(ble.connection_task())
    ]
    await asyncio.gather(*tasks) # type: ignore

def run():
    asyncio.run(main_task())