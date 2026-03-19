# scripts/import_to_db.py
import json
import asyncio
import aiomysql
from dotenv import load_dotenv
import os

load_dotenv()


async def import_to_mysql(json_file: str):
    """
    将JSON文件导入MySQL
    """
    print(f"\n📦 开始导入: {json_file}")

    # 1. 读取JSON
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"  共 {len(data)} 条知识")

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

            # 3. 清空旧数据（可选）
            await cursor.execute("TRUNCATE TABLE knowledge_base")
            print("  已清空旧数据")

            # 4. 批量插入
            inserted = 0
            for item in data:
                sql = """
                    INSERT INTO knowledge_base 
                    (title, content, category, tags, source_file, chunk_index, char_count)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                try:
                    await cursor.execute(sql, (
                        item.get('title', ''),
                        item.get('content', ''),
                        item.get('category', '其他'),
                        item.get('tags', ''),
                        item.get('source_file', ''),
                        item.get('chunk_index', 0),
                        item.get('char_count', 0)
                    ))
                    inserted += 1
                except Exception as e:
                    print(f"    ❌ 插入失败: {e}")

            await conn.commit()
            print(f"  ✅ 成功导入 {inserted} 条")

    pool.close()
    await pool.wait_closed()


async def main():
    # 导入两个文件
    json_files = [
        "../data/knowledge/故障指南文档_structured.json",
        "../data/knowledge/建筑能源系统智能运维手册_structured.json"
    ]

    for json_file in json_files:
        if os.path.exists(json_file):
            await import_to_mysql(json_file)
        else:
            print(f"⚠️ 文件不存在: {json_file}")


if __name__ == "__main__":
    asyncio.run(main())