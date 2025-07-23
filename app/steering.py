from servo import Servo


class Steering:
    def __init__(self, steering_servo_pin, center = 90, left = 45, right = 125):
        self.steering_servo = Servo(steering_servo_pin)
        self.center = center
        self.left = left
        self.right = right
        self.steering_servo.set_angle(self.center)
        self.steer_position = 0


    def set_steering_position(self, pos):
        angle = 0
        # mapping
        if pos >=0:
            angle = self.left + (self.center - self.left) / 128 * pos
        else:
            angle = self.center + (self.right - self.center) / 127 * pos
        # validating
        if self.left <= angle <= self.right:
            self.steering_servo.set_angle(angle)
        else:
            print(f'[Steering]: Invalid position: {pos}')