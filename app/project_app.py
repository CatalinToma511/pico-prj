import asyncio
import time
from ble_central import BLE_Central
from car import Car

MOTOR_IN1 = 2
MOTOR_IN2 = 3
STEERING_PIN = 9
GEARBOX_SHIFT_PIN = 5
HORN_PIN = 11
MPU_BUS_ID = 1
MPU_SCL_PIN = 19
MPU_SDA_PIN = 18
VOLTAGE_PIN = 26

async def main_task():
    ble = BLE_Central("PicoW_BLE")
    my_car = Car(MOTOR_IN1,
                 MOTOR_IN2,
                 STEERING_PIN,
                 GEARBOX_SHIFT_PIN,
                 HORN_PIN,
                 VOLTAGE_PIN,
                 MPU_BUS_ID,
                 MPU_SCL_PIN,
                 MPU_SDA_PIN)
    tasks = [
        asyncio.create_task(ble.connection_task()),
        asyncio.create_task(ble.blink_task()),
        asyncio.create_task(ble.characteristic_listener(ble.controls_characteristic, my_car.process_data)),
        asyncio.create_task(ble.send_parameters(ble.parameters_characteristic, my_car.get_parameters_encoded)),
        asyncio.create_task(my_car.smooth_controls()),
    ]
    await asyncio.gather(*tasks) # type: ignore

def run():
    asyncio.run(main_task())