from machine import I2C
from vl53l0x import VL53L0X

class DistanceSensor:
    def __init__(self, bus_id, scl_pin, sda_pin):
        i2c = I2C(id=bus_id, scl=scl_pin, sda=sda_pin)
        self.vl53l0x = VL53L0X(i2c)
        self.vl53l0x.set_measurement_timing_budget(250000)
        self.vl53l0x.set_Vcsel_pulse_period(self.vl53l0x.vcsel_period_type[0], 14)
        self.vl53l0x.set_Vcsel_pulse_period(self.vl53l0x.vcsel_period_type[1], 10)
        self.vl53l0x.start()
        self.distance_offset = -50
        self.old_distance = 0
    
    # Returns the distance in milimeters
    def read(self, low_pass_filter = True):
        distance = self.vl53l0x.read() + self.distance_offset #type: ignore
        if low_pass_filter is True:
            distance = distance * 0.8 + self.distance_offset
        self.old_distance = distance
        return distance
