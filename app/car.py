from motor import Motor
from gearbox import Gearbox
from steering import Steering
from mpu6050 import MPU6050
from horn import Horn
from voltagereader import VoltageReader
from distance_sensor import DistanceSensor
from suspension import Suspension
from receiver import Receiver
import machine
import struct
import time
from machine import Timer

class Car:
    def __init__(self):
        self.motor = None
        self.gearbox = None
        self.steering = None
        self.horn = None
        self.voltage_reader = None
        self.imu = None
        self.distance_sensor = None
        self.suspension = None
        self.receiver = None
        self.receiver_timer = None

        self.speed_target = 0
        self.motor_rps = 0
        self.wheel_speed = 0
        self.speed_mmps = 0
        self.steering_target = 0
        self.steering_servo_angle = 0
        self.steering_alpha = 0.4
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
        self.aeb_max_safe_speed_rps = 1000
        self.drive_train_backlash_mm = 30

        self.wheel_diameter_mm = 82

        self.gearing_ratio = 1

        self.horn_state = 0

        self.ch1 = 0
        self.ch2 = 0
        self.ch3 = 0
        self.ch4 = 0
        self.ch5 = 0
        self.ch6 = 0

    def config_motor(self, motor_in1, motor_in2, enc_a, enc_b):
        self.motor = Motor(motor_in1, motor_in2, enc_a, enc_b)
        self.speed_target = 0
        self.motor.start_control_loop()

    def config_steering(self, steering_pin, center, max_left, max_right):
        self.steering = Steering(steering_pin, center=center, left=max_left, right=max_right, max_left_pos=1000, max_right_pos=2000, center_pos=1500, pos_deadzone=0)
    
    def config_gearbox(self, gearbox_shift_pin):
        self.gearbox = Gearbox(gearbox_shift_pin)

    def config_horn(self, horn_pin):
        self.horn = Horn(horn_pin)

    def config_voltage_reader(self, voltage_pin):
        self.voltage_reader = VoltageReader(pin=voltage_pin)

    def config_mpu6050(self, bus_id, scl_pin, sda_pin):
        try:
            time.sleep(0.5)
            self.imu = MPU6050(bus_id, scl_pin, sda_pin)
            self.imu.calibrate()
            self.imu.start_reading()
        except Exception as e:
            print(f"Error initializing MPU6050: {e}")
            self.imu = None

    def config_distance_sensor(self, bus_id, scl_pin, sda_pin):
        try:
            self.distance_sensor = DistanceSensor(bus_id, scl_pin, sda_pin)
        except Exception as e:
            print(f"Error initializing distance sensor: {e}")
            self.distance_sensor = None

    def config_suspension(self, config, full_range_time_ms = 0):
        try:
            self.suspension = Suspension()
            self.suspension.full_range_time = full_range_time_ms
            for entry in config:
                if len(entry) >= 4:
                    self.suspension.config_servo(*entry)
            self.suspension.set_imu(self.imu)
            self.suspension.start_control_loop()
        except Exception as e:
            print(f"Error configuring suspension: {e}")
            self.suspension = None

    def config_receiver(self, channel_pins):
        try:
            self.receiver = Receiver(channel_pins)
            self.receiver.start()
            self.receiver_timer = Timer()
            self.receiver_timer.init(freq=50, mode=Timer.PERIODIC, callback=self.update_receiver_data)
        except Exception as e:
            print(f"Error configuring receiver: {e}")
            self.receiver = None

    def process_data(self, data):
        try:
            # restart the Pico if needed
            if data == b'RESET':
                print("Resetting the machine...")
                self.stop_car_activity()
                machine.reset()

            # # suspension manual control
            # if self.suspension and data[10] is not None and data[11] is not None:
            #     suspension_x = (data[10] - 128) / 128
            #     suspension_y = (data[11] - 128) / 128
            #     self.suspension.set_axis_gain(suspension_x, suspension_y)

        except Exception as e:
            print(f"Error processing data: {e}")

    def update_receiver_data(self, timer):
        try:
            if self.receiver:
                self.receiver.decode_channels()

                # self.ch1 = self.receiver.steering_channel
                # self.ch2 = self.receiver.throttle_channel
                # self.ch3 = self.receiver.vra_channel
                # self.ch4 = self.receiver.a_channel
                # self.ch5 = self.receiver.swa_channel
                # self.ch6 = self.receiver.swb_channel

                # motor control
                if self.motor:
                    # speed
                    self.speed_target = (self.receiver.throttle_channel - 1500) / 5 # 5 because (/ 500 * 100) to convert to percentage
                    self.motor.set_speed_percent(self.speed_target)

                    # limit factor
                    limit_factor = 1
                    if self.receiver.swb_channel < 1250:
                        limit_factor = 0.5
                    self.motor.set_speed_limit_factor(limit_factor)

                    # control mode
                    mode = 0
                    if self.receiver.a_channel > 1500:
                        mode = 2
                    self.motor.pid.set_mode(mode)

                # steering control
                if self.steering:
                    self.steering_target = self.receiver.steering_channel
                    self.steering.set_steering_position(self.steering_target)

                # gearbox control
                if self.gearbox:
                    if self.receiver.swb_channel < 1750:
                        gear = 0
                    else:
                        gear = 1
                    self.gearbox.set_gear(gear)
                    self.gearing_ratio = self.gearbox.get_gearing_ratio()

                # suspension control
                if self.suspension:
                    gain = (self.receiver.vra_channel - 1000) / 1000
                    self.suspension.set_base_gain(gain)
                    mode = 0
                    if 1250 <= self.receiver.b_channel < 1750:
                        if self.receiver.c_channel < 1500:
                            mode = 1
                        else:
                            mode = 3
                    elif self.receiver.b_channel >= 1750:
                        mode = 2
                    self.suspension.set_mode(mode)

                    self.ch1 = self.suspension.mode
                    self.ch2 = self.suspension.base_gain * 100
                    self.ch3 = self.suspension.bounce_gain * 100
                    self.ch4 = self.suspension.bounce_offset * 100
                    self.ch5 = self.suspension.bounce_step * 100

                if self.horn:
                    if self.receiver.swa_channel == 2000:
                        self.horn_state = 1
                    elif self.receiver.swa_channel == 1000:
                        self.horn_state = 0
                    self.horn.set_state(self.horn_state)
        except Exception as e:
            print(f"Error updating receiver data: {e}")

    def acquire_sensors_data(self):
        try:
            if self.voltage_reader:
                # read voltage in decavolts to avoid using float
                self.voltage = int(self.voltage_reader.read() * 10)
                # battery safety, put pico to sleep if voltage is too low
                # if battery level under 6.5V
                # take account for situations when motor draws battery tension down

                if self.voltage < 70 and self.motor and self.motor.get_speed_rps() == 0 and self.motor.pid.target_rps == 0: 
                    # self.horn_state = 1
                    pass

            if self.imu:
                self.roll, self.pitch = self.imu.read_position()

            if self.distance_sensor:
                    self.distance_mm = int(self.distance_sensor.read())
        except Exception as e:
                    print(f'Error while reading distance sensor data: {e}')

    def get_parameters_encoded(self):
        steering_angle = int(self.steering.servo.angle) if self.steering else 0
        roll = int(self.roll) if self.imu else 0
        pitch = int(self.pitch) if self.imu else 0
        voltage = self.voltage if self.voltage_reader else 0
        motor_pwm = int(self.motor.pwm) if self.motor else 0
        self.motor_rps = int(self.motor.get_speed_rps()) if self.motor else 0
        self.speed_mmps = int(self.motor_rps * self.gearing_ratio * 3.1415 * self.wheel_diameter_mm) if self.motor else 0
        fl_gain = int(self.suspension.fl_gain * 100) if self.suspension else 0
        fr_gain = int(self.suspension.fr_gain * 100) if self.suspension else 0
        rl_gain = int(self.suspension.rl_gain * 100) if self.suspension else 0
        rr_gain = int(self.suspension.rr_gain * 100) if self.suspension else 0
        data = [voltage,
                roll,
                pitch,
                self.motor_rps,
                self.speed_mmps,
                steering_angle,
                motor_pwm,
                fl_gain,
                fr_gain,
                rl_gain,
                rr_gain,
                int(self.ch1),
                int(self.ch2),
                int(self.ch3),
                int(self.ch4),
                int(self.ch5),
                int(self.ch6)
                ]
        encoded_data = struct.pack('>Bhhhhbhhhhhhhhhhh', *data)
        return encoded_data
    
    def stop_car_activity(self):
        if self.motor:
            self.motor.force_stop()
        if self.steering:
            self.steering.force_stop()
        if self.gearbox:
            self.gearbox.force_stop()
        if self.suspension:
            self.suspension.force_stop()
        if self.horn:
            self.horn.force_stop()
        if self.imu:
            self.imu.force_stop()
        time.sleep(0.5)
        print("Car activity stopped.")