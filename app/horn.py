from machine import Pin, PWM

class Horn:
    def __init__(self, pin):
        self.horn_pin = Pin(pin, Pin.OUT)
        # self.horn_pwm = PWM(self.horn_pin)
        # self.horn_pwm.freq(500)
        # self.horn_pwm.duty_u16(0)

    def turn_on(self):
        # self.horn_pwm.duty_u16(65535 // 2)
        self.horn_pin.on()
        pass

    def turn_off(self):
        # self.horn_pwm.duty_u16(0)
        self.horn_pin.off()
        pass