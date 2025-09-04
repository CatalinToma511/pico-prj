import bluetooth
import machine
import time
from micropython import const
_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)
_IRQ_GATTS_READ_REQUEST = const(4)
_IRQ_SCAN_RESULT = const(5)
_IRQ_SCAN_DONE = const(6)
_IRQ_PERIPHERAL_CONNECT = const(7)
_IRQ_PERIPHERAL_DISCONNECT = const(8)
_IRQ_GATTC_SERVICE_RESULT = const(9)
_IRQ_GATTC_SERVICE_DONE = const(10)
_IRQ_GATTC_CHARACTERISTIC_RESULT = const(11)
_IRQ_GATTC_CHARACTERISTIC_DONE = const(12)
_IRQ_GATTC_DESCRIPTOR_RESULT = const(13)
_IRQ_GATTC_DESCRIPTOR_DONE = const(14)
_IRQ_GATTC_READ_RESULT = const(15)
_IRQ_GATTC_READ_DONE = const(16)
_IRQ_GATTC_WRITE_DONE = const(17)
_IRQ_GATTC_NOTIFY = const(18)
_IRQ_GATTC_INDICATE = const(19)
_IRQ_GATTS_INDICATE_DONE = const(20)
_IRQ_MTU_EXCHANGED = const(21)
_IRQ_L2CAP_ACCEPT = const(22)
_IRQ_L2CAP_CONNECT = const(23)
_IRQ_L2CAP_DISCONNECT = const(24)
_IRQ_L2CAP_RECV = const(25)
_IRQ_L2CAP_SEND_READY = const(26)
_IRQ_CONNECTION_UPDATE = const(27)
_IRQ_ENCRYPTION_UPDATE = const(28)
_IRQ_GET_SECRET = const(29)
_IRQ_SET_SECRET = const(30)



class BLE_Central:
    def __init__(self, name="PicoW_Car", controls_callback = None):
        self.led = machine.Pin("LED", machine.Pin.OUT)
        self.last_led_toggle = 0
        self.name = name
        self.connection = None
        self.connected = False

        self.controls_callback = controls_callback

        CONST_CONTROLS_SERVICE_UUID = "12345678-1234-5678-1234-56789abcdef0"
        CONST_CONTROLS_CHARACTERISTIC_UUID = "12345678-1234-5678-1234-56789abcdef1"
        CONST_PARAMTERES_CHARACTERISTIC_UUID = "72de3993-9b26-4ec8-89ac-fb17424769f3"
        CONST_CHARACTERISTIC_USER_DESCRIPTION = 0x2901

        self.CONTROLS_SERVICE_UUID = bluetooth.UUID(CONST_CONTROLS_SERVICE_UUID)
        self.CONTROLS_CHARACTERISTIC_UUID = bluetooth.UUID(CONST_CONTROLS_CHARACTERISTIC_UUID)
        self.PARAMETERS_CHARACTERISTIC_UUID = bluetooth.UUID(CONST_PARAMTERES_CHARACTERISTIC_UUID)

        self._ble = bluetooth.BLE()
        self._ble.active(True)
        self._ble.irq(self._irq)

        controls_service = (
            CONST_CONTROLS_SERVICE_UUID,
            (
                (CONST_CONTROLS_CHARACTERISTIC_UUID,
                 bluetooth.FLAG_READ | bluetooth.FLAG_WRITE | bluetooth.FLAG_NOTIFY),
                (CONST_PARAMTERES_CHARACTERISTIC_UUID,
                 bluetooth.FLAG_READ | bluetooth.FLAG_NOTIFY),
            ),
        )

        ((self._controls_handle,
          self._parameters_handle),) = self._ble.gatts_register_services((controls_service,))
        
        self._connections = set()
        

    def _irq(self, event, data):
        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, _, _ = data
            self._connections.add(conn_handle)
            self.connected = True
            self.led.on()
            print("Connected:", conn_handle)

        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle, _, _ = data
            self._connections.discard(conn_handle)
            self.connected = False
            self.led.off()
            print("Disconnected")
            # Restart advertising so new connections are possible
            self.advertise()

        elif event == _IRQ_GATTS_WRITE:
            conn_handle, attr_handle = data
            if attr_handle == self._controls_handle:
                value = self._ble.gatts_read(attr_handle)
                print("Received:", value)
                if self.controls_callback:
                    self.controls_callback(value)

    def advertise(self, interval_us=150_000):
        name = bytes(self.name, "utf-8")
        adv_data = bytearray(
            b"\x02\x01\x06" +                # Flags
            bytes((len(name) + 1, 0x09)) +   # Complete Local Name
            name
        )
        self._ble.gap_advertise(interval_us, adv_data)
        print("Advertising as", self.name)

    def send_parameters(self, get_encoded_data_handler):
        if self.connected and self._connections:
            data_encoded = get_encoded_data_handler()
            if data_encoded:
                for conn_handle in self._connections:
                    # Write local value
                    self._ble.gatts_write(self._parameters_handle, data_encoded)
                    # Notify central
                    self._ble.gatts_notify(conn_handle, self._parameters_handle, data_encoded)

    def blink_task(self):
        if self.connected:
            self.led.on()
        else:
            now = time.ticks_ms()
            if time.ticks_diff(now, self.last_led_toggle) > 1000:
                self.led.toggle()
                self.last_led_toggle = now