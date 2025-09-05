from machine import Pin, PWM, Timer
import time

class MotorPID():
    def __init__(self, enc_a_pin, enc_b_pin):
        # speed and time parameters
        self.target_cpi = 0
        self.last_count = 0
        self.last_rps = 0
        self.last_time = 0
        self.last_pwm = 0
        # default values for ff+PI
        self.default_kp = 130
        self.default_ki = 600
        self.default_kff = 85
        # init values for paramters
        self.kp = 0
        self.ki = 0
        self.kff = 0
        self.dt = 0.020 # seconds
        self.I = 0
        # motor parameters
        self.min_speed = 20
        self.u0 = 3000
        self.max_accel = 600 # rot/s^2
        self.max_decel = 1200 # rot/s^2
        self.filtered_target_cpi = 0 # filtered speed
        # alpha coef for filters
        self.speed_filter_alpha = 1
        self.pwm_filter_alpha = 0.7
        # encoder parameters and interrupts
        self.total_pulse_count = 0
        self.direction = 1
        self.pulse_pin_a = Pin(enc_a_pin, Pin.IN)
        self.pulse_pin_b = Pin(enc_b_pin, Pin.IN)
        self.pulse_pin_a.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=self.pin_a_irq, hard = True)
        self.pulse_pin_b.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=self.pin_b_irq, hard = True)
        self.ppr = 12
        # minimum values
        min_pulses_per_iteration = 3
        self.min_countable_speed = (min_pulses_per_iteration / self.ppr) * (1 / self.dt)
        self.deadband = 1 / (self.ppr * self.dt) # how much counts per dt is considered noise
        # preallocating variables for hard irq
        self.current_count = 0
        self.diff_count = 0
        self.dt_ms = 20
        self.current_rps = 0
        self.err = 0
        self.err_i = 0
        self.P = 0
        self.pwm = 0
        self.pwm_ff = 0
        self.target_cpi_ramp = 0
        self.max_accel_cpi = 360
        self.max_decel_cpi = 720
        self.kp2_default = 78
        self.ki2_default = 360
        self.kp2 = 0
        self.ki2 = 0
        # logging, may be useful for later
        # self.total_time = 0
        # self.log_data = []
        # self.file = "data.csv"
        # opperating mode
        self.mode = 0
        self.set_mode(self.mode)

        
    def pin_a_irq(self, pin):
        self.total_pulse_count += 1
        self.direction = 1 if self.pulse_pin_a.value() == self.pulse_pin_b.value() else -1

    def pin_b_irq(self, pin):
        self.total_pulse_count += 1
        self.direction = 1 if self.pulse_pin_a.value() != self.pulse_pin_b.value() else -1

    def set_target_rps(self, rps):
        if abs(rps) < self.min_speed:
            rps = 0
        self.target_cpi = int(rps) *  self.ppr / self.dt

    def update(self):
        # 1. calculate actual elapsed time since last update
        time_now = time.ticks_ms()
        real_dt = (time_now - self.last_time) / 1000
        if self.last_time == 0 or real_dt >= 2 * self.dt:
            #avoid situation where dt is too big
            real_dt = self.dt
        self.last_time = time_now

        # 2. read counts from the encoder
        current_count = self.total_pulse_count
        elapsed_counts = current_count - self.last_count
        self.last_count = current_count

        # 3. calculate current speed in rps
        raw_rps = self.direction * (1 / real_dt) * elapsed_counts / self.ppr
        current_rps = raw_rps * self.speed_filter_alpha + self.last_rps * (1 - self.speed_filter_alpha)
        self.last_rps = current_rps

        # 4. filtering speed to avoid harsh transitions
        # using asymmetrical transitions, one value for acceleration and one for braking
        target_ramp = 0
        if self.filtered_target_cpi * self.target_cpi < 0: # if changing direction, break first
            target_ramp = self.max_decel
        else:
            # if same direction, check if it need acceleration or decceleration
            target_ramp = self.max_accel if abs(self.target_cpi) > abs(self.filtered_target_cpi) else self.max_decel
        target_ramp *= real_dt
        self.filtered_target_cpi += max(-target_ramp, min(target_ramp, self.target_cpi - self.filtered_target_cpi))

        # 5. calculate parameters of PI control
        err = self.filtered_target_cpi - current_rps
        # since motor cannot determine the exact speed, we use a deadband of 1 count, half above and half below
        if abs(err) < self.deadband/2:
            err = 0
        err_i = err * real_dt
        P = err * self.kp
        self.I += err_i * self.ki
        self.I = int(max(-65535, min(self.I, 65535))) # anti windup

        # 6. calculate feed-forward
        # motor model was calculated at a past point and is:
        # rps = pwm_percent * 7.1 - 10 =>
        # => pwm_percent = (rps + 10) / 7.1 = pwm / 65535 * 100 =>
        # => pwm = (pwm_percent * 65535 / 100) = (rps + 10) / 7.1 * 65535 / 100
        # keep the abs(result) between u0 (min pwm at which motor rotates) and max pwm
        pwm_ff = (self.filtered_target_cpi + 10) / 7.1 * 65535 / 100 * (self.kff/100)
        pwm_ff = max(-65535, min(pwm_ff, 65535))
        if abs(pwm_ff) < self.u0:
            pwm_ff = 0

        # 7. calculate pwm based on feed-forward and PI control
        # if desired speed is below min_countable_speed, set pwm to 0
        if abs(self.filtered_target_cpi) >= self.min_countable_speed:
            pwm = pwm_ff + P + self.I
            pwm = pwm * self.pwm_filter_alpha + self.last_pwm * (1 - self.pwm_filter_alpha)
            pwm = int(max(-65535, min(pwm, 65535)))
        else:
            pwm = 0
        self.last_pwm = pwm

        # logging, may be useful for later
        # self.total_time += self.dt
        # self.log_data.append((self.total_time, self.target_rps, self.filtered_target_rps, raw_rps, current_rps, (pwm/65535*100), err, err_i))
        return pwm
    
    def update_hard_irq(self):
        self.current_count = self.total_pulse_count
        self.diff_count = self.current_count - self.last_count
        self.last_count = self.current_count

        self.target_cpi_ramp = 0
        if self.filtered_target_cpi * self.target_cpi < 0: # if changing direction, break first
            self.target_cpi_ramp = self.max_decel_cpi
        else:
            # if same direction, check if it need acceleration or decceleration
            self.target_cpi_ramp = self.max_accel_cpi if abs(self.target_cpi) > abs(self.filtered_target_cpi) else self.max_decel_cpi

        self.filtered_target_cpi += max(-self.target_cpi_ramp, min(self.target_cpi_ramp, self.target_cpi - self.filtered_target_cpi))

        # P = rps_dif * kp                 convertit in cps = rps_dif * ppr
        # P = (cps_dif * ppr) * kp         convertit in cpi = cps / timp_ms
        # P = (cpi_dif / dt) * ppr * kp    dt = 20ms
        # P = cpi_dif * kp * ppr / dt
        # kp2 = kp * ppr / dt              kp2 = 78
        # P = cpi_dif * kp2
        #
        # err_i = rps_dif * dt                 dt in ms
        # err_i = (cps_dif * ppr) * dt
        # err_i = (cpi_dif / dt * ppr) * dt
        # I gain = erri * ki
        # I gain = (cpi_dif / dt * ppr) * dt * ki
        # I gain = (cpi_dif * dt) * ki * ppr / dt
        # ki2 = ki * ppr / dt
        self.err = self.filtered_target_cpi - self.diff_count
        self.err_i = self.err * self.dt_ms
        self.P = self.err * self.kp2
        self.I += self.err_i * self.ki2
        self.I = int(max(-65535, min(self.I, 65535)))

        # rps = cps * ppr
        # rps = cpi / dt * ppr
        # cpi = rps / dt * ppr
        self.pwm_ff = (self.filtered_target_cpi + 10) * self.kff * 553 // 1000
        self.pwm_ff = max(-65535, min(self.pwm_ff, 65535))
        if abs(self.pwm_ff) < self.u0:
            self.pwm_ff = 0

        self.pwm = self.pwm_ff + self.P + self.I
        self.pwm = int(max(-65535, min(self.pwm, 65535)))

        return self.pwm

    def set_mode(self, mode):
        # mode 0: using Feed Forward
        if mode == 0:
            self.kff = self.default_kff
            self.kp = 0
            self.ki = 0
            self.kp2 = 0
            self.ki2 = 0
            self.I = 0
        # mode 1: using Feed Forward + P
        elif mode == 1:
            self.kff = self.default_kff
            self.kp = self.default_kp
            self.ki = 0
            self.kp2 = self.kp2_default
            self.ki2 = 0
            self.I = 0
        # mode 2: using Feed Forward + P + I
        elif mode == 2:
            self.kff = self.default_kff
            self.kp = self.default_kp
            self.ki = self.default_ki
            self.kp2 = self.kp2_default
            self.ki2 = self.ki2_default
            self.I = 0
        # mode 3: using P + I:
        elif mode == 3:
            self.kff = 0
            self.kp = self.default_kp
            self.ki = self.default_ki
            self.kp2 = self.kp2_default
            self.ki2 = self.ki2_default
            self.I = 0
        else:
            print(f"[MotorPID] Invalid mode: {mode}")
            return
        self.mode = mode


class Motor:
    def __init__(self, in1, in2, enc_a, enc_b, debug_pin, pwm_irq_pin, MOTOR_PWM_FREQ=2000):
        self.in1 = PWM(Pin(in1), freq = MOTOR_PWM_FREQ, duty_u16 = 0)
        self.in2 = PWM(Pin(in2), freq = MOTOR_PWM_FREQ, duty_u16 = 0)
        self.pid = MotorPID(enc_a, enc_b)
        self.control_loop_running = False
        self.max_pwm = int(65535 * 0.95) # limiting according to IBT-4 datasheet
        self.max_rps = 666 # max rps of the motor, 40000 rpm / 60
        self.speed_limit_factor = 1
        self.debug_pin = Pin(debug_pin, Pin.OUT)
        self.irq_timer = Timer(debug_pin)
        self.irq_pin = Pin(pwm_irq_pin)
        self.irq_pwm = PWM(self.irq_pin, freq=50, duty_u16=10)
        self.pwm = 0

    def set_speed_limit_factor(self, speed_limit_factor):
        if 0 < speed_limit_factor <= 1:
            self.speed_limit_factor = speed_limit_factor

    def set_speed_percent(self, speed_percent):
        if -100 <= speed_percent <= 100:
            self.set_speed_rps((speed_percent / 100) * self.max_rps * self.speed_limit_factor)
        else:
            print(f"[Motor] Invalid speed percent: {speed_percent}")

    def convert_speed_percent_to_rps(self, speed_percent):
        if -100 <= speed_percent <= 100:
            return (speed_percent / 100) * self.max_rps * self.speed_limit_factor
        else:
            print(f"[Motor] Invalid speed percent: {speed_percent}")
            return 0

    # Positive speed goes forward, negative speed goes backwards
    def set_speed_rps(self, target_speed_rps):
        set_point_rps = (max(-self.max_rps, min(target_speed_rps, self.max_rps)))
        self.pid.set_target_rps(int(set_point_rps))

    def get_speed_rps(self):
        return self.pid.last_rps

    def get_max_speed_rps(self):
        return self.max_rps * self.speed_limit_factor

    def control_irq(self, tmr):
        self.debug_pin.on()
        pwm = self.pid.update()
        # limit pwm to max_pwm; account for negative pwm
        pwm = int(max(-self.max_pwm, min(pwm, self.max_pwm)))
        if pwm >= 0:
            self.in1.duty_u16(pwm)
            self.in2.duty_u16(0)
        else:
            self.in1.duty_u16(0)
            self.in2.duty_u16(-pwm)
        self.debug_pin.off()

    def control_irq_hard(self, pin):
        try:
            self.debug_pin.on()
            self.pwm = self.pid.update_hard_irq()
            self.pwm = int(max(-self.max_pwm, min(self.pwm, self.max_pwm)))
            if self.pwm >= 0:
                self.in1.duty_u16(self.pwm)
                self.in2.duty_u16(0)
            else:
                self.in1.duty_u16(0)
                self.in2.duty_u16(-self.pwm)
            self.debug_pin.off()
        except Exception as e:
            print(f"IRQ Exception: {e}")

    def start_control_loop(self, interval_ms=20):
        self.irq_timer.init(mode=Timer.PERIODIC, period=interval_ms, callback=self.control_irq)
        # self.irq_pin.irq(trigger=Pin.IRQ_RISING, handler=self.control_irq_hard, hard = True)

    def stop_control_loop(self, interval_ms=20):
        self.irq_timer.deinit()
        # self.irq_pin.irq(trigger=0, handler=None)

    