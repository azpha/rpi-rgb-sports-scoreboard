import asyncio
import json
import time
from typing import Optional

GOVEE_LAN_PORT = 4003
INTER_SEGMENT_DELAY = 0.1

class GoveeProtocol(asyncio.DatagramProtocol):
    def __init__(self):
        self.transport = None
        self._pending: asyncio.Future | None = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        if self._pending and not self._pending.done():
            self._pending.set_result(json.loads(data.decode()))

    def error_received(self, exc):
        if self._pending and not self._pending.done():
            self._pending.set_exception(exc)

class GoveeApi:
    def __init__(self, device_ip: str, retries: int = 3, retry_delay: float = 0.05):
        self.device_ip = device_ip
        self.retries = retries
        self.retry_delay = retry_delay
        self._protocol: Optional[GoveeProtocol] = None

    async def connect(self):
        loop = asyncio.get_running_loop()
        _, self._protocol = await loop.create_datagram_endpoint(
            GoveeProtocol,
            remote_addr=(self.device_ip, GOVEE_LAN_PORT)
        )

    async def close(self):
        if self._protocol and self._protocol.transport:
            self._protocol.transport.close()

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def send_scene(self, scene_code: str):
        power_payload = {
            "msg": {
                "cmd": "turn",
                "data": {
                    "value": 1  # 1 = on, 0 = off
                }
            }
        }
        self._send(power_payload)
        time.sleep(0.5)

        segments = scene_code.split(",")
        for i, segment in enumerate(segments):
            payload = {"msg": {"cmd": "ptReal", "data": {"command": [segment]}}}
            await self._send(payload)
            if i < len(segments) - 1:
                await asyncio.sleep(INTER_SEGMENT_DELAY)

    async def set_color(self, r: int, g: int, b: int, kelvin: int = 0):
        payload = {
            "msg": {
                "cmd": "colorwc",
                "data": {
                    "color": {"r": r, "g": g, "b": b},
                    "colorTemInKelvin": kelvin
                }
            }
        }
        await self._send(payload)

    async def _send(self, payload: dict) -> Optional[dict]:
        if not self._protocol:
            raise RuntimeError("Not connected — use async with or call connect() first")

        data = json.dumps(payload).encode()
        loop = asyncio.get_running_loop()

        for attempt in range(self.retries):
            future: asyncio.Future = loop.create_future()
            self._protocol._pending = future
            self._protocol.transport.sendto(data)

            try:
                return await asyncio.wait_for(future, timeout=1.0)
            except asyncio.TimeoutError:
                if attempt < self.retries - 1:
                    await asyncio.sleep(self.retry_delay)

        print(f"Warning: no response after {self.retries} attempts")
        return None