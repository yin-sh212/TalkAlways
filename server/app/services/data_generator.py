import random
from datetime import datetime, timedelta
import pandas as pd
import numpy as np


async def generate_all_data(cursor):
    """生成所有测试数据"""

    # 1. 清空现有数据
    await cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    await cursor.execute("TRUNCATE TABLE energy_consumption")
    await cursor.execute("TRUNCATE TABLE meters")
    await cursor.execute("TRUNCATE TABLE buildings")
    await cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

    # 2. 生成建筑数据
    buildings = [
        ('B001', '办公大楼A', '办公楼', 12000),
        ('B002', '教学楼B', '教学楼', 8500),
        ('B003', '医院C', '医院', 20000),
        ('B004', '商场D', '商业', 15000),
        ('B005', '宿舍E', '住宅', 6000),
    ]

    for b in buildings:
        await cursor.execute(
            "INSERT INTO buildings (id, name, type, area) VALUES (%s, %s, %s, %s)",
            b
        )
    print(f"✅ 生成 {len(buildings)} 条建筑数据")

    # 3. 生成监测点数据
    meters = []
    meter_id = 1
    for building_id, _, building_type, _ in buildings:
        # 每个建筑3-5个监测点
        num_meters = random.randint(3, 5)
        for i in range(num_meters):
            meter_id_str = f"{building_id}_M{i + 1}"
            meter_type = random.choice(['电表', '水表', '空调'])
            meters.append((meter_id_str, building_id, meter_type, 'normal'))
            meter_id += 1

    for m in meters:
        await cursor.execute(
            "INSERT INTO meters (id, building_id, type, status) VALUES (%s, %s, %s, %s)",
            m
        )
    print(f"✅ 生成 {len(meters)} 条监测点数据")

    # 4. 生成能耗数据（1000+条）
    start_date = datetime(2025, 1, 1)
    end_date = datetime(2025, 3, 1)

    data = []
    current_date = start_date
    while current_date <= end_date:
        for building_id, _, building_type, area in buildings:
            for hour in range(8, 22):  # 只生成8:00-22:00的数据
                # 基础负荷逻辑
                is_weekend = current_date.weekday() >= 5
                hour_factor = 1.0

                # 工作日高峰
                if not is_weekend and 9 <= hour <= 17:
                    hour_factor = random.uniform(1.5, 2.0)
                elif is_weekend:
                    hour_factor = random.uniform(0.6, 0.9)

                # 不同类型建筑的特性
                type_factor = {
                    '办公楼': random.uniform(0.8, 1.2),
                    '教学楼': random.uniform(0.7, 1.1),
                    '医院': random.uniform(1.2, 1.5),
                    '商业': random.uniform(1.1, 1.4),
                    '住宅': random.uniform(0.5, 0.8)
                }.get(building_type, 1.0)

                # 基础用电量
                base_elec = area / 100 * hour_factor * type_factor

                # 加入随机波动
                electricity = base_elec * random.uniform(0.8, 1.2)

                # 5%的概率生成异常数据（突增50%以上）
                is_anomaly = random.random() < 0.05
                if is_anomaly:
                    electricity *= random.uniform(1.5, 2.5)

                # 温度数据
                ambient_temp = random.uniform(15, 30)
                humidity = random.uniform(40, 80)

                # 空调相关
                supply_temp = random.uniform(7, 12)
                return_temp = random.uniform(12, 18)

                # 用水量（可选）
                water = random.uniform(5, 20) if random.random() > 0.3 else None

                timestamp = current_date.replace(hour=hour, minute=0, second=0)

                # 随机选择一个监测点
                building_meters = [m[0] for m in meters if m[1] == building_id]
                meter_id = random.choice(building_meters) if building_meters else None

                data.append((
                    building_id,
                    meter_id,
                    timestamp,
                    round(electricity, 2),
                    round(water, 2) if water else None,
                    round(supply_temp, 1),
                    round(return_temp, 1),
                    round(ambient_temp, 1),
                    round(humidity, 1),
                    round(random.uniform(10, 50), 1),  # occupancy
                    is_anomaly
                ))

        current_date += timedelta(days=1)

    # 批量插入数据
    insert_sql = """
        INSERT INTO energy_consumption 
        (building_id, meter_id, timestamp, electricity, water, 
         supply_temp, return_temp, ambient_temp, humidity, occupancy, is_anomaly)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    batch_size = 100
    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]
        await cursor.executemany(insert_sql, batch)

    print(f"✅ 生成 {len(data)} 条能耗数据")

    # 5. 导出到CSV文件（备用）
    df = pd.DataFrame(data, columns=[
        'building_id', 'meter_id', 'timestamp', 'electricity', 'water',
        'supply_temp', 'return_temp', 'ambient_temp', 'humidity',
        'occupancy', 'is_anomaly'
    ])
    df.to_csv('data/dataset.csv', index=False)
    print(f"✅ 数据已导出到 data/dataset.csv")