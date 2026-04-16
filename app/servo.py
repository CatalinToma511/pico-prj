from machine import Pin, PWM, Timer


class Servo:
    def __init__(self, pin, min_pulse_us=500, max_pulse_us=2500, frequency=50, deadzone = 0, speed_ms = 0, control_loop_interval_ms = 10):
        self.pulse_width_target_us = 0
        self.min_pulse_us = min_pulse_us
        self.max_pulse_us = max_pulse_us
        self.angle = 0
        self.deadzone = deadzone
        self.pin = pin
        self.servo_pin = PWM(Pin(pin))
        self.servo_pin.freq(frequency)
        self.servo_pin.duty_ns(0)
        self.max_step_us = self.max_pulse_us - self.min_pulse_us
        self.control_loop_interval_ms = control_loop_interval_ms
        self.control_loop_timer = Timer()
        if speed_ms > 0:
            # in servos, speed is often defined as the time it takes to move 60 degrees (666us), so we calculate the max step in microseconds based on that
            # so, the max step is in us per control loop interval is 666 us divided by the speed in ms, multiplied by the control loop interval in ms
            self.max_step_us = 666 / speed_ms * self.control_loop_interval_ms
            self.control_loop_timer.init(period=self.control_loop_interval_ms, mode=Timer.PERIODIC, callback=self.control_loop)
    

    def control_loop(self, timer):
        step_us = self.pulse_width_target_us - self.servo_pin.duty_ns() * 1000
        step_us = max(min(step_us, self.max_step_us), -self.max_step_us)
        pulse_width_ns = int(self.servo_pin.duty_ns() + step_us * 1000)
        self.servo_pin.duty_ns(self.pulse_width_target_ns)
    
    
    def set_angle(self, angle):
        if abs(self.angle - angle) > self.deadzone and 0 <= angle <= 180:
            pulse_width_us = self.min_pulse_us + (angle / 180) * (self.max_pulse_us - self.min_pulse_us)
            pulse_width_us = max(min(pulse_width_us, self.max_pulse_us), self.min_pulse_us)
            self.pulse_width_target_us = pulse_width_us
            self.angle = angle
        else:
            print(f'[Servo] Invalid angle: {angle}')

    
    def deactivate(self):
        self.servo_pin.duty_ns(0)