from machine import Pin, PWM, Timer
import machine
import time

machine.freq(250_000_000)

# irq handlers
pulse_count = 0
last_ticks_us = 0
pulse_us = 0
def pin_a_irq(pin):
    global pulse_count, last_ticks_us, pulse_us
    pulse_count += 1
def pin_b_irq(pin):
    global pulse_count, last_ticks_us, pulse_us
    pulse_count += 1

class Motor():
    def __init__(self):
        self.pulse_pin_a = Pin(2, Pin.IN)
        self.pulse_pin_b = Pin(3, Pin.IN)
        self.pulse_pin_a.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=pin_a_irq, hard = True)
        self.pulse_pin_b.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=pin_b_irq, hard = True)
        self.ppr = 12

        self.motor_in1 = PWM(Pin(0), freq = 2000, duty_u16 = 0)
        self.motor_in2 = PWM(Pin(1), freq = 2000, duty_u16 = 0)

    def set_pwm(self, pwm):
        self.motor_in1.duty_u16(int(pwm))

m = Motor()
print('%\tRPS(counts)\tKv')
last_avg_count = 0
sum_kv = 0
last_percentage = 0
vcc = 8.2
last_pwm = 0
for percentage in range(5, 101, 5):
    sum_rps_count = 0
    measuments = 2
    pwm = percentage / 100 * 65535
    for tries in range(0, measuments):
        time.sleep(2) # give it a bit of rest, make sure battery or driver does not overheat

        # progressive accel
        m.set_pwm(pwm / 4)
        time.sleep(0.2)
        m.set_pwm(pwm / 2)
        time.sleep(0.2)
        m.set_pwm(pwm)

        time.sleep(0.2) # give it time to accelerate

        # read current
        state = machine.disable_irq()
        start_count = pulse_count
        machine.enable_irq(state)

        # wait 1 sec
        time.sleep(1)

        # read after 1 sec
        state = machine.disable_irq()
        stop_count = pulse_count
        machine.enable_irq(state)

        # progressive deccel
        m.set_pwm(pwm / 2)
        time.sleep(0.2)
        m.set_pwm(pwm / 4)
        time.sleep(0.2)
        m.set_pwm(0)

        rps_count = (stop_count - start_count)/m.ppr
        sum_rps_count += rps_count

    avg_rps_count = sum_rps_count / measuments

    # calculating kv (speed in rpm/volts). not the best practice to calculate by pwm
    kv =  (avg_rps_count - last_avg_count) * 60 / ((pwm - last_pwm) * vcc / 65535)
    sum_kv += kv

    print(f'{percentage}\t{avg_rps_count:.1f}\t\t{kv:.1f}')

    last_pwm = pwm
    last_percentage = percentage
    last_avg_count = avg_rps_count

print(f'Avg KV: {sum_kv / 20}')
