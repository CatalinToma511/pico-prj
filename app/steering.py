from servo import Servo


class Steering:
    def __init__(self, steering_servo_pin, center = 88., left = 150., right = 30.):
        self.servo = Servo(steering_servo_pin)
        self.center = center
        self.left = left
        self.right = right
        self.set_steering_position(0)
        self.position = 0


    def set_steering_position(self, new_pos, max_left_pos=-128, max_right_pos=127, center_pos=0):
        angle = self.center
        # mapping
        if max_left_pos <= new_pos <= center_pos:
            # steering left
            angle = self.center - abs(self.center - self.left) / abs(max_left_pos) * new_pos
        elif center_pos < new_pos <= max_right_pos:
            # steering right
            angle = self.center - abs(self.right - self.center) / abs(max_right_pos) * new_pos
        else:
            print(f'[Steering]: Invalid position (remote input): {new_pos}')
        # validating
        if self.left <= angle <= self.right or self.right <= angle <= self.left:
            self.servo.set_angle(angle)
            self.position = new_pos
        else:
            print(f'[Steering]: Invalid angle (servo output): {angle}')