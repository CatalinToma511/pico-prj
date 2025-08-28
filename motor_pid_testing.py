from machine import Pin, PWM, Timer
import machine
import time

machine.freq(250_000_000)



# irq handlers
class MotorPID():
    def __init__(self, enc_a_pin, enc_b_pin):
        self.target_rps = 0
        self.last_pulse = 0
        self.last_rps = 0
        self.kp = 250
        self.ki = 1100
        self.dt = 0.025 # seconds
        self.I = 0
        self.min_speed = 20
        self.u0 = 3000
        self.max_accel = 5 # rot/s per dt
        self.filtered_target_rps = 0 # filtered speed
        self.total_time = 0
        self.speed_filter_alpha = 0.7
        

        self.pulse_count = 0
        self.direction = 1
        self.pulse_pin_a = Pin(enc_a_pin, Pin.IN)
        self.pulse_pin_b = Pin(enc_b_pin, Pin.IN)
        self.pulse_pin_a.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=self.pin_a_irq, hard = True)
        self.pulse_pin_b.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=self.pin_b_irq, hard = True)
        self.ppr = 12

        min_pulses_per_iteration = 3
        self.min_countable_speed = (min_pulses_per_iteration / self.ppr) * (1 / self.dt)
        self.deadband = 1 / (self.ppr * self.dt)

        self.motor_in1 = PWM(Pin(0), freq = 2000, duty_u16 = 0)
        self.motor_in2 = PWM(Pin(1), freq = 2000, duty_u16 = 0)

        self.log_data = []
        self.file = "data.csv"
        
    def pin_a_irq(self, pin):
        self.pulse_count += 1
        self.direction = 1 if self.pulse_pin_a.value() == self.pulse_pin_b.value() else -1

    def pin_b_irq(self, pin):
        self.pulse_count += 1
        self.direction = 1 if self.pulse_pin_a.value() != self.pulse_pin_b.value() else -1

    def set_target_rps(self, rps):
        if abs(rps) < self.min_speed:
            rps = 0
        self.target_rps = rps

    def update(self):
        self.total_time += self.dt
        # read counts
        current_count = self.pulse_count
        elapsed_counts = current_count - self.last_pulse
        self.last_pulse = current_count

        # calculate current speed
        raw_rps = self.direction * (1 / self.dt) * elapsed_counts / self.ppr
        current_rps = raw_rps * self.speed_filter_alpha + self.last_rps * (1 - self.speed_filter_alpha)
        self.last_rps = current_rps

        #filtering speed
        self.filtered_target_rps += max(-self.max_accel, min(self.max_accel, self.target_rps - self.filtered_target_rps))

        # calculate parameters
        err = self.filtered_target_rps - current_rps
        if abs(err) < self.deadband/2:
            err = 0
        err_i = err * self.dt
        P = err * self.kp
        self.I += err_i * self.ki
        self.I = int(max(-65535, min(self.I, 65535)))
        
        if self.filtered_target_rps >= self.min_countable_speed:
            pwm = self.u0 + P + self.I
            pwm = int(max(-65535, min(pwm, 65535)))
            if(abs(pwm) < self.u0):
                pwm = 0
        elif self.filtered_target_rps <= -self.min_countable_speed:
            pwm = -self.u0 + P + self.I
            pwm = int(max(-65535, min(pwm, 65535)))
            if(abs(pwm) < self.u0):
                pwm = 0
        else:
            pwm = 0

        if pwm >= 0:
            self.motor_in1.duty_u16(pwm)
            self.motor_in2.duty_u16(0)
        else:
            self.motor_in1.duty_u16(0)
            self.motor_in2.duty_u16(-pwm)

        self.log_data.append((self.total_time, self.target_rps, self.filtered_target_rps, raw_rps, current_rps, (pwm/65535*100), err, err_i))

    def stop(self):
        self.motor_in1.duty_u16(0)
        self.motor_in2.duty_u16(0)



try:
    mp = MotorPID(2, 3)
    mp.set_target_rps(100)
    for i in range(0, int(2/mp.dt)):
        mp.update()
        time.sleep(mp.dt)
    
    mp.set_target_rps(-50)
    for i in range(0, int(2/mp.dt)):
        mp.update()
        time.sleep(mp.dt)
    mp.stop()
    t = 0
    with open(f'{mp.file}', 'w') as newfile:
        newfile.write('time, target, filtered_target, raw_rps, current_rps, pwm, err, err_i\n')
        for time, target_rps, filtered_target_rps, raw_rps, current_rps, pwm, err, err_i in mp.log_data:
            newfile.write(f'{time}, {target_rps}, {filtered_target_rps}, {raw_rps}, {current_rps}, {pwm}, {err}, {err_i}\n')
            t+=mp.dt
        newfile.close()
except KeyboardInterrupt:
    mp.stop()
    print("Stopped")
