# check_fonts.py
import os

# Windows常见中文字体路径
font_paths = [
    "C:/Windows/Fonts/simhei.ttf",   # 黑体
    "C:/Windows/Fonts/simsun.ttc",   # 宋体
    "C:/Windows/Fonts/msyh.ttc",     # 微软雅黑
    "C:/Windows/Fonts/msyhbd.ttc",   # 微软雅黑粗体
    "C:/Windows/Fonts/simkai.ttf",   # 楷体
    "C:/Windows/Fonts/fangsong.ttf", # 仿宋
    "C:/Windows/Fonts/STSONG.TTF",   # 华文宋体
    "C:/Windows/Fonts/STKAITI.TTF",  # 华文楷体
]

print("检查系统字体文件：")
print("-" * 50)

found_fonts = []
for font_path in font_paths:
    if os.path.exists(font_path):
        size = os.path.getsize(font_path) / 1024  # KB
        print(f"✅ {font_path} (大小: {size:.1f} KB)")
        found_fonts.append(font_path)
    else:
        print(f"❌ {font_path}")

print("-" * 50)
if found_fonts:
    print(f"\n找到 {len(found_fonts)} 个中文字体，可以使用")
    print(f"推荐使用: {found_fonts[0]}")
else:
    print("\n⚠️ 未找到中文字体文件")