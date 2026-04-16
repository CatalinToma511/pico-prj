from machine import Pin, PWM, Timer


class Servo:
    def __init__(self, pin, min_pulse_us=500, max_pulse_us=2500, frequency=50, deadzone = 0, speed_ms = 0, control_loop_interval_ms = 0):
        self.pulse_width_target_us = 0
        self.min_pulse_us = min_pulse_us
        self.max_pulse_us = max_pulse_us
        self.angle = 0
        self.deadzone = deadzone
        self.pin = pin
        self.servo_pwm_pin = PWM(Pin(pin))
        self.servo_pwm_pin.freq(frequency)
        self.current_pulse_width_us = None
        self.servo_pwm_pin.duty_ns(0)
        self.max_step_us = self.max_pulse_us - self.min_pulse_us
        self.control_loop_interval_ms = control_loop_interval_ms
        self.control_loop_timer = Timer()
        if speed_ms > 0 and control_loop_interval_ms > 0:
            # in servos, speed is often defined as the time it takes to move 60 degrees (666us), so we calculate the max step in microseconds based on that
            # so, the max step is in us per control loop interval is 666 us divided by the speed in ms, multiplied by the control loop interval in ms
            self.max_step_us = 666 / speed_ms * self.control_loop_interval_ms
            self.control_loop_timer.init(period=self.control_loop_interval_ms, mode=Timer.PERIODIC, callback=self.control_loop)
    

    def control_loop(self, timer):
        if self.current_pulse_width_us is None:
            return
        delta_us = self.pulse_width_target_us - self.current_pulse_width_us
        step_us = max(min(delta_us, self.max_step_us), -self.max_step_us)
        pulse_width_us = self.current_pulse_width_us + step_us
        pulse_width_us = max(min(pulse_width_us, self.max_pulse_us), self.min_pulse_us)
        pulse_width_ns = int(pulse_width_us * 1000)
        self.servo_pwm_pin.duty_ns(pulse_width_ns)
        self.current_pulse_width_us = pulse_width_us
    
    
    def set_angle(self, angle):
        if abs(self.angle - angle) < self.deadzone:
            return
        if angle < 0 or angle > 180:
            print(f'[Servo] Invalid angle: {angle}')
            return
        
        pulse_width_us = self.min_pulse_us + (angle / 180) * (self.max_pulse_us - self.min_pulse_us)
        pulse_width_us = max(min(pulse_width_us, self.max_pulse_us), self.min_pulse_us)
        self.pulse_width_target_us = int(pulse_width_us * 1000)
        self.angle = angle

        # if control loop is not used or is the first time adjusting position from initialization, set the pulse width directly
        if self.control_loop_interval_ms == 0 or self.current_pulse_width_us is None:
            self.servo_pwm_pin.duty_ns(self.pulse_width_target_us)
            self.current_pulse_width_us = self.pulse_width_target_us
            
    
    def deactivate(self):
        self.control_loop_timer.deinit()
        self.servo_pwm_pin.duty_ns(0)
        self.pulse_width_target_us = None