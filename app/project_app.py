import asyncio
import time
from ble_central import BLE_Central
from car import Car

XINPUT_GAMEPAD_DPAD_UP_MASK = 0x0001
XINPUT_GAMEPAD_DPAD_DOWN_MASK = 0x0002
XINPUT_GAMEPAD_DPAD_LEFT_MASK = 0x0004
XINPUT_GAMEPAD_DPAD_RIGHT_MASK = 0x0008
XINPUT_GAMEPAD_START_MASK = 0x0010
XINPUT_GAMEPAD_BACK_MASK = 0x0020
XINPUT_GAMEPAD_LEFT_THUMB_MASK = 0x0040
XINPUT_GAMEPAD_RIGHT_THUMB_MASK = 0x0080
XINPUT_GAMEPAD_LEFT_SHOULDER_MASK = 0x0100
XINPUT_GAMEPAD_RIGHT_SHOULDER_MASK = 0x0200
XINPUT_GAMEPAD_A_MASK = 0x1000
XINPUT_GAMEPAD_B_MASK = 0x2000
XINPUT_GAMEPAD_X_MASK = 0x4000
XINPUT_GAMEPAD_Y_MASK = 0x8000

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

    buttons = data[3]
    #gearbox
    left_button = (buttons & XINPUT_GAMEPAD_LEFT_SHOULDER_MASK) != 0
    right_button = (buttons & XINPUT_GAMEPAD_RIGHT_SHOULDER_MASK) != 0
    if left_button and not right_button:
        my_car.gearbox.set_gear(0)
    elif right_button and not left_button:
        my_car.gearbox.set_gear(1)



async def main_task():
    ble = BLE_Central("PicoW_BLE")
    global my_car
    my_car = Car(2,3,8,5)
    tasks = [
        asyncio.create_task(ble.characteristic_listener(ble.controls_characteristic, controls_callback)),
        asyncio.create_task(ble.connection_task()),
        asyncio.create_task(ble.blink_task())
    ]
    await asyncio.gather(*tasks) # type: ignore

def run():
    asyncio.run(main_task())