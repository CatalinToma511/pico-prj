from servo import Servo
from machine import Timer


class Steering:
    def __init__(self, steering_servo_pin, center = 90., left = 135., right = 45., max_left_pos=-128, max_right_pos=127, center_pos=0, pos_deadzone = 5):
        self.servo = Servo(steering_servo_pin, frequency=100, speed_ms=250, control_loop_interval_ms=10)
        self.position = 0
        # angles
        self.center = center
        self.left = left
        self.right = right
        # input positions
        self.max_left_pos = max_left_pos
        self.max_right_pos = max_right_pos
        self.center_pos = center_pos
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
        self.set_steering_position(self.center_pos)


    def set_steering_position(self, target_position):
        angle = self.center # just initialize to avoid unbound variable error
        # if input is in deadzone
        if abs(target_position - self.center_pos) < self.pos_deadzone:
            angle = self.center
        # if steering left
        elif min(self.min_left_pos, self.max_left_pos) <= target_position < max(self.min_left_pos, self.max_left_pos):
            angle = self.center + (target_position - self.min_left_pos) * (self.left - self.center) / (self.max_left_pos - self.min_left_pos)
        # if steering right
        elif min(self.min_right_pos, self.max_right_pos) < target_position <= max(self.min_right_pos, self.max_right_pos):
            angle = self.center + (target_position - self.min_right_pos) * (self.right - self.center) / (self.max_right_pos - self.min_right_pos)
        # validating
        if self.left <= angle <= self.right or self.right <= angle <= self.left:
            self.servo.set_angle(angle)
            self.position = target_position