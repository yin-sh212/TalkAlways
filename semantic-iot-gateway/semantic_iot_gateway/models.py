from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Any, Literal, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, PositiveInt


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Protocol(str, Enum):
    MODBUS_TCP = "modbus_tcp"
    BACNET_IP = "bacnet_ip"


class DeviceStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class Quality(str, Enum):
    GOOD = "good"
    BAD = "bad"
    UNCERTAIN = "uncertain"
    STALE = "stale"


class RetryPolicy(BaseModel):
    base_delay_s: float = 1.0
    max_delay_s: float = 30.0
    multiplier: float = 2.0


class PointBase(BaseModel):
    point_id: str
    tag: str
    standard_tag: str
    unit: Optional[str] = None
    scale: float = 1.0
    offset: float = 0.0
    deadband: Optional[float] = None
    enabled: bool = True
    meta: dict[str, Any] = Field(default_factory=dict)


class ModbusRegisterType(str, Enum):
    HOLDING = "holding"
    INPUT = "input"
    COIL = "coil"
    DISCRETE = "discrete"


class ModbusDataType(str, Enum):
    BOOL = "bool"
    UINT16 = "uint16"
    INT16 = "int16"
    UINT32 = "uint32"
    INT32 = "int32"
    FLOAT32 = "float32"
    FLOAT64 = "float64"
    STRING = "string"


class ByteOrder(str, Enum):
    BIG = "big"
    LITTLE = "little"


class WordOrder(str, Enum):
    BIG = "big"
    LITTLE = "little"


class ModbusPointConfig(PointBase):
    register_type: ModbusRegisterType
    address: int
    data_type: ModbusDataType
    register_count: Optional[PositiveInt] = None
    byte_order: ByteOrder = ByteOrder.BIG
    word_order: WordOrder = WordOrder.BIG


class BacnetPointConfig(PointBase):
    object_type: str
    object_instance: int
    property_identifier: str = "present-value"
    array_index: Optional[int] = None


class DeviceBase(BaseModel):
    device_id: str
    name: str
    building_id: str
    device_type: str
    host: str
    port: int
    enabled: bool = True
    poll_interval_ms: PositiveInt = 5000
    timeout_s: float = 3.0
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)


class ModbusAddressStyle(str, Enum):
    OFFSET = "offset"
    REFERENCE = "reference"


class ModbusDeviceConfig(DeviceBase):
    protocol: Literal[Protocol.MODBUS_TCP] = Protocol.MODBUS_TCP
    unit_id: int = 1
    address_style: ModbusAddressStyle = ModbusAddressStyle.OFFSET
    points: list[ModbusPointConfig]


class BacnetDeviceConfig(DeviceBase):
    protocol: Literal[Protocol.BACNET_IP] = Protocol.BACNET_IP
    device_instance: Optional[int] = None
    points: list[BacnetPointConfig]


AnyDeviceConfig = Annotated[
    Union[ModbusDeviceConfig, BacnetDeviceConfig],
    Field(discriminator="protocol"),
]


class BacnetRuntimeConfig(BaseModel):
    enabled: bool = True
    local_address: Optional[str] = None
    local_device_instance: int = 599001
    local_device_name: str = "SemanticEdgeGateway"
    vendor_identifier: int = 999
    network: int = 0
    foreign: Optional[str] = None
    ttl: int = 300


class HttpSinkConfig(BaseModel):
    enabled: bool = True
    endpoint: str
    auth_token: Optional[str] = None
    timeout_s: float = 5.0
    verify_tls: bool = True


class SpoolConfig(BaseModel):
    enabled: bool = True
    path: str = "data/spool.db"
    retry_interval_s: float = 5.0
    retry_batch_size: PositiveInt = 20


class OutputConfig(BaseModel):
    batch_size: PositiveInt = 100
    flush_interval_s: float = 1.0
    stdout_enabled: bool = True
    http: Optional[HttpSinkConfig] = None
    spool: SpoolConfig = Field(default_factory=SpoolConfig)


class GatewayConfig(BaseModel):
    gateway_id: str
    site_id: str
    output: OutputConfig
    bacnet: BacnetRuntimeConfig = Field(default_factory=BacnetRuntimeConfig)
    devices: list[AnyDeviceConfig]

    @property
    def enabled_devices(self) -> list[AnyDeviceConfig]:
        return [device for device in self.devices if device.enabled]


class CollectedReading(BaseModel):
    timestamp: str = Field(default_factory=utc_now_iso)
    building_id: str
    device_id: str
    device_type: str
    point_id: str
    tag: str
    standard_tag: str
    protocol: Protocol
    raw_value: Any
    value: Any
    unit: Optional[str] = None
    quality: Quality = Quality.GOOD
    status: DeviceStatus = DeviceStatus.ONLINE
    source_address: dict[str, Any] = Field(default_factory=dict)
    meta: dict[str, Any] = Field(default_factory=dict)


class DeviceState(BaseModel):
    observed_at: str = Field(default_factory=utc_now_iso)
    building_id: str
    device_id: str
    device_type: str
    protocol: Protocol
    status: DeviceStatus
    quality: Quality
    latency_ms: Optional[float] = None
    error: Optional[str] = None


class BatchEnvelope(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    schema_name: Literal["talkalways.iot.ingest.batch.v1"] = Field(
        default="talkalways.iot.ingest.batch.v1",
        alias="schema",
    )
    gateway_id: str
    site_id: str
    sent_at: str = Field(default_factory=utc_now_iso)
    batch_id: str = Field(default_factory=lambda: uuid4().hex)
    sequence: int
    readings: list[CollectedReading]
    device_states: list[DeviceState]


class ModbusProbeResult(BaseModel):
    host: str
    port: int
    reachable: bool
    protocol: Literal["modbus_tcp"] = "modbus_tcp"
    detail: Optional[str] = None


class BacnetProbeResult(BaseModel):
    address: str
    device_instance: int
    vendor_id: Optional[int] = None
    max_apdu_length: Optional[int] = None
    segmentation_supported: Optional[str] = None
