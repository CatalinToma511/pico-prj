import machine
import ustruct
import math

MPU6050_ADDR = 0x68
MPU6050_REG_CONFIG = 0x1A
MPU6050_REG_ACCEL_CONFIG = 0x1C
MPU6050_REG_ACCEL_XOUT_H = 0x3B
MPU6050_REG_GYRO_XOUT_H = 0x43
MPU6050_REG_PWR_MGMT_1 = 0x6B
DLPF_CFG_MASK_INVERSE = 0xF8
DLPF_CFG_6 = 0x06 # Accelerometer: bandwidth=5Hz, delay=19ms | Gyroscope: bandwidth=5Hz, delay=18.6ms, Fs=1kHz
AFS_TABLE = [16384, 8192, 4096, 2048] # LSB sensitivity for ±2g, ±4g, ±8g, ±16g; smallest change in acceleration that can be detected
AFS_SEL_MASK = 0x18
AFS_SEL_MASK_INVERSE = 0xE7
AFS_SEL_3 = 0x03 # Full scale range: ±16g
G_CONSTANT = 9.81

class MPU6050:
    def __init__(self, bus_id, scl_pin, sda_pin, addr = MPU6050_ADDR):
        self.i2c = machine.I2C(bus_id, scl = machine.Pin(scl_pin), sda = machine.Pin(sda_pin))
        self.addr = addr
        self.accel_x = 0
        self.accel_y = 0
        self.accel_z = 0
        self.accel_factors = [1.0, 1.0, 1.0]
        self.accel_offsets = [0.0, 0.0, 0.0]
        
        # wake up
        self.i2c.writeto_mem(self.addr, MPU6050_REG_PWR_MGMT_1, bytes([0]))
        
        # adjust sample rate
        cfg = self.i2c.readfrom_mem(self.addr, MPU6050_REG_CONFIG, 1)
        dlpf_cfg = DLPF_CFG_6
        new_cfg = (cfg[0] & DLPF_CFG_MASK_INVERSE) | dlpf_cfg
        self.i2c.writeto_mem(self.addr, MPU6050_REG_CONFIG, bytes([new_cfg]))
        
        # adjust accelerometer high pass filter
        accel_cfg = self.i2c.readfrom_mem(self.addr, MPU6050_REG_ACCEL_CONFIG, 1)
        afs_sel = AFS_SEL_3
        new_accel_cfg = (accel_cfg[0] & AFS_SEL_MASK_INVERSE) | (AFS_SEL_3 << 3)
        self.i2c.writeto_mem(self.addr, MPU6050_REG_ACCEL_CONFIG, bytes([new_accel_cfg]))
        
        
    def read_accelerometer_raw(self):
        data = self.i2c.readfrom_mem(self.addr, MPU6050_REG_ACCEL_XOUT_H, 6)
        accel_cfg = self.i2c.readfrom_mem(self.addr, MPU6050_REG_ACCEL_CONFIG, 1)
        sensitivity = AFS_TABLE[(accel_cfg[0] & DLPF_CFG_6) >> 3]
        self.accel_x_raw = ustruct.unpack('>h', data[0:2])[0] / sensitivity * G_CONSTANT
        self.accel_y_raw = ustruct.unpack('>h', data[2:4])[0] / sensitivity * G_CONSTANT
        self.accel_z_raw = ustruct.unpack('>h', data[4:6])[0] / sensitivity * G_CONSTANT
        
        return self.accel_x_raw, self.accel_y_raw, self.accel_z_raw
    
    
    def calibrate_accelerometer(self, samples = 100):
        sum_x, sum_y, sum_z = 0.0, 0.0, 0.0
        for _ in range(samples):
            ax, ay, az = self.read_accelerometer_raw()
            sum_x += ax * self.accel_factors[0]
            sum_y += ay * self.accel_factors[1]
            sum_z += az * self.accel_factors[2]
        self.accel_offsets = [9.81 - sum_x / samples,
                              0 - sum_y / samples,
                              0 - sum_z / samples]
        
    def read_accelerometer(self):
        self.read_accelerometer_raw()
        self.accel_x = self.accel_x_raw * self.accel_factors[0] + self.accel_offsets[0]
        self.accel_y = self.accel_y_raw * self.accel_factors[1] + self.accel_offsets[1]
        self.accel_z = self.accel_z_raw * self.accel_factors[2] + self.accel_offsets[2]
        return self.accel_x, self.accel_y, self.accel_z
    
    
    def read_position(self):
        try:
            self.read_accelerometer()
            roll = math.atan2(self.accel_y, self.accel_x) * (180.0 / math.pi)
            pitch = math.atan2(-self.accel_z, math.sqrt(self.accel_y**2 + self.accel_x**2)) * (180.0 / math.pi)
            print(f"Roll: {roll}, Pitch: {pitch}")
            return int(roll), int(pitch)
        except Exception as e:
            print(f"Error reading position: {e}")
            return 0, 0