from machine import Pin, PWM
import asyncio
import time

class MotorPID():
    def __init__(self, enc_a_pin, enc_b_pin):
        self.target_rps = 0
        self.last_pulse = 0
        self.last_rps = 0
        self.kp = 250
        self.ki = 1100
        self.kff = 0.85
        self.dt = 0.020 # seconds
        self.I = 0
        self.min_speed = 20
        self.u0 = 3000
        self.max_accel = 300 # rot/s^2
        self.max_accel_dt = self.max_accel * self.dt
        self.max_decel = 600 # rot/s^2
        self.max_decel_dt = self.max_decel * self.dt
        self.filtered_target_rps = 0 # filtered speed
        
        self.speed_filter_alpha = 1

        self.last_time = 0

        self.pwm_filter_alpha = 0.7
        self.last_pwm = 0

        self.pulse_count = 0
        self.direction = 1
        self.pulse_pin_a = Pin(enc_a_pin, Pin.IN)
        self.pulse_pin_b = Pin(enc_b_pin, Pin.IN)
        self.pulse_pin_a.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=self.pin_a_irq, hard = True)
        self.pulse_pin_b.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=self.pin_b_irq, hard = True)
        self.ppr = 12

        min_pulses_per_iteration = 3
        self.min_countable_speed = (min_pulses_per_iteration / self.ppr) * (1 / self.dt)
        self.deadband = 3 / (self.ppr * self.dt) # how much counts per dt is considered noise

        # logging, may be useful for later
        self.total_time = 0
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
        # 1. calculate actual elapsed time since last update
        time_now = time.ticks_ms()
        real_dt = (time_now - self.last_time) / 1000
        if self.last_time == 0 or real_dt >= 2 * self.dt:
            #avoid situation where dt is too big
            real_dt = self.dt
        self.last_time = time_now

        # 2. read counts from the encoder
        current_count = self.pulse_count
        elapsed_counts = current_count - self.last_pulse
        self.last_pulse = current_count

        # 3. calculate current speed in rps
        raw_rps = self.direction * (1 / real_dt) * elapsed_counts / self.ppr
        current_rps = raw_rps * self.speed_filter_alpha + self.last_rps * (1 - self.speed_filter_alpha)
        self.last_rps = current_rps

        # 4. filtering speed to avoid harsh transitions
        # using asymmetrical transitions, one value for acceleration and one for braking
        target_ramp = 0
        if self.filtered_target_rps * self.target_rps < 0: # if changing direction, break first
            target_ramp = self.max_decel
        else:
            # if same direction, check if it need acceleration or decceleration
            target_ramp = self.max_accel if abs(self.target_rps) > abs(self.filtered_target_rps) else self.max_decel
        target_ramp *= real_dt
        self.filtered_target_rps += max(-target_ramp, min(target_ramp, self.target_rps - self.filtered_target_rps))

        # 5. calculate parameters of PI control
        err = self.filtered_target_rps - current_rps
        # since motor cannot determine the exact speed, we use a deadband of 1 count, half above and half below
        if abs(err) < self.deadband/2:
            err = 0
        err_i = err * real_dt
        P = err * self.kp
        self.I += err_i * self.ki
        self.I = int(max(-65535, min(self.I, 65535))) # anti windup

        # 6. calculate feed-forward
        # motor model was calculated at a past point and is:
        # rps = pwm_percent * 7.1 - 10 => pwm_percent = (rps - 10) / 7.1
        # keep the abs(result) between u0 (min pwm at which motor rotates) and max pwm
        pwm_ff = self.filtered_target_rps / 7.1 * 65535 / 100 * self.kff
        pwm_ff = max(-65535, min(pwm_ff, 65535))
        if abs(pwm_ff) < self.u0:
            pwm_ff = 0

        # 7. calculate pwm based on feed-forward and PI control
        # if desired speed is below min_countable_speed, set pwm to 0
        # adding a low pass filter to pwm to reduce abrupt changes
        if abs(self.filtered_target_rps) >= self.min_countable_speed:
            pwm = pwm_ff + P + self.I
            pwm = pwm * self.pwm_filter_alpha + self.last_pwm * (1 - self.pwm_filter_alpha)
            pwm = int(max(-65535, min(pwm, 65535)))
        else:
            pwm = 0
        self.last_pwm = pwm

        # logging, may be useful for later
        self.total_time += self.dt
        self.log_data.append((self.total_time, self.target_rps, self.filtered_target_rps, raw_rps, current_rps, (pwm/65535*100), err, err_i))
        return pwm


class Motor:
    def __init__(self, in1, in2, enc_a, enc_b, MOTOR_PWM_FREQ=2000):
        self.in1 = PWM(Pin(in1), freq = MOTOR_PWM_FREQ, duty_u16 = 0)
        self.in2 = PWM(Pin(in2), freq = MOTOR_PWM_FREQ, duty_u16 = 0)
        self.pid = MotorPID(enc_a, enc_b)
        self.control_loop_running = False
        self.max_pwm = 65535 * 0.95 # according to IBT-4 datasheet, PWM should not exceed 98%
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
            pwm = int(max(-self.max_pwm, min(pwm, self.max_pwm)))
            if pwm >= 0:
                self.in1.duty_u16(pwm)
                self.in2.duty_u16(0)
            else:
                self.in1.duty_u16(0)
                self.in2.duty_u16(-pwm)
            await asyncio.sleep(self.pid.dt)
        self.in1.duty_u16(0)
        self.in2.duty_u16(0)

async def main():
    m = Motor(0, 1, 2, 3)
    m.pid.kp = 130
    m.pid.ki = 600
    m.pid.kff = 0.85
    print("Starting control loop...")
    asyncio.create_task(m.control_loop())
    m.set_speed_rps(300)  # Set target speed to 100 RPS
    await asyncio.sleep(3)
    # m.set_speed_rps(300)  # Set target speed to 200 RPS
    # await asyncio.sleep(2)
    # m.set_speed_rps(-100)  # Set target speed to 300 RPS
    # await asyncio.sleep(2)
    m.set_speed_rps(0)
    await asyncio.sleep(2)
    m.control_loop_running = False
    await asyncio.sleep(0.25)
    print("Control loop stopped.")

    with open(f'{m.pid.file}', 'w') as newfile:
        newfile.write('time, target, filtered_target, raw_rps, current_rps, pwm, err, err_i\n')
        for time, target_rps, filtered_target_rps, raw_rps, current_rps, pwm, err, err_i in m.pid.log_data:
            newfile.write(f'{time}, {target_rps}, {filtered_target_rps}, {raw_rps}, {current_rps}, {pwm}, {err}, {err_i}\n')
        newfile.close()
    print("Data file done")

asyncio.run(main())