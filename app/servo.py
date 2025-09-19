import machine


class Servo:
    def __init__(self, pin, min_pulse_ms=500, max_pulse_ms=2500, frequency=50):
        self.ms = 0
        self.min_pulse_ms = min_pulse_ms
        self.max_pulse_ms = max_pulse_ms
        self.angle = 0
        self.pin = pin
        self.servo_pin = machine.PWM(machine.Pin(pin))
        self.servo_pin.freq(frequency)
        self.servo_pin.duty_ns(0)
    
    
    def set_angle(self, angle):
        if 0 <= angle <= 180:
            angle = int(angle)
            pulse_width_ms = int(self.min_pulse_ms + (angle / 180) * (self.max_pulse_ms - self.min_pulse_ms))
            self.servo_pin.duty_ns(pulse_width_ms * 1_000)
            self.ms = pulse_width_ms
            self.angle = int(angle)
        else:
            print(f'[Servo] Invalid angle: {angle}')