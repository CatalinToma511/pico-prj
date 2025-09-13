import time
from app.ble_server import BLE_Server
from car import Car

_MOTOR_IN1 = 12
_MOTOR_IN2 = 13
_MOTOR_ENC_A = 17
_MOTOR_ENC_B = 16
_MOTOR_DEBUG_PIN = 4
_MOTOR_PWM_IRQ_PIN = 5
_STEERING_PIN = 2
_GEARBOX_SHIFT_PIN = 1
_HORN_PIN = 3
_VOLTAGE_PIN = 26
_MPU_BUS_ID = 0
_MPU_SCL_PIN = 21
_MPU_SDA_PIN = 20
_VL53L0X_BUS_ID = 0
_VL53L0X_SCL_PIN = 21
_VL53L0X_SDA_PIN = 20

MAIN_PERIOD_MS = 20
overtime_cnt = 0

def run():
    try:
        my_car = Car()
        my_car.config_motor(_MOTOR_IN1, _MOTOR_IN2, _MOTOR_ENC_A, _MOTOR_ENC_B, _MOTOR_DEBUG_PIN, _MOTOR_PWM_IRQ_PIN)
        my_car.config_steering(_STEERING_PIN)
        my_car.config_gearbox(_GEARBOX_SHIFT_PIN)
        my_car.config_horn(_HORN_PIN)
        my_car.config_voltage_reader(_VOLTAGE_PIN)
        my_car.config_mpu6050(_MPU_BUS_ID, _MPU_SCL_PIN, _MPU_SDA_PIN)
        my_car.config_distance_sensor(_VL53L0X_BUS_ID, _VL53L0X_SCL_PIN, _VL53L0X_SDA_PIN)
        ble = BLE_Server("PicoW_BLE", controls_callback=my_car.process_data)
        ble.advertise()

        while True:
            time1 = time.ticks_ms()
            ble.blink_task()
            # ble.send_parameters(my_car.get_parameters_encoded)
            my_car.aquire_sensors_data()
            my_car.update()
            time2 = time.ticks_ms()
            loop_exec_time = time.ticks_diff(time2, time1)
            if loop_exec_time < MAIN_PERIOD_MS:
                time.sleep_ms(MAIN_PERIOD_MS - loop_exec_time)
            else:
                overtime_cnt += 1

    except Exception as e:
        print(f'Err runing main loop: {e}')
        my_car.stop_car_activity()