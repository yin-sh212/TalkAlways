"""
测试CAD上传接口 - 生成简单DXF文件
"""
import ezdxf

# 创建DXF文档
doc = ezdxf.new('R2010')
msp = doc.modelspace()

# 添加一些简单的几何图形
# 矩形
msp.add_lwpolyline([(0, 0), (100, 0), (100, 80), (0, 80), (0, 0)])

# 内部房间
msp.add_lwpolyline([(10, 10), (45, 10), (45, 35), (10, 35), (10, 10)])
msp.add_lwpolyline([(55, 10), (90, 10), (90, 35), (55, 35), (55, 10)])
msp.add_lwpolyline([(10, 45), (45, 45), (45, 70), (10, 70), (10, 45)])
msp.add_lwpolyline([(55, 45), (90, 45), (90, 70), (55, 70), (55, 45)])

# 圆形（柱子）
msp.add_circle((25, 22.5), 3)
msp.add_circle((72.5, 22.5), 3)
msp.add_circle((25, 57.5), 3)
msp.add_circle((72.5, 57.5), 3)

# 保存
doc.saveas('test_floor.dxf')
print("✅ 测试DXF文件已生成: test_floor.dxf")
