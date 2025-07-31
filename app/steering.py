from servo import Servo


class Steering:
    def __init__(self, steering_servo_pin, center = 71., left = 110., right = 30.):
        self.steering_servo = Servo(steering_servo_pin)
        self.center = center
        self.left = left
        self.right = right
        self.set_steering_position(0)
        self.steer_position = 0


    def set_steering_position(self, pos):
        angle = self.center
        # mapping
        if -128 <= pos <= 0:
            # for pos in (-128, 0)
            # steering left
            angle = self.center - abs(self.center - self.left) / 128 * pos
        elif 0 < pos <= 127:
            # for pos in (0, 127)
            # steering right
            angle = self.center - abs(self.right - self.center) / 127 * pos
        else:
            print(f'[Steering]: Invalid position (remote input): {pos}')
        # validating
        if self.left <= angle <= self.right or self.right <= angle <= self.left:
            self.steering_servo.set_angle(angle)
            self.steer_position = pos
        else:
            print(f'[Steering]: Invalid angle (servo output): {angle}')