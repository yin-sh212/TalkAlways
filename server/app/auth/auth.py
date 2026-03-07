# app/auth/auth.py
from datetime import datetime, timedelta
from typing import Optional, Dict
import jwt
import re
from fastapi import HTTPException, Depends, Header
from pydantic import BaseModel

# 配置（生产环境应放在.env）
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# 模拟用户数据库（实际应用应改用真实数据库）
fake_users_db = {
    "13800138000": {
        "phone": "13800138000",
        "email": "test@example.com",
        "password": "123456",  # 实际应用应存哈希值
        "user_id": "U001",
        "name": "测试用户"
    },
    "test@example.com": {
        "phone": "13800138000",
        "email": "test@example.com",
        "password": "123456",
        "user_id": "U001",
        "name": "测试用户"
    }
}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user_info: Dict


class LoginRequest(BaseModel):
    account: str  # 手机号或邮箱
    password: str
    login_type: Optional[str] = "auto"  # phone/email/auto


def validate_phone(phone: str) -> bool:
    """验证手机号格式"""
    pattern = r'^1[3-9]\d{9}$'
    return re.match(pattern, phone) is not None


def validate_email(email: str) -> bool:
    """验证邮箱格式"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def authenticate_user(account: str, password: str) -> Optional[Dict]:
    """验证用户"""
    # 直接匹配
    if account in fake_users_db:
        user = fake_users_db[account]
        if user["password"] == password:
            return user

    # 尝试用手机号匹配
    for uid, user in fake_users_db.items():
        if user["phone"] == account or user["email"] == account:
            if user["password"] == password:
                return user

    return None


def create_access_token(data: Dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建JWT token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(authorization: str = Header(None)) -> Dict:
    """获取当前用户（依赖项）"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未提供认证信息")

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="认证方案错误")

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="无效的token")

        # 查找用户
        for user in fake_users_db.values():
            if user["user_id"] == user_id:
                return user

        raise HTTPException(status_code=401, detail="用户不存在")

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="token已过期")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="无效的token")
    except ValueError:
        raise HTTPException(status_code=401, detail="无效的认证头")