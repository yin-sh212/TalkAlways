from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from app.database.db import Database

router = APIRouter(prefix="/api/meter-binding", tags=["点位绑定"])


@router.get("/unbound")
async def get_unbound_meters(floor_id: Optional[str] = Query(None, description="楼层ID")):
    """获取未绑定空间的监测点"""
    if floor_id:
        # 获取指定楼层下未绑定的 meters
        sql = """
            SELECT m.id, m.building_id, m.type, m.status, m.installed_at
            FROM meters_new m
            LEFT JOIN spaces s ON m.space_id = s.id
            LEFT JOIN floors f ON s.floor_id = f.id
            WHERE (m.space_id IS NULL OR m.space_id = '')
            AND f.id = %s
        """
        meters = await Database.fetch_all(sql, (floor_id,))
    else:
        # 获取所有未绑定的 meters
        sql = """
            SELECT id, building_id, type, status, installed_at
            FROM meters_new
            WHERE space_id IS NULL OR space_id = ''
        """
        meters = await Database.fetch_all(sql)
    
    return {
        "code": 200,
        "message": "成功",
        "data": meters
    }


@router.post("/bind")
async def bind_meter(bind_data: dict):
    """绑定监测点到空间"""
    if "meter_id" not in bind_data or "space_id" not in bind_data:
        raise HTTPException(status_code=400, detail="缺少 meter_id 或 space_id")
    
    meter_id = bind_data["meter_id"]
    space_id = bind_data["space_id"]
    
    # 验证 space_id 是否存在
    space = await Database.fetch_one("SELECT id FROM spaces WHERE id = %s", (space_id,))
    if not space:
        raise HTTPException(status_code=404, detail="空间不存在")
    
    # 更新绑定
    sql = "UPDATE meters_new SET space_id = %s WHERE id = %s"
    await Database.execute(sql, (space_id, meter_id))
    
    return {
        "code": 200,
        "message": "绑定成功",
        "data": {"is_success": True}
    }


@router.post("/unbind")
async def unbind_meter(unbind_data: dict):
    """解绑监测点"""
    if "meter_id" not in unbind_data:
        raise HTTPException(status_code=400, detail="缺少 meter_id")
    
    meter_id = unbind_data["meter_id"]
    
    sql = "UPDATE meters_new SET space_id = NULL WHERE id = %s"
    await Database.execute(sql, (meter_id,))
    
    return {
        "code": 200,
        "message": "解绑成功",
        "data": {"is_success": True}
    }


@router.post("/batch-bind")
async def batch_bind_meters(bind_list: list):
    """批量绑定监测点"""
    if not bind_list:
        raise HTTPException(status_code=400, detail="绑定数据不能为空")
    
    success_count = 0
    for bind_data in bind_list:
        try:
            await bind_meter(bind_data)
            success_count += 1
        except Exception as e:
            print(f"Failed to bind meter: {e}")
    
    return {
        "code": 200,
        "message": f"批量绑定完成，成功 {success_count}/{len(bind_list)}",
        "data": {"success_count": success_count}
    }


@router.get("/bound-list")
async def get_bound_meters(space_id: Optional[str] = Query(None, description="空间ID")):
    """获取已绑定的监测点列表"""
    if space_id:
        sql = """
            SELECT m.id, m.building_id, m.type, m.status, m.space_id
            FROM meters_new m
            WHERE m.space_id = %s
        """
        meters = await Database.fetch_all(sql, (space_id,))
    else:
        sql = """
            SELECT m.id, m.building_id, m.type, m.status, m.space_id
            FROM meters_new m
            WHERE m.space_id IS NOT NULL AND m.space_id != ''
        """
        meters = await Database.fetch_all(sql)
    
    return {
        "code": 200,
        "message": "成功",
        "data": meters
    }
