from machine import Pin, PWM, Timer
import time

# irq handler
pulse_count = 0
pulse_pin_a = Pin(2, Pin.IN)
pulse_pin_b = Pin(3, Pin.IN)
def pin_a_irq(pin):
    global pulse_count
    pulse_count += 1

def pin_b_irq(pin):
    global pulse_count
    pulse_count += 1

pulse_pin_a.irq(trigger=Pin.IRQ_FALLING, handler=pin_a_irq, hard = True)
pulse_pin_b.irq(trigger=Pin.IRQ_FALLING, handler=pin_b_irq, hard = True)
ppr = 6

while True:
    pc = pulse_count
    pulse_count = 0
    rps = (pc / ppr)  # per second
    print(rps)
    time.sleep(1)