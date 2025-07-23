import aioble
import bluetooth
import machine
import utime
import asyncio


class BLE_Central:
    def __init__(self, name="PicoW_Car"):
        self.name = name
        self.connection = None
        self.connected = False
        self.CONTROLS_SERVICE_UUID = bluetooth.UUID("12345678-1234-5678-1234-56789abcdef0")
        self.CONTROLS_CHARACTERISTIC_UUID = bluetooth.UUID("12345678-1234-5678-1234-56789abcdef1")
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
            bluetooth.UUID(0x2901),  # Characteristic User Description
            read=True
        )
        aioble.register_services(self.controls_service)
        self.controls_descriptor.write("Controller data".encode('utf-8'))


    async def connection_task(self):
        _ADV_INTERVAL_US = 150_000
        while True:
            try:
                print("Advertising and waiting for central...")
                self.connection = await aioble.advertise(_ADV_INTERVAL_US, name=self.name, services=[self.CONTROLS_SERVICE_UUID]) # type: ignore
                self.connected = True
                print("Connected:", self.connection.device)

                await self.connection.disconnected(timeout_ms = None)
                print("Disconnected")
            except Exception as e:
                print(f"Error while establishing connection: {e}")

    async def characteristic_listener(self, characteristic, callback):
        try:
            while True:
                await characteristic.written()
                data = characteristic.read()
                #callback(data.decode('utf-8'))
                callback(data)
        except Exception as e:
            print(f"Error while listening to a characteristic: {e}")