# app/api/chart_api.py
from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime, timedelta
from app.database.db import Database

router = APIRouter(prefix="/api/charts", tags=["图表数据"])


@router.get("/trend")
async def get_trend_data(
        building_id: str = Query(..., description="建筑编号，如：Eagle_education_Cassie"),
        days: int = Query(7, ge=1, le=30, description="天数，默认7天")
):
    """获取趋势图数据（ECharts格式）- 适配新数据"""
    try:
        # 新数据是2016年的，不能用 NOW()，需要调整时间范围
        # 这里改为查询最后N天的数据（从数据集的最后一天往前推）
        sql = """
            SELECT 
                DATE(timestamp) as date,
                HOUR(timestamp) as hour,
                AVG(electricity) as avg_elec,
                MAX(electricity) as max_elec,
                MIN(electricity) as min_elec
            FROM energy_consumption
            WHERE building_id = %s 
            GROUP BY DATE(timestamp), HOUR(timestamp)
            ORDER BY date DESC, hour DESC
            LIMIT %s
        """
        # 注意：这里简化了，直接取N天的数据点
        # 如果需要精确的N天，需要用子查询

        data = await Database.fetch_all(sql, (building_id, days * 24))  # 每天24小时

        if not data:
            return {
                "code": 200,
                "data": {
                    "categories": [],
                    "series": [
                        {"name": "平均用电量", "type": "line", "data": [], "smooth": True},
                        {"name": "最大用电量", "type": "line", "data": [], "smooth": True}
                    ]
                }
            }

        # 反转数据，让时间正序
        data = list(reversed(data))

        # 格式化时间
        categories = []
        avg_values = []
        max_values = []

        for item in data:
            hour_str = f"{item['date']} {item['hour']:02d}:00"
            categories.append(hour_str)
            avg_values.append(float(item['avg_elec']) if item['avg_elec'] is not None else 0)
            max_values.append(float(item['max_elec']) if item['max_elec'] is not None else 0)

        series = [
            {
                "name": "平均用电量",
                "type": "line",
                "data": avg_values,
                "smooth": True
            },
            {
                "name": "最大用电量",
                "type": "line",
                "data": max_values,
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
        print(f"趋势图错误: {e}")
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
        building_ids: str = Query(...,
                                  description="建筑编号，逗号分隔，如：Eagle_education_Cassie,Eagle_education_Wesley"),
        start_date: str = Query(..., description="开始日期，格式：YYYY-MM-DD，例如：2016-07-01"),
        end_date: str = Query(..., description="结束日期，格式：YYYY-MM-DD，例如：2016-07-31")
):
    """获取多建筑对比数据（柱状图）- 适配新数据"""
    ids = building_ids.split(',')

    result = []
    for building_id in ids:
        building_id = building_id.strip()

        # 查询能耗数据
        sql = """
            SELECT 
                COALESCE(SUM(electricity), 0) as total_elec,
                COALESCE(AVG(electricity), 0) as avg_elec,
                COALESCE(MAX(electricity), 0) as peak_elec,
                COALESCE(AVG(cooling_load), 0) as avg_cooling,
                COALESCE(AVG(heating_load), 0) as avg_heating,
                COALESCE(AVG(ambient_temp), 0) as avg_temp
            FROM energy_consumption
            WHERE building_id = %s 
                AND DATE(timestamp) BETWEEN %s AND %s
        """
        data = await Database.fetch_one(sql, (building_id, start_date, end_date))
        if not data:
            data = {
                "total_elec": 0, "avg_elec": 0, "peak_elec": 0,
                "avg_cooling": 0, "avg_heating": 0, "avg_temp": 0
            }

        # 获取建筑名称（从 buildings 表）
        name_sql = "SELECT name FROM buildings WHERE id = %s"
        name_data = await Database.fetch_one(name_sql, (building_id,))

        result.append({
            "building_id": building_id,
            "building_name": name_data['name'] if name_data else building_id,
            "total_electricity": float(data['total_elec']),
            "avg_electricity": float(data['avg_elec']),
            "peak_electricity": float(data['peak_elec']),
            "avg_cooling_load": float(data['avg_cooling']),
            "avg_heating_load": float(data['avg_heating']),
            "avg_temperature": float(data['avg_temp'])
        })

    # 基础对比（用电量）
    base_series = [
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

    # 可选：冷热负荷对比（如果前端需要）
    cooling_series = [
        {
            "name": "平均冷冻水冷量",
            "type": "bar",
            "data": [item['avg_cooling_load'] for item in result]
        }
    ]

    heating_series = [
        {
            "name": "平均供热能耗",
            "type": "bar",
            "data": [item['avg_heating_load'] for item in result]
        }
    ]

    return {
        "code": 200,
        "data": {
            "categories": [item['building_name'] for item in result],
            "series": base_series,
            # 如果需要更多对比，可以添加：
            "extra_series": {
                "cooling": cooling_series,
                "heating": heating_series,
                "temperature": [item['avg_temperature'] for item in result]
            }
        }
    }


@router.get("/distribution")
async def get_distribution_data(
        building_id: str = Query(..., description="建筑编号，如：Eagle_education_Cassie"),
        date: str = Query(..., description="日期，格式：YYYY-MM-DD，例如：2016-07-15")
):
    """获取某天的小时分布数据（折线图）- 适配新数据"""
    # 查询当天的小时分布
    sql = """
        SELECT 
            HOUR(timestamp) as hour,
            AVG(electricity) as electricity,
            AVG(cooling_load) as cooling_load,
            AVG(heating_load) as heating_load,
            AVG(ambient_temp) as ambient_temp
        FROM energy_consumption
        WHERE building_id = %s 
            AND DATE(timestamp) = %s
        GROUP BY HOUR(timestamp)
        ORDER BY hour
    """

    data = await Database.fetch_all(sql, (building_id, date))

    # 补全24小时
    hours = list(range(24))
    elec_values = [0] * 24
    cooling_values = [0] * 24
    heating_values = [0] * 24
    temp_values = [0] * 24

    for item in data:
        hour = item['hour']
        elec_values[hour] = float(item['electricity']) if item['electricity'] else 0
        cooling_values[hour] = float(item['cooling_load']) if item['cooling_load'] else 0
        heating_values[hour] = float(item['heating_load']) if item['heating_load'] else 0
        temp_values[hour] = float(item['ambient_temp']) if item['ambient_temp'] else 0

    # 默认返回用电量分布
    series = [
        {
            "name": "用电量 (kWh)",
            "type": "line",
            "data": elec_values,
            "areaStyle": {}
        }
    ]

    # 如果前端需要多系列，可以增加
    multi_series = [
        {
            "name": "用电量 (kWh)",
            "type": "line",
            "data": elec_values,
            "areaStyle": {}
        },
        {
            "name": "冷冻水冷量",
            "type": "line",
            "data": cooling_values,
            "lineStyle": {"type": "dashed"}
        },
        {
            "name": "供热能耗",
            "type": "line",
            "data": heating_values,
            "lineStyle": {"type": "dotted"}
        }
    ]

    return {
        "code": 200,
        "data": {
            "categories": [f"{h:02d}:00" for h in hours],
            "series": series,  # 默认单系列
            "multi_series": multi_series,  # 可选多系列
            "temperature": temp_values  # 温度数据
        }
    }

