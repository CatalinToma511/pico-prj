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
        self.led = machine.Pin("LED", machine.Pin.OUT)
        #self.mpu6050 = MPU6050(0, 21, 20)
        #self.mpu6050.calibrate_aceel()
              
        
    def process_moving_data(self, data):
        print(data)
        # validation
        if (len(data) != 20 or
            data[0].upper() != 'W' or
            data[1].upper() != 'S' or
            data[2].upper() != 'A' or
            data[3].upper() != 'D' or
            data[4].upper() != 'Q' or
            data[5].upper() != 'E' or
            ord(data[6]) - 33 > 10 or       # speed
            (data[7]) not in '01') :         # gear
            print(f'Invalid moving data received: {data}')
            return
        # direction
        if data[0] == 'W' and data[1] == 's' and self.motor.direction != 1:
            self.motor.set_direction(1)
            
        elif data[0] == 'w' and data[1] == 'S' and self.motor.direction != -1:
            self.motor.set_direction(-1)
            
        elif (((data[0] == 'w' and data[1] == 's') or (data[0] == 'W' and data[1] == 'S')) and
              self.motor.direction != 0):
            self.motor.set_direction(0)
            
        # steering
        steering_char = ''.join(char for char in data[2:6] if char.isupper())
        if (len(steering_char) > 1 or len(steering_char) == 0) and self.steering.steer_position != 0:
            self.steering.set_steering_position(0)
            self.led.off()
        elif steering_char == 'A' and self.steering.steer_position != -2:
            self.steering.set_steering_position(-2)
            self.led.on()
        elif steering_char == 'Q' and self.steering.steer_position != -1:
            self.steering.set_steering_position(-1)
            self.led.on()
        elif steering_char == 'E' and self.steering.steer_position != 1:
            self.steering.set_steering_position(1)
            self.led.on()
        elif steering_char == 'D' and self.steering.steer_position != 2:
            self.steering.set_steering_position(2)
            self.led.on()
            
        # gearbox
        if data[7] == '0' and self.gearbox.gear != 0:
            self.gearbox.set_gear(0)
        elif data[7] == '1' and self.gearbox.gear != 1:
            self.gearbox.set_gear(1)
            
        # speed
        print(f'{self.motor.speed} {(ord(data[6]) - 33) * 10}')
        if self.motor.speed != (ord(data[6]) - 33) * 10:
            print(f'new speed')
            self.motor.set_speed((ord(data[6]) - 33) * 10)