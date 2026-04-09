import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException, Query, Request
try:
    from pydantic import BaseModel, ConfigDict, Field
except ImportError:  # pragma: no cover
    from pydantic import BaseModel, Field  # type: ignore
    ConfigDict = None

from app.services.iot_ingest import (
    ensure_iot_ingest_tables,
    get_ingest_batch_detail,
    list_ingest_batches,
    save_ingest_batch,
)

router = APIRouter(prefix="/api/iot/ingest", tags=["物联网接入"])


class FlexibleModel(BaseModel):
    if ConfigDict is not None:
        model_config = ConfigDict(extra="allow", populate_by_name=True)
    else:
        class Config:
            extra = "allow"
            allow_population_by_field_name = True


class IngestReading(FlexibleModel):
    timestamp: str
    building_id: Optional[str] = None
    device_id: str
    point_id: str
    tag: Optional[str] = None
    standard_tag: Optional[str] = None
    value: Any = None
    raw_value: Any = None
    unit: Optional[str] = None
    quality: Optional[str] = None
    status: Optional[str] = None
    protocol: Optional[str] = None


class IngestDeviceState(FlexibleModel):
    observed_at: str
    device_id: str
    protocol: Optional[str] = None
    status: Optional[str] = None
    quality: Optional[str] = None
    error: Optional[str] = None


class IngestBatchRequest(FlexibleModel):
    schema_name: str = Field("talkalways.iot.ingest.batch.v1", alias="schema")
    gateway_id: str
    site_id: str
    sent_at: Optional[str] = None
    batch_id: str
    sequence: int = 0
    readings: List[IngestReading] = Field(default_factory=list)
    device_states: List[IngestDeviceState] = Field(default_factory=list)


def verify_ingest_token(authorization: Optional[str]) -> None:
    expected_token = os.getenv("IOT_INGEST_TOKEN", "").strip()
    if not expected_token:
        return

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="缺少物联网接入令牌")

    provided_token = authorization.removeprefix("Bearer ").strip()
    if provided_token != expected_token:
        raise HTTPException(status_code=401, detail="物联网接入令牌无效")


@router.post("/batch")
async def ingest_batch(
    request_body: IngestBatchRequest,
    request: Request,
    authorization: Optional[str] = Header(None),
):
    """接收边缘采集网关的批量上报数据。"""
    verify_ingest_token(authorization)

    if not request_body.gateway_id.strip():
        raise HTTPException(status_code=400, detail="gateway_id 不能为空")
    if not request_body.site_id.strip():
        raise HTTPException(status_code=400, detail="site_id 不能为空")
    if not request_body.batch_id.strip():
        raise HTTPException(status_code=400, detail="batch_id 不能为空")

    payload = request_body.dict(by_alias=True)
    source_ip = request.client.host if request.client else None
    result = await save_ingest_batch(payload, source_ip=source_ip)

    return {
        "code": 200,
        "message": "批次已接收" if result["stored"] else "重复批次，已忽略",
        "data": {
            **result,
            "accepted_at": datetime.now().isoformat(),
        },
    }


@router.get("/batches")
async def get_ingest_batches(
    limit: int = Query(20, ge=1, le=200, description="返回批次数量"),
    gateway_id: Optional[str] = Query(None, description="按网关过滤"),
    authorization: Optional[str] = Header(None),
):
    """查看最近接收到的批次，方便联调。"""
    verify_ingest_token(authorization)

    items = await list_ingest_batches(limit=limit, gateway_id=gateway_id)
    return {
        "code": 200,
        "message": "成功",
        "data": {
            "list": items,
            "limit": limit,
            "gateway_id": gateway_id,
        },
    }


@router.get("/batches/{record_id}")
async def get_ingest_batch(
    record_id: int,
    authorization: Optional[str] = Header(None),
):
    """查看单个批次的原始 payload。"""
    verify_ingest_token(authorization)

    item = await get_ingest_batch_detail(record_id)
    if not item:
        raise HTTPException(status_code=404, detail="批次不存在")

    return {
        "code": 200,
        "message": "成功",
        "data": item,
    }


@router.get("/health")
async def ingest_health(authorization: Optional[str] = Header(None)):
    """检查接入口和接收表是否可用。"""
    verify_ingest_token(authorization)
    await ensure_iot_ingest_tables()
    return {
        "code": 200,
        "message": "物联网接入口可用",
        "data": {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
        },
    }
