from motor import Motor
from gearbox import Gearbox
from steering import Steering
from mpu6050 import MPU6050
from horn import Horn
from voltagereader import VoltageReader
from vl53l0x import VL53L0X
import asyncio
import machine
import time
import struct

class Car:
    def __init__(self):
        self.motor = None
        self.gearbox = None
        self.steering = None
        self.horn = None
        self.voltage_reader = None
        self.mpu6050 = None
        self.distance_sensor = None

        self.speed_target = 0
        self.steering_target = None
        self.max_speed_increase = 0
        self.max_speed_decrease = 0
        self.max_steering_change = 0
        self.distance_offset = 0

        self.smooth_control_running = True
        self.smooth_control_interval_ms = 25

    def config_motor(self, motor_in1, motor_in2, max_speed_increase=5, max_speed_decrease=10):
        self.motor = Motor(motor_in1, motor_in2)
        self.max_speed_increase = max_speed_increase
        self.max_speed_decrease = max_speed_decrease
        self.speed_target = 0

    def config_steering(self, steering_pin, max_steering_change=30):
        self.steering = Steering(steering_pin)
        self.max_steering_change = max_steering_change
        self.steering_target = self.steering.steer_position
    
    def config_gearbox(self, gearbox_shift_pin):
        self.gearbox = Gearbox(gearbox_shift_pin)

    def config_horn(self, horn_pin):
        self.horn = Horn(horn_pin)

    def config_voltage_reader(self, voltage_pin):
        self.voltage_reader = VoltageReader(pin=voltage_pin)

    def config_mpu6050(self, bus_id, scl_pin, sda_pin):
        try:
            self.mpu6050 = MPU6050(bus_id, scl_pin, sda_pin)
            self.mpu6050.calibrate_accelerometer()
        except Exception as e:
            print(f"Error initializing MPU6050: {e}")
            self.mpu6050 = None

    def config_distance_sensor(self, bus_id, scl_pin, sda_pin):
        try:
            i2c = machine.I2C(id=bus_id, scl=scl_pin, sda=sda_pin)
            self.distance_sensor = VL53L0X(i2c)
            self.distance_sensor.set_measurement_timing_budget(250000)
            self.distance_sensor.set_Vcsel_pulse_period(self.distance_sensor.vcsel_period_type[0], 14)
            self.distance_sensor.set_Vcsel_pulse_period(self.distance_sensor.vcsel_period_type[1], 10)
            self.distance_sensor.start()
            self.distance_offset = -50
        except Exception as e:
            print(f"Error initializing distance sensor: {e}")
            self.distance_sensor = None

    def process_data(self, data):
        try:
            # restart the Pico if needed
            if data == b'RESET':
                print("Resetting the machine...")
                machine.reset()

            # speed
            spd = data[0] - data[1] #RT - LT
            self.speed_target = int(spd/255 * 100)
                
            # steering
            l_joystick_x = data[2] - 128
            self.steering_target = l_joystick_x

            #gearbox
            if self.gearbox:
                left_button = data[3]
                right_button = data[4]
                if left_button and not right_button:
                    self.gearbox.set_gear(0)
                elif right_button and not left_button:
                    self.gearbox.set_gear(1)

            # horn
            if self.horn:
                horn_button = data[5]
                if horn_button:
                    self.horn.turn_on()
                else:
                    self.horn.turn_off()
        except Exception as e:
            print(f"Error processing data: {e}")

    async def smooth_controls(self):
        while self.smooth_control_running:
            if self.motor:
                # if target speed is the same as current speed, do nothing
                speed_step = 0
                if self.speed_target == self.motor.speed:
                    speed_step = 0
                # accelerating when going forward -> step should increase current val
                elif self.speed_target > self.motor.speed and self.motor.speed >= 0:
                    difference = self.speed_target - self.motor.speed
                    speed_step = min(self.max_speed_increase, difference)
                # accelerating when going backward -> step should decrease current val
                elif self.speed_target < self.motor.speed and self.motor.speed <= 0:
                    difference = self.motor.speed - self.speed_target
                    speed_step = (-1) * min(self.max_speed_increase, difference)
                # braking when going forward -> step should decrease current val
                elif self.speed_target < self.motor.speed and self.motor.speed >= 0:
                    difference = self.motor.speed - self.speed_target
                    # added distance to 0 to avoid accelerating with brake rate
                    speed_step = (-1) * min(self.max_speed_decrease, difference, self.motor.speed)
                # braking when going backward -> step should increase current val
                elif self.speed_target > self.motor.speed and self.motor.speed <= 0:
                    difference = self.speed_target - self.motor.speed
                    # added distance to 0 to avoid accelerating with brake rate
                    speed_step = min(self.max_speed_decrease, difference, abs(self.motor.speed))
                # if the speed step is not zero, update the motor speed
                if speed_step != 0:
                    self.motor.set_speed(self.motor.speed + speed_step)

            # for now, no smooth steering
            if self.steering:
                self.steering.set_steering_position(self.steering_target)

            await asyncio.sleep_ms(self.smooth_control_interval_ms)

    def get_parameters_encoded(self):
        try:
            # since the maximum voltage is 10V and the precision is 0.1V, we can multiply by 10
            voltage = 0
            if self.voltage_reader:
                voltage = int(self.voltage_reader.read() * 10)

            # get MPU6050 position, 2 numbers between -180 and 180
            roll, pitch = 0, 0
            if self.mpu6050:
                roll, pitch = self.mpu6050.read_position()

            distance = 0
            if self.distance_sensor:
                distance = self.distance_sensor.read() + self.distance_offset

            # encode the parameters as a byte array
            data = [voltage, roll, pitch, distance]  # Placeholder for other parameters
            encoded_data = struct.pack('>Bhhh', *data)

            return encoded_data
        except Exception as e:
            print(f"Error encoding parameters: {e}")
            return b'/x00'