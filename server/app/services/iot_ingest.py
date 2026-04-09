import json
from typing import Any, Dict, List, Optional

from app.database.db import Database


IOT_INGEST_BATCHES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS iot_ingest_batches (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '接收批次 ID',
    gateway_id VARCHAR(100) NOT NULL COMMENT '边缘网关 ID',
    site_id VARCHAR(100) DEFAULT NULL COMMENT '站点 ID',
    schema_name VARCHAR(100) DEFAULT NULL COMMENT '上报协议版本',
    batch_id VARCHAR(100) NOT NULL COMMENT '批次 ID',
    sequence_no BIGINT DEFAULT 0 COMMENT '网关序号',
    sent_at VARCHAR(64) DEFAULT NULL COMMENT '边缘侧发送时间',
    source_ip VARCHAR(64) DEFAULT NULL COMMENT '请求来源 IP',
    reading_count INT NOT NULL DEFAULT 0 COMMENT '点位条数',
    device_state_count INT NOT NULL DEFAULT 0 COMMENT '设备状态条数',
    raw_payload LONGTEXT NOT NULL COMMENT '原始 JSON',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '接收时间',
    UNIQUE KEY uk_gateway_batch (gateway_id, batch_id),
    KEY idx_created_at (created_at),
    KEY idx_gateway_id (gateway_id),
    KEY idx_site_id (site_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='物联网网关原始批次接收表';
"""


async def ensure_iot_ingest_tables() -> None:
    await Database.execute(IOT_INGEST_BATCHES_TABLE_SQL)


async def save_ingest_batch(payload: Dict[str, Any], source_ip: Optional[str] = None) -> Dict[str, Any]:
    await ensure_iot_ingest_tables()

    gateway_id = str(payload.get("gateway_id") or "").strip()
    batch_id = str(payload.get("batch_id") or "").strip()
    site_id = str(payload.get("site_id") or "").strip() or None
    schema_name = str(payload.get("schema") or "").strip() or None
    sent_at = str(payload.get("sent_at") or "").strip() or None
    sequence_no = int(payload.get("sequence") or 0)
    readings = payload.get("readings") or []
    device_states = payload.get("device_states") or []

    existing = await Database.fetch_one(
        """
        SELECT id, gateway_id, batch_id, created_at
        FROM iot_ingest_batches
        WHERE gateway_id = %s AND batch_id = %s
        """,
        (gateway_id, batch_id),
    )
    if existing:
        return {
            "stored": False,
            "duplicate": True,
            "record_id": existing["id"],
            "gateway_id": existing["gateway_id"],
            "batch_id": existing["batch_id"],
            "received_at": existing["created_at"].isoformat() if existing.get("created_at") else None,
            "reading_count": len(readings),
            "device_state_count": len(device_states),
        }

    await Database.execute(
        """
        INSERT INTO iot_ingest_batches (
            gateway_id,
            site_id,
            schema_name,
            batch_id,
            sequence_no,
            sent_at,
            source_ip,
            reading_count,
            device_state_count,
            raw_payload
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            gateway_id,
            site_id,
            schema_name,
            batch_id,
            sequence_no,
            sent_at,
            source_ip,
            len(readings),
            len(device_states),
            json.dumps(payload, ensure_ascii=False),
        ),
    )

    created = await Database.fetch_one(
        """
        SELECT id, created_at
        FROM iot_ingest_batches
        WHERE gateway_id = %s AND batch_id = %s
        """,
        (gateway_id, batch_id),
    )

    return {
        "stored": True,
        "duplicate": False,
        "record_id": created["id"] if created else None,
        "gateway_id": gateway_id,
        "site_id": site_id,
        "batch_id": batch_id,
        "received_at": created["created_at"].isoformat() if created and created.get("created_at") else None,
        "reading_count": len(readings),
        "device_state_count": len(device_states),
    }


async def list_ingest_batches(limit: int = 20, gateway_id: Optional[str] = None) -> List[Dict[str, Any]]:
    await ensure_iot_ingest_tables()

    params: List[Any] = []
    where_sql = ""
    if gateway_id:
        where_sql = "WHERE gateway_id = %s"
        params.append(gateway_id)

    sql = f"""
        SELECT
            id,
            gateway_id,
            site_id,
            schema_name,
            batch_id,
            sequence_no,
            sent_at,
            source_ip,
            reading_count,
            device_state_count,
            created_at
        FROM iot_ingest_batches
        {where_sql}
        ORDER BY id DESC
        LIMIT %s
    """
    params.append(limit)
    return await Database.fetch_all(sql, tuple(params))


async def get_ingest_batch_detail(record_id: int) -> Optional[Dict[str, Any]]:
    await ensure_iot_ingest_tables()

    item = await Database.fetch_one(
        """
        SELECT
            id,
            gateway_id,
            site_id,
            schema_name,
            batch_id,
            sequence_no,
            sent_at,
            source_ip,
            reading_count,
            device_state_count,
            raw_payload,
            created_at
        FROM iot_ingest_batches
        WHERE id = %s
        """,
        (record_id,),
    )
    if not item:
        return None

    try:
        item["raw_payload"] = json.loads(item["raw_payload"])
    except Exception:
        pass
    return item
