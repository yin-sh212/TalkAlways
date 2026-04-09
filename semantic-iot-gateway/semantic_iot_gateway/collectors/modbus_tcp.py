from __future__ import annotations

import logging
import struct
from typing import Any

from pymodbus.client import AsyncModbusTcpClient

from ..models import (
    ModbusAddressStyle,
    ModbusDataType,
    ModbusDeviceConfig,
    ModbusPointConfig,
    ModbusRegisterType,
)
from .base import Collector, PollResult, RawPointResult

logger = logging.getLogger(__name__)


class ModbusTCPCollector(Collector):
    def __init__(self, device: ModbusDeviceConfig, output, normalizer) -> None:
        super().__init__(device, output, normalizer)
        self.device = device
        self.client: AsyncModbusTcpClient | None = None

    async def connect(self) -> None:
        if self.client and self.client.connected:
            return

        self.client = AsyncModbusTcpClient(
            self.device.host,
            port=self.device.port,
            timeout=self.device.timeout_s,
            reconnect_delay=self.device.retry_policy.base_delay_s,
            reconnect_delay_max=self.device.retry_policy.max_delay_s,
            retries=0,
        )
        connected = await self.client.connect()
        if not connected:
            raise ConnectionError(f"Unable to connect to Modbus device {self.device.device_id}")

    async def disconnect(self) -> None:
        if self.client:
            self.client.close()
            self.client = None

    async def poll_device(self) -> PollResult:
        if not self.client:
            raise RuntimeError("Modbus client is not connected.")

        poll_result = PollResult()
        for point in self.device.points:
            if not point.enabled:
                continue
            try:
                raw_value = await self._read_point(point)
                poll_result.results.append(
                    RawPointResult(
                        point=point,
                        raw_value=raw_value,
                        source_address={
                            "register_type": point.register_type.value,
                            "address": point.address,
                            "unit_id": self.device.unit_id,
                            "register_count": self._register_count(point),
                        },
                    )
                )
            except Exception as exc:
                logger.debug("modbus point %s failed: %s", point.point_id, exc)
                poll_result.errors.append(f"{point.point_id}: {exc}")

        return poll_result

    async def _read_point(self, point: ModbusPointConfig) -> Any:
        assert self.client is not None

        register_count = self._register_count(point)
        address = self._normalize_address(point)

        if point.register_type == ModbusRegisterType.HOLDING:
            response = await self.client.read_holding_registers(address, count=register_count, device_id=self.device.unit_id)
            self._raise_on_modbus_error(response)
            return self._decode_registers(response.registers, point)

        if point.register_type == ModbusRegisterType.INPUT:
            response = await self.client.read_input_registers(address, count=register_count, device_id=self.device.unit_id)
            self._raise_on_modbus_error(response)
            return self._decode_registers(response.registers, point)

        if point.register_type == ModbusRegisterType.COIL:
            response = await self.client.read_coils(address, count=register_count, device_id=self.device.unit_id)
            self._raise_on_modbus_error(response)
            return bool(response.bits[0])

        response = await self.client.read_discrete_inputs(address, count=register_count, device_id=self.device.unit_id)
        self._raise_on_modbus_error(response)
        return bool(response.bits[0])

    def _normalize_address(self, point: ModbusPointConfig) -> int:
        if self.device.address_style == ModbusAddressStyle.OFFSET:
            return point.address

        if point.register_type == ModbusRegisterType.HOLDING:
            return point.address - 40001
        if point.register_type == ModbusRegisterType.INPUT:
            return point.address - 30001
        if point.register_type == ModbusRegisterType.DISCRETE:
            return point.address - 10001
        return point.address - 1

    def _register_count(self, point: ModbusPointConfig) -> int:
        if point.register_count:
            return point.register_count

        defaults = {
            ModbusDataType.BOOL: 1,
            ModbusDataType.UINT16: 1,
            ModbusDataType.INT16: 1,
            ModbusDataType.UINT32: 2,
            ModbusDataType.INT32: 2,
            ModbusDataType.FLOAT32: 2,
            ModbusDataType.FLOAT64: 4,
            ModbusDataType.STRING: 4,
        }
        return defaults[point.data_type]

    def _decode_registers(self, registers: list[int], point: ModbusPointConfig) -> Any:
        words = list(registers)
        if point.word_order.value == "little" and len(words) > 1:
            words.reverse()

        chunks = [word.to_bytes(2, byteorder="big", signed=False) for word in words]
        if point.byte_order.value == "little":
            chunks = [bytes(reversed(chunk)) for chunk in chunks]
        payload = b"".join(chunks)

        if point.data_type == ModbusDataType.BOOL:
            return bool(words[0])
        if point.data_type == ModbusDataType.UINT16:
            return struct.unpack(">H", payload[:2])[0]
        if point.data_type == ModbusDataType.INT16:
            return struct.unpack(">h", payload[:2])[0]
        if point.data_type == ModbusDataType.UINT32:
            return struct.unpack(">I", payload[:4])[0]
        if point.data_type == ModbusDataType.INT32:
            return struct.unpack(">i", payload[:4])[0]
        if point.data_type == ModbusDataType.FLOAT32:
            return struct.unpack(">f", payload[:4])[0]
        if point.data_type == ModbusDataType.FLOAT64:
            return struct.unpack(">d", payload[:8])[0]
        return payload.decode("utf-8", errors="ignore").rstrip("\x00").strip()

    def _raise_on_modbus_error(self, response) -> None:
        if hasattr(response, "isError") and response.isError():
            raise RuntimeError(str(response))
