# app/api/device_api.py
from fastapi import APIRouter, Query, Body
from typing import Optional, List
from app.database.db import Database
from pydantic import BaseModel

router = APIRouter(prefix="/api/device", tags=["设备管理"])


class DeviceCreate(BaseModel):
    name: str
    type: str
    building_id: str
    status: str = "online"


class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    building_id: Optional[str] = None
    status: Optional[str] = None


@router.get("/list")
async def list_devices(
        device_name: Optional[str] = Query(None, description="设备名称模糊查询")
):
    """
    设备查询

    - 入参：deviceName（可选）
    - 出参：deviceName, deviceType, building（设备所在建筑ID）, deviceStatus, deviceTotal（设备总数）
    """
    conditions = ["d.is_deleted = FALSE"]
    params = []

    # 设备名称模糊查询（如果提供了）
    if device_name:
        conditions.append("d.name LIKE %s")
        params.append(f"%{device_name}%")

    where_clause = " AND ".join(conditions)

    # SQL 查询 - 严格按照要求的出参
    sql = f"""
        SELECT 
            d.id as id,
            d.name as deviceName,
            d.type as deviceType,
            d.building_id as building,
            d.status as deviceStatus,
            (SELECT COUNT(*) FROM devices WHERE is_deleted = FALSE) as deviceTotal
        FROM devices d
        WHERE {where_clause}
        ORDER BY d.created_at DESC
    """

    print(f"SQL: {sql}")  # 调试用
    print(f"Params: {params}")  # 调试用

    devices = await Database.fetch_all(sql, tuple(params) if params else None)

    return {
        "code": 200,
        "message": "成功",
        "data": {
            "total": len(devices),
            "items": devices
        }
    }

# 其他函数保持不变...


@router.post("/add")
async def add_device(device: DeviceCreate):
    """新增设备"""
    import uuid
    device_id = str(uuid.uuid4())[:8]

    sql = """
        INSERT INTO devices (id, name, type, building_id, status)
        VALUES (%s, %s, %s, %s, %s)
    """

    await Database.execute(sql, (device_id, device.name, device.type, device.building_id, device.status))

    return {
        "code": 200,
        "message": "设备添加成功",
        "data": {"device_id": device_id, "is_success": True}
    }


@router.put("/update/{device_id}")
async def update_device(device_id: str, device: DeviceUpdate):
    """更新设备信息"""
    updates = []
    params = []

    if device.name:
        updates.append("name = %s")
        params.append(device.name)
    if device.type:
        updates.append("type = %s")
        params.append(device.type)
    if device.building_id:
        updates.append("building_id = %s")
        params.append(device.building_id)
    if device.status:
        updates.append("status = %s")
        params.append(device.status)

    if not updates:
        return {"code": 400, "message": "没有要更新的字段", "data": None}

    params.append(device_id)
    sql = f"UPDATE devices SET {', '.join(updates)} WHERE id = %s"

    await Database.execute(sql, tuple(params))

    return {
        "code": 200,
        "message": "设备更新成功",
        "data": {"is_success": True}
    }


@router.delete("/delete/{device_id}")
async def delete_device(device_id: str):
    """软删除设备（不是真删除）"""
    sql = "UPDATE devices SET is_deleted = TRUE WHERE id = %s"
    await Database.execute(sql, (device_id,))

    return {
        "code": 200,
        "message": "设备已删除",
        "data": {"is_success": True}
    }


@router.get("/stats")
async def get_device_stats():
    """设备运行状态统计 & 设备类型占比"""
    # 1. 运行状态统计
    status_sql = """
        SELECT 
            status,
            COUNT(*) as count
        FROM devices
        WHERE is_deleted = FALSE
        GROUP BY status
    """
    status_stats = await Database.fetch_all(status_sql)

    # 2. 设备类型占比
    type_sql = """
        SELECT 
            type,
            COUNT(*) as count,
            ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM devices WHERE is_deleted = FALSE), 2) as percentage
        FROM devices
        WHERE is_deleted = FALSE
        GROUP BY type
        ORDER BY count DESC
    """
    type_stats = await Database.fetch_all(type_sql)

    # 3. 在线设备率
    total_sql = "SELECT COUNT(*) as total FROM devices WHERE is_deleted = FALSE"
    online_sql = "SELECT COUNT(*) as online FROM devices WHERE status = 'online' AND is_deleted = FALSE"

    total = await Database.fetch_one(total_sql)
    online = await Database.fetch_one(online_sql)

    online_rate = round((online['online'] / total['total'] * 100), 2) if total['total'] > 0 else 0

    return {
        "code": 200,
        "message": "成功",
        "data": {
            "online_rate": online_rate,
            "total_devices": total['total'],
            "online_devices": online['online'],
            "status_stats": {s['status']: s['count'] for s in status_stats},
            "type_stats": type_stats
        }
    }