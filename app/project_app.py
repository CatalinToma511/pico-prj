import asyncio
import time
from ble_central import BLE_Central
from car import Car

MOTOR_IN1 = 12
MOTOR_IN2 = 13
STEERING_PIN = 0
GEARBOX_SHIFT_PIN = 1
HORN_PIN = 2
VOLTAGE_PIN = 26
MPU_BUS_ID = 0
MPU_SCL_PIN = 21
MPU_SDA_PIN = 20
VL53L0X_BUS_ID = 0
VL53L0X_SCL_PIN = 21
VL53L0X_SDA_PIN = 20


async def main_task():
    ble = BLE_Central("PicoW_BLE")
    my_car = Car()
    my_car.config_motor(MOTOR_IN1, MOTOR_IN2)
    my_car.config_steering(STEERING_PIN)
    my_car.config_gearbox(GEARBOX_SHIFT_PIN)
    my_car.config_horn(HORN_PIN)
    my_car.config_voltage_reader(VOLTAGE_PIN)
    my_car.config_mpu6050(MPU_BUS_ID, MPU_SCL_PIN, MPU_SDA_PIN)
    my_car.config_distance_sensor(VL53L0X_BUS_ID, VL53L0X_SCL_PIN, VL53L0X_SDA_PIN)
    tasks = [
        asyncio.create_task(ble.connection_task()),
        asyncio.create_task(ble.no_connection_blink()),
        asyncio.create_task(ble.characteristic_listener(ble.controls_characteristic, my_car.process_data)),
        asyncio.create_task(ble.send_parameters(ble.parameters_characteristic, my_car.get_parameters_encoded)),
        asyncio.create_task(my_car.aquire_sensors_data()),
        asyncio.create_task(my_car.update()),
    ]
    await asyncio.gather(*tasks) # type: ignore

def run():
    asyncio.run(main_task())