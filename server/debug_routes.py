# debug_routes.py
import sys
sys.path.append('.')

from app.main import app

print("="*50)
print("所有已注册路由：")
print("="*50)

for route in app.routes:
    if hasattr(route, 'methods'):
        methods = ', '.join(route.methods)
        print(f"{methods:20} {route.path}")
    else:
        print(f"{'':20} {route.path}")

print("="*50)
print(f"总共 {len(app.routes)} 个路由")