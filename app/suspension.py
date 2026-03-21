from servocorner import ServoCorner

class Suspension:
    def __init__(self, mpu = None):
        self.mpu = mpu
        self.fl_servo = None
        self.fr_servo = None
        self.rl_servo = None
        self.rr_servo = None
        self.fr_gain = 0
        self.fl_gain = 0
        self.rr_gain = 0
        self.rl_gain = 0
    
    def config_servo(self, corner, servo_pin, center = 90, top_angle = 100, botton_angle = 80):
        if corner == 'fl':
            self.fl_servo = ServoCorner(servo_pin, center, top_angle, botton_angle)
        elif corner == 'fr':
            self.fr_servo = ServoCorner(servo_pin, center, top_angle, botton_angle)
        elif corner == 'rl':
            self.rl_servo = ServoCorner(servo_pin, center, top_angle, botton_angle)
        elif corner == 'rr':
            self.rr_servo = ServoCorner(servo_pin, center, top_angle, botton_angle)

    def set_base_gain(self, gain):
        # self.fl_gain = gain
        # self.fr_gain = gain
        self.rl_gain = gain
        self.rr_gain = gain
    
    def update(self):
        if self.fl_servo:
            self.fl_servo.set_gain(self.fl_gain)
        if self.fr_servo:
            self.fr_servo.set_gain(self.fr_gain)
        if self.rl_servo:
            self.rl_servo.set_gain(self.rl_servo)
        if self.rr_servo:
            self.rr_servo.set_gain(self.rr_gain) 
