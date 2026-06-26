from servocorner import ServoCorner
from machine import Timer

class Suspension:
    def __init__(self):
        self.imu = None
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
        self.fr_input_gain = 0
        self.fl_input_gain = 0
        self.rr_input_gain = 0
        self.rl_input_gain = 0
        self.fr_tilt_gain = 0
        self.fl_tilt_gain = 0
        self.rr_tilt_gain = 0
        self.rl_tilt_gain = 0
        self.bounce_gain = 0
        self.bounce_step = 0.02
        self.bounce_range = 0.5
        self.update_timer = Timer()
        self.mode = 0
        self.roll = 0
        self.pitch = 0
        self.incline_epsilon = 0.25 # degrees of acceptable incline, above this suspension tries to compensate
        # suspension can change roll by -13 to +13 deg, pitch by -5 to +5, and gain is from 0.0 to 1.0
        self.kp_roll = 0.0075
        self.kp_pitch = 0.003
        self.diag_weight = 0
        self.axis_weight = 0

    def set_imu(self, imu):
        self.imu = imu

    def start_control_loop(self):
        self.update_timer.init(freq=50, mode=Timer.PERIODIC, callback=self.update)

    def config_servo(self, corner, servo_pin, center = 90, top_angle = 100, botton_angle = 80):
        if corner == 'fl':
            self.fl_servo = ServoCorner(servo_pin,  top_angle, botton_angle)
        elif corner == 'fr':
            self.fr_servo = ServoCorner(servo_pin,  top_angle, botton_angle)
        elif corner == 'rl':
            self.rl_servo = ServoCorner(servo_pin, top_angle, botton_angle)
        elif corner == 'rr':
            self.rr_servo = ServoCorner(servo_pin, top_angle, botton_angle)

    def set_mode(self, mode):
        self.mode = mode
        # reseting the gains
        if mode == 0:
            self.fl_input_gain = 0
            self.fr_input_gain = 0
            self.rl_input_gain = 0
            self.rr_input_gain = 0
        elif mode == 1:
            self.fl_tilt_gain = 0
            self.fr_tilt_gain = 0
            self.rl_tilt_gain = 0
            self.rr_tilt_gain = 0
        elif mode == 2:
            self.bounce_gain = 0
            self.bounce_step = abs(self.bounce_step)

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
        
        self.fl_input_gain = (x_gain + -y_gain) * scale
        self.fr_input_gain = (-x_gain + -y_gain) * scale
        self.rl_input_gain = (x_gain + y_gain) * scale
        self.rr_input_gain = (-x_gain + y_gain) * scale

    def update(self, tmr):
        # MODE 0: manual mode, suspension tilts towards the input stick
        if self.mode == 0:
            self.fl_gain = self.fl_input_gain
            self.fr_gain = self.fr_input_gain
            self.rl_gain = self.rl_input_gain
            self.rr_gain = self.rr_input_gain
        # MODE 1: active mode, suspension tries to stabilez the car
        elif self.mode == 1:
            if self.imu:
                imu_roll, imu_pitch = self.imu.read_position()
                self.roll = imu_roll if abs(imu_roll) > self.incline_epsilon else 0
                self.pitch = imu_pitch if abs(imu_pitch) > self.incline_epsilon else 0
            roll_correction = self.kp_roll * self.roll
            pitch_correction = self.kp_pitch * self.pitch
            # add correction to each corner
            self.fl_tilt_gain = self.fl_tilt_gain + (-roll_correction + pitch_correction)
            self.fl_tilt_gain = max(min(self.fl_tilt_gain, 1.0), -1.0)
            self.fr_tilt_gain = self.fr_tilt_gain + (roll_correction + pitch_correction)
            self.fr_tilt_gain = max(min(self.fr_tilt_gain, 1.0), -1.0)
            # for the rear, analize if tilt is more alligned with roll/pitch axis or diagonal
            rl_diag_correction = roll_correction + pitch_correction
            rl_axis_correction = -roll_correction - pitch_correction
            rr_diag_correction = -roll_correction + pitch_correction
            rr_axis_correction = roll_correction - pitch_correction
            r = abs(self.roll)
            p = abs(self.pitch)
            self.diag_weight = min(r, p) / max(r, p) if max(r, p) > 0 else 0
            # self.diag_weight = 0
            self.axis_weight = 1.0 - self.diag_weight
            rl_gain = self.diag_weight * rl_diag_correction + self.axis_weight * rl_axis_correction
            rr_gain = self.diag_weight * rr_diag_correction + self.axis_weight * rr_axis_correction
            self.rl_tilt_gain = self.rl_tilt_gain + rl_gain
            self.rl_tilt_gain = max(min(self.rl_tilt_gain, 1.0), -1.0)
            self.rr_tilt_gain = self.rr_tilt_gain + rr_gain
            self.rr_tilt_gain = max(min(self.rr_tilt_gain, 1.0), -1.0)
            # set the gain to each corner
            self.fl_gain = self.fl_tilt_gain
            self.fr_gain = self.fr_tilt_gain
            self.rl_gain = self.rl_tilt_gain
            self.rr_gain = self.rr_tilt_gain
        # MODE 2: bounce mode, suspension bounces to get the car unstuck
        elif self.mode == 2:
            self.bounce_gain += self.bounce_step
            if self.bounce_gain <= 0 or self.bounce_gain >= self.bounce_range:
                self.bounce_step = -self.bounce_step
            self.fl_gain = self.bounce_gain
            self.fr_gain = self.bounce_gain
            self.rl_gain = self.bounce_gain
            self.rr_gain = self.bounce_gain

        # correcting possible overflow or underflow due to having both base gain and another gain
        correction = 0
        max_total_gain = max(self.fl_base_gain + self.fl_gain,
                       self.fr_base_gain + self.fr_gain,
                       self.rl_base_gain + self.rl_gain,
                       self.rr_base_gain + self.rr_gain)
        min_total_gain = min(self.fl_base_gain + self.fl_gain,
                        self.fr_base_gain + self.fr_gain,
                        self.rl_base_gain + self.rl_gain,
                        self.rr_base_gain + self.rr_gain)
        if max_total_gain > 1 and min_total_gain > 0:
            # overflow
            correction = 1 - max_total_gain
        elif min_total_gain < 0 and max_total_gain < 1:
            # underflow
            correction = -min_total_gain
        else:
            # both overflow and underflow should not happen at the same time, but if they do, ignore correction
            # each servo will take care of clamping its gain to its range
            correction = 0
        self.fl_input_gain += correction
        self.fr_input_gain += correction
        self.rl_input_gain += correction
        self.rr_input_gain += correction

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


    def force_stop(self):
        if self.update_timer:
            self.update_timer.deinit()
        if self.fl_servo:
            self.fl_servo.force_stop()
        if self.fr_servo:
            self.fr_servo.force_stop()
        if self.rl_servo:
            self.rl_servo.force_stop()
        if self.rr_servo:
            self.rr_servo.force_stop()