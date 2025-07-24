from motor import Motor
from gearbox import Gearbox
from steering import Steering
from mpu6050 import MPU6050
import machine

class Car:
    def __init__(self, motor_in1, motor_in2, steering_pin, gearbox_shift_pin):
        self.motor = Motor(motor_in1, motor_in2)
        self.gearbox = Gearbox(gearbox_shift_pin)
        self.steering = Steering(steering_pin)
        #self.mpu6050 = MPU6050(0, 21, 20)
        #self.mpu6050.calibrate_aceel()