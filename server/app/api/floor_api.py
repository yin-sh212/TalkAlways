from fastapi import APIRouter, Query, UploadFile, File, HTTPException, Form
from typing import Optional
from app.database.db import Database
import os
import uuid
from pathlib import Path
import xml.etree.ElementTree as ET

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


@router.post("/upload-cad")
async def upload_cad_file(
    file: UploadFile = File(...),
    floor_id: str = Form(None, description="楼层ID（可选，提供则自动更新楼层底图）")
):
    """
    上传CAD文件并转换为SVG
    支持 .dxf 格式（DWG需先转换为DXF）
    如果提供floor_id，会自动更新该楼层的image_url，并使用楼层ID作为文件名
    """
    # 验证文件类型
    filename_lower = file.filename.lower() if file.filename else ""
    
    # DWG格式需要特殊处理
    if filename_lower.endswith('.dwg'):
        raise HTTPException(
            status_code=400, 
            detail="DWG格式需要先转换为DXF。推荐使用以下方法:\n" +
                   "1. LibreCAD (免费): 打开DWG → 另存为DXF\n" +
                   "2. ODA File Converter (免费): 批量转换工具\n" +
                   "3. 在线转换: https://cloudconvert.com/dwg-to-dxf\n" +
                   "转换后再上传DXF文件"
        )
    
    if not filename_lower.endswith(('.dxf',)):
        raise HTTPException(
            status_code=400, 
            detail="仅支持 DXF 格式。DWG文件请先转换为DXF后再上传"
        )
    
    try:
        # 读取文件内容
        content = await file.read()
        
        # 生成文件名：如果提供了floor_id则使用楼层ID，否则使用UUID
        if floor_id:
            unique_name = f"{floor_id}.svg"
        else:
            unique_name = f"{uuid.uuid4().hex}.svg"
        
        # 保存路径
        upload_dir = PROJECT_ROOT / "client" / "public" / "floor-plans"
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        svg_path = upload_dir / unique_name
        
        # 临时保存DXF文件用于转换
        temp_dxf_path = upload_dir / f"temp_{uuid.uuid4().hex}.dxf"
        with open(temp_dxf_path, "wb") as f:
            f.write(content)
        
        try:
            # 转换 DXF 为 SVG
            if filename_lower.endswith('.dxf'):
                svg_content = convert_dxf_to_svg(str(temp_dxf_path))
            else:
                raise HTTPException(status_code=400, detail="不支持的文件格式")
            
            # 保存 SVG 文件
            with open(svg_path, "w", encoding="utf-8") as f:
                f.write(svg_content)
        finally:
            # 删除临时DXF文件
            if temp_dxf_path.exists():
                temp_dxf_path.unlink()
        
        # 返回访问 URL
        image_url = f"/floor-plans/{unique_name}"
        
        # 如果提供了floor_id，自动更新楼层信息
        if floor_id:
            update_sql = "UPDATE floors SET image_url = %s WHERE id = %s"
            await Database.execute(update_sql, (image_url, floor_id))
            print(f"✅ 已更新楼层 {floor_id} 的底图为: {image_url}")
        
        return {
            "code": 200,
            "message": "CAD文件转换成功" + ("并已关联到楼层" if floor_id else ""),
            "data": {
                "image_url": image_url,
                "filename": unique_name,
                "original_filename": file.filename,
                "floor_id": floor_id
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"CAD转换失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"转换失败: {str(e)}")


def convert_dxf_to_svg(dxf_file_path: str) -> str:
    """
    将 DXF 文件转换为 SVG
    使用 ezdxf 库解析 DXF，然后生成简化版 SVG
    """
    try:
        import ezdxf
        
        # 解析 DXF 文件 - 使用文件路径
        doc = ezdxf.readfile(dxf_file_path)
        msp = doc.modelspace()
        
        # 计算边界框
        min_x, min_y = float('inf'), float('inf')
        max_x, max_y = float('-inf'), float('-inf')
        
        entities_data = []
        
        # 遍历所有实体
        for entity in msp:
            try:
                if entity.dxftype() == 'LINE':
                    start = entity.dxf.start
                    end = entity.dxf.end
                    x1, y1 = start.x, start.y
                    x2, y2 = end.x, end.y
                    
                    min_x = min(min_x, x1, x2)
                    min_y = min(min_y, y1, y2)
                    max_x = max(max_x, x1, x2)
                    max_y = max(max_y, y1, y2)
                    
                    entities_data.append({
                        'type': 'line',
                        'x1': x1, 'y1': y1,
                        'x2': x2, 'y2': y2
                    })
                
                elif entity.dxftype() == 'LWPOLYLINE':
                    points = list(entity.get_points())
                    if len(points) >= 2:
                        poly_points = []
                        for p in points:
                            x, y = p[0], p[1]
                            min_x = min(min_x, x)
                            min_y = min(min_y, y)
                            max_x = max(max_x, x)
                            max_y = max(max_y, y)
                            poly_points.append((x, y))
                        
                        entities_data.append({
                            'type': 'polyline',
                            'points': poly_points
                        })
                
                elif entity.dxftype() == 'CIRCLE':
                    center = entity.dxf.center
                    radius = entity.dxf.radius
                    cx, cy = center.x, center.y
                    
                    min_x = min(min_x, cx - radius)
                    min_y = min(min_y, cy - radius)
                    max_x = max(max_x, cx + radius)
                    max_y = max(max_y, cy + radius)
                    
                    entities_data.append({
                        'type': 'circle',
                        'cx': cx, 'cy': cy, 'r': radius
                    })
            
            except Exception as e:
                print(f"跳过实体解析错误: {e}")
                continue
        
        # 如果没有实体，返回空 SVG
        if not entities_data:
            return generate_empty_svg()
        
        # 计算缩放比例（适配 800x600）
        width = max_x - min_x if max_x > min_x else 1
        height = max_y - min_y if max_y > min_y else 1
        
        target_width = 800
        target_height = 600
        
        scale = min(target_width / width, target_height / height)
        offset_x = (target_width - width * scale) / 2
        offset_y = (target_height - height * scale) / 2
        
        # 生成 SVG
        svg_lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg width="{target_width}" height="{target_height}" xmlns="http://www.w3.org/2000/svg">',
            f'  <rect width="{target_width}" height="{target_height}" fill="#ffffff"/>',
            f'  <g transform="translate({offset_x}, {offset_y})">'
        ]
        
        # 添加实体
        for entity in entities_data:
            if entity['type'] == 'line':
                x1 = (entity['x1'] - min_x) * scale
                y1 = target_height - (entity['y1'] - min_y) * scale  # Y轴翻转
                x2 = (entity['x2'] - min_x) * scale
                y2 = target_height - (entity['y2'] - min_y) * scale
                
                svg_lines.append(
                    f'    <line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
                    f'stroke="#333" stroke-width="1.5" stroke-linecap="round"/>'
                )
            
            elif entity['type'] == 'polyline':
                points_str = ' '.join([
                    f"{(p[0] - min_x) * scale:.2f},{target_height - (p[1] - min_y) * scale:.2f}"
                    for p in entity['points']
                ])
                
                svg_lines.append(
                    f'    <polyline points="{points_str}" '
                    f'fill="none" stroke="#333" stroke-width="1.5" stroke-linejoin="round"/>'
                )
            
            elif entity['type'] == 'circle':
                cx = (entity['cx'] - min_x) * scale
                cy = target_height - (entity['cy'] - min_y) * scale
                r = entity['r'] * scale
                
                svg_lines.append(
                    f'    <circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" '
                    f'fill="none" stroke="#333" stroke-width="1.5"/>'
                )
        
        svg_lines.append('  </g>')
        svg_lines.append('</svg>')
        
        return '\n'.join(svg_lines)
    
    except ImportError:
        # ezdxf 未安装，返回提示
        raise ImportError("请安装 ezdxf 库: pip install ezdxf")
    except Exception as e:
        print(f"DXF解析失败: {e}")
        # 降级方案：返回占位 SVG
        return generate_placeholder_svg(str(e))


def generate_empty_svg() -> str:
    """生成空 SVG"""
    return '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="800" height="600" xmlns="http://www.w3.org/2000/svg">
  <rect width="800" height="600" fill="#f5f5f5"/>
  <text x="400" y="300" font-size="16" text-anchor="middle" fill="#999">CAD图纸内容为空</text>
</svg>'''


def generate_placeholder_svg(error_msg: str) -> str:
    """生成占位 SVG（转换失败时）"""
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="800" height="600" xmlns="http://www.w3.org/2000/svg">
  <rect width="800" height="600" fill="#fff3e0"/>
  <text x="400" y="280" font-size="16" text-anchor="middle" fill="#ff6b00">CAD转换失败</text>
  <text x="400" y="310" font-size="12" text-anchor="middle" fill="#666">{error_msg[:100]}</text>
  <text x="400" y="340" font-size="12" text-anchor="middle" fill="#666">请检查DXF文件格式</text>
</svg>'''

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
