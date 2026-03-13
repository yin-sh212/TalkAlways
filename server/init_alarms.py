# init_alarms.py
import asyncio
import random
from datetime import datetime, timedelta
from app.database.db import Database
from app.config import config
import aiomysql


async def init_alarm_tables():
    """初始化告警表和字典数据"""

    # 创建表（如果不存在）
    create_tables_sql = """
    -- 告警记录表
    CREATE TABLE IF NOT EXISTS alarms (
        id INT AUTO_INCREMENT PRIMARY KEY COMMENT '告警ID',
        building_id VARCHAR(50) NOT NULL COMMENT '建筑编号',
        meter_id VARCHAR(50) COMMENT '设备编号',
        alarm_type VARCHAR(50) NOT NULL COMMENT '告警类型：equipment/energy/environment',
        alarm_level INT NOT NULL COMMENT '告警级别：1-严重/2-警告/3-提示',
        description TEXT COMMENT '告警描述',
        start_time DATETIME NOT NULL COMMENT '告警开始时间',
        end_time DATETIME COMMENT '告警结束时间（解决后）',
        status VARCHAR(20) DEFAULT 'pending' COMMENT '状态：pending/confirmed/resolved',
        value FLOAT COMMENT '触发告警的数值',
        threshold FLOAT COMMENT '告警阈值',
        solution TEXT COMMENT '解决方案',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_building (building_id),
        INDEX idx_status (status),
        INDEX idx_time (start_time)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='告警记录表';

    -- 告警类型字典表
    CREATE TABLE IF NOT EXISTS alarm_types (
        code VARCHAR(50) PRIMARY KEY COMMENT '类型代码',
        name VARCHAR(100) NOT NULL COMMENT '类型名称',
        description VARCHAR(255) COMMENT '描述',
        sort_order INT DEFAULT 0 COMMENT '排序'
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='告警类型字典';

    -- 告警级别字典表
    CREATE TABLE IF NOT EXISTS alarm_levels (
        level INT PRIMARY KEY COMMENT '级别数值',
        name VARCHAR(50) NOT NULL COMMENT '级别名称',
        color VARCHAR(20) COMMENT '前端显示颜色',
        description VARCHAR(255) COMMENT '描述'
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='告警级别字典';
    """

    # 先获取连接池
    pool = await Database.get_pool()

    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # 执行建表语句
            for sql in create_tables_sql.split(';'):
                if sql.strip():
                    await cursor.execute(sql)
            print("✅ 告警表创建成功")

            # 初始化字典数据
            # 清空现有数据
            await cursor.execute("DELETE FROM alarm_types")
            await cursor.execute("DELETE FROM alarm_levels")

            # 插入告警类型
            await cursor.executemany(
                "INSERT INTO alarm_types (code, name, description, sort_order) VALUES (%s, %s, %s, %s)",
                [
                    ('equipment', '设备告警', '设备运行异常', 1),
                    ('energy', '能耗告警', '能耗数据异常', 2),
                    ('environment', '环境告警', '环境参数异常', 3)
                ]
            )

            # 插入告警级别
            await cursor.executemany(
                "INSERT INTO alarm_levels (level, name, color, description) VALUES (%s, %s, %s, %s)",
                [
                    (1, '严重', 'red', '需要立即处理'),
                    (2, '警告', 'orange', '需要关注'),
                    (3, '提示', 'blue', '仅供参考')
                ]
            )

            await conn.commit()
            print("✅ 字典数据初始化成功")


async def generate_sample_alarms():
    """生成示例告警数据（用于测试）"""

    pool = await Database.get_pool()

    # 先清空现有告警
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("DELETE FROM alarms")
            await conn.commit()

    # 查询所有建筑
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT id FROM buildings")
            buildings = await cursor.fetchall()

    if not buildings:
        print("⚠️ 没有找到建筑数据，请先初始化 buildings 表")
        return

    alarms = []
    status_list = ['pending', 'confirmed', 'resolved']
    types = ['equipment', 'energy', 'environment']

    for building in buildings:
        building_id = building[0]  # 根据实际情况调整索引
        # 每个建筑生成5-10条告警
        for _ in range(random.randint(5, 10)):
            start_time = datetime.now() - timedelta(days=random.randint(0, 30), hours=random.randint(0, 23))
            status = random.choice(status_list)

            # 如果是resolved状态，设置结束时间
            end_time = None
            if status == 'resolved':
                end_time = start_time + timedelta(hours=random.randint(1, 48))

            alarm = (
                building_id,
                f"{building_id}_M1",  # 随机设备
                random.choice(types),
                random.randint(1, 3),
                f"示例告警描述 {random.randint(1000, 9999)}",
                start_time.strftime('%Y-%m-%d %H:%M:%S'),
                end_time.strftime('%Y-%m-%d %H:%M:%S') if end_time else None,
                status,
                round(random.uniform(50, 500), 2),
                round(random.uniform(100, 300), 2),
                f"解决方案示例 {random.randint(1, 5)}"
            )
            alarms.append(alarm)

    # 批量插入
    if alarms:
        sql = """
            INSERT INTO alarms 
            (building_id, meter_id, alarm_type, alarm_level, description, 
             start_time, end_time, status, value, threshold, solution)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.executemany(sql, alarms)
                await conn.commit()

        print(f"✅ 生成 {len(alarms)} 条示例告警数据")
    else:
        print("⚠️ 没有生成告警数据")


async def main():
    print("🚀 开始初始化告警系统...")
    await init_alarm_tables()
    await generate_sample_alarms()
    print("🎉 告警系统初始化完成！")


if __name__ == "__main__":
    asyncio.run(main())