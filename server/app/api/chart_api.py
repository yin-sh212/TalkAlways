# app/api/chart_api.py
from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime, timedelta
from app.database.db import Database

router = APIRouter(prefix="/api/charts", tags=["图表数据"])


@router.get(
    "/trend",
    responses={
        200: {
            "description": "成功返回趋势图数据",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "data": {
                            "categories": ["2025-01-01 08:00", "2025-01-01 09:00", "2025-01-01 10:00"],
                            "series": [
                                {
                                    "name": "平均用电量",
                                    "type": "line",
                                    "data": [156.3, 178.2, 201.5],
                                    "smooth": True
                                },
                                {
                                    "name": "最大用电量",
                                    "type": "line",
                                    "data": [189.4, 210.3, 235.6],
                                    "smooth": True,
                                    "lineStyle": {"type": "dashed"}
                                }
                            ]
                        }
                    }
                }
            }
        }
    }
)
async def get_trend_data(
        building_id: str = Query(..., description="建筑编号，如：B001"),
        days: int = Query(7, ge=1, le=30, description="天数，默认7天")
):
    """获取趋势图数据（ECharts格式）"""
    try:
        # 先用一个简单的查询获取数据
        sql = """
            SELECT 
                DATE(timestamp) as date,
                HOUR(timestamp) as hour,
                AVG(electricity) as avg_elec,
                MAX(electricity) as max_elec,
                MIN(electricity) as min_elec
            FROM energy_consumption
            WHERE building_id = %s 
                AND timestamp >= DATE_SUB(NOW(), INTERVAL %s DAY)
            GROUP BY DATE(timestamp), HOUR(timestamp)
            ORDER BY date, hour
        """

        data = await Database.fetch_all(sql, (building_id, days))

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

        # 在Python中格式化时间字符串，而不是在SQL中
        categories = []
        avg_values = []
        max_values = []

        for item in data:
            # 格式化成 "YYYY-MM-DD HH:00"
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

@router.get(
    "/comparison",
    responses={
        200: {
            "description": "成功返回对比图数据",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "data": {
                            "categories": ["办公大楼A", "教学楼B", "医院C"],
                            "series": [
                                {
                                    "name": "总用电量 (kWh)",
                                    "type": "bar",
                                    "data": [8719.2, 5234.5, 15678.3]
                                },
                                {
                                    "name": "平均用电量 (kWh)",
                                    "type": "bar",
                                    "data": [155.7, 98.3, 234.5]
                                }
                            ]
                        }
                    }
                }
            }
        }
    }
)
async def get_comparison_data(
        building_ids: str = Query(..., description="建筑编号，逗号分隔，如：B001,B002"),
        start_date: str = Query(..., description="开始日期，格式：YYYY-MM-DD，例如：2025-01-01"),
        end_date: str = Query(..., description="结束日期，格式：YYYY-MM-DD，例如：2025-01-31")
):
    """获取多建筑对比数据（柱状图）"""
    ids = building_ids.split(',')

    result = []
    for building_id in ids:
        building_id = building_id.strip()

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


@router.get(
    "/distribution",
    responses={
        200: {
            "description": "成功返回分布图数据",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "data": {
                            "categories": ["00:00", "01:00", "02:00", "03:00", "04:00", "05:00",
                                           "06:00", "07:00", "08:00", "09:00", "10:00", "11:00",
                                           "12:00", "13:00", "14:00", "15:00", "16:00", "17:00",
                                           "18:00", "19:00", "20:00", "21:00", "22:00", "23:00"],
                            "series": [
                                {
                                    "name": "用电量 (kWh)",
                                    "type": "line",
                                    "data": [45.2, 42.1, 38.5, 35.2, 34.8, 36.2,
                                             42.5, 78.3, 156.2, 178.3, 201.5, 189.4,
                                             165.3, 158.2, 145.6, 142.3, 148.5, 156.7,
                                             168.2, 145.3, 123.4, 98.5, 67.3, 52.1],
                                    "areaStyle": {}
                                }
                            ]
                        }
                    }
                }
            }
        }
    }
)
async def get_distribution_data(
        building_id: str = Query(..., description="建筑编号，如：B001"),
        date: str = Query(..., description="日期，格式：YYYY-MM-DD，例如：2025-01-15")
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