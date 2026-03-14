# import_csv_to_db.py
import pandas as pd
import asyncio
import aiomysql
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()


async def import_csv_to_mysql(csv_file):
    """将CSV数据导入MySQL"""

    # 1. 读取CSV
    print(f"📄 读取CSV文件: {csv_file}")
    df = pd.read_csv(csv_file, encoding='utf-8')
    print(f"✅ 共读取 {len(df)} 条数据")

    # 2. 连接数据库
    pool = await aiomysql.create_pool(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', 3306)),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', '123456'),
        db=os.getenv('DB_NAME', 'energy_management'),
        autocommit=False
    )

    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:

            # 3. 清空现有数据
            print("🧹 清空现有数据...")
            await cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            await cursor.execute("TRUNCATE TABLE energy_consumption")
            await cursor.execute("TRUNCATE TABLE meters")
            await cursor.execute("TRUNCATE TABLE buildings")
            await cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

            # 4. 导入建筑信息
            print("🏢 导入建筑信息...")
            buildings = df[['建筑编号', '建筑类型']].drop_duplicates()
            for _, row in buildings.iterrows():
                building_id = row['建筑编号']
                building_type = row['建筑类型']
                # 根据建筑类型设置名称和面积
                name_map = {
                    '办公楼': f'{building_id}办公楼',
                    '教学楼': f'{building_id}教学楼',
                    '公共机构': f'{building_id}公共机构'
                }
                name = name_map.get(building_type, building_id)
                area = 10000  # 默认面积，可调整

                sql = "INSERT INTO buildings (id, name, type, area) VALUES (%s, %s, %s, %s)"
                await cursor.execute(sql, (building_id, name, building_type, area))
            print(f"✅ 导入 {len(buildings)} 个建筑")

            # 5. 导入设备信息
            print("📊 导入设备信息...")
            meters = df[['设备编号', '建筑编号', '运行状态']].drop_duplicates()
            meter_count = 0
            for _, row in meters.iterrows():
                meter_id = row['设备编号']
                building_id = row['建筑编号']
                status = row['运行状态']
                # 判断设备类型
                if 'METER' in meter_id:
                    device_type = '电表'
                else:
                    device_type = '未知'

                sql = "INSERT INTO meters (id, building_id, type, status) VALUES (%s, %s, %s, %s)"
                try:
                    await cursor.execute(sql, (meter_id, building_id, device_type, status))
                    meter_count += 1
                except Exception as e:
                    print(f"  跳过设备 {meter_id}: {e}")
            print(f"✅ 导入 {meter_count} 个设备")

            # 6. 导入能耗数据
            print("⚡ 导入能耗数据...")
            data_count = 0
            batch_size = 100
            data_batch = []

            for _, row in df.iterrows():
                # 处理时间格式
                timestamp = row['监测时间']
                if isinstance(timestamp, str):
                    timestamp = timestamp.replace('/', '-')

                data_batch.append((
                    row['建筑编号'],
                    row['设备编号'],
                    timestamp,
                    float(row['电力能耗_kWh']),
                    float(row['水耗_m3']) if pd.notna(row['水耗_m3']) else None,
                    float(row['空调出水温度_℃']) if pd.notna(row['空调出水温度_℃']) else None,
                    float(row['空调回水温度_℃']) if pd.notna(row['空调回水温度_℃']) else None,
                    float(row['环境温度_℃']),
                    float(row['湿度_%RH']),
                    float(row['人员密度_人/100㎡']) if pd.notna(row['人员密度_人/100㎡']) else None,
                    1 if row['运行状态'] == '异常' else 0
                ))

                if len(data_batch) >= batch_size:
                    sql = """
                        INSERT INTO energy_consumption 
                        (building_id, meter_id, timestamp, electricity, water, 
                         supply_temp, return_temp, ambient_temp, humidity, occupancy, is_anomaly)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    await cursor.executemany(sql, data_batch)
                    data_count += len(data_batch)
                    data_batch = []
                    print(f"  已导入 {data_count} 条...")

            # 导入剩余数据
            if data_batch:
                sql = """
                    INSERT INTO energy_consumption 
                    (building_id, meter_id, timestamp, electricity, water, 
                     supply_temp, return_temp, ambient_temp, humidity, occupancy, is_anomaly)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                await cursor.executemany(sql, data_batch)
                data_count += len(data_batch)

            # 提交事务
            await conn.commit()

            print(f"✅ 导入 {data_count} 条能耗数据")

            # 7. 验证数据
            await cursor.execute("SELECT COUNT(*) FROM buildings")
            building_count = (await cursor.fetchone())[0]
            await cursor.execute("SELECT COUNT(*) FROM meters")
            meter_count = (await cursor.fetchone())[0]
            await cursor.execute("SELECT COUNT(*) FROM energy_consumption")
            energy_count = (await cursor.fetchone())[0]

            print("\n" + "=" * 50)
            print("📊 导入完成统计：")
            print(f"建筑数量: {building_count}")
            print(f"设备数量: {meter_count}")
            print(f"能耗数据: {energy_count} 条")
            print("=" * 50)

    pool.close()
    await pool.wait_closed()


if __name__ == "__main__":
    csv_file = "building_energy_dataset2.csv"
    if os.path.exists(csv_file):
        # 注意：函数名是 import_csv_to_mysql，不是 import_csv_to_db
        asyncio.run(import_csv_to_mysql(csv_file))
    else:
        print(f"❌ 文件不存在: {csv_file}")
        print("请确保 building_energy_dataset2.csv 文件在当前目录下")