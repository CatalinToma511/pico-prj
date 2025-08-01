import machine


class Servo:
    def __init__(self, pin, min_pulse_ms=500, max_pulse_ms=2500):
        self.ms = 0
        self.min_pulse_ms = min_pulse_ms
        self.max_pulse_ms = max_pulse_ms
        self.angle = 0
        self.pin = pin
        self.servo_pin = machine.PWM(machine.Pin(pin))
        self.servo_pin.freq(50)
        self.write_microseconds(0)
    
    
    def set_angle(self, angle):
        if 0 <= angle <= 180:
            pulse_width = int(self.min_pulse_ms + (angle / 180) * (self.max_pulse_ms - self.min_pulse_ms))
            self.write_microseconds(pulse_width)
        else:
            print(f'[Servo] Invalid angle: {angle}')
    
    
    def write_microseconds(self, ms):
        duty_cycle = int((ms / 20000) * 65535) # ms / (50hz = 20ms * 1000us) * max duty cycle (65535)
        self.servo_pin.duty_u16(duty_cycle)
        self.ms = ms
        self.angle = (ms - self.min_pulse_ms) * 180 / (self.max_pulse_ms - self.min_pulse_ms)