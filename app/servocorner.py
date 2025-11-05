from servo import Servo

class ServoCorner:
    def __init__(self, servo_pin, center = 90, top_limit = 80, bottom_limit= 100):
        self.servo = Servo(servo_pin)
        self.center = center
        self.top_limit = top_limit
        self.bottom_limit = bottom_limit
        self._set_angle(center)

    def _set_angle(self, angle):
        if self.bottom_limit <= angle <= self.top_limit or self.top_limit <= angle <= self.bottom_limit:
            self.servo.set_angle(angle)

    def set_gain(self, gain):
        if self.bottom_limit < self.top_limit:
            gain = -gain
        self._set_angle(self.top_limit + gain)