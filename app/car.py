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
        if len(data) != 20:         # gear
            print(f'Invalid moving data received: {data}')
            return
            
        # direction
        spd = int.from_bytes(data[0], byteorder='big', signed=True)
        if spd != 0:
            self.led.on()
        else:
            self.led.off()

        if spd >= 0:
            self.motor.set_direction(1)
        else:
            self.motor.set_direction(-1)

         # speed
        self.motor.set_speed(abs(spd)/128 * 100)
            
        # steering
        self.steering.set_steering_position(data[1])
            
        # gearbox
        # if data[7] == '0' and self.gearbox.gear != 0:
        #     self.gearbox.set_gear(0)
        # elif data[7] == '1' and self.gearbox.gear != 1:
        #     self.gearbox.set_gear(1)