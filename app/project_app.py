import time
import machine
from machine import Timer
from app.ble_server import BLE_Server
from car import Car

_MOTOR_IN1 = 12
_MOTOR_IN2 = 13
_MOTOR_ENC_A = 17
_MOTOR_ENC_B = 16

_STEERING_PIN = 2
_GEARBOX_SHIFT_PIN = 3
_HORN_PIN = 4
_VOLTAGE_PIN = 26
_MPU_BUS_ID = 0
_MPU_SCL_PIN = 21
_MPU_SDA_PIN = 20
_VL53L0X_BUS_ID = 0
_VL53L0X_SCL_PIN = 21
_VL53L0X_SDA_PIN = 20
_FL_SERVO_PIN = 8
_FR_SERVO_PIN = 9
_RL_SERVO_PIN = 10
_RR_SERVO_PIN = 11

_RECEIVER_CHANNEL_PINS = [28, 27, 22, 19, 18, 15]

MAIN_PERIOD_MS = 10
TELEMETRY_INTERVAL_MS = 100
ACQUIRE_SENSOR_INTERVAL_MS = 25
CAR_UPDATE_INTERVAL_MS = 10

app = None

class App():
    def __init__(self):
        self.my_car = Car()
        self.ble = BLE_Server("PicoW_BLE", controls_callback=self.my_car.process_data)
        self.loop_timer = Timer()
        self.last_telemetry_time = 0
        self.last_sensor_data_time = 0
        self.overtime_count = 0
        self.time_now = 0

    def config(self):
        self.my_car.config_motor(_MOTOR_IN1, _MOTOR_IN2, _MOTOR_ENC_A, _MOTOR_ENC_B)
        self.my_car.config_steering(_STEERING_PIN, 84.5, 140, 39)
        self.my_car.config_gearbox(_GEARBOX_SHIFT_PIN)
        self.my_car.config_horn(_HORN_PIN)
        self.my_car.config_voltage_reader(_VOLTAGE_PIN)
        # my_car.config_distance_sensor(_VL53L0X_BUS_ID, _VL53L0X_SCL_PIN, _VL53L0X_SDA_PIN)
        servo_cfg = [('fl', _FL_SERVO_PIN, 45, 111),
                     ('fr', _FR_SERVO_PIN, 137, 72),
                     ('rl', _RL_SERVO_PIN, 42, 117),
                     ('rr', _RR_SERVO_PIN, 132, 57)]
        self.my_car.config_suspension(servo_cfg, full_range_time_ms=600)
        self.my_car.config_receiver(_RECEIVER_CHANNEL_PINS)
        self.my_car.config_mpu6050(_MPU_BUS_ID, _MPU_SCL_PIN, _MPU_SDA_PIN)
        self.ble.advertise()
        self.loop_timer.init(freq = int(1000/MAIN_PERIOD_MS), mode=Timer.PERIODIC, callback=self.control_loop)

    def control_loop(self, timer):
        try:
            self.time_now = time.ticks_ms()
            self.ble.blink_task()
            if time.ticks_diff(self.time_now, self.last_telemetry_time) > TELEMETRY_INTERVAL_MS:
                self.ble.send_parameters(self.my_car.get_parameters_encoded)
                self.last_telemetry_time = self.time_now
            if time.ticks_diff(self.time_now, self.last_sensor_data_time) > ACQUIRE_SENSOR_INTERVAL_MS:
                self.my_car.acquire_sensors_data()
                self.last_sensor_data_time = self.time_now
        except Exception as e:
            print(f'Err runing main loop: {e}')
            self.my_car.stop_car_activity()

    def start_control_loop(self):
        self.loop_timer.init(freq = int(1000/MAIN_PERIOD_MS), mode=Timer.PERIODIC, callback=self.control_loop)

def run():
    global app
    try:
        app = App()
        app.config()
        app.start_control_loop()
        while True:
            time.sleep(1)
    except Exception as e:
        print(f'Error in main: {e}')
