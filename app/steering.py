from servo import Servo
from machine import Timer


class Steering:
    def __init__(self, steering_servo_pin,
                 center = 90., left = 135., right = 45.,
                 max_left_pos=-128, max_right_pos=127, center_pos=0, pos_deadzone = 5,
                 imu = None):
        self.servo = Servo(steering_servo_pin, frequency=100, speed_ms=150, control_loop_interval_ms=10)
        self.target_position = 0
        # angles
        self.center = center
        self.left = left
        self.right = right
        # input positions
        self.max_left_pos = max_left_pos
        self.max_right_pos = max_right_pos
        self.center_pos = center_pos
        self.min_range = min(max_left_pos, max_right_pos)
        self.max_range = max(max_left_pos, max_right_pos)
        # deadzone
        self.min_left_pos = center_pos
        self.min_right_pos = center_pos
        self.pos_deadzone = pos_deadzone
        if self.max_left_pos < self.max_right_pos:
            self.min_left_pos = self.center_pos - self.pos_deadzone
            self.min_right_pos = self.center_pos + self.pos_deadzone
        else:
            self.min_left_pos = self.center_pos + self.pos_deadzone
            self.min_right_pos = self.center_pos - self.pos_deadzone
        self.set_steering_angle(self.center_pos)
        self.imu = imu

        # gyro PID state, now living in the same object
        self.pid_freq = 100 # Hz
        self.kg = abs(max_left_pos - center_pos) / 200 # 200 = aproximation of max yaw rate in deg/s
        self.pid_output_limit = abs(max_left_pos - center_pos) * 0.3 # could also be max_right_pos - center_pos
        self.kp = self.pid_output_limit * 0.3 / 100 # aim for kp to be around 30% of output limit
        self.ki = 0
        self.integral_limit = 75
        self.dt = 1.0 / self.pid_freq
        self.integral = 0.0
        self.prev_error = 0.0
        self.gyro_gain = 0.0
        self.gyro_correction = 0.0
        self.timer = Timer()
        self.timer.init(freq=self.pid_freq, mode=Timer.PERIODIC, callback=self.update)

    def update(self):
        if self.imu:
            driver_delta = self.target_position - self.center_pos
            error = driver_delta - self.imu.gyro_y * self.kg
            p = self.kp * error
            d = (self.prev_error - error) / self.dt
            self.gyro_correction = p + self.integral + d
            self.gyro_correction = max(min(self.gyro_correction, self.pid_output_limit), -self.pid_output_limit)
            self.integral += error * self.dt
            self.integral = max(min(self.integral, self.integral_limit), -self.integral_limit)
            self.prev_error = error
        else:
            self.gyro_correction = 0.0
        self.set_steering_angle(self.target_position + self.gyro_correction * self.gyro_gain)

    def set_target_position(self, target_position):
        # clamping the target position to the valid range
        if not (self.min_range <= target_position <= self.max_range):
            target_position = max(min(target_position, self.max_range), self.min_range)
        # if input is in deadzone
        if abs(target_position - self.center_pos) < self.pos_deadzone:
            target_position = self.center_pos
        self.target_position = target_position

    def set_steering_angle(self, target_position):
        angle = self.center # just initialize to avoid unbound variable error
        # if steering left
        if min(self.min_left_pos, self.max_left_pos) <= target_position < max(self.min_left_pos, self.max_left_pos):
            angle = self.center + (target_position - self.min_left_pos) * (self.left - self.center) / (self.max_left_pos - self.min_left_pos)
        # if steering right
        elif min(self.min_right_pos, self.max_right_pos) < target_position <= max(self.min_right_pos, self.max_right_pos):
            angle = self.center + (target_position - self.min_right_pos) * (self.right - self.center) / (self.max_right_pos - self.min_right_pos)
        # validating
        if self.left <= angle <= self.right or self.right <= angle <= self.left:
            self.servo.set_angle(angle)

    def set_gyro_gain(self, gain):
        self.gyro_gain = max(min(gain, 1.0), 0.0)
    
    def force_stop(self):
        self.servo.deactivate()