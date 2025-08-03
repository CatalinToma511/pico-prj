import aioble
import bluetooth
import machine
import asyncio


class BLE_Central:
    def __init__(self, name="PicoW_Car"):
        self.led = machine.Pin("LED", machine.Pin.OUT)
        self.name = name
        self.connection = None
        self.connected = False
        CONST_CONTROLS_SERVICE_UUID = "12345678-1234-5678-1234-56789abcdef0"
        CONST_CONTROLS_CHARACTERISTIC_UUID = "12345678-1234-5678-1234-56789abcdef1"
        CONST_PARAMTERES_CHARACTERISTIC_UUID = "72de3993-9b26-4ec8-89ac-fb17424769f3"
        CONST_CHARACTERISTIC_USER_DESCRIPTION = 0x2901
        self.CONTROLS_SERVICE_UUID = bluetooth.UUID(CONST_CONTROLS_SERVICE_UUID)
        self.CONTROLS_CHARACTERISTIC_UUID = bluetooth.UUID(CONST_CONTROLS_CHARACTERISTIC_UUID)
        self.PARAMETERS_CHARACTERISTIC_UUID = bluetooth.UUID(CONST_PARAMTERES_CHARACTERISTIC_UUID)
        self.controls_service =  aioble.Service(self.CONTROLS_SERVICE_UUID)
        self.controls_characteristic = aioble.Characteristic(
            self.controls_service,
            self.CONTROLS_CHARACTERISTIC_UUID,
            read=True,
            write=True,
            notify=True,
        )
        self.controls_descriptor = aioble.Descriptor(
            self.controls_characteristic,
            bluetooth.UUID(CONST_CHARACTERISTIC_USER_DESCRIPTION),  # Characteristic User Description
            read=True
        )
        self.parameters_characteristic = aioble.Characteristic(
            self.controls_service,
            self.PARAMETERS_CHARACTERISTIC_UUID,
            read=True,
            write=False,
            notify=True,
        )
        self.paramters_descriptor = aioble.Descriptor(
            self.parameters_characteristic,
            bluetooth.UUID(CONST_CHARACTERISTIC_USER_DESCRIPTION),  # Characteristic User Description
            read=True
        )
        aioble.register_services(self.controls_service)
        self.controls_descriptor.write("Controller data".encode('utf-8'))
        self.parameters_characteristic.write("Car parameters".encode('utf-8'))


    async def connection_task(self, _ADV_INTERVAL_US=150_000):
        while True:
            try:
                print("Advertising and waiting for central...")
                self.connection = await aioble.advertise(
                    _ADV_INTERVAL_US,
                    name=self.name,
                    services=[self.CONTROLS_SERVICE_UUID]) # type: ignore
                self.connected = True
                print("Connected:", self.connection.device)

                await self.connection.disconnected(timeout_ms = None)
                self.connected = False
                print("Disconnected")
            except Exception as e:
                print(f"Error while establishing connection: {e}")

    async def characteristic_listener(self, characteristic, callback):
        while True:
            try:
                await characteristic.written()
                data = characteristic.read()
                callback(data)
            except Exception as e:
                print(f"Error while listening to a characteristic: {e}")

    async def send_parameters(self, characteristic, get_encoded_data_callback, interval_ms=100):
        while True:
            try:
                while not self.connected:
                    await asyncio.sleep_ms(interval_ms)
                data_encoded = get_encoded_data_callback()
                if data_encoded is None:
                    print("No data to send")
                    await asyncio.sleep_ms(interval_ms)
                    continue
                await characteristic.write(data_encoded)
                await asyncio.sleep_ms(interval_ms)
            except Exception as e:
                print(f"Error while getting data list: {e}")
                return


    async def blink_task(self, interval_ms=500):
        while True:
            while self.connected is False:
                self.led.toggle()
                await asyncio.sleep_ms(interval_ms)
            while self.connected is True:
                self.led.on()
                await asyncio.sleep_ms(interval_ms)