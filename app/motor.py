from machine import Pin, PWM
import asyncio

class MotorPID():
    def __init__(self, enc_a_pin, enc_b_pin):
        self.target_rps = 0
        self.last_pulse = 0
        self.last_rps = 0
        self.kp = 250
        self.ki = 1100
        self.dt = 0.010 # seconds
        self.I = 0
        self.min_speed = 20
        self.u0 = 3000
        self.max_accel = 18 # rot/s per dt
        self.filtered_target_rps = 0 # filtered speed
        
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

        # logging, may be useful for later
        # self.total_time = 0
        # self.log_data = []
        # self.file = "data.csv"
        
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
        
        # calculate pwm based on direction, min pwm and max pwm
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

        # logging, may be useful for later
        # self.total_time += self.dt
        # self.log_data.append((self.total_time, self.target_rps, self.filtered_target_rps, raw_rps, current_rps, (pwm/65535*100), err, err_i))
        return pwm


class Motor:
    def __init__(self, in1, in2, enc_a, enc_b, MOTOR_PWM_FREQ=2000):
        self.in1 = PWM(Pin(in1), freq = MOTOR_PWM_FREQ, duty_u16 = 0)
        self.in2 = PWM(Pin(in2), freq = MOTOR_PWM_FREQ, duty_u16 = 0)
        self.pid = MotorPID(enc_a, enc_b)
        self.control_loop_running = False
        self.max_pwm = 65535 * 0.95 # limiting according to IBT-4 datasheet
        self.max_rps = 666 # max rps of the motor, 40000 rpm / 60

    def set_speed_percent(self, speed_percent):
        if -100 <= speed_percent <= 100:
            self.set_speed_rps((speed_percent / 100) * self.max_rps)
        else:
            print(f"[Motor] Invalid speed: {speed_percent}")
        
    # Positive speed goes forward, negative speed goes backwards
    def set_speed_rps(self, target_speed_rps):
        set_point_rps = (max(-self.max_rps, min(target_speed_rps, self.max_rps)))
        self.pid.set_target_rps(set_point_rps)

    def get_speed_rps(self):
        return self.pid.last_rps

    async def control_loop(self):
        self.control_loop_running = True
        while self.control_loop_running:
            pwm = self.pid.update()
            # limit pwm to max_pwm; account for negative pwm
            pw = int(max(-self.max_pwm, min(pwm, self.max_pwm)))
            if pwm >= 0:
                self.in1.duty_u16(pwm)
                self.in2.duty_u16(0)
            else:
                self.in1.duty_u16(0)
                self.in2.duty_u16(-pwm)
            await asyncio.sleep(self.pid.dt)
        self.in1.duty_u16(0)
        self.in2.duty_u16(0)