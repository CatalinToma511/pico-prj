import machine
from machine import Pin, PWM, Timer
import time
import micropython

class Receiver:
    def __init__(self, channel_pins = [28, 27, 22, 19, 18, 15]):
        self.channel_pins = channel_pins

        self.last_capture_time = [0] * len(channel_pins)
        self.pulse_widths = [0] * len(channel_pins)
        self.current_time = 0

        for pin_num in self.channel_pins:
            pin = Pin(pin_num, Pin.IN)
            pin.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=self._capture_pulse)

        self.channels_values = [1500] * len(channel_pins)
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


    def _capture_pulse(self, pin):
        self.current_time = time.ticks_us()
        if pin.value() == 1:  # Rising edge
            self.last_capture_time[self.channel_pins.index(pin.pin)] = self.current_time
        else:  # Falling edge
            self.pulse_widths[self.channel_pins.index(pin.pin)] = time.ticks_diff(self.current_time, self.last_capture_time[self.channel_pins.index(pin.pin)])

    def decode_mixed_channel(self, pulse_width):
        host_channel_pulse = (pulse_width - 400) % 500
        sub_channel_pulse = pulse_width - host_channel_pulse + 100
        return host_channel_pulse, sub_channel_pulse

    def decode_channels(self):
        self.channels_values = [1500] * len(self.channel_pins)
        for i, pulse_width in enumerate(self.pulse_widths):
            if 800 <= pulse_width <= 2200:
                self.channels_values[i] = pulse_width
            else:
                self.channels_values[i] = 1500  # Default to center position if out of range

        # Assign channels to specific controls
        self.steering_channel = self.channels_values[0]
        self.throttle_channel = self.channels_values[1]

        self.swa_channel, self.swb_channel = self.decode_mixed_channel(self.channels_values[2])
        self.a_channel, self.vra_channel = self.decode_mixed_channel(self.channels_values[3])
        self.b_channel, self.vrb_channel = self.decode_mixed_channel(self.channels_values[4])
        self.c_channel = self.channels_values[5]
        