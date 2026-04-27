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
        self.max_decel = 900 # rot/s^2
        self.filtered_target_rps = 0
        # stall paramters
        self.stall_count = 0
        self.stall_pause_iterations = 0
        self.stall_pause_time = 2 # how much time the motor is paused if stalled, in seconds
        self.stall_max_time = 2 # how much time the motor is allowed to be stalled before pausing, in seconds
        # boost parameters
        self.pwm_boost = 0
        self.stall_boost = 500
        self.start_boost = 600
        # motor parameters
        # alpha coef for filters
        self.pwm_filter_alpha = 1
        # encoder parameters and interrupts
        self.total_pulse_count = 0
        # 1 pulse = 1/12 rot ~ 0.029 cm distance, so aprox 0.34cm per pulse. at 100hz at 1cm/s, there is 0.34 pulses per update
        # so, 3 updates for 1 pulse, that aproximates 30 iterations needed for 10 pulses
        # so, for 10 pulses needed we can have a delay of even 34 iterations, which is good for low speed, but can be a jittered movement
        self.pulse_count_list_size = 34
        self.pulse_count_list = [0] * self.pulse_count_list_size
        self.min_pulse_count = 10
        # encoder
        self.pulse_pin_a = Pin(enc_a_pin, Pin.IN)
        self.pulse_pin_b = Pin(enc_b_pin, Pin.IN)
        self.pulse_pin_a.irq(trigger=(Pin.IRQ_FALLING | Pin.IRQ_RISING), handler=self.pin_a_irq, hard = True)
        self.pulse_pin_b.irq(trigger=(Pin.IRQ_FALLING | Pin.IRQ_RISING), handler=self.pin_b_irq, hard = True)
        self.ppr = 12
        # minimum values
        self.min_countable_speed = (0 / self.ppr) # rps, below this speed the speed reading is not reliable
        self.deadband = 1 / (self.ppr * self.dt) # how much counts per dt is considered noise
        # another values, to avoid memory allocation each time
        self.time_now = 0
        self.real_dt = 0
        self.old_filtered_target_rps = 0
        self.pwm_start_boost = 0
        self.pwm_stall_boost = 0
        self.boost_fall_alpha = 0.90
        self.err = 0
        self.err_i = 0
        self.P = 0
        
        # logging, may be useful for later
        self.total_time = 0
        self.log_data = []
        self.logfile_name = "motor_pid_datalog.csv"

        #opperating mode
        self.mode = 0
        self.set_mode(self.mode)

        # flags
        self.stall_boost_enabled = True
        self.start_boost_enabled = True
        self.logging = False

    def pin_a_irq(self, pin):
        self.total_pulse_count += 1 - 2 * (self.pulse_pin_a.value() ^ self.pulse_pin_b.value())   # +1 if equal, -1 if not

    def pin_b_irq(self, pin):
        self.total_pulse_count += 1 - 2 * (self.pulse_pin_a.value() ^ self.pulse_pin_b.value() ^ 1)   # reversed sense for B

    def set_target_rps(self, rps):
        if abs(rps) < self.min_countable_speed:
            rps = 0
        self.target_rps = rps

    def pwm_feed_forward(self, rps):
        a = -0.00000314968
        b = 0.000521175
        c = 0.444807
        d = 2.43761
        return (a * rps**3 + b * rps**2 + c * rps + d) / 100 * 65535

    def update(self):
        # if motor is stalled, pause the control for a few iterations
        if self.stall_pause_iterations > 0:
            self.stall_pause_iterations -= 1
            return 0
        
        # 1. calculate actual elapsed time since last update
        self.time_now = time.ticks_ms()
        self.real_dt = (self.time_now - self.last_time) / 1000
        if self.last_time == 0 or self.real_dt >= 2 * self.dt:
            #avoid situation where dt is too big
            self.real_dt = self.dt
        self.last_time = self.time_now

        # 2. filtering speed to avoid harsh transitions
        # using asymmetrical transitions, one value for acceleration and one for braking
        self.old_filtered_target_rps = self.filtered_target_rps
        target_ramp = 0
        if self.filtered_target_rps * self.target_rps < 0: # if changing direction, break first
            target_ramp = self.max_decel
        else:
            # if same direction, check if it need acceleration or decceleration
            target_ramp = self.max_accel if abs(self.target_rps) > abs(self.filtered_target_rps) else self.max_decel
        target_ramp *= self.real_dt
        self.filtered_target_rps += max(-target_ramp, min(target_ramp, self.target_rps - self.filtered_target_rps))

        # 3. read counts from the encoder
        current_count = self.total_pulse_count
        elapsed_counts = current_count - self.last_count
        self.last_count = current_count
        self.pulse_count_list.append(elapsed_counts)
        if len(self.pulse_count_list) > self.pulse_count_list_size:
            self.pulse_count_list.pop(0)

        # average the counts if low count rate and speed is not 0
        if self.filtered_target_rps != 0 and elapsed_counts < self.min_pulse_count:
            pulse_sum = 0
            i = 0
            while pulse_sum < self.min_pulse_count and i < self.pulse_count_list_size:
                pulse_sum += self.pulse_count_list[-1-i]
                i += 1
            elapsed_counts = pulse_sum / i

        # 4. calculate current speed in rps
        self.current_rps = elapsed_counts / self.ppr * (1 / self.real_dt)

        # 5. calculate parameters of PI control
        self.err = self.filtered_target_rps - self.current_rps
        self.err_i = self.err * self.real_dt
        self.P = self.err * self.kp
        self.I += self.err_i * self.ki
        self.I = int(max(-65535, min(self.I, 65535))) # anti windup

        # 6. calculate feed-forward
        pwm_ff = self.pwm_feed_forward(abs(self.filtered_target_rps)) * (self.kff/100)
        if self.filtered_target_rps < 0:
            pwm_ff = -pwm_ff
        pwm_ff = max(-65535, min(pwm_ff, 65535))

        # # 7. check for stall
        # if self.current_rps == 0 and self.filtered_target_rps != 0:
        #     self.stall_count += 1
        # else:
        #     self.stall_count = 0
        # if self.stall_count * self.dt > self.stall_max_time: # if stalled for more than 1s, pause control
        #     print("[MotorPID] Motor stalled, pausing control.")
        #     self.stall_pause_iterations = int(self.stall_pause_time / self.dt)
        #     self.stall_count = 0
        #     self.I = 0
        #     return 0

        # # 8. calculate boosts for start or stall
        # # stall boost
        # if self.stall_boost_enabled:
        #     if self.stall_count > 0.20 / self.dt: # if stalled for more than x seconds, start adding stall boost
        #         self.pwm_stall_boost = self.stall_boost / (self.stall_count * self.dt)
        #     else:
        #         self.pwm_stall_boost = 0
        # # start boost
        # if self.start_boost_enabled:
        #     if self.filtered_target_rps != 0 and self.old_filtered_target_rps == 0:
        #         self.pwm_start_boost = self.start_boost
        #     else:
        #         self.pwm_start_boost = 0
        # # change boost based on direction, and decay it over time
        # if self.filtered_target_rps < 0:
        #     self.pwm_boost = (self.pwm_stall_boost + self.pwm_stall_boost) + self.pwm_boost * self.boost_fall_alpha
        # else:
        #     self.pwm_boost = -(self.pwm_start_boost + self.pwm_stall_boost) + self.pwm_boost * self.boost_fall_alpha

        # if abs(self.pwm_boost) < 10: # if boost is very low, set it to 0 to avoid jitter
        #     self.pwm_boost = 0

        # 7. calculate pwm based on feed-forward and PI control
        if abs(self.filtered_target_rps) != 0:
            pwm = pwm_ff + self.P + self.I + self.pwm_boost
            pwm = pwm * self.pwm_filter_alpha + self.last_pwm * (1 - self.pwm_filter_alpha)
            if self.filtered_target_rps > 0:
                pwm = int(max(pwm_ff, min(pwm, 65535)))
            else:
                pwm = int(max(-65535, min(pwm, -pwm_ff)))
        else:
            pwm = 0
        self.last_pwm = pwm

        # logging, may be useful for later

        self.total_time += self.dt

        if self.logging:
            self.log_data.append((self.total_time, self.filtered_target_rps, self.current_rps, pwm))

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
            self.kff = 90
            self.kp = 250
            self.ki = 0
            self.I = 0
        # mode 2: using Feed Forward + P + I
        elif mode == 2:
            self.kff = 90
            self.kp = 250
            self.ki = 1250
            self.I = 0
        # mode 3: using P + I:
        elif mode == 3:
            self.kff = 0
            self.kp = 250
            self.ki = 1400
            self.I = 0
        else:
            print(f"[MotorPID] Invalid mode: {mode}")
            return
        self.mode = mode

    def save_log(self):
        with open(self.logfile_name, "w") as f:
            f.write("time, target_rps, rps, pwm\n")
            for entry in self.log_data:
                f.write(f"{entry[0]}, {entry[1]}, {entry[2]}, {entry[3]}\n")


class Motor:
    def __init__(self, in1, in2, enc_a, enc_b, DEBUG_PIN = None, MOTOR_PWM_FREQ=10000):
        self.in1 = PWM(Pin(in1), freq = MOTOR_PWM_FREQ, duty_u16 = 0)
        self.in2 = PWM(Pin(in2), freq = MOTOR_PWM_FREQ, duty_u16 = 0)
        self.pid = MotorPID(enc_a, enc_b)
        self.control_loop_running = False
        self.max_pwm = int(65535 * 0.98) # limiting according to IBT-4 datasheet
        self.max_rps = 280 # max rps of the motor, rpm / 60
        self.speed_limit_factor = 1
        self.debug_pin = None
        if DEBUG_PIN:
            self.debug_pin = Pin(DEBUG_PIN, Pin.OUT)
        self.irq_timer = Timer()
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
        self.pid.set_target_rps(set_point_rps)

    def get_speed_rps(self):
        return self.pid.current_rps

    def get_max_speed_rps(self):
        return self.max_rps * self.speed_limit_factor

    def control_irq(self, tmr):
        if self.debug_pin:
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

        self.dir_is_front = 1 if self.pwm >= 0 else 0
        self.pwm = abs(self.pwm)

        if self.debug_pin:
            self.debug_pin.off()
        

    def start_control_loop(self, interval_ms=10):
        self.pid.dt = interval_ms / 1000
        self.irq_timer.init(mode=Timer.PERIODIC, period=interval_ms, callback=self.control_irq)


    def stop_control_loop(self):
        self.irq_timer.deinit()