# app/api/chart_api.py
from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime, timedelta
from app.database.db import Database

router = APIRouter(prefix="/api/charts", tags=["图表数据"])


@router.get("/trend")
async def get_trend_data(
        building_id: str,
        days: int = Query(7, ge=1, le=30)
):
    """获取趋势图数据（ECharts格式）- 修复版"""
    sql = """
        SELECT 
            CONCAT(DATE(timestamp), ' ', HOUR(timestamp), ':00') as hour,
            AVG(electricity) as avg_elec,
            MAX(electricity) as max_elec,
            MIN(electricity) as min_elec
        FROM energy_consumption
        WHERE building_id = %s 
            AND timestamp >= DATE_SUB(NOW(), INTERVAL %s DAY)
        GROUP BY DATE(timestamp), HOUR(timestamp)
        ORDER BY DATE(timestamp), HOUR(timestamp)
    """

    try:
        data = await Database.fetch_all(sql, (building_id, days))

        # 如果没有数据，返回空数组
        if not data:
            return {
                "code": 200,
                "data": {
                    "categories": [],
                    "series": [
                        {"name": "平均用电量", "type": "line", "data": [], "smooth": True},
                        {"name": "最大用电量", "type": "line", "data": [], "smooth": True,
                         "lineStyle": {"type": "dashed"}}
                    ]
                }
            }

        # 转换为ECharts格式
        categories = [item['hour'] for item in data]
        series = [
            {
                "name": "平均用电量",
                "type": "line",
                "data": [float(item['avg_elec']) if item['avg_elec'] is not None else 0 for item in data],
                "smooth": True
            },
            {
                "name": "最大用电量",
                "type": "line",
                "data": [float(item['max_elec']) if item['max_elec'] is not None else 0 for item in data],
                "smooth": True,
                "lineStyle": {"type": "dashed"}
            }
        ]

        return {
            "code": 200,
            "data": {
                "categories": categories,
                "series": series
            }
        }
    except Exception as e:
        print(f"趋势图数据错误: {e}")
        return {
            "code": 500,
            "message": str(e),
            "data": {
                "categories": [],
                "series": []
            }
        }


@router.get("/comparison")
async def get_comparison_data(
        building_ids: str,  # 逗号分隔，如 "B001,B002"
        start_date: str,
        end_date: str
):
    """获取多建筑对比数据（柱状图）"""
    ids = building_ids.split(',')

    result = []
    for building_id in ids:
        building_id = building_id.strip()

        # 查询能耗数据
        sql = """
            SELECT 
                COALESCE(SUM(electricity), 0) as total_elec,
                COALESCE(AVG(electricity), 0) as avg_elec,
                COALESCE(MAX(electricity), 0) as peak_elec
            FROM energy_consumption
            WHERE building_id = %s 
                AND DATE(timestamp) BETWEEN %s AND %s
        """
        data = await Database.fetch_one(sql, (building_id, start_date, end_date))
        if not data:
            data = {"total_elec": 0, "avg_elec": 0, "peak_elec": 0}

        # 获取建筑名称
        name_sql = "SELECT name FROM buildings WHERE id = %s"
        name_data = await Database.fetch_one(name_sql, (building_id,))

        result.append({
            "building_id": building_id,
            "building_name": name_data['name'] if name_data else building_id,
            "total_electricity": float(data['total_elec']),
            "avg_electricity": float(data['avg_elec']),
            "peak_electricity": float(data['peak_elec'])
        })

    return {
        "code": 200,
        "data": {
            "categories": [item['building_name'] for item in result],
            "series": [
                {
                    "name": "总用电量 (kWh)",
                    "type": "bar",
                    "data": [item['total_electricity'] for item in result]
                },
                {
                    "name": "平均用电量 (kWh)",
                    "type": "bar",
                    "data": [item['avg_electricity'] for item in result]
                }
            ]
        }
    }


@router.get("/distribution")
async def get_distribution_data(
        building_id: str,
        date: str
):
    """获取某天的小时分布数据（折线图）"""
    sql = """
        SELECT 
            HOUR(timestamp) as hour,
            AVG(electricity) as electricity
        FROM energy_consumption
        WHERE building_id = %s 
            AND DATE(timestamp) = %s
        GROUP BY HOUR(timestamp)
        ORDER BY hour
    """

    data = await Database.fetch_all(sql, (building_id, date))

    # 补全24小时
    hours = list(range(24))
    values = [0] * 24

    for item in data:
        hour = item['hour']
        values[hour] = float(item['electricity']) if item['electricity'] else 0

    return {
        "code": 200,
        "data": {
            "categories": [f"{h:02d}:00" for h in hours],
            "series": [
                {
                    "name": "用电量 (kWh)",
                    "type": "line",
                    "data": values,
                    "areaStyle": {}
                }
            ]
        }
    }