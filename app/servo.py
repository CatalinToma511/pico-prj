import machine


class Servo:
    def __init__(self, pin):
        self.pin = pin
        self.servo_pin = machine.PWM(machine.Pin(pin))
        self.servo_pin.freq(50)
        self.write_microseconds(0)
        self.ms = 0
        self.angle = 0
    
    
    def set_angle(self, angle):
        if 0 <= angle <= 180:
            pulse_width = int(500 + (angle / 180) * 2000)
            self.write_microseconds(pulse_width)
        else:
            print(f'[Servo] Invalid angle: {angle}')
    
    
    def write_microseconds(self, ms):
        duty_cycle = int((ms / 20000) * 65535)
        print(f"{ms}({duty_cycle}) on pin {self.pin}")
        #abc = input(f'Enter to continue.')
        self.servo_pin.duty_u16(duty_cycle)
        self.ms = ms
        self.angle = (ms - 500) * 180 / 2000