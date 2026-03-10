from fastapi import APIRouter, Query, HTTPException,Body
from typing import Optional, List
from datetime import datetime
from app.database.db import Database

router = APIRouter(prefix="/api/query", tags=["数据查询"])


# @router.get("/raw")
@router.get(
    "/raw",
    responses={
        200: {
            "description": "成功返回数据",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "data": [
                            {
                                "id": 1,
                                "building_id": "B001",
                                "timestamp": "2025-01-01 08:00:00",
                                "electricity": 156.32,
                                "water": 12.5,
                                "ambient_temp": 22.3,
                                "is_anomaly": False
                            }
                        ],
                        "pagination": {
                            "total": 1240,
                            "limit": 5,
                            "offset": 0,
                            "has_more": True
                        }
                    }
                }
            }
        },
        400: {
            "description": "请求参数错误",
            "content": {
                "application/json": {
                    "example": {"detail": "日期格式错误，应为YYYY-MM-DD"}
                }
            }
        }
    }
)
async def get_raw_data(
        building_id: Optional[str] = Query(None, description="建筑编号，如：B001"),
        meter_id: Optional[str] = Query(None, description="监测点编号，如：B001_M1"),
        start_date: Optional[str] = Query(
            None,
            description="开始日期，格式：YYYY-MM-DD，例如：2025-01-01"
        ),
        end_date: Optional[str] = Query(
            None,
            description="结束日期，格式：YYYY-MM-DD，例如：2025-01-31"
        ),
        limit: int = Query(100, ge=1, le=1000, description="返回条数，默认100"),
        offset: int = Query(0, ge=0, description="分页偏移，默认0")
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


@router.get(
    "/buildings",
    responses={
        200: {
            "description": "成功返回建筑列表",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "data": [
                            {
                                "id": "B001",
                                "name": "办公大楼A",
                                "type": "办公楼",
                                "area": 12000
                            },
                            {
                                "id": "B002",
                                "name": "教学楼B",
                                "type": "教学楼",
                                "area": 8500
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def get_buildings():
    """获取所有建筑列表"""
    sql = "SELECT id, name, type, area FROM buildings ORDER BY id"
    data = await Database.fetch_all(sql)
    return {"code": 200, "data": data}


# @router.get("/meters")
@router.get(
    "/meters",
    responses={
        200: {
            "description": "成功返回监测点列表",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "data": [
                            {
                                "id": "B001_M1",
                                "building_id": "B001",
                                "type": "电表",
                                "status": "normal"
                            },
                            {
                                "id": "B001_M2",
                                "building_id": "B001",
                                "type": "水表",
                                "status": "normal"
                            },
                            {
                                "id": "B002_M1",
                                "building_id": "B002",
                                "type": "空调",
                                "status": "abnormal"
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def get_meters(building_id: Optional[str] = Query(None, description="建筑编号，如：B001")):
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
# @router.get("/device-status")
@router.get(
    "/device-status",
    responses={
        200: {
            "description": "成功返回设备状态",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "data": [
                            {
                                "meter_id": "B001_M1",
                                "building_id": "B001",
                                "type": "电表",
                                "status": "normal",
                                "data_count": 1240,
                                "last_update": "2025-03-07 18:00:00",
                                "avg_power": 156.3,
                                "anomaly_count": 3,
                                "health_score": 97.6,
                                "status_desc": "正常"
                            },
                            {
                                "meter_id": "B002_M1",
                                "building_id": "B002",
                                "type": "空调",
                                "status": "abnormal",
                                "data_count": 1180,
                                "last_update": "2025-03-07 17:00:00",
                                "avg_power": 234.5,
                                "anomaly_count": 15,
                                "health_score": 72.8,
                                "status_desc": "需关注"
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def get_device_status(
        building_id: Optional[str] = Query(None, description="建筑编号，如：B001"),
        meter_id: Optional[str] = Query(None, description="设备类型：电表/水表/空调"),
        status: Optional[str] = Query(None, description="状态：normal/abnormal")  # normal/abnormal
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

        # 状态判断
        if item['status'] == 'abnormal':
            item['status_desc'] = '异常'
        elif health_score < 80:
            item['status_desc'] = '需关注'
        else:
            item['status_desc'] = '正常'

    return {"code": 200, "data": data}


# @router.post("/query")  # 新接口：POST /api/query
@router.post(
    "/query",
    responses={
        200: {
            "description": "成功返回查询数据",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "data": [
                            {
                                "timestamp": "2025-01-01 08:00:00",
                                "electricity": 156.32
                            },
                            {
                                "timestamp": "2025-01-01 09:00:00",
                                "electricity": 178.21
                            }
                        ],
                        "meta": {
                            "total": 1240,
                            "param_type": "electricity",
                            "time_range": "2025-01-01 至 2025-01-31"
                        }
                    }
                }
            }
        }
    }
)
async def query_data(
        building_ids: List[str] = Body(["B001"], description="建筑编号列表，如：['B001', 'B002']"),
        start_time: Optional[str] = Body(None, description="开始时间，格式：YYYY-MM-DD，例如：2025-01-01"),
        end_time: Optional[str] = Body(None, description="结束时间，格式：YYYY-MM-DD，例如：2025-01-31"),
        param_type: str = Body("electricity", description="查询参数类型：electricity/water/temperature"),
        limit: int = Body(100, description="返回条数，默认100")
):
    """简化版查询接口"""
    # 构建查询条件
    conditions = []
    params = []

    if building_ids and building_ids != ["ALL"]:
        placeholders = ','.join(['%s'] * len(building_ids))
        conditions.append(f"building_id IN ({placeholders})")
        params.extend(building_ids)

    # 修复：检查 start_time 是否是有效的字符串且不等于 "string"
    if start_time and start_time != "string" and start_time.lower() != "string":
        conditions.append("DATE(timestamp) >= %s")
        params.append(start_time)

    if end_time and end_time != "string" and end_time.lower() != "string":
        conditions.append("DATE(timestamp) <= %s")
        params.append(end_time)

    # 构建SQL
    sql = f"SELECT timestamp, {param_type} FROM energy_consumption"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY timestamp DESC LIMIT %s"
    params.append(limit)

    # 查询数据
    data = await Database.fetch_all(sql, tuple(params))

    return {
        "code": 200,
        "data": data,
        "meta": {
            "total": len(data),
            "param_type": param_type,
            "time_range": f"{start_time} 至 {end_time}" if start_time and end_time and start_time != "string" and end_time != "string" else "全部"
        }
    }