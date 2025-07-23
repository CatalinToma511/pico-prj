from servo import Servo


class Steering:
    def __init__(self, steering_servo_pin, center = 90., left = 45., right = 125.):
        self.steering_servo = Servo(steering_servo_pin)
        self.center = center
        self.left = left
        self.right = right
        self.steering_servo.set_angle(self.center)
        self.steer_position = 0


    def set_steering_position(self, pos):
        angle = self.center
        # mapping
        if pos < 0:
            # for pos in (0, 128)
            angle = self.center + (self.center - self.left) / 128 * pos
        else:
            # for pos in (-127, 0)
            angle = self.center + (self.right - self.center) / 127 * pos
        # validating
        if self.left <= angle <= self.right:
            print(f'Servo angle: {angle}')
            self.steering_servo.set_angle(angle)
        else:
            print(f'[Steering]: Invalid position: {pos} ({angle})')