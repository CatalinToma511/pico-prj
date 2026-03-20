from machine import I2C, Pin, Timer
import ustruct
import math
import time

MPU6050_ADDR = 0x68
MPU6050_REG_CONFIG = 0x1A
MPU6050_REG_ACCEL_CONFIG = 0x1C
MPU6050_REG_GYRO_CONFIG = 0x1B
MPU6050_REG_ACCEL_XOUT_H = 0x3B
MPU6050_REG_GYRO_XOUT_H = 0x43
MPU6050_REG_PWR_MGMT_1 = 0x6B
MPU6050_REG_SMPRT_DIV = 0x19
DLPF_CFG_MASK_INVERSE = 0xF8
DLPF_CFG_MASK = 0x07
DLPF_CFG_0 = 0x00 # Accelerometer: bandwidth=260Hz, delay=0.98ms | Gyroscope: bandwidth=256Hz, delay=0.98ms, Fs=8kHz
DLPF_CFG_1 = 0x01 # Accelerometer: bandwidth=184Hz, delay=2.0ms | Gyroscope: bandwidth=188Hz, delay=1.9ms, Fs=1kHz
DLPF_CFG_2 = 0x02 # Accelerometer: bandwidth=94Hz, delay=3.0ms | Gyroscope: bandwidth=98Hz, delay=2.8ms, Fs=1kHz
DLPF_CFG_3 = 0x03 # Accelerometer: bandwidth=44Hz, delay=4.9ms | Gyroscope: bandwidth=42Hz, delay=4.8ms, Fs=1kHz
DLPF_CFG_4 = 0x04 # Accelerometer: bandwidth=21Hz, delay=8.5ms | Gyroscope: bandwidth=20Hz, delay=8.3ms, Fs=1kHz
DLPF_CFG_5 = 0x05 # Accelerometer: bandwidth=10Hz, delay=13.8ms | Gyroscope: bandwidth=10Hz, delay=13.4ms, Fs=1kHz
DLPF_CFG_6 = 0x06 # Accelerometer: bandwidth=5Hz, delay=19.0ms | Gyroscope: bandwidth=5Hz, delay=18.6ms, Fs=1kHz
ACC_SEN_TABLE = [16384, 8192, 4096, 2048] # LSB sensitivity for ±2g, ±4g, ±8g, ±16g; smallest change in acceleration that can be detected
AFS_SEL_MASK = 0x18
AFS_SEL_MASK_INVERSE = 0xE7
AFS_SEL_0 = 0x00 # Scale range: ±2g
AFS_SEL_1 = 0x01 # Scale range: ±4g
AFS_SEL_2 = 0x02 # Scale range: ±8g
AFS_SEL_3 = 0x03 # Scale range: ±16g
GYRO_SEN_TABLE = [131, 65.5, 32.8, 16.4] # LSB sensitivity for ±250°/s, ±500°/s, ±1000°/s, ±2000°/s; smallest change in angular velocity that can be detected
FS_SEL_MASK = 0x18
FS_SEL_MASK_INVERSE = 0xE7
FS_SEL_0 = 0x00 # Scale range: ±250°/s
FS_SEL_1 = 0x01 # Scale range: ±500°/s
FS_SEL_2 = 0x02 # Scale range: ±1000°/s
FS_SEL_3 = 0x03 # Scale range: ±2000°/s
G_CONSTANT = 9.81

class MPU6050:
    def __init__(self, bus_id, scl_pin, sda_pin, addr = MPU6050_ADDR):
        self.i2c = I2C(bus_id, scl = Pin(scl_pin), sda = Pin(sda_pin))
        self.addr = addr
        self.accel_x_raw = 0
        self.accel_y_raw = 0
        self.accel_z_raw = 0
        self.gyro_x_raw = 0
        self.gyro_y_raw = 0
        self.gyro_z_raw = 0
        self.accel_x = 0
        self.accel_y = 0
        self.accel_z = 0
        self.accel_factors = [1.0, 1.0, 1.0]
        self.accel_offsets = [0.0, 0.0, 0.0]
        self.gyro_x = 0
        self.gyro_y = 0
        self.gyro_z = 0
        self.gyro_factors = [1.0, 1.0, 1.0]
        self.gyro_offsets = [0.0, 0.0, 0.0]
        self.accel_sensitivity = 0
        self.gyro_sensitivity = 0
        self.read_timer = Timer()
        self.pitch = 0
        self.roll = 0
        self.yaw = 0
        self.last_update_time = 0
        self.complementary_filter_alpha = 0.96
        
        # wake up
        self.i2c.writeto_mem(self.addr, MPU6050_REG_PWR_MGMT_1, bytes([0]))
        time.sleep(0.5)

        # adjust sample rate; sample rate = gyro output rate (Fs) / (1 + sample_rate_div)
        sample_rate_div = 9 # divide Fs by 10 (1 + 9), with dlpf_cfg_6, Fs = 1kHz, so sample rate = 100Hz
        self.i2c.writeto_mem(self.addr, MPU6050_REG_SMPRT_DIV, bytes([sample_rate_div]))
        
        # set dlpf
        cfg = self.i2c.readfrom_mem(self.addr, MPU6050_REG_CONFIG, 1)
        dlpf_cfg = DLPF_CFG_2
        new_cfg = (cfg[0] & DLPF_CFG_MASK_INVERSE) | dlpf_cfg
        self.i2c.writeto_mem(self.addr, MPU6050_REG_CONFIG, bytes([new_cfg]))
        
        # set accelerometer high pass filter
        accel_cfg = self.i2c.readfrom_mem(self.addr, MPU6050_REG_ACCEL_CONFIG, 1)
        afs_sel = AFS_SEL_3
        new_accel_cfg = (accel_cfg[0] & AFS_SEL_MASK_INVERSE) | (afs_sel << 3)
        self.i2c.writeto_mem(self.addr, MPU6050_REG_ACCEL_CONFIG, bytes([new_accel_cfg]))

        # set gyro range
        gyro_cfg = self.i2c.readfrom_mem(self.addr, MPU6050_REG_GYRO_CONFIG, 1)
        fs_sel = FS_SEL_0
        new_gyro_cfg = (gyro_cfg[0] & FS_SEL_MASK_INVERSE) | (fs_sel << 3)
        self.i2c.writeto_mem(self.addr, MPU6050_REG_GYRO_CONFIG, bytes([new_gyro_cfg]))


    def read_sensitivity_factors(self):
        accel_cfg = self.i2c.readfrom_mem(self.addr, MPU6050_REG_ACCEL_CONFIG, 1)
        self.accel_sensitivity = ACC_SEN_TABLE[(accel_cfg[0] & AFS_SEL_MASK) >> 3]
        gyro_cfg = self.i2c.readfrom_mem(self.addr, MPU6050_REG_GYRO_CONFIG, 1)
        self.gyro_sensitivity = GYRO_SEN_TABLE[(gyro_cfg[0] & FS_SEL_MASK) >> 3]
        
        
    def read_accelerometer_raw(self):
        data = self.i2c.readfrom_mem(self.addr, MPU6050_REG_ACCEL_XOUT_H, 6)
        if self.accel_sensitivity == 0:
            self.read_sensitivity_factors()
        self.accel_x_raw = ustruct.unpack('>h', data[0:2])[0] / self.accel_sensitivity * G_CONSTANT
        self.accel_y_raw = ustruct.unpack('>h', data[2:4])[0] / self.accel_sensitivity * G_CONSTANT
        self.accel_z_raw = ustruct.unpack('>h', data[4:6])[0] / self.accel_sensitivity * G_CONSTANT
        return self.accel_x_raw, self.accel_y_raw, self.accel_z_raw


    def read_gyroscope_raw(self):
        data = self.i2c.readfrom_mem(self.addr, MPU6050_REG_GYRO_XOUT_H, 6)
        if self.gyro_sensitivity == 0:
            self.read_sensitivity_factors()
        self.gyro_x_raw = ustruct.unpack('>h', data[0:2])[0] / self.gyro_sensitivity
        self.gyro_y_raw = ustruct.unpack('>h', data[2:4])[0] / self.gyro_sensitivity
        self.gyro_z_raw = ustruct.unpack('>h', data[4:6])[0] / self.gyro_sensitivity
        return self.gyro_x_raw, self.gyro_y_raw, self.gyro_z_raw
    
    def calibrate(self, samples = 100):
        try:
            acc_sum_x, acc_sum_y, acc_sum_z = 0.0, 0.0, 0.0
            gyro_sum_x, gyro_sum_y, gyro_sum_z = 0.0, 0.0, 0.0

            # sample rate = output rate Fs / (1 + sample_rate_div)
            # since for accel Fs is always 1khz and gyro is either 1khz or 8khz, we use 1khz
            sample_rate_div = self.i2c.readfrom_mem(self.addr, MPU6050_REG_SMPRT_DIV, 1)[0]
            sample_rate_duration = 1 / (1000 / (1 + sample_rate_div)) # duration between samples in seconds

            for _ in range(samples):
                self.read_accelerometer_raw()
                self.read_gyroscope_raw()
                acc_sum_x += self.accel_x_raw * self.accel_factors[0]
                acc_sum_y += self.accel_y_raw * self.accel_factors[1]
                acc_sum_z += self.accel_z_raw * self.accel_factors[2]
                gyro_sum_x += self.gyro_x_raw * self.gyro_factors[0]
                gyro_sum_y += self.gyro_y_raw * self.gyro_factors[1]
                gyro_sum_z += self.gyro_z_raw * self.gyro_factors[2]
                time.sleep(sample_rate_duration)

            self.accel_offsets = [9.81 - acc_sum_x / samples,
                                0 - acc_sum_y / samples,
                                0 - acc_sum_z / samples]
            self.gyro_offsets = [0 - gyro_sum_x / samples,
                                0 - gyro_sum_y / samples,
                                0 - gyro_sum_z / samples]
        except Exception as e:
            print(f"Error calibrating IMU: {e}")
        

    def read_accelerometer(self):
        self.read_accelerometer_raw()
        self.accel_x = self.accel_x_raw * self.accel_factors[0] + self.accel_offsets[0]
        self.accel_y = self.accel_y_raw * self.accel_factors[1] + self.accel_offsets[1]
        self.accel_z = self.accel_z_raw * self.accel_factors[2] + self.accel_offsets[2]
        return self.accel_x, self.accel_y, self.accel_z


    def read_gyroscope(self):
        self.read_gyroscope_raw()
        self.gyro_x = self.gyro_x_raw * self.gyro_factors[0] + self.gyro_offsets[0]
        self.gyro_y = self.gyro_y_raw * self.gyro_factors[1] + self.gyro_offsets[1]
        self.gyro_z = self.gyro_z_raw * self.gyro_factors[2] + self.gyro_offsets[2]
        return self.gyro_x, self.gyro_y, self.gyro_z


    def update_position(self, timer):
        try:
            self.time_now = time.ticks_ms()
            accel_roll, accel_pitch = self.read_accelerometer_position()
            self.read_gyroscope()
            dt = (self.time_now - self.last_update_time) / 1000.0
            # self.roll += self.gyro_y * dt
            # self.pitch += self.gyro_z * dt
            self.roll = self.complementary_filter_alpha * (self.roll + self.gyro_y * dt) + (1 - self.complementary_filter_alpha) * accel_roll
            self.pitch = self.complementary_filter_alpha * (self.pitch + self.gyro_z * dt) + (1 - self.complementary_filter_alpha) * accel_pitch
            self.yaw += self.gyro_x * dt
            self.last_update_time = self.time_now
        except Exception as e:
            print(f"Error updating position: {e}")
            self.roll, self.pitch, self.yaw = 0, 0, 0


    def start_reading(self, freq = 100):
        roll0, pitch0 = self.read_accelerometer_position()
        self.roll = roll0
        self.pitch = pitch0
        self.last_update_time = time.ticks_ms()
        interval_ms = int(1000 / freq)
        self.read_timer.init(mode=Timer.PERIODIC, period=interval_ms, callback=self.update_position)
    
    
    def read_accelerometer_position(self):
        try:
            self.read_accelerometer()
            roll = math.atan2(self.accel_z, self.accel_x) * (180.0 / math.pi)
            pitch = math.atan2(-self.accel_y, math.sqrt(self.accel_x**2 + self.accel_z**2)) * (180.0 / math.pi)
            return roll, pitch
        except Exception as e:
            print(f"Error reading position: {e}")
            return 0, 0

    def read_position(self):
        return self.roll, self.pitch