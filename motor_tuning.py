from motor_temp import Motor, MotorPID
import time

motor = Motor(0, 1, 3, 2, MOTOR_PWM_FREQ = 10000)

motor.pid.kp = 250
motor.pid.ki = 1250
motor.pid.kff = 90

motor.pid.stall_boost_enabled = False
motor.pid.start_boost_enabled = True
motor.pid.stall_boost = 200
motor.pid.start_boost = 500

motor.set_speed_rps(0)
motor.start_control_loop(interval_ms = 10)
motor.pid.logging = True

time.sleep(0.01)
motor.set_speed_rps(50)
time.sleep(3)
motor.set_speed_rps(0)
time.sleep(0.01)

motor.stop_control_loop()
motor.pid.logging = False
motor.pid.save_log()

print("Done")