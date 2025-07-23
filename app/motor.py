import machine

class Motor:
    def __init__(self, in1, in2):
        self.in1 = machine.PWM(machine.Pin(in1))
        self.in1.freq(2000)
        self.in2 = machine.PWM(machine.Pin(in2))
        self.in2.freq(2000)
        self.direction = 0
        self.set_speed(0)
        self.nr = 0
        
    def set_speed(self, speed):
        if 0 <= speed <= 100: 
            self.speed = speed
            self.update()
        else:
            print(f"[Motor] Invalid speed: {speed}")
            
    def set_direction(self, direction):
        if -1 <= direction <= 1:
            # print(f'new dir {direction}, old dir {self.direction}')
            self.direction = direction
            self.update()
        else:
            print(f"[Motor] Invalid direction: {direction}")
            
    def update(self):
        # print(f"{self.direction} {self.speed}")
        if self.direction == 0:
            # print('stop')
            self.in1.duty_u16(0)
            self.in2.duty_u16(0)
            
        elif self.direction == 1:
            # print(self.speed)
            self.in1.duty_u16(65535 // 100 * self.speed)
            self.in2.duty_u16(0)
            
        elif self.direction == -1:
            self.in1.duty_u16(0)
            self.in2.duty_u16(65535 // 100 * self.speed)