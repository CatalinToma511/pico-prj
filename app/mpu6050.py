import machine
import ustruct
import math

MPU6050_ADDR = 0x68
MPU6050_REG_CONFIG = 0x1A
MPU6050_REG_ACCEL_CONFIG = 0x1C
MPU6050_REG_ACCEL_XOUT_H = 0x3B
MPU6050_REG_GYRO_XOUT_H = 0x43
MPU6050_REG_PWR_MGMT_1 = 0x6B

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
        dlpf_cfg = 0x06
        mask = 0xF8
        new_cfg = (cfg[0] & mask) | dlpf_cfg
        self.i2c.writeto_mem(self.addr, MPU6050_REG_CONFIG, bytes([new_cfg]))
        
        # adjust accelerometer high pass filter
        accel_cfg = self.i2c.readfrom_mem(self.addr, MPU6050_REG_ACCEL_CONFIG, 1)
        afs_sel = 0x10
        mask = 0xE7
        new_accel_cfg = (accel_cfg[0] & mask) | afs_sel
        self.i2c.writeto_mem(self.addr, MPU6050_REG_ACCEL_CONFIG, bytes([new_accel_cfg]))
        
        
    def read_accel_raw(self):
        data = self.i2c.readfrom_mem(self.addr, MPU6050_REG_ACCEL_XOUT_H, 6)
        
        afs_table = [16384, 8192, 4096, 2048]
        accel_cfg = self.i2c.readfrom_mem(self.addr, MPU6050_REG_ACCEL_CONFIG, 1)
        sensitivity = afs_table[(accel_cfg[0] & 0x18) >> 3]
        
        self.accel_x_raw = ustruct.unpack('>h', data[0:2])[0] / sensitivity * 9.81
        self.accel_y_raw = ustruct.unpack('>h', data[2:4])[0] / sensitivity * 9.81
        self.accel_z_raw = ustruct.unpack('>h', data[4:6])[0] / sensitivity * 9.81
        
        return self.accel_x_raw, self.accel_y_raw, self.accel_z_raw
    
    
    def calibrate_aceel(self, samples = 100):
        sum_x, sum_y, sum_z = 0.0, 0.0, 0.0
        for _ in range(samples):
            ax, ay, az = self.read_accel_raw()
            sum_x += ax * self.accel_factors[0]
            sum_y += ay * self.accel_factors[1]
            sum_z += az * self.accel_factors[2]
        self.accel_offsets = [9.81 - sum_x / samples,
                              0 - sum_y / samples,
                              0 - sum_z / samples]
        print(self.accel_offsets)
        
        
    def read_accel(self):
        self.read_accel_raw()
        self.accel_x = self.accel_x_raw * self.accel_factors[0] + self.accel_offsets[0]
        self.accel_y = self.accel_y_raw * self.accel_factors[1] + self.accel_offsets[1]
        self.accel_z = self.accel_z_raw * self.accel_factors[2] + self.accel_offsets[2]
        return self.accel_x, self.accel_y, self.accel_z
    
    
    def read_position(self):
        self.read_accel()
        roll = math.atan2(self.accel_y, self.accel_x) * (180.0 / math.pi)
        pitch = math.atan2(-self.accel_z, math.sqrt(self.accel_y**2 + self.accel_x**2)) * (180.0 / math.pi)
        return round(roll, 1), round(pitch, 1)      