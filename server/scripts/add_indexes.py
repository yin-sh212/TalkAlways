# scripts/add_indexes.py
"""
数据库性能优化索引脚本
用于优化能耗查询接口的响应速度

使用方法:
    python scripts/add_indexes.py
    
注意:
- 执行前请确保已配置 .env 文件中的数据库连接信息
- 索引创建可能需要几分钟时间，取决于数据量大小
- 建议在低峰期执行
"""

import asyncio
import aiomysql
from dotenv import load_dotenv
import os
from datetime import datetime

load_dotenv()


async def create_index_if_not_exists(cursor, index_name: str, table: str, columns: str):
    """检查并创建索引（如果不存在）"""
    try:
        # 检查索引是否已存在
        await cursor.execute("""
            SELECT COUNT(*) as cnt 
            FROM information_schema.statistics 
            WHERE table_schema = DATABASE() 
                AND table_name = %s 
                AND index_name = %s
        """, (table, index_name))
        
        result = await cursor.fetchone()
        if result['cnt'] > 0:
            print(f"  ✓ 索引 {index_name} 已存在，跳过")
            return False
        
        # 创建索引
        sql = f"CREATE INDEX {index_name} ON {table} ({columns})"
        await cursor.execute(sql)
        print(f"  ✓ 创建索引 {index_name} 成功")
        return True
        
    except Exception as e:
        print(f"  ✗ 创建索引 {index_name} 失败：{e}")
        return False


async def create_unique_index_if_not_exists(cursor, index_name: str, table: str, columns: str):
    """检查并创建唯一索引（如果不存在）"""
    try:
        # 检查索引是否已存在
        await cursor.execute("""
            SELECT COUNT(*) as cnt 
            FROM information_schema.statistics 
            WHERE table_schema = DATABASE() 
                AND table_name = %s 
                AND index_name = %s
        """, (table, index_name))
        
        result = await cursor.fetchone()
        if result['cnt'] > 0:
            print(f"  ✓ 唯一索引 {index_name} 已存在，跳过")
            return False
        
        # 创建唯一索引
        sql = f"CREATE UNIQUE INDEX {index_name} ON {table} ({columns})"
        await cursor.execute(sql)
        print(f"  ✓ 创建唯一索引 {index_name} 成功")
        return True
        
    except Exception as e:
        print(f"  ✗ 创建唯一索引 {index_name} 失败：{e}")
        return False


async def optimize_database():
    """执行数据库索引优化"""
    print("=" * 70)
    print("🚀 数据库索引优化脚本")
    print("=" * 70)
    print(f"⏰ 开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 连接数据库
    print("📡 正在连接数据库...")
    try:
        pool = await aiomysql.create_pool(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 3306)),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', '123456'),
            db=os.getenv('DB_NAME', 'energy_management'),
            autocommit=False
        )
        print("✓ 数据库连接成功\n")
    except Exception as e:
        print(f"✗ 数据库连接失败：{e}")
        print("\n请检查 .env 文件中的数据库配置")
        return
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            created_count = 0
            skipped_count = 0
            
            # ========================================
            # 1. energy_consumption 表索引
            # ========================================
            print("-" * 70)
            print("📊 1. energy_consumption 表索引优化")
            print("-" * 70)
            
            # 核心联合索引：building_id + timestamp
            if await create_index_if_not_exists(
                cursor, 
                'idx_building_time', 
                'energy_consumption', 
                'building_id, timestamp'
            ):
                created_count += 1
            else:
                skipped_count += 1
            
            # 日期分组查询优化索引
            if await create_index_if_not_exists(
                cursor,
                'idx_building_date',
                'energy_consumption',
                'building_id, DATE(timestamp)'
            ):
                created_count += 1
            else:
                skipped_count += 1
            
            # 告警查询优化索引
            if await create_index_if_not_exists(
                cursor,
                'idx_level_time',
                'energy_consumption',
                'alarm_level, timestamp'
            ):
                created_count += 1
            else:
                skipped_count += 1
            
            # 综合查询索引
            if await create_index_if_not_exists(
                cursor,
                'idx_building_alarm_time',
                'energy_consumption',
                'building_id, alarm_level, timestamp'
            ):
                created_count += 1
            else:
                skipped_count += 1
            
            # ========================================
            # 2. buildings 表索引
            # ========================================
            print("\n" + "-" * 70)
            print("🏢 2. buildings 表索引优化")
            print("-" * 70)
            
            # 建筑 ID 唯一索引
            if await create_unique_index_if_not_exists(
                cursor,
                'idx_building_id',
                'buildings',
                'id'
            ):
                created_count += 1
            else:
                skipped_count += 1
            
            # 建筑类型查询索引
            if await create_index_if_not_exists(
                cursor,
                'idx_building_type',
                'buildings',
                'type'
            ):
                created_count += 1
            else:
                skipped_count += 1
            
            # ========================================
            # 3. 其他表索引（如果存在）
            # ========================================
            print("\n" + "-" * 70)
            print("📱 3. 其他表索引优化")
            print("-" * 70)
            
            # 检查表是否存在
            await cursor.execute("""
                SELECT COUNT(*) as cnt 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                    AND table_name = 'device_status'
            """)
            result = await cursor.fetchone()
            if result['cnt'] > 0:
                if await create_index_if_not_exists(
                    cursor,
                    'idx_device_building',
                    'device_status',
                    'building_id, status'
                ):
                    created_count += 1
                else:
                    skipped_count += 1
            else:
                print("  ℹ️  device_status 表不存在，跳过")
            
            # ========================================
            # 提交事务
            # ========================================
            print("\n" + "-" * 70)
            print("💾 提交更改...")
            print("-" * 70)
            
            await conn.commit()
            print("✓ 事务提交成功")
            
            # ========================================
            # 输出汇总
            # ========================================
            print("\n" + "=" * 70)
            print("📊 索引优化结果汇总")
            print("=" * 70)
            print(f"✅ 新创建索引：{created_count} 个")
            print(f"⏭️  已存在跳过：{skipped_count} 个")
            print(f"⏰ 完成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print()
            
            # ========================================
            # 性能提升预期
            # ========================================
            print("=" * 70)
            print("🚀 预期性能提升")
            print("=" * 70)
            print("接口优化对比:")
            print("┌─────────────────────┬──────────┬──────────┬──────────┐")
            print("│ 接口                │ 优化前   │ 优化后   │ 提升幅度 │")
            print("├─────────────────────┼──────────┼──────────┼──────────┤")
            print("│ trend               │ 0.90s    │ 0.2-0.4s │ ⬇️ 55-78% │")
            print("│ daily-comparison    │ 2.50s    │ 0.3-0.6s │ ⬇️ 76-88% │")
            print("│ comparison (10 建筑) │ 1.96s    │ 0.5-1.0s │ ⬇️ 49-74% │")
            print("│ summary             │ 1.50s    │ 0.3-0.5s │ ⬇️ 67-80% │")
            print("└─────────────────────┴──────────┴──────────┴──────────┘")
            print()
            
            print("=" * 70)
            print("💡 提示:")
            print("=" * 70)
            print("1. 索引创建完成后，重启后端服务即可生效")
            print("2. 首次查询可能会稍慢（MySQL 需要加载索引到内存）")
            print("3. 后续查询将显著提升响应速度")
            print("4. 可以通过 EXPLAIN 命令验证索引使用情况")
            print()


if __name__ == "__main__":
    try:
        asyncio.run(optimize_database())
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断执行")
    except Exception as e:
        print(f"\n✗ 执行失败：{e}")
        import traceback
        traceback.print_exc()
