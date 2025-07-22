from servo import Servo


class Steering:
    def __init__(self, steering_servo_pin, center = 90, left = 45, right = 125, half_left = 67, half_right = 111):
        self.steering_servo = Servo(steering_servo_pin)
        self.center = center
        self.left = left
        self.right = right
        self.half_left = half_left
        self.half_right = half_right
        self.steering_servo.set_angle(self.center)
        self.steer_position = 0
        
        
    def set_steering_position_old(self, pos):
        print(pos)
        if pos == -2:
            self.steer_position = self.left
        elif pos == -1:
            self.steer_position = self.half_left
        elif pos == 0:
            self.steer_position = self.center
        elif pos == 1:
            self.steer_position = self.half_right
        elif pos == 2:
            self.steer_position = self.right
        else:
            print(f'[Steering]: Invalid position: {pos}')
            return
        self.steering_servo.set_angle(self.steer_position)

    def set_steering_position(self, pos):
        angle = 0
        # right steering
        if pos >=0:
            angle = pos / 128 * (self.right - self.center)
        else:
            angle = abs(pos) / 127 * (self.center - self.right)