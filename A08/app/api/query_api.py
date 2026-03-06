from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from datetime import datetime
from app.database.db import Database

router = APIRouter(prefix="/api/query", tags=["数据查询"])


@router.get("/raw")
async def get_raw_data(
        building_id: Optional[str] = None,
        meter_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = Query(100, ge=1, le=1000),
        offset: int = Query(0, ge=0)
):
    """获取原始能耗数据（支持多条件查询）"""
    sql = "SELECT * FROM energy_consumption WHERE 1=1"
    params = []

    if building_id:
        sql += " AND building_id = %s"
        params.append(building_id)

    if meter_id:
        sql += " AND meter_id = %s"
        params.append(meter_id)

    if start_date:
        sql += " AND DATE(timestamp) >= %s"
        params.append(start_date)

    if end_date:
        sql += " AND DATE(timestamp) <= %s"
        params.append(end_date)

    # 先查询总数
    count_sql = sql.replace("SELECT *", "SELECT COUNT(*) as total")
    count_result = await Database.fetch_one(count_sql, tuple(params))
    total = count_result['total'] if count_result else 0

    # 分页查询
    sql += " ORDER BY timestamp DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    data = await Database.fetch_all(sql, tuple(params))

    return {
        "code": 200,
        "data": data,
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total
        }
    }


@router.get("/buildings")
async def get_buildings():
    """获取所有建筑列表"""
    sql = "SELECT id, name, type, area FROM buildings ORDER BY id"
    data = await Database.fetch_all(sql)
    return {"code": 200, "data": data}


@router.get("/meters")
async def get_meters(building_id: Optional[str] = None):
    """获取监测点列表"""
    sql = "SELECT * FROM meters"
    params = []
    if building_id:
        sql += " WHERE building_id = %s"
        params.append(building_id)
    sql += " ORDER BY id"

    data = await Database.fetch_all(sql, tuple(params) if params else None)
    return {"code": 200, "data": data}


# 在 query_api.py 中添加
@router.get("/device-status")
async def get_device_status(
        building_id: Optional[str] = None,
        meter_id: Optional[str] = None,
        status: Optional[str] = None  # normal/abnormal
):
    """获取设备运行状态"""
    sql = """
        SELECT 
            m.id as meter_id,
            m.building_id,
            m.type,
            m.status,
            COUNT(e.id) as data_count,
            MAX(e.timestamp) as last_update,
            AVG(e.electricity) as avg_power,
            SUM(CASE WHEN e.is_anomaly = 1 THEN 1 ELSE 0 END) as anomaly_count
        FROM meters m
        LEFT JOIN energy_consumption e ON m.id = e.meter_id
        WHERE 1=1
    """
    params = []

    if building_id:
        sql += " AND m.building_id = %s"
        params.append(building_id)
    if meter_id:
        sql += " AND m.id = %s"
        params.append(meter_id)
    if status:
        sql += " AND m.status = %s"
        params.append(status)

    sql += " GROUP BY m.id"

    data = await Database.fetch_all(sql, tuple(params) if params else None)

    # 计算健康度
    for item in data:
        total = item['data_count'] or 1
        anomaly = item['anomaly_count'] or 0
        health_score = max(0, 100 - (anomaly / total * 100))
        item['health_score'] = round(health_score, 2)

    return {"code": 200, "data": data}