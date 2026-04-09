from __future__ import annotations

import abc
import asyncio
import logging
from dataclasses import dataclass, field
from time import monotonic
from typing import Any

from ..models import (
    AnyDeviceConfig,
    BacnetPointConfig,
    DeviceState,
    DeviceStatus,
    ModbusPointConfig,
    Protocol,
    Quality,
)
from ..normalizer import Normalizer, point_source_address

logger = logging.getLogger(__name__)

PointConfig = ModbusPointConfig | BacnetPointConfig


@dataclass
class RawPointResult:
    point: PointConfig
    raw_value: Any
    source_address: dict[str, Any]


@dataclass
class PollResult:
    results: list[RawPointResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class Collector(abc.ABC):
    def __init__(self, device: AnyDeviceConfig, output, normalizer: Normalizer) -> None:
        self.device = device
        self.output = output
        self.normalizer = normalizer
        self.protocol = Protocol(device.protocol)

    async def run(self, stop_event: asyncio.Event) -> None:
        backoff = self.device.retry_policy.base_delay_s

        while not stop_event.is_set():
            cycle_started = monotonic()
            try:
                await self.connect()
                poll_result = await self.poll_device()
                elapsed_ms = round((monotonic() - cycle_started) * 1000, 2)

                for item in poll_result.results:
                    reading = self.normalizer.normalize(
                        building_id=self.device.building_id,
                        device_id=self.device.device_id,
                        device_type=self.device.device_type,
                        point=item.point,
                        protocol=self.protocol,
                        raw_value=item.raw_value,
                        source_address=item.source_address or point_source_address(item.point),
                        status=DeviceStatus.ONLINE if not poll_result.errors else DeviceStatus.DEGRADED,
                        quality=Quality.GOOD if not poll_result.errors else Quality.UNCERTAIN,
                        poll_interval_ms=self.device.poll_interval_ms,
                    )
                    if reading:
                        await self.output.publish_reading(reading)

                await self.output.publish_device_state(
                    DeviceState(
                        building_id=self.device.building_id,
                        device_id=self.device.device_id,
                        device_type=self.device.device_type,
                        protocol=self.protocol,
                        status=DeviceStatus.ONLINE if not poll_result.errors else DeviceStatus.DEGRADED,
                        quality=Quality.GOOD if not poll_result.errors else Quality.UNCERTAIN,
                        latency_ms=elapsed_ms,
                        error="; ".join(poll_result.errors[:3]) if poll_result.errors else None,
                    )
                )
                backoff = self.device.retry_policy.base_delay_s
                await self._sleep_interval(stop_event)
            except Exception as exc:
                logger.warning("collector %s failed: %s", self.device.device_id, exc)
                await self.output.publish_device_state(
                    DeviceState(
                        building_id=self.device.building_id,
                        device_id=self.device.device_id,
                        device_type=self.device.device_type,
                        protocol=self.protocol,
                        status=DeviceStatus.OFFLINE,
                        quality=Quality.BAD,
                        error=str(exc),
                    )
                )
                await self.disconnect()
                await self._sleep(stop_event, backoff)
                backoff = min(
                    self.device.retry_policy.max_delay_s,
                    max(backoff, self.device.retry_policy.base_delay_s) * self.device.retry_policy.multiplier,
                )

        await self.disconnect()

    async def _sleep_interval(self, stop_event: asyncio.Event) -> None:
        await self._sleep(stop_event, self.device.poll_interval_ms / 1000.0)

    async def _sleep(self, stop_event: asyncio.Event, seconds: float) -> None:
        if seconds <= 0:
            return
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=seconds)
        except TimeoutError:
            return

    @abc.abstractmethod
    async def connect(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def disconnect(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def poll_device(self) -> PollResult:
        raise NotImplementedError
