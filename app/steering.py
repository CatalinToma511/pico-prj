from servo import Servo
from machine import Timer


class Steering:
    def __init__(self, steering_servo_pin, center = 90., left = 135., right = 45., max_left_pos=-128, max_right_pos=127, center_pos=0, filter_alpha=0.4):
        self.servo = Servo(steering_servo_pin, frequency=200)
        self.center = center
        self.left = left
        self.right = right
        self.max_left_pos = max_left_pos
        self.max_right_pos = max_right_pos
        self.center_pos = center_pos
        self.filter_alpha = filter_alpha
        self.target_angle = center
        self.position = 0
        self.set_steering_position(0)
        self.control_timer = Timer()


    def start_control_loop(self, update_interval_ms=10):
        self.control_timer.init(period=update_interval_ms, mode=Timer.PERIODIC, callback=self.update)


    def update(self, timer):
        angle = self.target_angle * self.filter_alpha + self.servo.angle * (1 - self.filter_alpha)
        # validating
        if self.left <= angle <= self.right or self.right <= angle <= self.left:
            self.servo.set_angle(angle)


    def set_steering_position(self, target_position):
        self.target_angle = self.center # just initialize to avoid unbound variable error
        # mapping
        if self.max_left_pos <= target_position <= self.center_pos:
            # steering left
            self.target_angle = self.center - abs(self.center - self.left) / abs(self.max_left_pos) * (target_position - self.center_pos)
        elif self.center_pos < target_position <= self.max_right_pos:
            # steering right
            self.target_angle = self.center - abs(self.center - self.right) / abs(self.max_right_pos) * (target_position - self.center_pos)
        self.position = target_position