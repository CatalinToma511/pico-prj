from servo import Servo

class ServoCorner:
    def __init__(self, servo_pin, top_limit = 80, bottom_limit= 100):
        self.servo = Servo(servo_pin, frequency=100, speed_ms=700, control_loop_interval_ms=5)
        self.top_limit = top_limit
        self.bottom_limit = bottom_limit
        self.total_travel = abs(bottom_limit - top_limit)
        self.travel_coef = bottom_limit - top_limit
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
        set_point = self.top_limit + self.gain + self.base_gain
        self._set_angle(set_point)

    def set_gain(self, gain_norm):
        self.gain = max(min(gain_norm, 1.), -1.) * self.travel_coef
        self._update()

    def set_base_gain(self, base_gain_norm):
        self.base_gain = max(min(base_gain_norm, 1.), 0.) * self.travel_coef
        self._update()

    def add_gain(self, gain_norm):
        self.gain += max(min(gain_norm, 1.), -1.) * self.travel_coef
        self._update()
    def get_total_gain(self):
        return self.base_gain + self.gain