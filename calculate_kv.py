from machine import Pin, PWM, Timer
import machine
import time

# irq handlers

class Motor():
    def __init__(self):
        self.pulse_pin_a = Pin(2, Pin.IN)
        self.pulse_pin_b = Pin(3, Pin.IN)
        self.pulse_pin_a.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=self.pin_a_irq, hard = True)
        self.pulse_pin_b.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=self.pin_b_irq, hard = True)
        self.ppr = 12
        self.error_count = 0
        self.total_pulse_count = 0
        self.pulses_forward = 0
        self.pulses_backward = 0

        self.motor_in1 = PWM(Pin(0), freq = 10000, duty_u16 = 0)
        self.motor_in2 = PWM(Pin(1), freq = 10000, duty_u16 = 0)

    def set_pwm(self, pwm):
        self.motor_in1.duty_u16(int(pwm))

    def pin_a_irq(self, pin):
        self.total_pulse_count += 1 - 2 * (self.pulse_pin_a.value() ^ self.pulse_pin_b.value() ^ 1)   # +1 if equal, -1 if not
        self.pulses_forward += 1 * (self.pulse_pin_a.value() ^ self.pulse_pin_b.value())
        self.pulses_backward += 1 * (self.pulse_pin_a.value() ^ self.pulse_pin_b.value() ^ 1)

    def pin_b_irq(self, pin):
        self.total_pulse_count += 1 - 2 * (self.pulse_pin_a.value() ^ self.pulse_pin_b.value())   # reversed sense for B
        self.pulses_forward += 1 * (self.pulse_pin_a.value() ^ self.pulse_pin_b.value() ^ 1)
        self.pulses_backward += 1 * (self.pulse_pin_a.value() ^ self.pulse_pin_b.value())


m = Motor()
vcc = 8.2
pwm_values = [2.5, 3, 3.5, 4, 4.5, 5] + list(range(6, 98, 2)) + [98]

print(f'PWM% @{vcc}\tRot/s\t\tRPM\t\tKV (RPM/V)\tF\tB')
for percentage in pwm_values:
    sum_rps_count = 0
    measuments = 1
    pwm = percentage / 100 * 65535
    m.set_pwm(pwm)
    for i in range(0, measuments):
        time.sleep(0.2) # give it time to accelerate

        # read current
        # state = machine.disable_irq()
        start_count = m.total_pulse_count
        start_f = m.pulses_forward
        start_b = m.pulses_backward
        start_time = time.ticks_ms()
        # machine.enable_irq(state)

        # wait 1 sec
        time.sleep(1)

        # read after 1 sec
        # state = machine.disable_irq()
        stop_time = time.ticks_ms()
        stop_count = m.total_pulse_count
        stop_f = m.pulses_forward
        stop_b = m.pulses_backward
        # machine.enable_irq(state)

        rps = (stop_count - start_count)/m.ppr / ((time.ticks_diff(stop_time, start_time)) / 1000)
        rpm = rps * 60
        kv = rpm / (pwm / 65535 * vcc)
        forward = stop_f - start_f
        backward = stop_b - start_b
        print(f'{percentage}\t\t{rps:.1f}\t\t{rpm:.1f}\t\t{kv:.1f}\t\t{forward}\t{backward}')
for pwm in range(90, -1, -5):
    m.set_pwm(pwm / 100 * 65535)
    time.sleep(0.1)
