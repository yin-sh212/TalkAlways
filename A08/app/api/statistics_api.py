from fastapi import APIRouter, HTTPException
from typing import Optional
from datetime import datetime
from app.database.db import Database
from app.services.anomaly_detector import detect_anomalies_3sigma

router = APIRouter(prefix="/api/statistics", tags=["统计分析"])


@router.get("/summary")
async def get_summary(
        building_id: str,
        start_date: str,
        end_date: str,
        group_by: str = "day"  # day, week, month
):
    """时段汇总统计"""
    # 根据group_by确定SQL
    if group_by == "day":
        time_format = "%Y-%m-%d"
        group_sql = "DATE(timestamp) as period"
    elif group_by == "week":
        group_sql = "DATE_FORMAT(timestamp, '%Y-%u') as period"
    elif group_by == "month":
        group_sql = "DATE_FORMAT(timestamp, '%Y-%m') as period"
    else:
        group_sql = "DATE(timestamp) as period"

    sql = f"""
        SELECT 
            {group_sql},
            SUM(electricity) as total_elec,
            AVG(electricity) as avg_elec,
            MAX(electricity) as max_elec,
            MIN(electricity) as min_elec,
            STDDEV(electricity) as std_elec,
            SUM(water) as total_water,
            COUNT(*) as data_points
        FROM energy_consumption
        WHERE building_id = %s 
            AND DATE(timestamp) BETWEEN %s AND %s
        GROUP BY period
        ORDER BY period
    """

    data = await Database.fetch_all(sql, (building_id, start_date, end_date))

    # 计算总计
    total_sql = """
        SELECT 
            SUM(electricity) as total_elec,
            AVG(electricity) as avg_elec,
            SUM(water) as total_water
        FROM energy_consumption
        WHERE building_id = %s 
            AND DATE(timestamp) BETWEEN %s AND %s
    """
    total = await Database.fetch_one(total_sql, (building_id, start_date, end_date))

    return {
        "building_id": building_id,
        "period": f"{start_date} 至 {end_date}",
        "group_by": group_by,
        "details": data,
        "summary": total
    }


@router.get("/cop")
async def calculate_cop(
        building_id: str,
        start_date: str,
        end_date: str
):
    """计算能效比(COP)"""
    sql = """
        SELECT 
            timestamp,
            electricity,
            supply_temp,
            return_temp,
            -- 简化COP计算：制冷量 ≈ 4.2 * 流量 * (回水-出水) / 耗电量
            -- 假设流量为常数1
            CASE 
                WHEN electricity > 0 
                THEN (return_temp - supply_temp) * 4.2 * 1 / electricity
                ELSE 0
            END as cop
        FROM energy_consumption
        WHERE building_id = %s 
            AND DATE(timestamp) BETWEEN %s AND %s
            AND electricity > 0
            AND supply_temp IS NOT NULL
            AND return_temp IS NOT NULL
        ORDER BY timestamp
    """

    data = await Database.fetch_all(sql, (building_id, start_date, end_date))

    # 计算平均COP
    if data:
        avg_cop = sum(item['cop'] for item in data) / len(data)
    else:
        avg_cop = 0

    return {
        "building_id": building_id,
        "period": f"{start_date} 至 {end_date}",
        "avg_cop": round(avg_cop, 2),
        "data": data
    }


@router.get("/anomaly")
async def detect_anomaly(
        building_id: str,
        start_date: str,
        end_date: str,
        threshold: float = 2.0
):
    """能耗异常检测"""
    sql = """
        SELECT 
            timestamp,
            electricity,
            ambient_temp,
            humidity
        FROM energy_consumption
        WHERE building_id = %s 
            AND DATE(timestamp) BETWEEN %s AND %s
        ORDER BY timestamp
    """

    data = await Database.fetch_all(sql, (building_id, start_date, end_date))

    if not data:
        return {
            "building_id": building_id,
            "period": f"{start_date} 至 {end_date}",
            "total_points": 0,
            "anomaly_count": 0,
            "anomalies": []
        }

    # 提取用电量列表
    values = [item['electricity'] for item in data]
    timestamps = [item['timestamp'] for item in data]

    # 调用异常检测服务
    anomalies = detect_anomalies_3sigma(values, timestamps, threshold)

    return {
        "building_id": building_id,
        "period": f"{start_date} 至 {end_date}",
        "threshold": f"{threshold}倍标准差",
        "total_points": len(values),
        "anomaly_count": len(anomalies),
        "anomalies": anomalies
    }