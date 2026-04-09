from __future__ import annotations

from collections.abc import Hashable
from typing import Any

from .models import (
    BacnetPointConfig,
    CollectedReading,
    DeviceStatus,
    ModbusPointConfig,
    PointBase,
    Protocol,
    Quality,
)


class Normalizer:
    def __init__(self) -> None:
        self._last_values: dict[str, Any] = {}

    def normalize(
        self,
        *,
        building_id: str,
        device_id: str,
        device_type: str,
        point: PointBase,
        protocol: Protocol,
        raw_value: Any,
        source_address: dict[str, Any],
        status: DeviceStatus = DeviceStatus.ONLINE,
        quality: Quality = Quality.GOOD,
        poll_interval_ms: int,
    ) -> CollectedReading | None:
        normalized_value = self._apply_transform(raw_value, point)
        if self._should_skip(point.point_id, point.deadband, normalized_value):
            return None

        self._last_values[point.point_id] = normalized_value

        return CollectedReading(
            building_id=building_id,
            device_id=device_id,
            device_type=device_type,
            point_id=point.point_id,
            tag=point.tag,
            standard_tag=point.standard_tag,
            protocol=protocol,
            raw_value=self._serialize_value(raw_value),
            value=self._serialize_value(normalized_value),
            unit=point.unit,
            quality=quality,
            status=status,
            source_address=source_address,
            meta={
                "poll_interval_ms": poll_interval_ms,
                **point.meta,
            },
        )

    def _apply_transform(self, raw_value: Any, point: PointBase) -> Any:
        value = self._unwrap_value(raw_value)
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return round(value * point.scale + point.offset, 6)
        return value

    def _should_skip(self, point_id: str, deadband: float | None, value: Any) -> bool:
        if deadband is None or not isinstance(value, (int, float)):
            return False

        previous = self._last_values.get(point_id)
        if previous is None or not isinstance(previous, (int, float)):
            return False

        return abs(value - previous) < deadband

    def _unwrap_value(self, value: Any) -> Any:
        if hasattr(value, "value"):
            return value.value
        return value

    def _serialize_value(self, value: Any) -> Any:
        unwrapped = self._unwrap_value(value)
        if isinstance(unwrapped, Hashable) and isinstance(unwrapped, (str, int, float, bool)):
            return unwrapped
        return str(unwrapped)


def point_source_address(point: ModbusPointConfig | BacnetPointConfig) -> dict[str, Any]:
    if isinstance(point, ModbusPointConfig):
        return {
            "register_type": point.register_type.value,
            "address": point.address,
            "register_count": point.register_count,
            "data_type": point.data_type.value,
        }

    return {
        "object_type": point.object_type,
        "object_instance": point.object_instance,
        "property_identifier": point.property_identifier,
        "array_index": point.array_index,
    }
