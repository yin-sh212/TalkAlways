from __future__ import annotations

import asyncio
import logging

from .collectors import BacnetApplicationManager, BacnetIPCollector, ModbusTCPCollector
from .models import GatewayConfig, Protocol
from .normalizer import Normalizer
from .sinks import OutputManager

logger = logging.getLogger(__name__)


class EdgeGatewayRuntime:
    def __init__(self, config: GatewayConfig) -> None:
        self.config = config
        self.stop_event = asyncio.Event()
        self.normalizer = Normalizer()
        self.output = OutputManager(config)
        self.bacnet_manager = BacnetApplicationManager(config.bacnet)

    def request_stop(self) -> None:
        self.stop_event.set()

    async def run(self, duration_s: float | None = None) -> None:
        collectors = []
        for device in self.config.enabled_devices:
            if device.protocol == Protocol.MODBUS_TCP:
                collectors.append(ModbusTCPCollector(device, self.output, self.normalizer))
            else:
                collectors.append(BacnetIPCollector(device, self.output, self.normalizer, self.bacnet_manager))

        await self.output.initialize()
        tasks = [asyncio.create_task(self.output.run(self.stop_event), name="output-flusher")]
        tasks.extend(
            asyncio.create_task(collector.run(self.stop_event), name=f"collector-{collector.device.device_id}")
            for collector in collectors
        )

        try:
            if duration_s is None:
                while not self.stop_event.is_set():
                    await asyncio.sleep(3600)
            else:
                await asyncio.sleep(duration_s)
        except asyncio.CancelledError:
            logger.info("runtime cancelled")
            raise
        finally:
            self.stop_event.set()
            await asyncio.gather(*tasks, return_exceptions=True)
            await self.bacnet_manager.close()
            await self.output.close()
