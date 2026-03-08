# app/api/auth_api.py
from fastapi import APIRouter, HTTPException, Depends, Header
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta
from typing import Optional, Dict
import jwt
import re
from pydantic import BaseModel

router = APIRouter(prefix="/api/auth", tags=["认证"])

# 配置
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# 模拟用户数据库
fake_users_db = {
    "13800138000": {
        "phone": "13800138000",
        "email": "test@example.com",
        "password": "123456",
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
    account: str
    password: str
    login_type: Optional[str] = "auto"


class UserResponse(BaseModel):
    user_id: str
    name: str
    phone: str
    email: str


def validate_phone(phone: str) -> bool:
    pattern = r'^1[3-9]\d{9}$'
    return re.match(pattern, phone) is not None


def validate_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def authenticate_user(account: str, password: str) -> Optional[Dict]:
    if account in fake_users_db and fake_users_db[account]["password"] == password:
        return fake_users_db[account]
    for user in fake_users_db.values():
        if (user["phone"] == account or user["email"] == account) and user["password"] == password:
            return user
    return None


def create_access_token(data: Dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(authorization: str = Header(None)) -> Dict:
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
        for user in fake_users_db.values():
            if user["user_id"] == user_id:
                return user
        raise HTTPException(status_code=401, detail="用户不存在")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="token已过期")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="无效的token")


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={
        200: {
            "description": "登录成功",
            "content": {
                "application/json": {
                    "examples": {
                        "phone_login": {
                            "summary": "手机号登录",
                            "value": {
                                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJVMD...",
                                "token_type": "bearer",
                                "expires_in": 1800,
                                "user_info": {
                                    "user_id": "U001",
                                    "name": "测试用户",
                                    "phone": "13800138000",
                                    "email": "test@example.com"
                                }
                            }
                        },
                        "email_login": {
                            "summary": "邮箱登录",
                            "value": {
                                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJVMD...",
                                "token_type": "bearer",
                                "expires_in": 1800,
                                "user_info": {
                                    "user_id": "U001",
                                    "name": "测试用户",
                                    "phone": "13800138000",
                                    "email": "test@example.com"
                                }
                            }
                        }
                    }
                }
            }
        },
        400: {
            "description": "请求参数错误",
            "content": {
                "application/json": {
                    "example": {"detail": "账号格式不正确（应为手机号或邮箱）"}
                }
            }
        },
        401: {
            "description": "认证失败",
            "content": {
                "application/json": {
                    "example": {"detail": "账号或密码错误"}
                }
            }
        }
    }
)
async def login(request: LoginRequest):
    """用户登录（支持手机号/邮箱）"""
    if not request.account or not request.password:
        raise HTTPException(status_code=400, detail="账号和密码不能为空")

    login_type = request.login_type
    if login_type == "auto":
        if validate_phone(request.account):
            login_type = "phone"
        elif validate_email(request.account):
            login_type = "email"
        else:
            raise HTTPException(status_code=400, detail="账号格式不正确（应为手机号或邮箱）")

    user = authenticate_user(request.account, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="账号或密码错误")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["user_id"], "account": request.account},
        expires_delta=access_token_expires
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_info={
            "user_id": user["user_id"],
            "name": user["name"],
            "phone": user["phone"],
            "email": user["email"]
        }
    )


@router.post(
    "/logout",
    responses={
        200: {
            "description": "退出成功",
            "content": {
                "application/json": {
                    "example": {"message": "退出成功"}
                }
            }
        }
    }
)
async def logout(current_user: dict = Depends(get_current_user)):
    """退出登录"""
    return {"message": "退出成功"}


@router.get(
    "/me",
    response_model=UserResponse,
    responses={
        200: {
            "description": "成功获取用户信息",
            "content": {
                "application/json": {
                    "example": {
                        "user_id": "U001",
                        "name": "测试用户",
                        "phone": "13800138000",
                        "email": "test@example.com"
                    }
                }
            }
        },
        401: {
            "description": "未认证",
            "content": {
                "application/json": {
                    "example": {"detail": "未提供认证信息"}
                }
            }
        }
    }
)
async def get_me(current_user: dict = Depends(get_current_user)):
    """获取当前用户信息"""
    return {
        "user_id": current_user["user_id"],
        "name": current_user["name"],
        "phone": current_user["phone"],
        "email": current_user["email"]
    }


@router.post(
    "/register",
    responses={
        200: {
            "description": "注册成功",
            "content": {
                "application/json": {
                    "example": {"message": "注册成功", "account": "13800138000"}
                }
            }
        },
        400: {
            "description": "参数错误",
            "content": {
                "application/json": {
                    "examples": {
                        "missing": {"value": {"detail": "手机号或邮箱至少填一个"}},
                        "invalid_phone": {"value": {"detail": "手机号格式不正确"}},
                        "invalid_email": {"value": {"detail": "邮箱格式不正确"}}
                    }
                }
            }
        }
    }
)
async def register(
        phone: Optional[str] = None,
        email: Optional[str] = None,
        password: str = None,
        name: str = None
):
    """用户注册（简化版）"""
    if not phone and not email:
        raise HTTPException(status_code=400, detail="手机号或邮箱至少填一个")

    if phone and not validate_phone(phone):
        raise HTTPException(status_code=400, detail="手机号格式不正确")

    if email and not validate_email(email):
        raise HTTPException(status_code=400, detail="邮箱格式不正确")

    return {"message": "注册成功（演示版）", "account": phone or email}