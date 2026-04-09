from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from app.database.db import Database
import json

router = APIRouter(prefix="/api/space", tags=["空间管理"])


@router.get("/list")
async def list_spaces(floor_id: str = Query(..., description="楼层ID")):
    """获取楼层下所有空间"""
    sql = """
        SELECT id, floor_id, space_type, name, code, polygon, center_x, center_y, area_sqm, created_at
        FROM spaces
        WHERE floor_id = %s
        ORDER BY code ASC
    """
    
    spaces = await Database.fetch_all(sql, (floor_id,))
    
    # 解析 polygon JSON
    for space in spaces:
        if space['polygon']:
            space['polygon'] = json.loads(space['polygon'])
    
    return {
        "code": 200,
        "message": "成功",
        "data": spaces
    }


@router.post("/create")
async def create_space(space_data: dict):
    """创建空间"""
    required_fields = ["floor_id", "space_type", "name", "code", "polygon"]
    for field in required_fields:
        if field not in space_data:
            raise HTTPException(status_code=400, detail=f"缺少必填字段: {field}")
    
    # 生成 ID
    import uuid
    space_id = f"SP_{uuid.uuid4().hex[:8]}"
    
    # 计算中心点（如果未提供）
    polygon = space_data["polygon"]
    if "center_x" not in space_data or "center_y" not in space_data:
        xs = [p[0] for p in polygon]
        ys = [p[1] for p in polygon]
        center_x = sum(xs) / len(xs)
        center_y = sum(ys) / len(ys)
    else:
        center_x = space_data["center_x"]
        center_y = space_data["center_y"]
    
    # 计算面积（如果未提供）
    if "area_sqm" not in space_data:
        # 简化计算：多边形包围盒面积
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        area_sqm = round((max_x - min_x) * (max_y - min_y) / 100, 2)  # 假设 100px² = 1㎡
    else:
        area_sqm = space_data["area_sqm"]
    
    sql = """
        INSERT INTO spaces (id, floor_id, space_type, name, code, polygon, center_x, center_y, area_sqm)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    await Database.execute(sql, (
        space_id,
        space_data["floor_id"],
        space_data["space_type"],
        space_data["name"],
        space_data["code"],
        json.dumps(polygon),
        center_x,
        center_y,
        area_sqm
    ))
    
    return {
        "code": 200,
        "message": "创建成功",
        "data": {
            "id": space_id,
            "is_success": True
        }
    }


@router.put("/update/{space_id}")
async def update_space(space_id: str, space_data: dict):
    """更新空间信息"""
    updates = []
    params = []
    
    if "name" in space_data:
        updates.append("name = %s")
        params.append(space_data["name"])
    
    if "code" in space_data:
        updates.append("code = %s")
        params.append(space_data["code"])
    
    if "space_type" in space_data:
        updates.append("space_type = %s")
        params.append(space_data["space_type"])
    
    if "polygon" in space_data:
        updates.append("polygon = %s")
        params.append(json.dumps(space_data["polygon"]))
        
        # 重新计算中心点
        polygon = space_data["polygon"]
        xs = [p[0] for p in polygon]
        ys = [p[1] for p in polygon]
        center_x = sum(xs) / len(xs)
        center_y = sum(ys) / len(ys)
        updates.append("center_x = %s")
        params.append(center_x)
        updates.append("center_y = %s")
        params.append(center_y)
    
    if "area_sqm" in space_data:
        updates.append("area_sqm = %s")
        params.append(space_data["area_sqm"])
    
    if not updates:
        return {"code": 400, "message": "没有要更新的字段", "data": None}
    
    params.append(space_id)
    sql = f"UPDATE spaces SET {', '.join(updates)} WHERE id = %s"
    
    await Database.execute(sql, tuple(params))
    
    return {
        "code": 200,
        "message": "更新成功",
        "data": {"is_success": True}
    }


@router.delete("/delete/{space_id}")
async def delete_space(space_id: str):
    """删除空间"""
    sql = "DELETE FROM spaces WHERE id = %s"
    await Database.execute(sql, (space_id,))
    
    return {
        "code": 200,
        "message": "删除成功",
        "data": {"is_success": True}
    }


@router.post("/batch-create")
async def batch_create_spaces(spaces_data: List[dict]):
    """批量创建空间"""
    if not spaces_data:
        raise HTTPException(status_code=400, detail="空间数据不能为空")
    
    success_count = 0
    for space_data in spaces_data:
        try:
            await create_space(space_data)
            success_count += 1
        except Exception as e:
            print(f"Failed to create space: {e}")
    
    return {
        "code": 200,
        "message": f"批量创建完成，成功 {success_count}/{len(spaces_data)}",
        "data": {"success_count": success_count}
    }
