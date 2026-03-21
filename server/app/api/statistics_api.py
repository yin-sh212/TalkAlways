# app/api/statistics_api.py
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import datetime
from app.database.db import Database
from app.services.anomaly_detector import detect_anomalies_3sigma
import numpy as np

router = APIRouter(prefix="/api/statistics", tags=["统计分析"])


@router.get("/summary")
async def get_summary(
        building_id: str,
        start_date: str,
        end_date: str,
        time_unit: str = Query("day", pattern="^(hour|day|week|month)$"),
        include_fields: Optional[str] = Query("all", description="包含的字段：all/electricity/cooling/heating/env")
):
    """时段汇总统计 - 支持多种能耗指标"""
    group_by = time_unit

    # 根据group_by确定SQL
    if group_by == "day":
        group_sql = "DATE(timestamp) as period"
    elif group_by == "week":
        group_sql = "DATE_FORMAT(timestamp, '%Y-%u') as period"
    elif group_by == "month":
        group_sql = "DATE_FORMAT(timestamp, '%Y-%m') as period"
    else:
        group_sql = "DATE(timestamp) as period"

    # 根据include_fields决定查询哪些字段
    select_fields = [group_sql]

    # 总是包含计数
    select_fields.append("COUNT(*) as data_points")

    if include_fields in ["all", "electricity"]:
        select_fields.extend([
            "SUM(electricity) as total_elec",
            "AVG(electricity) as avg_elec",
            "MAX(electricity) as max_elec",
            "MIN(electricity) as min_elec",
            "STDDEV(electricity) as std_elec"
        ])

    if include_fields in ["all", "cooling"]:
        select_fields.extend([
            "SUM(cooling_load) as total_cooling",
            "AVG(cooling_load) as avg_cooling",
            "MAX(cooling_load) as max_cooling",
            "MIN(cooling_load) as min_cooling"
        ])

    if include_fields in ["all", "heating"]:
        select_fields.extend([
            "SUM(heating_load) as total_heating",
            "AVG(heating_load) as avg_heating",
            "MAX(heating_load) as max_heating",
            "MIN(heating_load) as min_heating"
        ])

    if include_fields in ["all", "env"]:
        select_fields.extend([
            "AVG(ambient_temp) as avg_temp",
            "MAX(ambient_temp) as max_temp",
            "MIN(ambient_temp) as min_temp",
            "AVG(pressure) as avg_pressure"
        ])

    select_clause = ", ".join(select_fields)

    sql = f"""
        SELECT 
            {select_clause}
        FROM energy_consumption
        WHERE building_id = %s 
            AND DATE(timestamp) BETWEEN %s AND %s
        GROUP BY period
        ORDER BY period
    """

    data = await Database.fetch_all(sql, (building_id, start_date, end_date))

    # 计算总计
    total_select = ["COUNT(*) as total_points"]

    if include_fields in ["all", "electricity"]:
        total_select.extend([
            "SUM(electricity) as total_elec",
            "AVG(electricity) as avg_elec"
        ])
    if include_fields in ["all", "cooling"]:
        total_select.extend([
            "SUM(cooling_load) as total_cooling",
            "AVG(cooling_load) as avg_cooling"
        ])
    if include_fields in ["all", "heating"]:
        total_select.extend([
            "SUM(heating_load) as total_heating",
            "AVG(heating_load) as avg_heating"
        ])
    if include_fields in ["all", "env"]:
        total_select.extend([
            "AVG(ambient_temp) as avg_temp",
            "AVG(pressure) as avg_pressure"
        ])

    total_clause = ", ".join(total_select)
    total_sql = f"""
        SELECT 
            {total_clause}
        FROM energy_consumption
        WHERE building_id = %s 
            AND DATE(timestamp) BETWEEN %s AND %s
    """
    total = await Database.fetch_one(total_sql, (building_id, start_date, end_date))

    return {
        "code": 200,
        "message": "成功",
        "data": {
            "building_id": building_id,
            "period": f"{start_date} 至 {end_date}",
            "time_unit": time_unit,
            "include_fields": include_fields,
            "details": data,
            "summary": total
        }
    }


@router.get("/cop")
async def calculate_cop(
        building_id: str = Query(..., description="建筑编号"),
        start_date: str = Query(..., description="开始日期"),
        end_date: str = Query(..., description="结束日期"),
        cop_type: str = Query("cooling", pattern="^(cooling|heating|both)$", description="COP类型：制冷/供热/两者")
):
    """计算能效比(COP) - 使用新数据集的实际数据"""

    # 基础SQL
    base_sql = """
        SELECT 
            timestamp,
            electricity,
            cooling_load,
            heating_load,
            ambient_temp
        FROM energy_consumption
        WHERE building_id = %s 
            AND DATE(timestamp) BETWEEN %s AND %s
            AND electricity > 0
        ORDER BY timestamp
    """

    data = await Database.fetch_all(base_sql, (building_id, start_date, end_date))

    if not data:
        return {
            "code": 200,
            "data": {
                "building_id": building_id,
                "period": f"{start_date} 至 {end_date}",
                "avg_cop_cooling": None,
                "avg_cop_heating": None,
                "details": []
            }
        }

    # 计算COP
    result = []
    cooling_cops = []
    heating_cops = []

    for row in data:
        item = {
            "timestamp": row['timestamp'],
            "electricity": row['electricity'],
            "ambient_temp": row['ambient_temp']
        }

        # 制冷COP = 冷冻水冷量 / 耗电量
        if cop_type in ["cooling", "both"] and row['cooling_load'] and row['cooling_load'] > 0:
            cop_cooling = row['cooling_load'] / row['electricity']
            item['cop_cooling'] = round(cop_cooling, 2)
            cooling_cops.append(cop_cooling)

        # 供热COP = 供热能耗 / 耗电量
        if cop_type in ["heating", "both"] and row['heating_load'] and row['heating_load'] > 0:
            cop_heating = row['heating_load'] / row['electricity']
            item['cop_heating'] = round(cop_heating, 2)
            heating_cops.append(cop_heating)

        result.append(item)

    # 计算平均值
    avg_cooling = sum(cooling_cops) / len(cooling_cops) if cooling_cops else None
    avg_heating = sum(heating_cops) / len(heating_cops) if heating_cops else None

    return {
        "code": 200,
        "message": "成功",
        "data": {
            "building_id": building_id,
            "period": f"{start_date} 至 {end_date}",
            "cop_type": cop_type,
            "avg_cop_cooling": round(avg_cooling, 2) if avg_cooling else None,
            "avg_cop_heating": round(avg_heating, 2) if avg_heating else None,
            "details": result
        }
    }


@router.get("/anomaly")
async def detect_anomaly(
        building_id: str = Query(..., description="建筑编号"),
        start_date: str = Query(..., description="开始日期"),
        end_date: str = Query(..., description="结束日期"),
        metric: str = Query("electricity", pattern="^(electricity|cooling_load|heating_load|all)$",
                            description="检测指标：电量/冷量/热量/全部"),
        method: str = Query("dataset", pattern="^(3sigma|moving_average|dataset)$", description="检测方法"),
        threshold: float = Query(2.0, description="异常阈值")
):
    """能耗异常检测 - 支持多种指标"""

    # 确定要查询的字段
    if metric == "all":
        fields = ["electricity", "cooling_load", "heating_load"]
    else:
        fields = [metric]

    # 构建SQL
    select_fields = ["timestamp"] + fields
    if "is_anomaly" in await get_table_columns():  # 检查是否有is_anomaly字段
        select_fields.append("is_anomaly")

    select_clause = ", ".join(select_fields)

    sql = f"""
        SELECT 
            {select_clause}
        FROM energy_consumption
        WHERE building_id = %s 
            AND DATE(timestamp) BETWEEN %s AND %s
        ORDER BY timestamp
    """

    data = await Database.fetch_all(sql, (building_id, start_date, end_date))

    if not data:
        return {
            "code": 200,
            "data": {
                "building_id": building_id,
                "period": f"{start_date} 至 {end_date}",
                "total_points": 0,
                "anomalies": {}
            }
        }

    result = {}

    for field in fields:
        values = [d[field] for d in data if d[field] is not None]
        timestamps = [d['timestamp'] for d in data if d[field] is not None]

        if method == "dataset" and 'is_anomaly' in data[0]:
            # 使用数据集标记
            anomalies = [d for d in data if d['is_anomaly']]
            result[field] = {
                "method": "dataset_marked",
                "total": len(values),
                "anomaly_count": len(anomalies),
                "anomalies": [
                    {
                        "timestamp": d['timestamp'],
                        "value": d[field],
                        "is_anomaly": d['is_anomaly']
                    } for d in anomalies if d[field] is not None
                ]
            }
        else:
            # 使用算法检测
            if len(values) < 5:
                result[field] = {
                    "method": method,
                    "total": len(values),
                    "anomaly_count": 0,
                    "anomalies": []
                }
                continue

            if method == "3sigma":
                anomalies = detect_anomalies_3sigma(values, timestamps, threshold)
            else:
                anomalies = detect_anomalies_moving_average(values, timestamps, threshold)

            result[field] = {
                "method": method,
                "threshold": f"{threshold}倍标准差",
                "total": len(values),
                "anomaly_count": len(anomalies),
                "anomalies": anomalies
            }

    return {
        "code": 200,
        "message": "成功",
        "data": {
            "building_id": building_id,
            "period": f"{start_date} 至 {end_date}",
            "metric": metric,
            "results": result if metric == "all" else result[metric]
        }
    }


# 辅助函数
def detect_anomalies_moving_average(values, timestamps, window=3, threshold=3):
    """移动平均法异常检测"""
    anomalies = []
    for i in range(len(values)):
        start = max(0, i - window)
        end = min(len(values), i + window + 1)
        window_values = values[start:end]
        mean = sum(window_values) / len(window_values)
        std = (sum((x - mean) ** 2 for x in window_values) / len(window_values)) ** 0.5
        if std > 0 and abs(values[i] - mean) > threshold * std:
            anomalies.append({
                "index": i,
                "timestamp": timestamps[i],
                "value": float(values[i]),
                "mean": float(mean),
                "z_score": float(abs(values[i] - mean) / std),
                "deviation": f"{((values[i] - mean) / mean * 100):.1f}%" if mean > 0 else "N/A"
            })
    return anomalies


@router.get("/summary/buildings")
async def get_buildings_summary(
        start_date: str,
        end_date: str,
        time_unit: str = Query("day", pattern="^(hour|day|week|month)$"),
        building_ids: Optional[List[str]] = Query(None, description="建筑 ID 列表，不传则查询所有建筑")
):
    """批量获取多个建筑的能耗汇总 - 用于建筑能耗对比"""
    group_by = time_unit

    # 根据 group_by 确定 SQL
    if group_by == "day":
        group_sql = "DATE(e.timestamp) as period"
    elif group_by == "week":
        group_sql = "DATE_FORMAT(e.timestamp, '%Y-%u') as period"
    elif group_by == "month":
        group_sql = "DATE_FORMAT(e.timestamp, '%Y-%m') as period"
    else:
        group_sql = "DATE(e.timestamp) as period"

    # 构建 WHERE 条件
    where_conditions = ["DATE(e.timestamp) BETWEEN %s AND %s"]
    params = [start_date, end_date]

    if building_ids:
        placeholders = ",".join(["%s"] * len(building_ids))
        where_conditions.append(f"e.building_id IN ({placeholders})")
        params.extend(building_ids)

    where_clause = " AND ".join(where_conditions)

    # 简化版本：不关联 buildings 表，直接使用 building_id
    sql = f"""
        SELECT 
            {group_sql},
            e.building_id,
            SUM(e.electricity) as total_elec,
            AVG(e.electricity) as avg_elec,
            COUNT(*) as data_points
        FROM energy_consumption e
        WHERE {where_clause}
        GROUP BY period, e.building_id
        ORDER BY period, e.building_id
    """

    data = await Database.fetch_all(sql, tuple(params))

    return {
        "code": 200,
        "data": {
            "buildings": data
        }
    }


@router.get("/summary/daily-comparison")
async def get_daily_comparison(
        building_id: str,
        dates: List[str] = Query(..., description="日期列表，例如：['2016-07-15', '2016-07-14', '2016-07-08']")
):
    """批量获取多日的能耗数据 - 用于日环比、周同比计算"""
    if not dates:
        raise HTTPException(status_code=400, detail="dates 参数不能为空")

    placeholders = ",".join(["%s"] * len(dates))
    sql = f"""
        SELECT 
            DATE(timestamp) as date,
            SUM(electricity) as total_elec,
            AVG(electricity) as avg_elec,
            COUNT(*) as data_points
        FROM energy_consumption
        WHERE building_id = %s 
            AND DATE(timestamp) IN ({placeholders})
        GROUP BY DATE(timestamp)
        ORDER BY DATE(timestamp)
    """

    params = [building_id] + list(dates)
    data = await Database.fetch_all(sql, tuple(params))

    return {
        "code": 200,
        "data": {
            "daily_data": data
        }
    }


async def get_table_columns():
    """移动平均法异常检测"""
    anomalies = []
    for i in range(len(values)):
        start = max(0, i - window)
        end = min(len(values), i + window + 1)
        window_values = values[start:end]
        mean = sum(window_values) / len(window_values)
        std = (sum((x - mean) ** 2 for x in window_values) / len(window_values)) ** 0.5
        if std > 0 and abs(values[i] - mean) > threshold * std:
            anomalies.append({
                "index": i,
                "timestamp": timestamps[i],
                "value": float(values[i]),
                "mean": float(mean),
                "z_score": float(abs(values[i] - mean) / std),
                "deviation": f"{((values[i] - mean) / mean * 100):.1f}%" if mean > 0 else "N/A"
            })
    return anomalies


async def get_table_columns():
    """获取表的所有列名（缓存）"""
    sql = "SHOW COLUMNS FROM energy_consumption"
    data = await Database.fetch_all(sql)
    return [row['Field'] for row in data]