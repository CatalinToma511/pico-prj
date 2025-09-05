from motor import Motor
from gearbox import Gearbox
from steering import Steering
from mpu6050 import MPU6050
from horn import Horn
from voltagereader import VoltageReader
from distance_sensor import DistanceSensor
import machine
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
        self.motor_rps = 0
        self.wheel_speed = 0
        self.speed_mmps = 0
        self.steering_target = None
        self.steering_angle = 0
        self.max_steering_change = 0
        self.max_speed_rps = 0

        self.update_interval_ms = 25

        self.aquire_data_interval_ms = 25

        self.battery_voltage = 0
        self.roll = 0
        self.pitch = 0
        self.distance_mm = 0

        self.aeb = False
        self.aeb_safety_distance_mm = 500
        self.aeb_max_safe_speed_mmps = 500
        self.aeb_max_safe_speed_rps = 666
        self.drive_train_backlash_mm = 30

        self.wheel_diameter_mm = 82

        self.gearing_ratio = 1

    def config_motor(self, motor_in1, motor_in2, enc_a, enc_b):
        self.motor = Motor(motor_in1, motor_in2, enc_a, enc_b)
        self.speed_target = 0
        self.motor.start_control_loop()

    def config_steering(self, steering_pin, max_steering_change=30):
        self.steering = Steering(steering_pin)
        self.max_steering_change = max_steering_change
        self.steering_target = self.steering.position
    
    def config_gearbox(self, gearbox_shift_pin):
        self.gearbox = Gearbox(gearbox_shift_pin)

    def config_horn(self, horn_pin):
        self.horn = Horn(horn_pin)

    def config_voltage_reader(self, voltage_pin):
        self.voltage_reader = VoltageReader(pin=voltage_pin)

    def config_mpu6050(self, bus_id, scl_pin, sda_pin):
        try:
            self.mpu6050 = MPU6050(bus_id, scl_pin, sda_pin)
        except Exception as e:
            print(f"Error initializing MPU6050: {e}")
            self.mpu6050 = None

    def config_distance_sensor(self, bus_id, scl_pin, sda_pin):
        try:
            self.distance_sensor = DistanceSensor(bus_id, scl_pin, sda_pin)
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
            self.steering_target = int(l_joystick_x)

            #gearbox
            if self.gearbox:
                left_button = data[3]
                right_button = data[4]
                if left_button and not right_button:
                    self.gearbox.set_gear(0)
                elif right_button and not left_button:
                    self.gearbox.set_gear(1)
                self.gearing_ratio = self.gearbox.get_gearing_ratio()

            # horn
            if self.horn:
                horn_button = data[5]
                if horn_button:
                    self.horn.turn_on()
                else:
                    self.horn.turn_off()

            # limit
            if self.motor:
                speed_limit = data[6]
                self.motor.set_speed_limit_factor(speed_limit / 100)

            # aeb:
            if self.motor and self.distance_sensor:
                aeb_state = data[7]
                self.aeb = bool(aeb_state)

            # control mode
            if self.motor and self.motor.pid:
                mode = data[8]
                self.motor.pid.set_mode(mode)

        except Exception as e:
            print(f"Error processing data: {e}")

    def aquire_sensors_data(self):
        try:
            if self.voltage_reader:
                # read voltage in decavolts to avoid using float
                self.voltage = int(self.voltage_reader.read() * 10)
                # battery safety, put pico to sleep if voltage is too low
                # if battery level under 6.5V
                # take account for situations when motor draws battery tension down

                # !seems to cause issues, will check later a better method
                # if self.voltage < 65 and self.motor and self.motor.get_speed_rps() == 0 and self.motor.pid.target_rps == 0: 
                #     self.stop_car_activity()
                #     print("Battery voltage too low, going to sleep...")
                #     machine.deepsleep()

            if self.mpu6050:
                self.roll, self.pitch = self.mpu6050.read_position()

            if self.distance_sensor:
                    self.distance_mm = int(self.distance_sensor.read())
        except Exception as e:
                    print(f'Error while reading distance sensor data: {e}')

    def aeb_max_safe_speed(self):
        # calculate the speed at which the car can stop within the safe distance to the object
        # d = v^2 / (2 * a)
        # so, the stopping distance is: current_speed^2 / (2 * wheel_decel)
        # the stopping distance + aeb max safe speed is also the maximum accepted distance for the specific speed
        # so the maximum speed at which the car can safely stop is: sqrt(desired stopping distance * 2 * wheel_decel)
        if self.distance_sensor and self.motor and self.aeb:
            # stopping distance is within a safety margin to the obstacle
            stopping_distance = self.distance_mm - self.aeb_safety_distance_mm - self.drive_train_backlash_mm
            stopping_distance = max(0, stopping_distance) # cannot be negative
            wheel_decel = self.motor.pid.max_decel * self.gearing_ratio * 3.1415 * self.wheel_diameter_mm
            max_safe_speed_mmps = (2 * stopping_distance * wheel_decel) ** 0.5
            # clamp value between 0 and motor max rps
            max_safe_speed_mmps = max(0, min(max_safe_speed_mmps, self.max_speed_rps*self.gearing_ratio*3.1415*self.wheel_diameter_mm))
            # convert back to motor rps
            self.aeb_max_safe_speed_rps = max_safe_speed_mmps / (self.gearing_ratio * 3.1415 * self.wheel_diameter_mm)
        else:
            self.aeb_max_safe_speed_rps = self.motor.get_max_speed_rps() if self.motor else 0

    def update(self):
        if self.motor:
            # speed control and limit
            speed_target_rps = self.motor.convert_speed_percent_to_rps(self.speed_target)
            if self.aeb:
                self.aeb_max_safe_speed()
                speed_target_rps = min(speed_target_rps, self.aeb_max_safe_speed_rps)
            self.motor.set_speed_rps(speed_target_rps)

            # data to be sent to client
            self.motor_rps = int(self.motor.get_speed_rps())
            self.speed_mmps = int(self.motor_rps * self.gearing_ratio * 3.1415 * self.wheel_diameter_mm) # mm/s to avoid problems with struct and float
            self.max_speed_rps = int(self.motor.get_max_speed_rps())
        # for now, no smooth steering
        if self.steering:
            self.steering.set_steering_position(self.steering_target)
            self.steering_angle = int(self.steering.servo.angle)

    def get_parameters_encoded(self):
        data = [self.voltage,
                self.roll,
                self.pitch,
                self.distance_mm,
                self.motor_rps,
                self.speed_mmps,
                self.steering_angle,
                int(self.aeb_max_safe_speed_rps)
                ]
        encoded_data = struct.pack('>Bhhhhhbh', *data)
        return encoded_data
    
    def stop_car_activity(self):
        if self.motor:
            self.motor.stop_control_loop()
        if self.horn:
            self.horn.turn_off()
        print("Car activity stopped.")