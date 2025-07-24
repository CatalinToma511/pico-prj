import asyncio
import time
from ble_central import BLE_Central
from car import Car

def controls_callback(data):
    global my_car
    # speed
    spd = data[0] - data[1] #RT - LT
    if spd >= 0:
        # positive value means go forward
        my_car.motor.set_direction(1)
    else:
        # negative value go backwards
        my_car.motor.set_direction(-1)
    my_car.motor.set_speed(int(abs(spd)/255 * 100))
        
    # steering
    l_joystick_x = data[2] - 128
    my_car.steering.set_steering_position(l_joystick_x)

    #gearbox
    left_button = data[3]
    right_button = data[4]
    if left_button and not right_button:
        my_car.gearbox.set_gear(0)
    elif right_button and not left_button:
        my_car.gearbox.set_gear(1)



async def main_task():
    ble = BLE_Central("PicoW_BLE")
    global my_car
    my_car = Car(2,3,9,5)
    tasks = [
        asyncio.create_task(ble.characteristic_listener(ble.controls_characteristic, controls_callback)),
        asyncio.create_task(ble.connection_task()),
        asyncio.create_task(ble.blink_task())
    ]
    await asyncio.gather(*tasks) # type: ignore

def run():
    asyncio.run(main_task())