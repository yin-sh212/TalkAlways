# scripts/process_all.py
import os
import sys
import subprocess


def main():
    """
    一键执行：解析Word → 生成JSON/CSV → 导入MySQL
    """
    print("=" * 60)
    print("🚀 开始处理知识库文档")
    print("=" * 60)

    # 1. 确保目录存在
    os.makedirs("data/knowledge", exist_ok=True)

    # 2. 检查Word文件
    docx_files = [
        "../data/knowledge/故障指南文档.docx",
        "../data/knowledge/建筑能源系统智能运维手册.docx"
    ]

    for f in docx_files:
        if not os.path.exists(f):
            print(f"❌ 文件不存在: {f}")
            print("请将Word文档放到 data/knowledge/ 目录下")
            return

    # 3. 解析Word
    print("\n📝 步骤1: 解析Word文档...")
    from parse_manual import ManualParser
    parser = ManualParser()

    for docx_file in docx_files:
        print(f"\n处理: {os.path.basename(docx_file)}")

        # 解析
        result = parser.parse_file(docx_file)

        # 保存JSON
        json_file = docx_file.replace('.docx', '_structured.json')
        parser.save_to_json(result, json_file)

        # 保存CSV
        csv_file = docx_file.replace('.docx', '_structured.csv')
        parser.save_to_csv(result, csv_file)

    # 4. 导入MySQL
    print("\n📦 步骤2: 导入MySQL...")
    import asyncio
    from import_to_db import main as import_main
    asyncio.run(import_main())

    print("\n" + "=" * 60)
    print("✅ 全部完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()