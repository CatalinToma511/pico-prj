from servo import Servo

class ServoCorner:
    def __init__(self, servo_pin, center = 90, top_limit = 80, bottom_limit= 100):
        self.servo = Servo(servo_pin, frequency=100, speed_ms=1000)
        self.center = center
        self.top_limit = top_limit
        self.bottom_limit = bottom_limit
        self.base_gain = 0
        self.gain = 0
        self._update()

    def _set_angle(self, angle):
        if self.top_limit < self.bottom_limit:
            angle = max(min(angle, self.bottom_limit), self.top_limit)
        else:
            angle = max(min(angle, self.top_limit), self.bottom_limit)
        self.servo.set_angle(angle)

    def _update(self):
        self._set_angle(self.center + self.gain + self.base_gain)

    def set_gain(self, gain):
        if self.bottom_limit < self.top_limit:
            gain = -gain
        self.gain = gain
        self._update()

    def set_base_gain(self, gain):
        if self.bottom_limit < self.top_limit:
            gain = -gain
        self.base_gain = gain
        self._update()

    