import machine
from machine import Pin, PWM, Timer
import time
import micropython

micropython.alloc_emergency_exception_buf(100)

class MotorPID():
    def __init__(self, enc_a_pin, enc_b_pin):
        # speed and time parameters
        self.target_rps = 0
        self.last_count = 0
        self.current_rps = 0
        self.last_time = 0
        self.last_pwm = 0
        # init values for paramters
        self.kp = 0
        self.ki = 0
        self.kff = 0
        self.dt = 0.020 # seconds
        self.I = 0
        self.min_pwm = 1500
        self.max_accel = 600 # rot/s^2
        self.max_decel = 1200 # rot/s^2
        self.filtered_target_rps = 0
        # stall paramters
        self.stall_count = 0
        self.stall_pause_iterations = 0
        self.stall_boost = 0 # how much pwm is added per second of stall
        self.stall_pause_time = 2 # how much time the motor is paused if stalled, in seconds
        self.stall_max_time = 2 # how much time the motor is allowed to be stalled before pausing, in seconds
        # motor parameters
        # alpha coef for filters
        self.pwm_filter_alpha = 0.7
        # encoder parameters and interrupts
        self.total_pulse_count = 0
        self.pulse_count_list = []
        self.pulse_pin_a = Pin(enc_a_pin, Pin.IN)
        self.pulse_pin_b = Pin(enc_b_pin, Pin.IN)
        self.pulse_pin_a.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=self.pin_a_irq, hard = True)
        self.pulse_pin_b.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=self.pin_b_irq, hard = True)
        self.ppr = 12
        # minimum values
        self.min_countable_speed = (0 / self.ppr) # rps, below this speed the speed reading is not reliable
        self.deadband = 1 / (self.ppr * self.dt) # how much counts per dt is considered noise
        # logging, may be useful for later
        # self.total_time = 0
        # self.log_data = []
        # self.file = "data.csv"
        # opperating mode
        self.mode = 0
        self.set_mode(self.mode)

    def pin_a_irq(self, pin):
        self.total_pulse_count += 1 - 2 * (self.pulse_pin_a.value() ^ self.pulse_pin_b.value())   # +1 if equal, -1 if not

    def pin_b_irq(self, pin):
        self.total_pulse_count += 1 - 2 * (self.pulse_pin_a.value() ^ self.pulse_pin_b.value() ^ 1)   # reversed sense for B

    def set_target_rps(self, rps):
        if abs(rps) < self.min_countable_speed:
            rps = 0
        self.target_rps = rps

    def update(self):
        # if motor is stalled, pause the control for a few iterations
        if self.stall_pause_iterations > 0:
            self.stall_pause_iterations -= 1
            return 0
        
        # 1. calculate actual elapsed time since last update
        time_now = time.ticks_ms()
        real_dt = (time_now - self.last_time) / 1000
        if self.last_time == 0 or real_dt >= 2 * self.dt:
            #avoid situation where dt is too big
            real_dt = self.dt
        self.last_time = time_now

        # 2. filtering speed to avoid harsh transitions
        # using asymmetrical transitions, one value for acceleration and one for braking
        target_ramp = 0
        if self.filtered_target_rps * self.target_rps < 0: # if changing direction, break first
            target_ramp = self.max_decel
        else:
            # if same direction, check if it need acceleration or decceleration
            target_ramp = self.max_accel if abs(self.target_rps) > abs(self.filtered_target_rps) else self.max_decel
        target_ramp *= real_dt
        self.filtered_target_rps += max(-target_ramp, min(target_ramp, self.target_rps - self.filtered_target_rps))

        # 3. read counts from the encoder
        current_count = self.total_pulse_count
        elapsed_counts = current_count - self.last_count
        self.last_count = current_count
        self.pulse_count_list.append(elapsed_counts)
        if len(self.pulse_count_list) > 5:
            self.pulse_count_list.pop(0)

        # average the counts if low count rate and speed is not 0
        if self.filtered_target_rps != 0 and elapsed_counts < 6:
            pulse_sum = 0
            i = 0
            while pulse_sum < 6 and i < len(self.pulse_count_list):
                pulse_sum += self.pulse_count_list[-1-i]
                i += 1
            elapsed_counts = pulse_sum / i

        # 4. calculate current speed in rps
        self.current_rps = elapsed_counts / self.ppr * (1 / real_dt)

        # 5. calculate parameters of PI control
        err = self.filtered_target_rps - self.current_rps
        err_i = err * real_dt
        P = err * self.kp
        self.I += err_i * self.ki
        self.I = int(max(-65535, min(self.I, 65535))) # anti windup

        # check for stall
        pwm_stall_boost = 0
        if self.current_rps == 0 and self.filtered_target_rps != 0:
            self.stall_count += 1
            if self.stall_count * self.dt > self.stall_max_time: # if stalled for more than 1s, pause control
                print("[MotorPID] Motor stalled, pausing control for 1s")
                self.stall_pause_iterations = int(self.stall_pause_time / self.dt)
                self.stall_count = 0
                self.I = 0
                return 0
            pwm_stall_boost = self.stall_boost / (self.stall_count * self.dt)
            if self.filtered_target_rps < 0:
                pwm_stall_boost = -pwm_stall_boost
        else:
            self.stall_count = 0 # do not count if speed target is 0

        # 6. calculate feed-forward
        # motor model was calculated at a past point and is:
        # rps = pwm_percent * 7.1 - 10 =>
        # => pwm_percent = (rps + 10) / 7.1 = pwm / 65535 * 100 =>
        # => pwm = (pwm_percent * 65535 / 100) = (rps + 10) / 7.1 * 65535 / 100
        # keep the abs(result) between u0 (min pwm at which motor rotates) and max pwm
        pwm_ff = (self.filtered_target_rps) / 7.1 * 65535 / 100 * (self.kff/100)
        pwm_ff = max(-65535, min(pwm_ff, 65535))

        # 7. calculate pwm based on feed-forward and PI control
        # if desired speed is below min_countable_speed, set pwm to 0
        if abs(self.filtered_target_rps) != 0:
            pwm0 = self.min_pwm if self.filtered_target_rps >= 0 else -self.min_pwm
            pwm = pwm0 + pwm_ff + P + self.I + pwm_stall_boost
            pwm = pwm * self.pwm_filter_alpha + self.last_pwm * (1 - self.pwm_filter_alpha)
            pwm = int(max(-65535, min(pwm, 65535)))
        else:
            pwm = 0
        self.last_pwm = pwm

        # logging, may be useful for later
        # self.total_time += self.dt
        # self.log_data.append((self.total_time, self.target_rps, self.filtered_target_rps, raw_rps, current_rps, (pwm/65535*100), err, err_i))
        return pwm

    def set_mode(self, mode):
        # mode 0: using Feed Forward
        if mode == 0:
            self.kff = 100
            self.kp = 0
            self.ki = 0
            self.I = 0
        # mode 1: using Feed Forward + P
        elif mode == 1:
            self.kff = 85
            self.kp = 250
            self.ki = 0
            self.I = 0
        # mode 2: using Feed Forward + P + I
        elif mode == 2:
            self.kff = 85
            self.kp = 250
            self.ki = 700
            self.I = 0
        # mode 3: using P + I:
        elif mode == 3:
            self.kff = 0
            self.kp = 250
            self.ki = 1300
            self.I = 0
        else:
            print(f"[MotorPID] Invalid mode: {mode}")
            return
        self.mode = mode


class Motor:
    def __init__(self, in1, in2, enc_a, enc_b, debug_pin, pwm_irq_pin, MOTOR_PWM_FREQ=200):
        self.in1 = PWM(Pin(in1), freq = MOTOR_PWM_FREQ, duty_u16 = 0)
        self.in2 = PWM(Pin(in2), freq = MOTOR_PWM_FREQ, duty_u16 = 0)
        self.pid = MotorPID(enc_a, enc_b)
        self.control_loop_running = False
        self.max_pwm = int(65535 * 0.98) # limiting according to IBT-4 datasheet
        self.max_rps = 700 # max rps of the motor, 40000 rpm / 60
        self.speed_limit_factor = 1
        self.debug_pin = Pin(debug_pin, Pin.OUT)
        self.irq_timer = Timer()
        self.pwm = 0
        # self.dir_is_front = 1 # 1 = forward, 0 = backward
        # self.dither_irq_pin = Pin(pwm_irq_pin)
        # self.pwm_dither_irq_pin = PWM(self.dither_irq_pin, freq = 50)
        # self.dither_low = 500
        # self.dither_high = 65535 // 10
        # self.dither_treshold = 3000
        # self.actual_pwm = 0

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
        return self.pid.current_rps

    def get_max_speed_rps(self):
        return self.max_rps * self.speed_limit_factor

    def control_irq(self, tmr):
        self.debug_pin.on()
        self.pwm = self.pid.update()
        # limit pwm to max_pwm; account for negative pwm
        self.pwm = int(max(-self.max_pwm, min(self.pwm, self.max_pwm)))
        if self.pwm >= 0:
            self.in1.duty_u16(self.pwm)
            self.in2.duty_u16(0)
        else:
            self.in1.duty_u16(0)
            self.in2.duty_u16(-self.pwm)
        # self.dir_is_front = 1 if self.pwm >= 0 else 0
        # if 0 < abs(self.pwm) < self.dither_treshold:
        #     dither_duty = (abs(self.pwm) - self.dither_low) / (self.dither_high - self.dither_low) * 65535
        #     self.pwm_dither_irq_pin.duty_u16(int(dither_duty))
           
        # else:
        #     self.pwm_dither_irq_pin.duty_u16(0)
        #     if self.pwm >= 0:
        #         self.in1.duty_u16(self.pwm)
        #         self.in2.duty_u16(0)
        #     else:
        #         self.in1.duty_u16(0)
        #         self.in2.duty_u16(-self.pwm)

        self.pwm = abs(self.pwm)
        self.debug_pin.off()
        

    def start_control_loop(self, interval_ms=20):
        self.pid.dt = interval_ms / 1000
        self.irq_timer.init(mode=Timer.PERIODIC, period=interval_ms, callback=self.control_irq)
        # self.dither_irq_pin.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=self.pwm_dither_cb, hard = True)

    def stop_control_loop(self):
        self.irq_timer.deinit()

    # def pwm_dither_cb(self, _irq_pin):
    #     if self.dither_irq_pin.value() == 1:
    #         self.actual_pwm = self.dither_high
    #     else:
    #         self.actual_pwm = self.dither_low

    #     if self.dir_is_front == 1:
    #         self.in1.duty_u16(self.actual_pwm)
    #         self.in2.duty_u16(0)
    #     else:
    #         self.in1.duty_u16(0)
    #         self.in2.duty_u16(self.actual_pwm)