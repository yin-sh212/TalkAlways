# app/api/query_api.py
from fastapi import APIRouter, Query, HTTPException, Body
from typing import Optional, List
from datetime import datetime
from app.database.db import Database

router = APIRouter(prefix="/api/query", tags=["数据查询"])


@router.get("/raw")
async def get_raw_data(
        building_id: Optional[str] = Query(None, description="建筑编号，如：Eagle_education_Cassie"),
        meter_id: Optional[str] = Query(None, description="设备编号，如：Eagle_education_Cassie_machine"),
        start_date: Optional[str] = Query(
            None,
            description="开始日期，格式：YYYY-MM-DD，例如：2016-07-01"
        ),
        end_date: Optional[str] = Query(
            None,
            description="结束日期，格式：YYYY-MM-DD，例如：2016-07-31"
        ),
        limit: int = Query(100, ge=1, le=1000, description="返回条数，默认 100"),
        offset: int = Query(0, ge=0, description="分页偏移，默认 0")
):
    """获取原始能耗数据 - 包含所有实际字段"""
    # 查询所有实际存在的字段
    sql = """
        SELECT 
            id,
            building_id,
            meter_id,
            timestamp,
            electricity,
            cooling_load,
            heating_load,
            ambient_temp,
            pressure,
            is_anomaly
        FROM energy_consumption 
        WHERE 1=1
    """
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
    count_sql = "SELECT COUNT(*) as total FROM energy_consumption WHERE 1=1"
    count_params = params.copy()
    if building_id:
        count_sql += " AND building_id = %s"
    if meter_id:
        count_sql += " AND meter_id = %s"
    if start_date:
        count_sql += " AND DATE(timestamp) >= %s"
    if end_date:
        count_sql += " AND DATE(timestamp) <= %s"

    count_result = await Database.fetch_one(count_sql, tuple(count_params) if count_params else None)
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
    """获取所有建筑列表 - 修复版"""
    # 先检查表结构，动态构建查询
    try:
        # 尝试查询包含所有可能字段
        sql = """
            SELECT 
                id,
                name,
                type,
                area
            FROM buildings 
            ORDER BY id
        """
        data = await Database.fetch_all(sql)

        # 如果成功，直接返回
        return {"code": 200, "data": data}
    except Exception as e:
        # 如果失败，可能是表结构不同，尝试基本查询
        print(f"建筑列表查询失败，尝试基本查询: {e}")
        sql = "SELECT id, name, type FROM buildings ORDER BY id"
        data = await Database.fetch_all(sql)
        return {"code": 200, "data": data}


@router.get("/meters")
async def get_meters(building_id: Optional[str] = Query(None, description="建筑编号，如：Eagle_education_Cassie")):
    """获取设备列表"""
    sql = """
        SELECT 
            id,
            building_id,
            type,
            status
        FROM meters
    """
    params = []
    if building_id:
        sql += " WHERE building_id = %s"
        params.append(building_id)
    sql += " ORDER BY id"

    data = await Database.fetch_all(sql, tuple(params) if params else None)
    return {"code": 200, "data": data}


@router.get("/device-status")
async def get_device_status(
        building_id: Optional[str] = Query(None, description="建筑编号"),
        meter_id: Optional[str] = Query(None, description="设备 ID"),
        status: Optional[str] = Query(None, description="状态")
):
    """获取设备运行状态 - 返回统计汇总数据"""
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

    # 修改：GROUP BY 包含所有非聚合字段
    sql += " GROUP BY m.id, m.building_id, m.type, m.status"

    data = await Database.fetch_all(sql, tuple(params) if params else None)

    # 计算健康度
    for item in data:
        total = item['data_count'] or 1
        anomaly = item['anomaly_count'] or 0
        health_score = max(0, 100 - (anomaly / total * 100))
        item['health_score'] = round(health_score, 2)

        if item['status'] == 'abnormal':
            item['status_desc'] = '异常'
        elif health_score < 80:
            item['status_desc'] = '需关注'
        else:
            item['status_desc'] = '正常'

    # 新增：统计汇总数据
    total_count = len(data)
    normal_count = sum(1 for item in data if item['status'] == 'normal')
    abnormal_count = sum(1 for item in data if item['status'] == 'abnormal')
    offline_count = sum(1 for item in data if item['status'] == 'offline' or not item['status'])
    
    # 计算整体健康度
    health_score = round((normal_count / total_count * 100) if total_count > 0 else 0, 2)

    # 返回统计对象
    return {
        "code": 200,
        "data": {
            "totalCount": total_count,
            "normalCount": normal_count,
            "abnormalCount": abnormal_count,
            "offlineCount": offline_count,
            "healthScore": health_score,
            "details": data  # 保留原始详细数据供参考
        }
    }

@router.post("/query")
async def query_data(
        building_ids: List[str] = Body(["Eagle_education_Cassie"], description="建筑编号列表"),
        start_time: Optional[str] = Body(None, description="开始时间，格式：YYYY-MM-DD，例如：2016-07-01"),
        end_time: Optional[str] = Body(None, description="结束时间，格式：YYYY-MM-DD，例如：2016-07-31"),
        fields: List[str] = Body(["electricity"],
                                 description="查询字段列表，如：['electricity', 'cooling_load', 'ambient_temp']"),
        limit: int = Body(100, description="返回条数，默认100")
):
    """灵活查询接口 - 可以指定要查询的字段"""
    # 验证字段是否有效
    valid_fields = ['electricity', 'cooling_load', 'heating_load', 'ambient_temp', 'pressure', 'is_anomaly',
                    'run_status']
    selected_fields = []
    for field in fields:
        if field in valid_fields:
            selected_fields.append(field)

    if not selected_fields:
        selected_fields = ['electricity']

    # 构建查询条件
    conditions = []
    params = []

    if building_ids and building_ids != ["ALL"]:
        placeholders = ','.join(['%s'] * len(building_ids))
        conditions.append(f"building_id IN ({placeholders})")
        params.extend(building_ids)

    if start_time and start_time != "string" and start_time.lower() != "string":
        conditions.append("DATE(timestamp) >= %s")
        params.append(start_time)

    if end_time and end_time != "string" and end_time.lower() != "string":
        conditions.append("DATE(timestamp) <= %s")
        params.append(end_time)

    # 构建SQL
    fields_str = ', '.join(['timestamp'] + selected_fields)
    sql = f"SELECT {fields_str} FROM energy_consumption"
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
            "fields": selected_fields,
            "time_range": f"{start_time} 至 {end_time}" if start_time and end_time else "全部"
        }
    }
