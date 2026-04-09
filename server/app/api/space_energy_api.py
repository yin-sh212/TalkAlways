from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from app.database.db import Database
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/space-energy", tags=["空间能耗"])


@router.get("/{space_id}/trend")
async def get_space_energy_trend(
    space_id: str,
    time_range: str = Query("today", description="时间范围: today/yesterday/week/month/custom"),
    start_date: Optional[str] = Query(None, description="自定义开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="自定义结束日期 YYYY-MM-DD"),
    energy_type: Optional[str] = Query("electricity", description="能耗类型: electricity/water/gas")
):
    """获取空间能耗趋势数据（ECharts 格式）"""
    # 验证空间存在
    space = await Database.fetch_one("SELECT id, name, area_sqm FROM spaces WHERE id = %s", (space_id,))
    if not space:
        raise HTTPException(status_code=404, detail="空间不存在")
    
    # 计算时间范围
    now = datetime.now()
    if time_range == "today":
        start_dt = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_dt = now
        days = 1
    elif time_range == "yesterday":
        yesterday = now - timedelta(days=1)
        start_dt = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_dt = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
        days = 1
    elif time_range == "week":
        start_dt = now - timedelta(days=now.weekday())
        start_dt = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        end_dt = now
        days = 7
    elif time_range == "month":
        start_dt = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_dt = now
        days = (end_dt - start_dt).days + 1
    elif time_range == "custom":
        if not start_date or not end_date:
            raise HTTPException(status_code=400, detail="自定义范围需要提供 start_date 和 end_date")
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59, microsecond=999999)
        days = (end_dt - start_dt).days + 1
    else:
        raise HTTPException(status_code=400, detail="无效的时间范围参数")
    
    # 根据天数决定时间粒度
    if days == 1:
        # 今日：按小时展示
        group_by = "DATE(ec.timestamp), HOUR(ec.timestamp)"
        select_time = "DATE(ec.timestamp) as date, HOUR(ec.timestamp) as hour"
        format_time = lambda item: f"{item['date']} {item['hour']:02d}:00"
    else:
        # 多天：按天展示
        group_by = "DATE(ec.timestamp)"
        select_time = "DATE(ec.timestamp) as date"
        format_time = lambda item: str(item['date'])
    
    # 确定能耗字段
    energy_field = "ec.electricity"
    if energy_type == "water":
        energy_field = "ec.water"
    elif energy_type == "gas":
        energy_field = "ec.gas"
    
    # 查询趋势数据
    sql = f"""
        SELECT 
            {select_time},
            AVG({energy_field}) as avg_energy,
            MAX({energy_field}) as max_energy,
            MIN({energy_field}) as min_energy
        FROM energy_consumption_new ec
        INNER JOIN meters_new m ON ec.meter_id = m.id
        WHERE m.space_id = %s
            AND ec.timestamp >= %s
            AND ec.timestamp <= %s
        GROUP BY {group_by}
        ORDER BY date ASC
    """
    
    data = await Database.fetch_all(sql, (space_id, start_dt, end_dt))
    
    if not data:
        return {
            "code": 200,
            "message": "成功",
            "data": {
                "categories": [],
                "series": [
                    {"name": "平均能耗", "type": "line", "data": [], "smooth": True},
                    {"name": "最大能耗", "type": "line", "data": [], "smooth": True, "lineStyle": {"type": "dashed"}}
                ]
            }
        }
    
    # 格式化数据
    categories = []
    avg_values = []
    max_values = []
    
    for item in data:
        categories.append(format_time(item))
        avg_values.append(float(item['avg_energy']) if item['avg_energy'] is not None else 0)
        max_values.append(float(item['max_energy']) if item['max_energy'] is not None else 0)
    
    series = [
        {
            "name": "平均能耗",
            "type": "line",
            "data": avg_values,
            "smooth": True
        },
        {
            "name": "最大能耗",
            "type": "line",
            "data": max_values,
            "smooth": True,
            "lineStyle": {"type": "dashed"}
        }
    ]
    
    return {
        "code": 200,
        "message": "成功",
        "data": {
            "categories": categories,
            "series": series
        }
    }


@router.get("/{space_id}")
async def get_space_energy(
    space_id: str,
    time_range: str = Query("today", description="时间范围: today/yesterday/week/month/custom"),
    start_date: Optional[str] = Query(None, description="自定义开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="自定义结束日期 YYYY-MM-DD"),
    energy_type: Optional[str] = Query(None, description="能耗类型: electricity/water/gas")
):
    """获取空间能耗数据"""
    # 验证空间存在
    space = await Database.fetch_one("SELECT id, name, area_sqm FROM spaces WHERE id = %s", (space_id,))
    if not space:
        raise HTTPException(status_code=404, detail="空间不存在")
    
    # 计算时间范围
    now = datetime.now()
    if time_range == "today":
        start_dt = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_dt = now
    elif time_range == "yesterday":
        yesterday = now - timedelta(days=1)
        start_dt = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_dt = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif time_range == "week":
        start_dt = now - timedelta(days=now.weekday())
        start_dt = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        end_dt = now
    elif time_range == "month":
        start_dt = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_dt = now
    elif time_range == "custom":
        if not start_date or not end_date:
            raise HTTPException(status_code=400, detail="自定义范围需要提供 start_date 和 end_date")
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59, microsecond=999999)
    else:
        raise HTTPException(status_code=400, detail="无效的时间范围参数")
    
    # 查询该空间下所有 meter 的能耗
    sql = """
        SELECT SUM(ec.electricity) as total_energy, COUNT(DISTINCT m.id) as meter_count
        FROM energy_consumption_new ec
        INNER JOIN meters_new m ON ec.meter_id = m.id
        WHERE m.space_id = %s
        AND ec.timestamp >= %s
        AND ec.timestamp <= %s
    """
    params = [space_id, start_dt, end_dt]
    
    # 根据能耗类型筛选
    if energy_type:
        if energy_type == "electricity":
            sql += " AND ec.electricity > 0"
        elif energy_type == "water":
            sql += " AND ec.water > 0"
        elif energy_type == "gas":
            sql += " AND ec.gas > 0"
    
    result = await Database.fetch_one(sql, tuple(params))
    
    total_energy = float(result['total_energy']) if result and result['total_energy'] else 0.0
    meter_count = int(result['meter_count']) if result and result['meter_count'] else 0
    area_sqm = float(space['area_sqm']) if space['area_sqm'] else 1.0
    
    # 计算单位面积能耗
    energy_per_sqm = round(total_energy / area_sqm, 2) if area_sqm > 0 else 0.0
    
    return {
        "code": 200,
        "message": "成功",
        "data": {
            "space_id": space_id,
            "space_name": space['name'],
            "area_sqm": area_sqm,
            "time_range": time_range,
            "start_time": start_dt.isoformat(),
            "end_time": end_dt.isoformat(),
            "total_energy": round(total_energy, 2),
            "energy_per_sqm": energy_per_sqm,
            "meter_count": meter_count
        }
    }


@router.get("/floor/{floor_id}/heatmap")
async def get_floor_heatmap(
    floor_id: str,
    time_range: str = Query("today", description="时间范围: today/yesterday/week/month"),
    energy_type: Optional[str] = Query(None, description="能耗类型: electricity/water/gas")
):
    """获取楼层热力图数据（所有空间的能耗）"""
    # 验证楼层存在
    floor = await Database.fetch_one("SELECT id FROM floors WHERE id = %s", (floor_id,))
    if not floor:
        raise HTTPException(status_code=404, detail="楼层不存在")
    
    # 获取该楼层下所有空间
    spaces = await Database.fetch_all("SELECT id, name, code, area_sqm FROM spaces WHERE floor_id = %s", (floor_id,))
    
    if not spaces:
        return {
            "code": 200,
            "message": "成功",
            "data": {"spaces": []}
        }
    
    # 计算时间范围
    now = datetime.now()
    if time_range == "today":
        start_dt = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif time_range == "yesterday":
        yesterday = now - timedelta(days=1)
        start_dt = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
    elif time_range == "week":
        start_dt = now - timedelta(days=now.weekday())
        start_dt = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    elif time_range == "month":
        start_dt = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        raise HTTPException(status_code=400, detail="无效的时间范围参数")
    
    end_dt = now
    
    # 批量查询每个空间的能耗
    space_energies = []
    for space in spaces:
        space_id = space['id']
        area_sqm = float(space['area_sqm']) if space['area_sqm'] else 1.0
        
        sql = """
            SELECT SUM(ec.electricity) as total_energy
            FROM energy_consumption_new ec
            INNER JOIN meters_new m ON ec.meter_id = m.id
            WHERE m.space_id = %s
            AND ec.timestamp >= %s
            AND ec.timestamp <= %s
        """
        params = [space_id, start_dt, end_dt]
        
        # 根据能耗类型筛选
        if energy_type:
            if energy_type == "electricity":
                sql += " AND ec.electricity > 0"
            elif energy_type == "water":
                sql += " AND ec.water > 0"
            elif energy_type == "gas":
                sql += " AND ec.gas > 0"
        
        result = await Database.fetch_one(sql, tuple(params))
        total_energy = float(result['total_energy']) if result and result['total_energy'] else 0.0
        energy_per_sqm = round(total_energy / area_sqm, 2) if area_sqm > 0 else 0.0
        
        space_energies.append({
            "space_id": space_id,
            "space_name": space['name'],
            "space_code": space['code'],
            "area_sqm": area_sqm,
            "total_energy": round(total_energy, 2),
            "energy_per_sqm": energy_per_sqm
        })
    
    return {
        "code": 200,
        "message": "成功",
        "data": {
            "floor_id": floor_id,
            "time_range": time_range,
            "spaces": space_energies
        }
    }
