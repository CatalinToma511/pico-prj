from servocorner import ServoCorner

class Suspension:
    def __init__(self, mpu = None):
        self.mpu = mpu
        self.fl_servo = None
        self.fr_servo = None
        self.rl_servo = None
        self.rr_servo = None
        self.gain = 0
    
    def config_servo(self, corner, servo_pin, center = 90, min_angle = 100, max_angle = 80):
        if corner == 'fl':
            self.fl_servo = ServoCorner(servo_pin, center, min_angle, max_angle)
        elif corner == 'fr':
            self.fr_servo = ServoCorner(servo_pin, center, min_angle, max_angle)
        elif corner == 'rl':
            self.rl_servo = ServoCorner(servo_pin, center, min_angle, max_angle)
        elif corner == 'rr':
            self.rr_servo = ServoCorner(servo_pin, center, min_angle, max_angle)

    def set_base_gain(self, gain):
        self.gain = gain
    
    def update(self):
        if self.fl_servo:
            self.fl_servo.set_gain(self.gain)
        if self.fr_servo:
            self.fr_servo.set_gain(self.gain)
        if self.rl_servo:
            self.rl_servo.set_gain(self.gain)
        if self.rr_servo:
            self.rr_servo.set_gain(self.gain) 
