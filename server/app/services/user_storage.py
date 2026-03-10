# app/services/user_storage.py
import json
import os
from typing import Dict, Optional

# 用户数据文件路径
USER_DATA_FILE = "data/users.json"

def ensure_data_dir():
    """确保data目录存在"""
    os.makedirs("data", exist_ok=True)

def load_users() -> Dict:
    """从文件加载用户数据"""
    ensure_data_dir()
    if os.path.exists(USER_DATA_FILE):
        try:
            with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return get_default_users()
    return get_default_users()

def save_users(users: Dict):
    """保存用户数据到文件"""
    ensure_data_dir()
    with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def get_default_users() -> Dict:
    """获取默认用户数据"""
    return {
        "testuser": {
            "user_id": "U001",
            "username": "testuser",
            "phone": "13800138000",
            "password": "123456",
            "name": "测试用户",
            "created_at": "2025-01-01 00:00:00"
        },
        "13800138000": {
            "user_id": "U001",
            "username": "testuser",
            "phone": "13800138000",
            "password": "123456",
            "name": "测试用户",
            "created_at": "2025-01-01 00:00:00"
        }
    }