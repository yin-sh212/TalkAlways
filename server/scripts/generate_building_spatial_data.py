"""
建筑空间数据生成脚本
为现有建筑生成楼层、房间/区域及简化的 SVG 平面图
"""
import asyncio
import json
import os
import random
import uuid
from app.database.db import Database


def generate_polygon(x, y, width, height):
    """生成矩形多边形的坐标数组"""
    return [
        [x, y],
        [x + width, y],
        [x + width, y + height],
        [x, y + height]
    ]


def generate_floor_plan_svg(floor_id, floor_number, rooms):
    """生成简化的 SVG 楼层平面图"""
    svg_width = 800
    svg_height = 600
    
    svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="{svg_width}" height="{svg_height}" xmlns="http://www.w3.org/2000/svg">
  <!-- 背景 -->
  <rect width="{svg_width}" height="{svg_height}" fill="#f5f5f5"/>
  
  <!-- 标题 -->
  <text x="20" y="30" font-size="18" font-weight="bold" fill="#333">Floor {floor_number}</text>
  
  <!-- 房间区块 -->
'''
    
    colors = ['#e3f2fd', '#f3e5f5', '#e8f5e9', '#fff3e0', '#fce4ec']
    
    for i, room in enumerate(rooms):
        poly = room['polygon']
        color = colors[i % len(colors)]
        
        # 转换多边形为 SVG points
        points = ' '.join([f"{p[0]},{p[1]}" for p in poly])
        
        svg_content += f'''  <!-- {room['name']} -->
  <polygon points="{points}" fill="{color}" stroke="#666" stroke-width="2" opacity="0.7"/>
  <text x="{room['center_x']}" y="{room['center_y']}" font-size="12" text-anchor="middle" fill="#333">{room['code']}</text>
'''
    
    svg_content += '''</svg>'''
    
    return svg_content


async def create_tables():
    """创建必要的表"""
    print("Creating tables...")
    
    # 创建 floors 表
    await Database.execute("""
        CREATE TABLE IF NOT EXISTS floors (
            id VARCHAR(50) PRIMARY KEY,
            building_id VARCHAR(50) NOT NULL,
            floor_number INT COMMENT '楼层编号：1,2,3...',
            floor_name VARCHAR(100) COMMENT '楼层名称：一层、二层...',
            image_url VARCHAR(500) COMMENT '平面图图片路径',
            width FLOAT COMMENT '图片宽度(像素)',
            height FLOAT COMMENT '图片高度(像素)',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='楼层信息表'
    """)
    
    # 创建 spaces 表
    await Database.execute("""
        CREATE TABLE IF NOT EXISTS spaces (
            id VARCHAR(50) PRIMARY KEY,
            floor_id VARCHAR(50) NOT NULL,
            space_type ENUM('room', 'area') COMMENT '类型：房间/区域',
            name VARCHAR(100) COMMENT '名称',
            code VARCHAR(50) COMMENT '编号',
            polygon JSON COMMENT '多边形坐标数组 [[x1,y1],[x2,y2]...]',
            center_x FLOAT COMMENT '中心点X',
            center_y FLOAT COMMENT '中心点Y',
            area_sqm FLOAT COMMENT '面积(㎡)',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='空间信息表'
    """)
    
    # 添加外键约束（使用 buildings_new）
    try:
        await Database.execute("""
            ALTER TABLE floors 
            ADD CONSTRAINT fk_floors_building 
            FOREIGN KEY (building_id) REFERENCES buildings_new(id) ON DELETE CASCADE
        """)
        print("Added foreign key: floors.building_id -> buildings_new.id")
    except Exception as e:
        if "Duplicate" in str(e) or "already exists" in str(e).lower():
            print("Foreign key floors.building_id already exists")
        else:
            print(f"Warning adding floors FK: {e}")
    
    try:
        await Database.execute("""
            ALTER TABLE spaces 
            ADD CONSTRAINT fk_spaces_floor 
            FOREIGN KEY (floor_id) REFERENCES floors(id) ON DELETE CASCADE
        """)
        print("Added foreign key: spaces.floor_id -> floors.id")
    except Exception as e:
        if "Duplicate" in str(e) or "already exists" in str(e).lower():
            print("Foreign key spaces.floor_id already exists")
        else:
            print(f"Warning adding spaces FK: {e}")
    
    # 修改 meters_new 表增加 space_id
    try:
        await Database.execute("""
            ALTER TABLE meters_new ADD COLUMN space_id VARCHAR(50) COMMENT '所属空间ID'
        """)
        print("Added space_id column to meters_new table")
    except Exception as e:
        if "Duplicate column name" in str(e):
            print("space_id column already exists")
        else:
            raise
    
    try:
        await Database.execute("""
            ALTER TABLE meters_new 
            ADD CONSTRAINT fk_meters_space 
            FOREIGN KEY (space_id) REFERENCES spaces(id)
        """)
        print("Added foreign key: meters_new.space_id -> spaces.id")
    except Exception as e:
        if "Duplicate" in str(e) or "already exists" in str(e).lower():
            print("Foreign key meters_new.space_id already exists")
        else:
            print(f"Warning adding meters FK: {e}")
    
    # 创建索引
    await Database.execute("CREATE INDEX IF NOT EXISTS idx_floors_building ON floors(building_id)")
    await Database.execute("CREATE INDEX IF NOT EXISTS idx_spaces_floor ON spaces(floor_id)")
    await Database.execute("CREATE INDEX IF NOT EXISTS idx_meters_space ON meters_new(space_id)")
    
    print("Tables created successfully\n")


async def generate_building_data():
    """为所有建筑生成楼层和空间数据"""
    print("Generating building spatial data...\n")
    
    # 使用 buildings_new 表
    buildings = await Database.fetch_all('SELECT id, name, type FROM buildings_new')
    
    for building in buildings:
        building_id = building['id']
        building_name = building['name']
        building_type = building['type']
        
        print(f"Processing building: {building_name} ({building_id})")
        
        # 根据建筑类型确定楼层数
        if '教学楼' in building_type or '办公楼' in building_type:
            num_floors = random.randint(4, 8)
        elif '住宅' in building_type:
            num_floors = random.randint(6, 12)
        else:
            num_floors = random.randint(2, 4)
        
        for floor_num in range(1, num_floors + 1):
            floor_id = f"{building_id}_F{floor_num}"
            floor_name = f"{floor_num}层"
            
            # 插入楼层记录
            await Database.execute("""
                INSERT INTO floors (id, building_id, floor_number, floor_name, image_url, width, height)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (floor_id, building_id, floor_num, floor_name, f"/floor-plans/{floor_id}.svg", 800, 600))
            
            # 生成该楼层的房间
            num_rooms = random.randint(8, 15)
            rooms = []
            
            # 简单的网格布局
            cols = 4
            rows = (num_rooms + cols - 1) // cols
            cell_width = 180
            cell_height = 130
            margin_x = 20
            margin_y = 50
            
            room_counter = 1
            for row in range(rows):
                for col in range(cols):
                    if room_counter > num_rooms:
                        break
                    
                    x = margin_x + col * cell_width
                    y = margin_y + row * cell_height
                    
                    # 随机调整大小
                    width = cell_width - 10 + random.randint(-10, 10)
                    height = cell_height - 10 + random.randint(-10, 10)
                    
                    room_id = f"{floor_id}_R{room_counter:02d}"
                    room_code = f"{floor_num}{chr(64 + room_counter)}"  # 1A, 1B, 1C...
                    room_name = f"房间{room_code}"
                    
                    polygon = generate_polygon(x, y, width, height)
                    center_x = x + width / 2
                    center_y = y + height / 2
                    area_sqm = round((width * height) / 100, 2)  # 假设 100px = 1㎡
                    
                    rooms.append({
                        'id': room_id,
                        'floor_id': floor_id,
                        'space_type': 'room',
                        'name': room_name,
                        'code': room_code,
                        'polygon': polygon,
                        'center_x': center_x,
                        'center_y': center_y,
                        'area_sqm': area_sqm
                    })
                    
                    # 插入空间记录
                    await Database.execute("""
                        INSERT INTO spaces (id, floor_id, space_type, name, code, polygon, center_x, center_y, area_sqm)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        room_id, floor_id, 'room', room_name, room_code,
                        json.dumps(polygon), center_x, center_y, area_sqm
                    ))
                    
                    room_counter += 1
            
            # 生成 SVG 平面图
            svg_content = generate_floor_plan_svg(floor_id, floor_num, rooms)
            
            # 保存 SVG 文件
            svg_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'client', 'public', 'floor-plans')
            os.makedirs(svg_dir, exist_ok=True)
            
            svg_path = os.path.join(svg_dir, f"{floor_id}.svg")
            with open(svg_path, 'w', encoding='utf-8') as f:
                f.write(svg_content)
            
            print(f"  Floor {floor_num}: {len(rooms)} rooms, SVG saved")
        
        print(f"Building {building_name} completed\n")


async def bind_meters_to_spaces():
    """将现有的 meters 随机绑定到 spaces"""
    print("Binding meters to spaces...")
    
    # 获取所有未绑定的 meters（使用 meters_new）
    meters = await Database.fetch_all("""
        SELECT id, building_id FROM meters_new 
        WHERE space_id IS NULL OR space_id = ''
    """)
    
    if not meters:
        print("No unbound meters found")
        return
    
    print(f"Found {len(meters)} unbound meters")
    
    for meter in meters:
        meter_id = meter['id']
        building_id = meter['building_id']
        
        # 查找该建筑下的所有空间
        spaces = await Database.fetch_all("""
            SELECT s.id 
            FROM spaces s
            JOIN floors f ON s.floor_id = f.id
            WHERE f.building_id = %s
        """, (building_id,))
        
        if spaces:
            # 随机选择一个空间
            space_id = random.choice(spaces)['id']
            
            await Database.execute("""
                UPDATE meters_new SET space_id = %s WHERE id = %s
            """, (space_id, meter_id))
    
    print(f"Bound {len(meters)} meters to spaces\n")


async def main():
    """主函数"""
    print("="*60)
    print("Building Spatial Data Generator")
    print("="*60 + "\n")
    
    try:
        # 1. 创建表
        await create_tables()
        
        # 2. 生成建筑空间数据
        await generate_building_data()
        
        # 3. 绑定 meters 到 spaces
        await bind_meters_to_spaces()
        
        # 4. 统计结果
        print("="*60)
        print("Generation Summary")
        print("="*60)
        
        floors_count = await Database.fetch_one("SELECT COUNT(*) as count FROM floors")
        spaces_count = await Database.fetch_one("SELECT COUNT(*) as count FROM spaces")
        bound_meters = await Database.fetch_one("SELECT COUNT(*) as count FROM meters_new WHERE space_id IS NOT NULL AND space_id != ''")
        
        print(f"Total floors created: {floors_count['count']}")
        print(f"Total spaces created: {spaces_count['count']}")
        print(f"Meters bound to spaces: {bound_meters['count']}")
        print("\nDatabase fields:")
        print("- floors: id, building_id, floor_number, floor_name, image_url, width, height, created_at")
        print("- spaces: id, floor_id, space_type, name, code, polygon, center_x, center_y, area_sqm, created_at")
        print("- meters_new: Added space_id field (foreign key to spaces.id)")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    asyncio.run(main())
