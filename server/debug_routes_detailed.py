# debug_routes_detailed.py
import sys
sys.path.append('.')

from app.main import app

print("="*60)
print("详细路由信息：")
print("="*60)

found_auth = False
for route in app.routes:
    if hasattr(route, 'methods') and '/api/auth' in str(route.path):
        found_auth = True
        methods = ', '.join(route.methods)
        print(f"✅ {methods:20} {route.path}")
        print(f"   名称: {route.name}")
        print(f"   端点: {route.endpoint}")
        print()

if not found_auth:
    print("❌ 没有找到任何 /api/auth 路由")

print("="*60)