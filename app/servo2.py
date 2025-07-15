from machine import Pin, PWM

class Servo2:
    def __init__(self, pin):
        self.servo = PWM(Pin(pin))
        self.servo.freq(50)
        self.servo.duty_u16(0)
        self.us = 0
        
    def set_angle(self, angle):
        if 0 <= angle <= 180:
            pulse_width_us = int(500 + (angle / 180) * 2000)
            self.write_microseconds(pulse_width_us)
        else:
            print(f'[Servo] Invalid angle: {angle}')
        
    def write_microseconds(self, us):
        duty_cycle = int((us / 20000) * 65535)
        print(f"{us} {duty_cycle}")
        self.servo.duty_u16(duty_cycle)