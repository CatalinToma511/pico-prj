from machine import ADC, Pin

class VoltageReader:
    def __init__(self, pin, R1 = 998_000, R2 = 470_000, correction_factor = 1.06):
        self.adc_pin = ADC(Pin(pin))
        self.R1 = R1
        self.R2 = R2
        self.voltage_divider_ratio = (self.R1 + self.R2) / self.R2
        self.correction_factor = correction_factor

    def read(self):
        try:
            raw = self.adc_pin.read_u16()
            voltage = (raw / 65535) * 3.3 * self.voltage_divider_ratio * self.correction_factor
            if voltage > 10:
                raise ValueError("Voltage too high")
            return round(voltage, 1)
        except Exception as e:
            print(f"Error reading voltage: {e}")
            return 0