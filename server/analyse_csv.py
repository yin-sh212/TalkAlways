# analyze_csv.py
import pandas as pd

# 读取CSV
df = pd.read_csv('building_energy_dataset2.csv', encoding='utf-8')

print("📊 CSV文件信息：")
print(f"行数: {len(df)}")
print(f"列数: {len(df.columns)}")
print("\n列名:")
for col in df.columns:
    print(f"  - {col}")

print("\n前3行数据:")
print(df.head(3).to_string())

print("\n数据统计:")
print(df.describe())