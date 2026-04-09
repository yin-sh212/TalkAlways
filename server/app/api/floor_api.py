from fastapi import APIRouter, Query, UploadFile, File, HTTPException
from typing import Optional
from app.database.db import Database
import os
import uuid
from pathlib import Path

router = APIRouter(prefix="/api/floor", tags=["楼层管理"])


@router.get("/list")
async def list_floors(building_id: str = Query(..., description="建筑ID")):
    """获取建筑下所有楼层"""
    sql = """
        SELECT id, building_id, floor_number, floor_name, image_url, width, height, created_at
        FROM floors
        WHERE building_id = %s
        ORDER BY floor_number ASC
    """
    
    floors = await Database.fetch_all(sql, (building_id,))
    
    return {
        "code": 200,
        "message": "成功",
        "data": floors
    }


@router.post("/upload")
async def upload_floor_plan(file: UploadFile = File(...)):
    """上传楼层平面图"""
    # 验证文件类型
    if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.svg')):
        raise HTTPException(status_code=400, detail="只支持 PNG/JPG/SVG 格式")
    
    # 生成唯一文件名
    file_ext = file.filename.split('.')[-1]
    unique_name = f"{uuid.uuid4().hex}.{file_ext}"
    
    # 保存路径
    upload_dir = Path(__file__).parent.parent.parent / "client" / "public" / "floor-plans"
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = upload_dir / unique_name
    
    # 保存文件
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    # 返回访问 URL
    image_url = f"/floor-plans/{unique_name}"
    
    return {
        "code": 200,
        "message": "上传成功",
        "data": {
            "image_url": image_url,
            "filename": unique_name
        }
    }


@router.put("/update/{floor_id}")
async def update_floor(floor_id: str, floor_data: dict):
    """更新楼层信息"""
    updates = []
    params = []
    
    if "floor_name" in floor_data:
        updates.append("floor_name = %s")
        params.append(floor_data["floor_name"])
    
    if "image_url" in floor_data:
        updates.append("image_url = %s")
        params.append(floor_data["image_url"])
    
    if "width" in floor_data:
        updates.append("width = %s")
        params.append(floor_data["width"])
    
    if "height" in floor_data:
        updates.append("height = %s")
        params.append(floor_data["height"])
    
    if not updates:
        return {"code": 400, "message": "没有要更新的字段", "data": None}
    
    params.append(floor_id)
    sql = f"UPDATE floors SET {', '.join(updates)} WHERE id = %s"
    
    await Database.execute(sql, tuple(params))
    
    return {
        "code": 200,
        "message": "更新成功",
        "data": {"is_success": True}
    }


@router.delete("/delete/{floor_id}")
async def delete_floor(floor_id: str):
    """删除楼层（级联删除空间）"""
    sql = "DELETE FROM floors WHERE id = %s"
    await Database.execute(sql, (floor_id,))
    
    return {
        "code": 200,
        "message": "删除成功",
        "data": {"is_success": True}
    }
