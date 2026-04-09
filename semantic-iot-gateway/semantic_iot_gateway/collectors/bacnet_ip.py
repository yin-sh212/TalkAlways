from __future__ import annotations

import argparse
import asyncio
import logging
from typing import Optional

from bacpypes3.app import Application

from ..models import BacnetDeviceConfig, BacnetProbeResult, BacnetRuntimeConfig
from .base import Collector, PollResult, RawPointResult

logger = logging.getLogger(__name__)


class BacnetApplicationManager:
    def __init__(self, config: BacnetRuntimeConfig) -> None:
        self.config = config
        self.app: Optional[Application] = None
        self._lock = asyncio.Lock()

    async def open(self) -> None:
        if self.app:
            return
        args = argparse.Namespace(
            vendoridentifier=self.config.vendor_identifier,
            instance=self.config.local_device_instance,
            name=self.config.local_device_name,
            network=self.config.network,
            address=self.config.local_address,
            foreign=self.config.foreign,
            ttl=self.config.ttl,
            bbmd=None,
        )
        self.app = Application.from_args(args)

    async def close(self) -> None:
        if self.app:
            self.app.close()
            self.app = None

    async def read_property(
        self,
        *,
        address: str,
        object_identifier: str,
        property_identifier: str,
        array_index: int | None = None,
    ):
        await self.open()
        assert self.app is not None
        async with self._lock:
            return await self.app.read_property(
                address=address,
                objid=object_identifier,
                prop=property_identifier,
                array_index=array_index,
            )

    async def who_is(self, *, timeout: float, address: str | None = None) -> list[BacnetProbeResult]:
        await self.open()
        assert self.app is not None
        async with self._lock:
            responses = await self.app.who_is(address=address, timeout=timeout)

        return [
            BacnetProbeResult(
                address=str(response.pduSource),
                device_instance=response.iAmDeviceIdentifier[1],
                vendor_id=getattr(response, "vendorID", None),
                max_apdu_length=getattr(response, "maxAPDULengthAccepted", None),
                segmentation_supported=str(getattr(response, "segmentationSupported", "")) or None,
            )
            for response in responses
        ]


class BacnetIPCollector(Collector):
    def __init__(
        self,
        device: BacnetDeviceConfig,
        output,
        normalizer,
        app_manager: BacnetApplicationManager,
    ) -> None:
        super().__init__(device, output, normalizer)
        self.device = device
        self.app_manager = app_manager

    async def connect(self) -> None:
        await self.app_manager.open()

    async def disconnect(self) -> None:
        return None

    async def poll_device(self) -> PollResult:
        poll_result = PollResult()
        target_address = f"{self.device.host}:{self.device.port}"

        for point in self.device.points:
            if not point.enabled:
                continue
            try:
                value = await self.app_manager.read_property(
                    address=target_address,
                    object_identifier=f"{point.object_type},{point.object_instance}",
                    property_identifier=point.property_identifier,
                    array_index=point.array_index,
                )
                poll_result.results.append(
                    RawPointResult(
                        point=point,
                        raw_value=self._unwrap_value(value),
                        source_address={
                            "target_address": target_address,
                            "object_type": point.object_type,
                            "object_instance": point.object_instance,
                            "property_identifier": point.property_identifier,
                            "array_index": point.array_index,
                        },
                    )
                )
            except Exception as exc:
                logger.debug("bacnet point %s failed: %s", point.point_id, exc)
                poll_result.errors.append(f"{point.point_id}: {exc}")

        return poll_result

    def _unwrap_value(self, value):
        if hasattr(value, "value"):
            return value.value
        if isinstance(value, (str, int, float, bool)):
            return value
        return str(value)
