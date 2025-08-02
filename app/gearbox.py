from servo import Servo


class Gearbox:
    def __init__(self, gear_shift_pin, low_gear_angle=9, high_gear_angle=108):
        self.gear_shift_servo = Servo(gear_shift_pin)
        self.low_gear_angle = low_gear_angle
        self.high_gear_angle = high_gear_angle
        self.gear = 0  # 0 for low gear, 1 for high gear
        self.set_gear(0)
        
        
    def set_gear(self, gear):
        if gear == 0:
            self.gear_shift_servo.set_angle(self.low_gear_angle)
            self.gear = gear
        elif gear == 1:
            self.gear_shift_servo.set_angle(self.high_gear_angle)
            self.gear = gear
        else:
            print(f'[Gearbox] Invalid gear: {gear}')