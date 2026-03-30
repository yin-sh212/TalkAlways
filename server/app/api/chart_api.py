# app/api/chart_api.py
from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime, timedelta
from app.database.db import Database

router = APIRouter(prefix="/api/charts", tags=["图表数据"])


@router.get("/trend")
async def get_trend_data(
        building_id: str = Query(..., description="建筑编号，如：Eagle_education_Cassie"),
        start_date: Optional[str] = Query(default=None, description="开始日期，格式：YYYY-MM-DD，例如：2016-07-01"),
        end_date: str = Query(default="2016-08-15", description="截止日期，格式：YYYY-MM-DD，例如：2016-08-15"),
        days: Optional[int] = Query(default=None, ge=1, le=365, description="天数，可选，若未提供则根据 start_date 和 end_date 计算")
):
    """获取趋势图数据（ECharts 格式）- 根据时间范围动态调整粒度"""
    try:
        # 如果提供了 start_date，则根据 start_date 和 end_date 计算实际天数
        if start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            days = (end_dt - start_dt).days + 1  # 包含首尾两天
        else:
            # 如果没有提供 start_date，使用 days 参数（默认 7 天）
            days = days or 7
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            start_dt = end_dt - timedelta(days=days-1)
            start_date = start_dt.strftime("%Y-%m-%d")
        
        # 根据天数决定时间粒度
        if days == 1:
            # 今日：按小时展示
            group_by = "DATE(timestamp), HOUR(timestamp)"
            select_time = "DATE(timestamp) as date, HOUR(timestamp) as hour"
            format_time = lambda item: f"{item['date']} {item['hour']:02d}:00"
        else:
            # 多天：按天展示
            group_by = "DATE(timestamp)"
            select_time = "DATE(timestamp) as date"
            format_time = lambda item: str(item['date'])
        
        sql = f"""
            SELECT 
                {select_time},
                AVG(electricity) as avg_elec,
                MAX(electricity) as max_elec,
                MIN(electricity) as min_elec
            FROM energy_consumption
            WHERE building_id = %s 
                AND DATE(timestamp) BETWEEN %s AND %s
            GROUP BY {group_by}
            ORDER BY date ASC
        """

        data = await Database.fetch_all(sql, (building_id, start_date, end_date))

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

        # 格式化时间
        categories = []
        avg_values = []
        max_values = []

        for item in data:
            categories.append(format_time(item))
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
        return {
            "code": 500,
            "message": f"获取趋势数据失败：{str(e)}",
            "data": {
                "categories": [],
                "series": []
            }
        }


@router.get("/alarm-trend")
async def get_alarm_trend_data(
        building_id: str = Query(..., description="建筑编号，如：Eagle_education_Cassie"),
        start_date: Optional[str] = Query(default=None, description="开始日期，格式：YYYY-MM-DD，例如：2016-07-01"),
        end_date: str = Query(default="2016-08-15", description="截止日期，格式：YYYY-MM-DD，例如：2016-08-15"),
        days: Optional[int] = Query(default=None, ge=1, le=365, description="天数，可选，若未提供则根据 start_date 和 end_date 计算")
):
    """获取告警趋势图数据（ECharts 格式）- 按时间统计各告警级别的数量"""
    try:
        # 如果提供了 start_date，则根据 start_date 和 end_date 计算实际天数
        if start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            days = (end_dt - start_dt).days + 1  # 包含首尾两天
        else:
            # 如果没有提供 start_date，使用 days 参数（默认 7 天）
            days = days or 7
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            start_dt = end_dt - timedelta(days=days-1)
            start_date = start_dt.strftime("%Y-%m-%d")
        
        # 根据天数决定时间粒度
        if days == 1:
            # 今日：按小时统计告警数量
            group_by = "DATE(start_time), HOUR(start_time)"
            select_time = "DATE(start_time) as date, HOUR(start_time) as hour"
            format_time = lambda item: f"{item['date']} {item['hour']:02d}:00"
            
            # 生成所有小时点（00:00 到 23:00）
            categories = [f"{start_date} {h:02d}:00" for h in range(24)]
        else:
            # 多天：按天统计告警数量
            group_by = "DATE(start_time)"
            select_time = "DATE(start_time) as date"
            format_time = lambda item: str(item['date'])
            
            # 生成所有日期（包含首尾）
            categories = []
            current_dt = start_dt
            while current_dt <= end_dt:
                categories.append(current_dt.strftime("%Y-%m-%d"))
                current_dt += timedelta(days=1)
        
        # 查询告警数量，按级别统计
        sql = f"""
            SELECT 
                {select_time},
                alarm_level,
                COUNT(*) as alarm_count
            FROM alarms
            WHERE building_id = %s 
                AND DATE(start_time) BETWEEN %s AND %s
            GROUP BY {group_by}, alarm_level
            ORDER BY date ASC, alarm_level ASC
        """

        data = await Database.fetch_all(sql, (building_id, start_date, end_date))

        # 初始化系列数据，所有时间点都初始化为 0
        series_data = {
            1: [0] * len(categories),  # 紧急
            2: [0] * len(categories),  # 重要
            3: [0] * len(categories),  # 一般
            4: [0] * len(categories)   # 提示
        }
        
        # 填充实际告警数量
        for item in data:
            time_key = format_time(item)
            if time_key in categories:
                time_index = categories.index(time_key)
                alarm_level = item['alarm_level']
                alarm_count = item['alarm_count']
                
                if alarm_level in series_data:
                    series_data[alarm_level][time_index] = alarm_count
        
        # 构建系列数据
        level_names = {
            1: "紧急",
            2: "重要",
            3: "一般",
            4: "提示"
        }
        
        series = []
        for level, name in level_names.items():
            series.append({
                "name": name,
                "type": "line",
                "data": series_data[level],
                "smooth": True
            })

        return {
            "code": 200,
            "data": {
                "categories": categories,
                "series": series
            }
        }
    except Exception as e:
        return {
            "code": 500,
            "message": f"获取告警趋势数据失败：{str(e)}",
            "data": {
                "categories": [],
                "series": []
            }
        }


@router.get("/comparison")
async def get_comparison_data(
        building_ids: str = Query(...,
                                  description="建筑编号，逗号分隔"),
        start_date: str = Query(..., description="开始日期，格式：YYYY-MM-DD"),
        end_date: str = Query(..., description="结束日期，格式：YYYY-MM-DD")
):
    """获取多建筑对比数据（增强版 - 支持多维度对比和综合评分）"""
    ids = building_ids.split(',')

    building_details = []
    
    # 第一阶段：收集所有建筑的原始数据
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
                COALESCE(AVG(ambient_temp), 0) as avg_temp,
                SUM(CASE WHEN is_anomaly = 1 THEN 1 ELSE 0 END) as anomaly_count,
                COUNT(*) as total_count
            FROM energy_consumption
            WHERE building_id = %s 
                AND DATE(timestamp) BETWEEN %s AND %s
        """
        data = await Database.fetch_one(sql, (building_id, start_date, end_date))

        if not data:
            data = {
                "total_elec": 0, "avg_elec": 0, "peak_elec": 0,
                "avg_cooling": 0, "avg_heating": 0, "avg_temp": 0,
                "anomaly_count": 0, "total_count": 0
            }

        # 获取建筑信息（包含面积）
        name_sql = "SELECT name, type, area FROM buildings WHERE id = %s"
        name_data = await Database.fetch_one(name_sql, (building_id,))
        
        building_name = name_data['name'] if name_data else building_id
        building_type = name_data['type'] if name_data else '未知'
        building_area = name_data['area'] if name_data and name_data['area'] else None
        
        # 计算各项指标
        total_elec = data['total_elec']
        avg_elec = data['avg_elec']
        peak_elec = data['peak_elec']
        anomaly_count = data['anomaly_count']
        total_count = data['total_count']
        
        # 单位面积能耗 (kWh/m²) - 如果面积缺失或为 0，使用平均能耗作为替代指标
        if building_area and building_area > 0:
            per_area = total_elec / building_area
        else:
            # 使用平均能耗作为相对指标（避免极端值）
            per_area = avg_elec * 10  # 乘以一个系数使其与其他评分量级相当
        
        # 峰值系数
        peak_ratio = peak_elec / avg_elec if avg_elec > 0 else 0
        
        # 异常率
        anomaly_rate = (anomaly_count / total_count * 100) if total_count > 0 else 0
        
        # 健康度 (100 - 异常率)
        health_score = 100 - anomaly_rate
        
        # 稳定性 (100 - (峰值系数 - 1) * 50)
        stability_score = max(0, min(100, 100 - (peak_ratio - 1) * 50))
        
        building_details.append({
            "building_id": building_id,
            "building_name": building_name,
            "building_type": building_type,
            "area": building_area,
            "total_elec": total_elec,
            "avg_elec": avg_elec,
            "per_area": per_area,
            "peak_ratio": peak_ratio,
            "health_score": health_score,
            "stability_score": stability_score,
            "efficiency_score": 0,  # 第二阶段计算
            "anomaly_rate": anomaly_rate
        })
    
    # 第二阶段：基于平均能耗计算节能性评分（相对比较）
    if len(building_details) > 0:
        avg_per_area = sum(b["per_area"] for b in building_details) / len(building_details)
        
        for b in building_details:
            # 节能性：低于平均水平的建筑得分更高
            # 使用标准差归一化：(当前值 - 平均值) / 平均值 * 50 + 50
            # 这样平均值为 50 分，优于平均 20% 得 60 分，差于平均 20% 得 40 分
            if avg_per_area > 0:
                relative_efficiency = 50 - (b["per_area"] - avg_per_area) / avg_per_area * 50
                b["efficiency_score"] = max(0, min(100, relative_efficiency))
            else:
                b["efficiency_score"] = 50  # 默认中间分
            
            # 防止出现 NaN 或无穷大
            if not b["efficiency_score"]:
                b["efficiency_score"] = 50

    # 构建雷达图数据
    radar_data = {
        "indicators": [
            {"name": "节能性", "max": 100},
            {"name": "稳定性", "max": 100},
            {"name": "健康度", "max": 100},
            {"name": "能效比", "max": 100}
        ],
        "buildings": [
            {
                "building_name": b["building_name"],
                "values": [
                    round(b["efficiency_score"], 2) if b["efficiency_score"] else 50,
                    round(b["stability_score"], 2) if b["stability_score"] else 50,
                    round(b["health_score"], 2) if b["health_score"] else 50,
                    # 能效比：基于单位面积能耗的相对评分（与节能性类似但权重不同）
                    round(max(0, min(100, 50 - (b["per_area"] - avg_per_area) / max(avg_per_area, 0.001) * 30)), 2) if avg_per_area > 0 else 50
                ]
            }
            for b in building_details
        ]
    }

    return {
        "code": 200,
        "data": radar_data
    }


@router.get("/distribution")
async def get_alarm_distribution(
        building_id: str = Query(..., description="建筑编号，如：Eagle_education_Cassie"),
        start_date: str = Query(default="2016-08-14", description="开始日期，格式：YYYY-MM-DD"),
        end_date: str = Query(default="2016-08-15", description="结束日期，格式：YYYY-MM-DD")
):
    """获取告警类型分布数据（饼图）- 按告警类型统计数量"""
    try:
        # 按告警类型统计数量
        sql = """
            SELECT 
                alarm_type,
                COUNT(*) as count
            FROM alarms
            WHERE building_id = %s 
                AND DATE(start_time) BETWEEN %s AND %s
            GROUP BY alarm_type
            ORDER BY count DESC
        """
        
        data = await Database.fetch_all(sql, (building_id, start_date, end_date))
        
        # 转换为饼图数据格式
        result = []
        for item in data:
            alarm_type = item['alarm_type'] or '未知类型'
            count = int(item['count']) if item['count'] else 0
            
            # 根据告警类型设置名称
            type_names = {
                'dynamic_baseline': '动态基线告警',
                'trend_decline': '趋势下降告警',
            }
            
            result.append({
                "name": type_names.get(alarm_type, alarm_type),
                "value": count
            })
        
        return {
            "code": 200,
            "data": result
        }
    
    except Exception as e:
        print(f"❌ 获取告警分布失败：{e}")
        return {
            "code": 500,
            "message": f"获取告警分布失败：{str(e)}",
            "data": []
        }


@router.get("/energy-distribution")
async def get_energy_distribution(
        building_id: str = Query(..., description="建筑编号，如：Eagle_education_Cassie"),
        date: str = Query(default="2016-09-01", description="日期，格式：YYYY-MM-DD")
):
    """获取 24 小时能耗分布数据（折线图）- 按小时统计能耗"""
    try:
        # 查询指定日期的 24 小时能耗数据
        sql = """
            SELECT 
                HOUR(timestamp) as hour,
                AVG(electricity) as avg_elec,
                MAX(electricity) as max_elec
            FROM energy_consumption
            WHERE building_id = %s 
                AND DATE(timestamp) = %s
            GROUP BY HOUR(timestamp)
            ORDER BY hour ASC
        """
        
        data = await Database.fetch_all(sql, (building_id, date))
        
        # 生成 24 个小时的 categories (00:00 - 23:00)
        categories = [f"{h:02d}:00" for h in range(24)]
        
        # 初始化所有小时的数据为 0
        avg_values = [0] * 24
        max_values = [0] * 24
        
        # 填充实际查询到的数据
        for item in data:
            hour = int(item['hour']) if item['hour'] is not None else 0
            if 0 <= hour < 24:
                avg_values[hour] = float(item['avg_elec']) if item['avg_elec'] is not None else 0
                max_values[hour] = float(item['max_elec']) if item['max_elec'] is not None else 0
        
        series = [
            {
                "name": "平均用电量",
                "type": "line",
                "data": avg_values,
                "smooth": True,
                "areaStyle": {"opacity": 0.2}
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
        print(f"❌ 获取能耗分布失败：{e}")
        return {
            "code": 500,
            "message": f"获取能耗分布失败：{str(e)}",
            "data": {
                "categories": [],
                "series": []
            }
        }