import machine
from machine import Pin, PWM, Timer
import time
import micropython
import rp2

class PWM_Pulse_Reader:
    @rp2.asm_pio()
    def _pulse_capture():
        label("start")
        mov(x, invert(null))        # set the counter to max (will count down)
        wait(0, pin, 0)             # wait for low level on the pin
        wait(1, pin, 0)             # wait for rise edge 

        label("loop")               # loop to count the pulse width
        jmp(x_dec, "check_pin")     # we don't have standalone x_dec
        label("check_pin")          #
        jmp(pin, "loop")            # if pin is still high, keep counting
        
        mov(isr, invert(x))         # store the count, reversed because we counted down
        push(noblock)              # push into pio fifo; do not block if fifo is full, just drop the value
        irq(0)                      # trigger the irq to notify the main program that a pulse has been captured

        jmp("start")                # repeat the process

    def __init__(self, pin_num, sm_id, capture_time_flag = False):
        self.pin = machine.Pin(pin_num, machine.Pin.IN, machine.Pin.PULL_DOWN)
        self.pulse_width = 0
        self.last_capture_time = 0
        self.sm = rp2.StateMachine(
            sm_id,
            self._pulse_capture,
            freq=20_000_000,
            in_base=self.pin,
        )
        if capture_time_flag:
            self.sm.irq(self._irq_capture_time)
        else:
            self.sm.irq(self._irq)

    def start(self):
        self.sm.active(1)

    def stop(self):
        self.sm.active(0)

    def _irq(self, sm):
        self.pulse_width = (sm.get() + 5) // 10 # Convert to microseconds

    def _irq_capture_time(self, sm):
        self.pulse_width = (sm.get() + 5) // 10 # Convert to microseconds
        self.last_capture_time = time.ticks_us()
        

class Receiver:
    def __init__(self, channel_pins = [28, 27, 22, 19, 18, 15]):
        self.channel_pins = channel_pins

        self.ch1_reader = PWM_Pulse_Reader(channel_pins[0], 0)
        self.ch1_reader.start()

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

    def read_channels(self):
        self.pulse_widths[0] = self.ch1_reader.pulse_width

    def decode_mixed_channel(self, pulse_width):
        host_channel_pulse = (pulse_width - 400) % 500
        sub_channel_pulse = pulse_width - host_channel_pulse + 100
        return host_channel_pulse, sub_channel_pulse

    def decode_channels(self):
        # for pulse_width in self.pulse_widths:
        #     if pulse_width < 800 or pulse_width > 2200:
        #         pulse_width = 1500  # Set to neutral if out of range

        # Assign channels to specific controls
        self.steering_channel = self.pulse_widths[0]
        self.throttle_channel = self.pulse_widths[1]

        self.swa_channel, self.swb_channel = self.decode_mixed_channel(self.pulse_widths[2])
        self.a_channel, self.vra_channel = self.decode_mixed_channel(self.pulse_widths[3])
        self.b_channel, self.vrb_channel = self.decode_mixed_channel(self.pulse_widths[4])
        self.c_channel = self.pulse_widths[5]
        