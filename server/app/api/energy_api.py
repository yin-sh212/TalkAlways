# app/api/energy_api.py（新建）
from fastapi import APIRouter, Query
from typing import Optional, List
from datetime import datetime, date, timedelta
from app.database.db import Database

router = APIRouter(prefix="/api/energy", tags=["能耗管理"])


@router.get("/dashboard/today")
async def get_today_energy():
    """今日总能耗、较昨日对比、能耗排名TOP5、各建筑能耗占比"""
    today = date(2016, 7, 16)
    yesterday = today - timedelta(days=1)
    last_week = today - timedelta(days=7)

    # 1. 今日总能耗
    today_sql = """
        SELECT 
            SUM(electricity) as total,
            COUNT(DISTINCT building_id) as building_count
        FROM energy_consumption 
        WHERE DATE(timestamp) = %s
    """
    today_data = await Database.fetch_one(today_sql, (today,))

    # 2. 昨日总能耗（用于对比）
    yesterday_sql = "SELECT SUM(electricity) as total FROM energy_consumption WHERE DATE(timestamp) = %s"
    yesterday_data = await Database.fetch_one(yesterday_sql, (yesterday,))

    # 3. 上周同天总能耗（用于对比）
    last_week_sql = "SELECT SUM(electricity) as total FROM energy_consumption WHERE DATE(timestamp) = %s"
    last_week_data = await Database.fetch_one(last_week_sql, (last_week,))

    # 计算变化率
    today_total = today_data['total'] or 0
    yesterday_total = yesterday_data['total'] or 0
    last_week_total = last_week_data['total'] or 0

    vs_yesterday = ((today_total - yesterday_total) / yesterday_total * 100) if yesterday_total > 0 else 0
    vs_last_week = ((today_total - last_week_total) / last_week_total * 100) if last_week_total > 0 else 0

    # 4. 能耗排名TOP5（按建筑）
    top5_sql = """
        SELECT 
            building_id,
            SUM(electricity) as total
        FROM energy_consumption 
        WHERE DATE(timestamp) = %s
        GROUP BY building_id
        ORDER BY total DESC
        LIMIT 5
    """
    top5 = await Database.fetch_all(top5_sql, (today,))

    # 5. 各建筑能耗占比
    all_sql = """
        SELECT 
            building_id,
            SUM(electricity) as total
        FROM energy_consumption 
        WHERE DATE(timestamp) = %s
        GROUP BY building_id
        ORDER BY total DESC
    """
    all_buildings = await Database.fetch_all(all_sql, (today,))

    # 计算占比
    total_all = sum(b['total'] for b in all_buildings)
    for b in all_buildings:
        b['percentage'] = round((b['total'] / total_all * 100), 2) if total_all > 0 else 0

    return {
        "code": 200,
        "message": "成功",
        "data": {
            "date": today.isoformat(),
            "total_energy": round(today_total, 2),
            "building_count": today_data['building_count'] or 0,
            "comparison": {
                "vs_yesterday": {
                    "value": round(vs_yesterday, 2),
                    "trend": "up" if vs_yesterday > 0 else "down" if vs_yesterday < 0 else "flat"
                },
                "vs_last_week": {
                    "value": round(vs_last_week, 2),
                    "trend": "up" if vs_last_week > 0 else "down" if vs_last_week < 0 else "flat"
                }
            },
            "top5": [
                {
                    "building_id": item['building_id'],
                    "energy": round(item['total'], 2)
                } for item in top5
            ],
            "building_share": all_buildings
        }
    }


@router.get("/query")
async def query_energy(
        start_time: str = Query(..., description="开始时间"),
        end_time: str = Query(..., description="结束时间"),
        building_id: Optional[str] = Query(None, description="建筑ID"),
        device_id: Optional[str] = Query(None, description="设备ID"),
        group_by: Optional[str] = Query(None, description="分组方式：building/device/hour/day"),
        limit: int = Query(100, description="返回条数"),
        sort: str = Query("desc", description="排序：asc/desc")
):
    """能耗查询（支持多维度）"""
    conditions = ["1=1"]
    params = []

    if building_id:
        conditions.append("building_id = %s")
        params.append(building_id)
    if device_id:
        conditions.append("meter_id = %s")
        params.append(device_id)

    conditions.append("DATE(timestamp) BETWEEN %s AND %s")
    params.append(start_time)
    params.append(end_time)

    where_clause = " AND ".join(conditions)

    if group_by == "building":
        sql = f"""
            SELECT 
                building_id,
                SUM(electricity) as total_energy,
                AVG(electricity) as avg_energy,
                COUNT(*) as data_points
            FROM energy_consumption
            WHERE {where_clause}
            GROUP BY building_id
            ORDER BY total_energy {sort}
        """
    elif group_by == "device":
        sql = f"""
            SELECT 
                meter_id as device_id,
                building_id,
                SUM(electricity) as total_energy,
                AVG(electricity) as avg_energy
            FROM energy_consumption
            WHERE {where_clause}
            GROUP BY meter_id, building_id
            ORDER BY total_energy {sort}
        """
    elif group_by == "hour":
        sql = f"""
            SELECT 
                HOUR(timestamp) as hour,
                SUM(electricity) as total_energy
            FROM energy_consumption
            WHERE {where_clause}
            GROUP BY HOUR(timestamp)
            ORDER BY hour {sort}
        """
    elif group_by == "day":
        sql = f"""
            SELECT 
                DATE(timestamp) as day,
                SUM(electricity) as total_energy
            FROM energy_consumption
            WHERE {where_clause}
            GROUP BY DATE(timestamp)
            ORDER BY day {sort}
        """
    else:
        # 原始数据
        sql = f"""
            SELECT 
                timestamp,
                building_id,
                meter_id as device_id,
                electricity
            FROM energy_consumption
            WHERE {where_clause}
            ORDER BY timestamp {sort}
            LIMIT {limit}
        """

    data = await Database.fetch_all(sql, tuple(params))

    return {
        "code": 200,
        "message": "成功",
        "data": {
            "total": len(data),
            "group_by": group_by,
            "items": data
        }
    }


# 在 energy_api.py 中添加
@router.get("/carbon/saving")
async def get_carbon_saving():
    """今日碳减排估算 - 使用历史平均值对比"""
    # 固定日期为2016-07-16
    today = date(2016, 7, 16)

    # 1. 查询今日总能耗
    today_sql = "SELECT SUM(electricity) as total FROM energy_consumption WHERE DATE(timestamp) = %s"
    today_data = await Database.fetch_one(today_sql, (today,))
    today_energy = today_data['total'] if today_data and today_data['total'] else 0

    # 2. 计算历史平均能耗（过去30天同一时段的平均值）
    # 取2016-06-16 到 2016-07-15 的数据（不包含今天）
    history_start = today - timedelta(days=30)
    history_end = today - timedelta(days=1)

    avg_sql = """
        SELECT 
            AVG(daily_total) as avg_daily_energy
        FROM (
            SELECT 
                DATE(timestamp) as date,
                SUM(electricity) as daily_total
            FROM energy_consumption
            WHERE DATE(timestamp) BETWEEN %s AND %s
            GROUP BY DATE(timestamp)
        ) as daily_totals
    """
    avg_data = await Database.fetch_one(avg_sql, (history_start, history_end))
    avg_energy = avg_data['avg_daily_energy'] if avg_data and avg_data['avg_daily_energy'] else today_energy

    # 3. 碳排放因子（每度电产生的CO2）
    carbon_factor = 0.785  # kg CO2/kWh（中国电网平均排放因子）

    # 4. 计算节能量和碳减排量（与历史平均值对比）
    if avg_energy > 0:
        energy_saved = avg_energy - today_energy  # 节能量（正数表示节能，负数表示多耗能）
        carbon_saved = energy_saved * carbon_factor  # 碳减排量
        reduction_rate = (energy_saved / avg_energy) * 100  # 节能率
        trend = "up" if energy_saved > 0 else "down" if energy_saved < 0 else "flat"
    else:
        energy_saved = 0
        carbon_saved = 0
        reduction_rate = 0
        trend = "flat"

    # 5. 当前碳排放量
    current_carbon = today_energy * carbon_factor
    avg_carbon = avg_energy * carbon_factor

    return {
        "code": 200,
        "message": "成功",
        "data": {
            "date": today.isoformat(),
            "total_energy": round(today_energy, 2),  # 今日总能耗 (kWh)
            "carbon_emission": round(current_carbon, 2),  # 今日碳排放 (kg CO2)
            "carbon_saved": round(abs(carbon_saved), 2),  # 碳减排绝对值 (kg CO2)
            "reduction_rate": round(abs(reduction_rate), 2),  # 减排率 (%)
            "trend": trend,  # up=节能, down=耗能增加, flat=持平
            "unit": "kg CO2",
            "comparison": {
                "baseline_type": "历史30天平均值",
                "baseline_period": f"{history_start} 至 {history_end}",
                "baseline_energy": round(avg_energy, 2),
                "baseline_carbon": round(avg_carbon, 2),
                "energy_saved": round(energy_saved, 2)  # 正数=节能，负数=耗能增加
            }
        }
    }

# 在 energy_api.py 中添加
@router.get("/trend")
async def get_energy_trend(
        start_time: str = Query(..., description="开始时间，格式：YYYY-MM-DD，例如：2016-07-01"),
        end_time: str = Query(..., description="结束时间，格式：YYYY-MM-DD，例如：2016-07-16"),
        granularity: str = Query("day", description="时间颗粒度：hour/day"),
        building_id: Optional[str] = Query(None, description="建筑ID（可选）")
):
    """能耗趋势查询

    - start_time: 开始日期
    - end_time: 结束日期
    - granularity: 时间颗粒度 (hour=小时级, day=天级)
    - building_id: 可选，指定建筑
    """
    params = []

    # 构建基础查询
    if granularity == "hour":
        # 小时级趋势
        sql = """
            SELECT 
                CONCAT(DATE(timestamp), ' ', HOUR(timestamp), ':00') as time_point,
                SUM(electricity) as energy
            FROM energy_consumption
            WHERE DATE(timestamp) BETWEEN %s AND %s
        """
        params = [start_time, end_time]

        if building_id:
            sql += " AND building_id = %s"
            params.append(building_id)

        sql += " GROUP BY DATE(timestamp), HOUR(timestamp) ORDER BY DATE(timestamp), HOUR(timestamp)"

    else:
        # 天级趋势
        sql = """
            SELECT 
                DATE(timestamp) as time_point,
                SUM(electricity) as energy
            FROM energy_consumption
            WHERE DATE(timestamp) BETWEEN %s AND %s
        """
        params = [start_time, end_time]

        if building_id:
            sql += " AND building_id = %s"
            params.append(building_id)

        sql += " GROUP BY DATE(timestamp) ORDER BY time_point"

    # 执行查询
    data = await Database.fetch_all(sql, tuple(params))

    # 格式化数据
    formatted_data = []
    valid_values = []

    for item in data:
        energy_value = float(item['energy']) if item['energy'] is not None else 0
        formatted_data.append({
            "time_point": item['time_point'],
            "energy": round(energy_value, 2)
        })
        if energy_value > 0:
            valid_values.append(energy_value)

    # 计算统计信息
    if valid_values:
        avg_value = sum(valid_values) / len(valid_values)
        max_value = max(valid_values)
        total_value = sum(valid_values)
    else:
        avg_value = 0
        max_value = 0
        total_value = 0

    return {
        "code": 200,
        "message": "成功",
        "data": {
            "query_params": {
                "start_time": start_time,
                "end_time": end_time,
                "granularity": granularity,
                "building_id": building_id
            },
            "statistics": {
                "avg": round(avg_value, 2),
                "max": round(max_value, 2),
                "total": round(total_value, 2),
                "days": len(formatted_data)
            },
            "trend": formatted_data
        }
    }