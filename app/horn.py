from machine import Pin, PWM

class Horn:
    def __init__(self, pin):
        self.horn_pin = Pin(pin, Pin.OUT)
        self.state = 0
        # self.horn_pwm = PWM(self.horn_pin)
        # self.horn_pwm.freq(500)
        # self.horn_pwm.duty_u16(0)

    def turn_on(self):
        # self.horn_pwm.duty_u16(65535 // 2)
        self.horn_pin.on()
        self.state = 1

    def turn_off(self):
        # self.horn_pwm.duty_u16(0)
        self.horn_pin.off()
        self.state = 0

    def set_state(self, state):
        if state == 0:
            self.turn_on()
        elif state == 1:
            self.turn_off()
        else:
            print(f'[Horn] Invalid horn state input: {state}')
        
    def force_stop(self):
        self.turn_off()