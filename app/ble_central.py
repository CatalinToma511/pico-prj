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
            read=True,
            initial = "Controller data".encode('utf-8')
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
            read=True,
            initial = "Device parameters".encode('utf-8')
        )
        aioble.register_services(self.controls_service)


    async def connection_task(self, _ADV_INTERVAL_US=150_000):
        while True:
            try:
                # Start advertising the BLE service
                print("Advertising and waiting for central...")
                # Wait for a connection
                self.connection = await aioble.advertise(
                    _ADV_INTERVAL_US,
                    name=self.name,
                    services=[self.CONTROLS_SERVICE_UUID]) # type: ignore
                
                # A connection is established
                self.connected = True
                # Blinking will stop automatically, set led to on
                print("Connected:", self.connection.device)

                # When the connection is ended
                await self.connection.disconnected(timeout_ms=None)
                self.connected = False
                self.led.off()
                print("Disconnected")
            except Exception as e:
                print(f"Error while establishing connection: {e}")

    async def characteristic_listener(self, characteristic, handler):
        while True:
            try:
                await characteristic.written()
                data = characteristic.read()
                handler(data)
            except Exception as e:
                print(f"Error while listening to a characteristic: {e}")

    async def send_parameters(self, characteristic, get_encoded_data_handler, interval_ms=1000):
        while True:
            try:
                if self.connected is True:
                    data_encoded = get_encoded_data_handler()
                    if data_encoded is not None:
                        await characteristic.write(data_encoded, send_update=True)
            except Exception as e:
                # print(f"Error while sending data list: {e}")
                # seemms to always give e('NoneType' object isn't iterable), but it works anyway
                pass
            finally:
                await asyncio.sleep_ms(interval_ms)

    async def no_connection_blink(self, interval_ms=500):
        while True:
            if self.connected is False:
                self.led.toggle()
            else:
                self.led.on()
            await asyncio.sleep_ms(interval_ms)