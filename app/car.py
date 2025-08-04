from motor import Motor
from gearbox import Gearbox
from steering import Steering
from mpu6050 import MPU6050
from horn import Horn
from voltagereader import VoltageReader
import asyncio
import machine
import time
import struct

class Car:
    def __init__(self,
                 motor_in1,
                 motor_in2,
                 steering_pin,
                 gearbox_shift_pin,
                 horn_pin,
                 voltage_pin,
                 mpu_bus_id,
                 mpu_scl_pin,
                 mpu_sda_pin):
        self.motor = Motor(motor_in1, motor_in2)
        self.gearbox = Gearbox(gearbox_shift_pin)
        self.steering = Steering(steering_pin)
        self.horn = Horn(horn_pin)
        self.voltage_reader = VoltageReader(pin=voltage_pin)
        self.mpu6050 = MPU6050(mpu_bus_id, mpu_scl_pin, mpu_sda_pin)
        self.voltage_reader = VoltageReader(pin=26)

        self.mpu6050.calibrate_accelerometer()

        self.speed_target = self.motor.speed
        self.steering_target = self.steering.steer_position
        self.max_speed_increase = 3
        self.max_speed_decrease = 5
        self.max_steering_change = 30

        self.smooth_control_running = True
        self.smooth_control_interval_ms = 25

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
            left_button = data[3]
            right_button = data[4]
            if left_button and not right_button:
                self.gearbox.set_gear(0)
            elif right_button and not left_button:
                self.gearbox.set_gear(1)

            # horn
            horn_button = data[5]
            if horn_button:
                self.horn.turn_on()
            else:
                self.horn.turn_off()
        except Exception as e:
            print(f"Error processing data: {e}")

    async def smooth_controls(self):
        while self.smooth_control_running:
            speed_step = 0
            # if target speed is the same as current speed, do nothing
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

            # steering_step = 0
            # # if target steering is the same as current steering, do nothing
            # if self.steering_target == self.steering.steer_position:
            #     steering_step = 0
            # # steering left -> step should increase current value
            # if self.steering_target > self.steering.steer_position:
            #     difference = self.steering_target - self.steering.steer_position
            #     steering_step = min(self.max_steering_change, difference)
            # # steering right -> step should decrease current value
            # elif self.steering_target < self.steering.steer_position:
            #     difference = self.steering.steer_position - self.steering_target
            #     steering_step = (-1) * min(self.max_steering_change, difference)
            # # if the steering step is not zero, update the steering position
            # if steering_step != 0:
            #     self.steering.set_steering_position(self.steering.steer_position + steering_step)

            # for now, no smooth steering
            self.steering.set_steering_position(self.steering_target)

            await asyncio.sleep_ms(self.smooth_control_interval_ms)

    def get_parameters_encoded(self):
        try:
            # since the maximum voltage is 10V and the precision is 0.1V, we can multiply by 10
            voltage = int(self.voltage_reader.read() * 10)

            # get MPU6050 position, 2 numbers between -180 and 180
            roll, pitch = self.mpu6050.read_position()

            # encode the parameters as a byte array
            data = [voltage, roll, pitch]  # Placeholder for other parameters
            print(f'Parameters before encoding: {data}')
            encoded_data = struct.pack('>Bhh', *data)

            return encoded_data
        except Exception as e:
            print(f"Error encoding parameters: {e}")
            return b'/x00'