# test_connection.py
import socket
import requests

# 测试本地端口
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
result = sock.connect_ex(('localhost', 8000))
if result == 0:
    print("✅ 端口 8000 正在监听")
else:
    print("❌ 端口 8000 没有监听")

# 测试根路径
try:
    r = requests.get("http://localhost:8000/", timeout=5)
    print(f"✅ 根路径响应: {r.status_code}")
    print(r.json())
except Exception as e:
    print(f"❌ 根路径请求失败: {e}")