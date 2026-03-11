from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime
from app.database.db import Database
from app.services.anomaly_detector import detect_anomalies_3sigma
import numpy as np

router = APIRouter(prefix="/api/statistics", tags=["统计分析"])


@router.get(
    "/summary",
    responses={
        200: {
            "description": "成功返回汇总数据",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "成功",
                        "data": {
                            "building_id": "B001",
                            "period": "2025-01-01 至 2025-01-07",
                            "time_unit": "day",
                            "details": [
                                {
                                    "period": "2025-01-01",
                                    "total_elec": 1245.6,
                                    "avg_elec": 155.7,
                                    "max_elec": 234.5,
                                    "min_elec": 89.2,
                                    "data_points": 8
                                }
                            ],
                            "summary": {
                                "total_elec": 8719.2,
                                "avg_elec": 155.7,
                                "total_water": 87.5
                            }
                        }
                    }
                }
            }
        },
        400: {
            "description": "参数错误",
            "content": {
                "application/json": {
                    "example": {
                        "code": 400,
                        "message": "日期格式错误，应为YYYY-MM-DD",
                        "data": None
                    }
                }
            }
        }
    }
)
async def get_summary(
        building_id: str,
        start_date: str,
        end_date: str,
        time_unit: str = Query("day", pattern="^(hour|day|week|month)$")
):
    """时段汇总统计"""
    try:
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
            "code": 200,
            "message": "成功",
            "data": {
                "building_id": building_id,
                "period": f"{start_date} 至 {end_date}",
                "time_unit": time_unit,
                "details": data,
                "summary": total
            }
        }
    except Exception as e:
        return {
            "code": 500,
            "message": f"服务器错误: {str(e)}",
            "data": None
        }


@router.get(
    "/cop",
    responses={
        200: {
            "description": "成功返回能效比(COP)计算结果",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "成功",
                        "data": {
                            "building_id": "B001",
                            "period": "2025-01-01 至 2025-01-31",
                            "avg_cop": 3.45,
                            "details": [
                                {
                                    "timestamp": "2025-01-01 08:00:00",
                                    "electricity": 156.32,
                                    "supply_temp": 8.5,
                                    "return_temp": 15.2,
                                    "cop": 4.2
                                },
                                {
                                    "timestamp": "2025-01-01 09:00:00",
                                    "electricity": 178.21,
                                    "supply_temp": 8.7,
                                    "return_temp": 15.5,
                                    "cop": 3.8
                                }
                            ]
                        }
                    }
                }
            }
        },
        400: {
            "description": "参数错误",
            "content": {
                "application/json": {
                    "example": {
                        "code": 400,
                        "message": "日期格式错误",
                        "data": None
                    }
                }
            }
        }
    }
)
async def calculate_cop(
        building_id: str = Query(..., description="建筑编号，如：B001"),
        start_date: str = Query(..., description="开始日期，格式：YYYY-MM-DD，例如：2025-01-01"),
        end_date: str = Query(..., description="结束日期，格式：YYYY-MM-DD，例如：2025-01-31")
):
    """计算能效比(COP)"""
    try:
        sql = """
            SELECT 
                timestamp,
                electricity,
                supply_temp,
                return_temp,
                CASE 
                    WHEN electricity > 0 AND supply_temp IS NOT NULL AND return_temp IS NOT NULL
                    THEN (return_temp - supply_temp) * 4.2 / electricity
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
            "code": 200,
            "message": "成功",
            "data": {
                "building_id": building_id,
                "period": f"{start_date} 至 {end_date}",
                "avg_cop": round(avg_cop, 2),
                "details": data
            }
        }
    except Exception as e:
        return {
            "code": 500,
            "message": f"服务器错误: {str(e)}",
            "data": None
        }


@router.get(
    "/anomaly",
    responses={
        200: {
            "description": "成功返回异常检测结果",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "成功",
                        "data": {
                            "building_id": "B001",
                            "period": "2025-01-01 至 2025-01-31",
                            "method": "moving_average",
                            "threshold": "2.0倍标准差",
                            "total_points": 744,
                            "anomaly_count": 3,
                            "mean": 156.3,
                            "std": 42.5,
                            "anomalies": [
                                {
                                    "index": 128,
                                    "timestamp": "2025-01-15 14:00:00",
                                    "value": 345.2,
                                    "mean": 168.5,
                                    "z_score": 4.2,
                                    "deviation": "+105%"
                                }
                            ]
                        }
                    }
                }
            }
        },
        400: {
            "description": "参数错误",
            "content": {
                "application/json": {
                    "example": {
                        "code": 400,
                        "message": "日期格式错误",
                        "data": None
                    }
                }
            }
        }
    }
)
async def detect_anomaly(
        building_id: str = Query(..., description="建筑编号，如：B001"),
        start_date: str = Query(..., description="开始日期，格式：YYYY-MM-DD，例如：2025-01-01"),
        end_date: str = Query(..., description="结束日期，格式：YYYY-MM-DD，例如：2025-01-31"),
        method: str = Query("moving_average", pattern="^(3sigma|moving_average)$",
                            description="检测方法：3sigma/moving_average"),
        threshold: float = Query(2.0, description="异常阈值（标准差倍数）")
):
    """能耗异常检测"""
    try:
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
                "code": 200,
                "message": "成功",
                "data": {
                    "building_id": building_id,
                    "period": f"{start_date} 至 {end_date}",
                    "total_points": 0,
                    "anomaly_count": 0,
                    "anomalies": []
                }
            }

        # 提取用电量列表
        values = [item['electricity'] for item in data]
        timestamps = [item['timestamp'] for item in data]
        mean_val = np.mean(values)
        std_val = np.std(values)

        # 调用异常检测服务
        anomalies = detect_anomalies_3sigma(values, timestamps, threshold)

        return {
            "code": 200,
            "message": "成功",
            "data": {
                "building_id": building_id,
                "period": f"{start_date} 至 {end_date}",
                "method": method,
                "threshold": f"{threshold}倍标准差",
                "total_points": len(values),
                "anomaly_count": len(anomalies),
                "mean": float(mean_val),
                "std": float(std_val),
                "anomalies": anomalies
            }
        }
    except Exception as e:
        return {
            "code": 500,
            "message": f"服务器错误: {str(e)}",
            "data": None
        }