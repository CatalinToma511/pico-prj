import machine
from machine import Pin, PWM, Timer
import time
import micropython

class Receiver:
    def __init__(self, channel_pins = [28, 27, 22, 19, 18, 15]):
        self.channel_pins = channel_pins
        self.pins = [Pin(pin_num, Pin.IN) for pin_num in channel_pins]
        self.pins[0].irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=self._irq0_handler, hard=True)
        self.pins[1].irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=self._irq1_handler, hard=True)
        self.pins[2].irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=self._irq2_handler, hard=True)
        self.pins[3].irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=self._irq3_handler, hard=True)
        self.pins[4].irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=self._irq4_handler, hard=True)
        self.pins[5].irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=self._irq5_handler, hard=True)

        self.last_capture_time = [0] * len(channel_pins)
        self.pulse_widths = [0] * len(channel_pins)
        self.current_time = 0

        self.steering_channel = 1500
        self.throttle_channel = 1500
        self.swa_channel = 1500
        self.swb_channel = 1500
        self.a_channel = 1500
        self.c_channel = 1500
        self.b_channel = 1500
        self.d_channel = 1500
        self.vra_channel = 1500
        self.vrb_channel = 1500

    def _irq0_handler(self, pin):
        self.current_time = time.ticks_us()
        if pin.value() == 1:  # Rising edge
            self.last_capture_time[0] = self.current_time
        else:  # Falling edge
            self.pulse_widths[0] = time.ticks_diff(self.current_time, self.last_capture_time[0])

    def _irq1_handler(self, pin):
        self.current_time = time.ticks_us()
        if pin.value() == 1:  # Rising edge
            self.last_capture_time[1] = self.current_time
        else:  # Falling edge
            self.pulse_widths[1] = time.ticks_diff(self.current_time, self.last_capture_time[1])

    def _irq2_handler(self, pin):
            self.current_time = time.ticks_us()
            if pin.value() == 1:  # Rising edge
                self.last_capture_time[2] = self.current_time
            else:  # Falling edge
                self.pulse_widths[2] = time.ticks_diff(self.current_time, self.last_capture_time[2])

    def _irq3_handler(self, pin):
            self.current_time = time.ticks_us()
            if pin.value() == 1:  # Rising edge
                self.last_capture_time[3] = self.current_time
            else:  # Falling edge
                self.pulse_widths[3] = time.ticks_diff(self.current_time, self.last_capture_time[3])

    def _irq4_handler(self, pin):
            self.current_time = time.ticks_us()
            if pin.value() == 1:  # Rising edge
                self.last_capture_time[4] = self.current_time
            else:  # Falling edge
                self.pulse_widths[4] = time.ticks_diff(self.current_time, self.last_capture_time[4])

    def _irq5_handler(self, pin):
                self.current_time = time.ticks_us()
                if pin.value() == 1:  # Rising edge
                    self.last_capture_time[5] = self.current_time
                else:  # Falling edge
                    self.pulse_widths[5] = time.ticks_diff(self.current_time, self.last_capture_time[5])

    def decode_mixed_channel(self, pulse_width):
        host_channel_pulse = (pulse_width - 400) % 500
        sub_channel_pulse = pulse_width - host_channel_pulse + 100
        return host_channel_pulse, sub_channel_pulse

    def decode_channels(self):
        for pulse_width in self.pulse_widths:
            if pulse_width < 800 or pulse_width > 2200:
                pulse_width = 1500  # Set to neutral if out of range

        # Assign channels to specific controls
        self.steering_channel = self.pulse_widths[0]
        self.throttle_channel = self.pulse_widths[1]

        self.swa_channel, self.swb_channel = self.decode_mixed_channel(self.pulse_widths[2])
        self.a_channel, self.vra_channel = self.decode_mixed_channel(self.pulse_widths[3])
        self.b_channel, self.vrb_channel = self.decode_mixed_channel(self.pulse_widths[4])
        self.c_channel = self.pulse_widths[5]
        