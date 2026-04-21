from servocorner import ServoCorner

class Suspension:
    def __init__(self, mpu = None):
        self.mpu = mpu
        self.fl_servo = None
        self.fr_servo = None
        self.rl_servo = None
        self.rr_servo = None
        self.fr_base_gain = 0
        self.fl_base_gain = 0
        self.rr_base_gain = 0
        self.rl_base_gain = 0
        self.fr_gain = 0
        self.fl_gain = 0
        self.rr_gain = 0
        self.rl_gain = 0
    

    def config_servo(self, corner, servo_pin, center = 90, top_angle = 100, botton_angle = 80):
        if corner == 'fl':
            self.fl_servo = ServoCorner(servo_pin,  top_angle, botton_angle)
        elif corner == 'fr':
            self.fr_servo = ServoCorner(servo_pin,  top_angle, botton_angle)
        elif corner == 'rl':
            self.rl_servo = ServoCorner(servo_pin, top_angle, botton_angle)
        elif corner == 'rr':
            self.rr_servo = ServoCorner(servo_pin, top_angle, botton_angle)


    def set_base_gain(self, gain, corner = 'all'):
        if corner == 'fl' or corner == 'all':
            self.fl_base_gain = gain
        if corner == 'fr' or corner == 'all':
            self.fr_base_gain = gain
        if corner == 'rl' or corner == 'all':
            self.rl_base_gain = gain
        if corner == 'rr' or corner == 'all':
            self.rr_base_gain = gain

    def set_gain(self, gain, corner = 'all'):
        if corner == 'fl' or corner == 'all':
            self.fl_gain = gain
        if corner == 'fr' or corner == 'all':
            self.fr_gain = gain
        if corner == 'rl' or corner == 'all':
            self.rl_gain = gain
        if corner == 'rr' or corner == 'all':
            self.rr_gain = gain
    

    def set_axis_gain(self, x_gain, y_gain):
        # joysticks gives values between -128 and 127, but not full range, their range is a circle
        # the usual formula would be for example something like FL = x_gain + y_gain
        # but this works well only if the are of range would be described be a square, |x| + |y| <= 0.5
        # since the actual range is a circle, for values inside circle but still with |x| + |y| > 0.5, we get gains > 1
        # to correct this, we need to clamp the magnitude to 1 and scale the gains accordingly
        # so, we are actually mapping L2 ball unit to L1 ball unit, getting the full range of gain values and direction

        l2_norm = (x_gain**2 + y_gain**2)**0.5
        if l2_norm > 1.0:
            # normalize the gains to maintain the direction but limit the magnitude to 1
            # this is because the joystick is not a perfect circle and can have distortion in inputs
            x_gain /= l2_norm
            y_gain /= l2_norm
            l2_norm = 1.0

        l1_norm = abs(x_gain) + abs(y_gain) # L1 norm of the input
        l1_norm = max(l1_norm, 0.01) # prevent division by zero, if both x and y are zero, the gains will be zero anyway, so it does not affect the result
        scale = 0.5 * l2_norm / l1_norm # scale factor to convert L2 ball to L1 ball
        # why divide by 2? so, each servo gets a gain in range [0, 1]. Since each corner is affected
        # the total range of the diamond shape must be also 1, so the corners needs to be (+/-0.5, +/-0.5) instead of (+/-1, +/-1)
        
        fl_input_gain = (x_gain + -y_gain) * scale
        fr_input_gain = (-x_gain + -y_gain) * scale
        rl_input_gain = (x_gain + y_gain) * scale
        rr_input_gain = (-x_gain + y_gain) * scale
    
        correction = 0
        max_total_gain = max(self.fl_base_gain + fl_input_gain,
                       self.fr_base_gain + fr_input_gain,
                       self.rl_base_gain + rl_input_gain,
                       self.rr_base_gain + rr_input_gain)
        min_total_gain = min(self.fl_base_gain + fl_input_gain,
                        self.fr_base_gain + fr_input_gain,
                        self.rl_base_gain + rl_input_gain,
                        self.rr_base_gain + rr_input_gain)
        
        if max_total_gain > 1 and min_total_gain > 0:
            # overflow
            correction = 1 - max_total_gain
        elif min_total_gain < 0 and max_total_gain < 1:
            # underflow
            correction = -min_total_gain
        else:
            # both overflow and underflow should not happen at the same time, but if they do, ignore correction
            # each servo will take care of clamping its gain to its range
            # here we can also abort using this inputs at all, but having a response may be useful for debugging and feedback
            correction = 0

        fl_input_gain += correction
        fr_input_gain += correction
        rl_input_gain += correction
        rr_input_gain += correction

        self.set_gain(fl_input_gain, corner='fl')
        self.set_gain(fr_input_gain, corner='fr')
        self.set_gain(rl_input_gain, corner='rl')
        self.set_gain(rr_input_gain, corner='rr')


    def update(self):
        if self.fl_servo:
            self.fl_servo.set_base_gain(self.fl_base_gain)
            self.fl_servo.set_gain(self.fl_gain)
        if self.fr_servo:
            self.fr_servo.set_base_gain(self.fr_base_gain)
            self.fr_servo.set_gain(self.fr_gain)
        if self.rl_servo:
            self.rl_servo.set_base_gain(self.rl_base_gain)
            self.rl_servo.set_gain(self.rl_gain)
        if self.rr_servo:
            self.rr_servo.set_base_gain(self.rr_base_gain)
            self.rr_servo.set_gain(self.rr_gain) 
