from machine import PWM, Pin

class L298N:
    EnA = None
    EnB = None
    IN1 = None
    IN2 = None
    IN3 = None
    IN4 = None
    speed = 0
    lastFunction = None
    
    def __init__(self, EnA_pin, EnB_pin, IN1_pin, IN2_pin, IN3_pin, IN4_pin):
        self.EnA = PWM(Pin(EnA_pin))
        self.EnA.freq(75)
        self.EnA.duty_u16(0)
        self.EnB = PWM(Pin(EnB_pin))
        self.EnB.freq(75)
        self.EnB.duty_u16(0)
        self.IN1 = Pin(IN1_pin, Pin.OUT)
        self.IN1.low()
        self.IN2 = Pin(IN2_pin, Pin.OUT)
        self.IN2.low()
        self.IN3 = Pin(IN3_pin, Pin.OUT)
        self.IN3.low()
        self.IN4 = Pin(IN4_pin, Pin.OUT)
        self.IN4.low()
        self.speed = 0
        
    def setSpeed(self, new_speed):
        if(new_speed < 0 or new_speed > 100):
            return
        self.speed = new_speed
    
    def setMotorA(self, duty_cycle, directionIsFront):
        # pin EnA scrie pwm de duty_cycle
        self.EnA.duty_u16(int((duty_cycle/100) * 65535))
        # IN1 = directionFront ? high : low
        self.IN1.value(directionIsFront)
        # IN2 = directionFront ? low : high
        self.IN2.value(not directionIsFront)
        
    def setMotorB(self, duty_cycle, directionIsFront):
        # pin EnB scrie pwm de duty_cycle
        self.EnB.duty_u16(int((duty_cycle/100) * 65535 * 0.9))
        # IN3 = directionFront ? high : low
        self.IN3.value(directionIsFront)
        # IN4 = directionFront ? low : high
        self.IN4.value(not directionIsFront)
        
    def goFront(self):
        self.setMotorA(self.speed, True)
        self.setMotorB(self.speed, True)
        
    def goBack(self):
        self.setMotorA(self.speed, False)
        self.setMotorB(self.speed, False)
        
    def rotateLeft(self):
        self.setMotorA(self.speed, True)
        self.setMotorB(self.speed, False)
        
    def rotateRight(self):
        self.setMotorA(self.speed, False)
        self.setMotorB(self.speed, True)
        
    def goFrontLeft(self):
        self.setMotorA(self.speed, True)
        self.setMotorB(self.speed * 0.25, True)
        
    def goFrontRight(self):
        self.setMotorA(self.speed * 0.25, True)
        self.setMotorB(self.speed, True)
        
    def goBackLeft(self):
        self.setMotorA(self.speed, False)
        self.setMotorB(self.speed * 0.25, False)
        
    def goBackRight(self):
        self.setMotorA(self.speed * 0.25, False)
        self.setMotorB(self.speed, False)
        
    def stopMotors(self):
        self.setMotorA(0, True)
        self.setMotorB(0, True)