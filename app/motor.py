import machine

class Motor:
    def __init__(self, in1, in2, MOTOR_PWM_FREQ=2000):
        self.in1 = machine.PWM(machine.Pin(in1))
        self.in1.freq(MOTOR_PWM_FREQ)
        self.in2 = machine.PWM(machine.Pin(in2))
        self.in2.freq(MOTOR_PWM_FREQ)
        self.speed = 0
        self.set_speed(0)
        
    # Positive speed goes forward, negative speed goes backwards
    def set_speed(self, speed):
        if 0 <= speed <= 100: 
            self.speed = speed
            self.in1.duty_u16(int(65535 / 100 * self.speed))
            self.in2.duty_u16(0)
        elif -100 <= speed <= 0:
            self.speed = speed
            self.in1.duty_u16(0)
            self.in2.duty_u16(int(65535 / 100 * abs(self.speed)))
        else:
            print(f"[Motor] Invalid speed: {speed}")