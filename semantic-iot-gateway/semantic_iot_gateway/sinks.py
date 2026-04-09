from __future__ import annotations

import abc
import asyncio
import json
from typing import Optional

import httpx

from .models import BatchEnvelope, DeviceState, GatewayConfig, HttpSinkConfig, OutputConfig
from .spool import SQLiteSpool


class Sink(abc.ABC):
    async def initialize(self) -> None:
        return None

    @abc.abstractmethod
    async def send_batch(self, batch: BatchEnvelope) -> bool:
        raise NotImplementedError

    async def close(self) -> None:
        return None


class StdoutSink(Sink):
    async def send_batch(self, batch: BatchEnvelope) -> bool:
        print(json.dumps(batch.model_dump(mode="json", by_alias=True), ensure_ascii=False))
        return True


class HttpPushSink(Sink):
    def __init__(self, config: HttpSinkConfig, spool: Optional[SQLiteSpool], retry_batch_size: int) -> None:
        self.config = config
        self.spool = spool
        self.retry_batch_size = retry_batch_size
        self.client: Optional[httpx.AsyncClient] = None

    async def initialize(self) -> None:
        self.client = httpx.AsyncClient(timeout=self.config.timeout_s, verify=self.config.verify_tls)
        if self.spool:
            await self.spool.initialize()

    async def send_batch(self, batch: BatchEnvelope) -> bool:
        payload = batch.model_dump(mode="json", by_alias=True)
        try:
            await self._post_payload(payload)
            return True
        except Exception as exc:
            if self.spool:
                await self.spool.enqueue(payload, str(exc))
            return False

    async def retry_pending(self) -> None:
        if not self.spool:
            return

        pending = await self.spool.fetch_pending(self.retry_batch_size)
        for row_id, payload in pending:
            try:
                await self._post_payload(payload)
            except Exception as exc:
                await self.spool.mark_failed(row_id, str(exc))
            else:
                await self.spool.delete([row_id])

    async def _post_payload(self, payload: dict) -> None:
        if not self.client:
            raise RuntimeError("HTTP sink is not initialized.")

        headers = {"Content-Type": "application/json"}
        if self.config.auth_token:
            headers["Authorization"] = f"Bearer {self.config.auth_token}"

        response = await self.client.post(self.config.endpoint, json=payload, headers=headers)
        response.raise_for_status()

    async def close(self) -> None:
        if self.client:
            await self.client.aclose()


class OutputManager:
    def __init__(self, gateway: GatewayConfig) -> None:
        self.gateway = gateway
        self.config: OutputConfig = gateway.output
        self.readings = []
        self.device_states: dict[str, DeviceState] = {}
        self.sequence = 0
        self._flush_event = asyncio.Event()
        self._lock = asyncio.Lock()
        self._spool = SQLiteSpool(self.config.spool.path) if self.config.spool.enabled else None
        self.sinks: list[Sink] = []
        if self.config.stdout_enabled:
            self.sinks.append(StdoutSink())
        if self.config.http and self.config.http.enabled:
            self.sinks.append(HttpPushSink(self.config.http, self._spool, self.config.spool.retry_batch_size))

    async def initialize(self) -> None:
        for sink in self.sinks:
            await sink.initialize()

    async def publish_reading(self, reading) -> None:
        async with self._lock:
            self.readings.append(reading)
            if len(self.readings) >= self.config.batch_size:
                self._flush_event.set()

    async def publish_device_state(self, state: DeviceState) -> None:
        async with self._lock:
            self.device_states[state.device_id] = state

    async def run(self, stop_event: asyncio.Event) -> None:
        while not stop_event.is_set():
            try:
                await asyncio.wait_for(self._flush_event.wait(), timeout=self.config.flush_interval_s)
            except TimeoutError:
                pass
            self._flush_event.clear()
            await self.flush()
            await self._retry_spooled()

        await self.flush()
        await self._retry_spooled()

    async def flush(self) -> None:
        async with self._lock:
            if not self.readings and not self.device_states:
                return
            self.sequence += 1
            batch = BatchEnvelope(
                gateway_id=self.gateway.gateway_id,
                site_id=self.gateway.site_id,
                sequence=self.sequence,
                readings=list(self.readings),
                device_states=list(self.device_states.values()),
            )
            self.readings.clear()
            self.device_states.clear()

        await asyncio.gather(*(sink.send_batch(batch) for sink in self.sinks))

    async def close(self) -> None:
        for sink in self.sinks:
            await sink.close()

    async def _retry_spooled(self) -> None:
        for sink in self.sinks:
            if isinstance(sink, HttpPushSink):
                await sink.retry_pending()
