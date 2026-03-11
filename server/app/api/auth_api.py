# app/api/auth_api.py
from fastapi import APIRouter, HTTPException, Depends, Header, Body
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta
from typing import Optional, Dict
import jwt
import re
from pydantic import BaseModel, Field
# from app.services.sms_tencent import tencent_sms
from app.services.sms_aliyun import aliyun_sms as sms_service
import random
import time
import redis
import os
from dotenv import load_dotenv

from app.services.user_storage import load_users, save_users

load_dotenv()

router = APIRouter(prefix="/api/auth", tags=["认证"])

# ==================== 配置 ====================
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

'''
# Redis连接（用于存储验证码）
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
try:
    import redis.asyncio as redis

    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    REDIS_AVAILABLE = True
    print("✅ Redis连接成功")
except:
    REDIS_AVAILABLE = False
    print("⚠️ Redis未连接，使用内存存储验证码（仅用于开发）")
    # 内存存储（开发环境备用）
    code_storage = {}
'''

# 强制使用内存存储（开发环境）
REDIS_AVAILABLE = False
print("⚠️ 使用内存存储验证码（仅用于开发）")
code_storage = {}

# ==================== 数据模型 ====================

# ✅ 注释掉 TokenResponse，因为现在统一用 {code, message, data} 格式
# class TokenResponse(BaseModel):
#     """登录响应"""
#     access_token: str
#     token_type: str
#     expires_in: int
#     user_info: Dict


class LoginRequest(BaseModel):
    """用户名密码登录请求"""
    username: str = Field(..., description="用户名/手机号")
    password: str = Field(..., description="密码")


class CodeLoginRequest(BaseModel):
    """验证码登录请求"""
    phone: str = Field(..., description="手机号", pattern=r'^1[3-9]\d{9}$')
    code: str = Field(..., description="验证码", min_length=6, max_length=6)


class SendCodeRequest(BaseModel):
    """发送验证码请求"""
    phone: str = Field(..., description="手机号", pattern=r'^1[3-9]\d{9}$')


class VerifyCodeRequest(BaseModel):
    """验证验证码请求"""
    phone: str = Field(..., description="手机号", pattern=r'^1[3-9]\d{9}$')
    code: str = Field(..., description="验证码", min_length=6, max_length=6)


class RegisterRequest(BaseModel):
    """注册请求"""
    username: str = Field(..., description="用户名", min_length=2, max_length=20)
    phone: str = Field(..., description="手机号", pattern=r'^1[3-9]\d{9}$')
    code: str = Field(..., description="验证码", min_length=6, max_length=6)
    password: str = Field(..., description="密码", min_length=6, max_length=20)


class UserResponse(BaseModel):
    """用户信息响应"""
    user_id: str
    username: str
    phone: str
    created_at: Optional[str] = None


# ==================== 模拟用户数据库 ====================
'''
fake_users_db = {
    "testuser": {
        "user_id": "U001",
        "username": "testuser",
        "phone": "13800138000",
        "password": "123456",  # 实际应用应存储哈希值
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
'''

fake_users_db = load_users()
print(f"📁 已加载 {len(fake_users_db)} 个用户")

# ==================== 工具函数 ====================

def validate_phone(phone: str) -> bool:
    """验证手机号格式"""
    pattern = r'^1[3-9]\d{9}$'
    return re.match(pattern, phone) is not None


def validate_username(username: str) -> bool:
    """验证用户名格式（字母数字下划线，2-20位）"""
    pattern = r'^[a-zA-Z0-9_]{2,20}$'
    return re.match(pattern, username) is not None


def authenticate_user(username: str, password: str) -> Optional[Dict]:
    """验证用户名密码"""
    # 直接匹配用户名
    if username in fake_users_db and fake_users_db[username]["password"] == password:
        return fake_users_db[username]

    # 用手机号匹配
    for user in fake_users_db.values():
        if user["phone"] == username and user["password"] == password:
            return user

    return None


def get_user_by_phone(phone: str) -> Optional[Dict]:
    """根据手机号获取用户"""
    for user in fake_users_db.values():
        if user["phone"] == phone:
            return user
    return None


def create_user(username: str, phone: str, password: str) -> Dict:
    """创建新用户"""
    # 计算新的user_id
    existing_ids = set()
    for user in fake_users_db.values():
        if isinstance(user, dict) and "user_id" in user:
            existing_ids.add(user["user_id"])

    # 生成新的user_id (U001, U002, ...)
    for i in range(1, 1000):
        user_id = f"U{i:03d}"
        if user_id not in existing_ids:
            break

    user = {
        "user_id": user_id,
        "username": username,
        "phone": phone,
        "password": password,  # 实际应用应存储哈希值
        "name": username,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    # 同时用用户名和手机号作为key存储
    fake_users_db[username] = user
    fake_users_db[phone] = user

    # 保存到文件
    save_users(fake_users_db)
    print(f"💾 用户 {username} 已保存到文件")

    return user


def create_access_token(data: Dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建JWT token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


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


# ==================== 验证码相关函数 ====================

async def store_code(phone: str, code: str, expire_seconds: int = 300):
    """存储验证码（5分钟有效）"""
    #if REDIS_AVAILABLE:
        #await redis_client.setex(f"sms:{phone}", expire_seconds, code)
    #else:
    code_storage[phone] = {
        "code": code,
        "expire_time": time.time() + expire_seconds
        }
    print(f"📱 验证码已存储: {phone} -> {code}")


async def verify_code(phone: str, input_code: str) -> bool:
    """验证验证码"""
    #if REDIS_AVAILABLE:
        #stored_code = await redis_client.get(f"sms:{phone}")
        #if stored_code and stored_code == input_code:
            #await redis_client.delete(f"sms:{phone}")
            #return True
    #else:
    stored = code_storage.get(phone)
    if stored and stored["code"] == input_code and stored["expire_time"] > time.time():
        del code_storage[phone]
        return True
    return False


def generate_code(length: int = 6) -> str:
    """生成6位随机验证码"""
    return ''.join([str(random.randint(0, 9)) for _ in range(length)])


# ==================== 验证码接口 ====================

@router.post(
    "/send-code",
    responses={
        200: {
            "description": "验证码发送成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "验证码发送成功",
                        "data": {
                            "phone": "138****8000",
                            "expire_in": 300
                        }
                    }
                }
            }
        },
        400: {
            "description": "参数错误",
            "content": {
                "application/json": {
                    "example": {
                        "code": 400,
                        "message": "手机号格式不正确",
                        "data": None
                    }
                }
            }
        },
        429: {
            "description": "发送太频繁",
            "content": {
                "application/json": {
                    "example": {
                        "code": 429,
                        "message": "发送太频繁，请稍后再试",
                        "data": None
                    }
                }
            }
        }
    }
)
async def send_verification_code(request: SendCodeRequest):
    """
    发送短信验证码

    流程：
    1. 验证手机号格式
    2. 检查发送频率（1分钟内不能重复发送）
    3. 生成6位随机验证码
    4. 存储到Redis（5分钟有效）
    5. 调用腾讯云短信服务发送
    """
    # 1. 验证手机号
    if not validate_phone(request.phone):
        return {
            "code": 400,
            "message": "手机号格式不正确",
            "data": None
        }

    # 2. 检查发送频率（防止刷短信）
    # 2. 检查发送频率（防止刷短信）- 内存版
    import time
    # 用内存记录最后发送时间
    if "last_send_time" not in code_storage:
        code_storage["last_send_time"] = {}

    last_send = code_storage["last_send_time"].get(request.phone, 0)
    if time.time() - last_send < 60:
        return {
            "code": 429,
            "message": "发送太频繁，请稍后再试",
            "data": None
        }
    code_storage["last_send_time"][request.phone] = time.time()

    # 3. 生成验证码
    code = generate_code()

    # 4. 存储验证码
    await store_code(request.phone, code)

    # 5. 调用腾讯云短信发送
    success = sms_service.send_sms(request.phone, code)

    if not success:
        return {
            "code": 500,
            "message": "短信发送失败，请稍后重试",
            "data": None
        }

    # 6. 返回成功（隐藏完整手机号）
    masked_phone = request.phone[:3] + "****" + request.phone[7:]

    return {
        "code": 200,
        "message": "验证码发送成功",
        "data": {
            "phone": masked_phone,
            "expire_in": 300
        }
    }


@router.post(
    "/verify-code",
    responses={
        200: {
            "description": "验证成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "验证成功",
                        "data": {
                            "verified": True
                        }
                    }
                }
            }
        },
        400: {
            "description": "验证码错误或过期",
            "content": {
                "application/json": {
                    "example": {
                        "code": 400,
                        "message": "验证码错误或已过期",
                        "data": None
                    }
                }
            }
        }
    }
)
async def verify_verification_code(request: VerifyCodeRequest):
    """验证短信验证码"""
    if not validate_phone(request.phone):
        return {
            "code": 400,
            "message": "手机号格式不正确",
            "data": None
        }

    if await verify_code(request.phone, request.code):
        return {
            "code": 200,
            "message": "验证成功",
            "data": {
                "verified": True
            }
        }
    else:
        return {
            "code": 400,
            "message": "验证码错误或已过期",
            "data": None
        }


# ==================== 登录接口 ====================

@router.post(
    "/login",
    # ✅ 去掉 response_model=TokenResponse
    responses={
        200: {
            "description": "登录成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "登录成功",
                        "data": {
                            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "token_type": "bearer",
                            "expires_in": 1800,
                            "user_info": {
                                "user_id": "U001",
                                "username": "testuser",
                                "phone": "13800138000"
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
                    "example": {
                        "code": 400,
                        "message": "用户名和密码不能为空",
                        "data": None
                    }
                }
            }
        },
        401: {
            "description": "认证失败",
            "content": {
                "application/json": {
                    "example": {
                        "code": 401,
                        "message": "用户名或密码错误",
                        "data": None
                    }
                }
            }
        }
    }
)
async def login(request: LoginRequest):
    """
    用户名密码登录

    - username: 用户名或手机号
    - password: 密码
    """
    if not request.username or not request.password:
        return {
            "code": 400,
            "message": "用户名和密码不能为空",
            "data": None
        }

    user = authenticate_user(request.username, request.password)
    if not user:
        return {
            "code": 401,
            "message": "用户名或密码错误",
            "data": None
        }

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["user_id"], "username": user["username"]},
        expires_delta=access_token_expires
    )

    # ✅ 统一返回格式
    return {
        "code": 200,
        "message": "登录成功",
        "data": {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user_info": {
                "user_id": user["user_id"],
                "username": user["username"],
                "phone": user["phone"]
            }
        }
    }


@router.post(
    "/login/code",
    responses={
        200: {
            "description": "登录成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "登录成功",
                        "data": {
                            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "token_type": "bearer",
                            "expires_in": 1800,
                            "user_info": {
                                "user_id": "U001",
                                "username": "testuser",
                                "phone": "13800138000"
                            }
                        }
                    }
                }
            }
        },
        400: {
            "description": "验证码错误",
            "content": {
                "application/json": {
                    "example": {
                        "code": 400,
                        "message": "验证码错误或已过期",
                        "data": None
                    }
                }
            }
        }
    }
)
async def login_with_code(request: CodeLoginRequest):
    """
    验证码登录

    - phone: 手机号
    - code: 验证码
    """
    # 1. 验证手机号
    if not validate_phone(request.phone):
        return {
            "code": 400,
            "message": "手机号格式不正确",
            "data": None
        }

    # 2. 验证验证码
    if not await verify_code(request.phone, request.code):
        return {
            "code": 400,
            "message": "验证码错误或已过期",
            "data": None
        }

    # 3. 查找或创建用户
    user = get_user_by_phone(request.phone)
    if not user:
        username = f"user_{request.phone[-4:]}"
        user = create_user(username, request.phone, "")

    # 4. 创建token
    access_token = create_access_token(
        data={"sub": user["user_id"], "phone": request.phone},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    # 5. 返回成功
    return {
        "code": 200,
        "message": "登录成功",
        "data": {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user_info": {
                "user_id": user["user_id"],
                "username": user["username"],
                "phone": user["phone"]
            }
        }
    }


# ==================== 其他接口 ====================

@router.post(
    "/logout",
    responses={
        200: {
            "description": "退出成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "退出成功",
                        "data": None
                    }
                }
            }
        }
    }
)
async def logout(current_user: dict = Depends(get_current_user)):
    """退出登录"""
    return {
        "code": 200,
        "message": "退出成功",
        "data": None
    }


@router.get(
    "/me",
    # ✅ 去掉 response_model=UserResponse，统一返回格式
    responses={
        200: {
            "description": "成功获取用户信息",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "成功",
                        "data": {
                            "user_id": "U001",
                            "username": "testuser",
                            "phone": "13800138000",
                            "created_at": "2025-01-01 00:00:00"
                        }
                    }
                }
            }
        },
        401: {
            "description": "未认证",
            "content": {
                "application/json": {
                    "example": {
                        "code": 401,
                        "message": "未提供认证信息",
                        "data": None
                    }
                }
            }
        }
    }
)
async def get_me(current_user: dict = Depends(get_current_user)):
    """获取当前用户信息"""
    return {
        "code": 200,
        "message": "成功",
        "data": {
            "user_id": current_user["user_id"],
            "username": current_user["username"],
            "phone": current_user["phone"],
            "created_at": current_user.get("created_at")
        }
    }


@router.post(
    "/register",
    responses={
        200: {
            "description": "注册成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "注册成功",
                        "data": {
                            "user_id": "U002",
                            "username": "newuser",
                            "phone": "13800138001"
                        }
                    }
                }
            }
        },
        400: {
            "description": "参数错误",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_code": {
                            "value": {
                                "code": 400,
                                "message": "验证码错误或已过期",
                                "data": None
                            }
                        },
                        "username_exists": {
                            "value": {
                                "code": 400,
                                "message": "用户名已存在",
                                "data": None
                            }
                        },
                        "phone_exists": {
                            "value": {
                                "code": 400,
                                "message": "手机号已注册",
                                "data": None
                            }
                        },
                        "invalid_phone": {
                            "value": {
                                "code": 400,
                                "message": "手机号格式不正确",
                                "data": None
                            }
                        },
                        "invalid_username": {
                            "value": {
                                "code": 400,
                                "message": "用户名格式不正确（只能包含字母、数字、下划线，2-20位）",
                                "data": None
                            }
                        }
                    }
                }
            }
        }
    }
)
async def register(request: RegisterRequest):
    """
    用户注册

    - username: 用户名（字母数字下划线，2-20位）
    - phone: 手机号
    - code: 验证码（6位数字）
    - password: 密码（6-20位）
    """
    # 1. 验证手机号
    if not validate_phone(request.phone):
        return {
            "code": 400,
            "message": "手机号格式不正确",
            "data": None
        }

    # 2. 验证用户名
    if not validate_username(request.username):
        return {
            "code": 400,
            "message": "用户名格式不正确（只能包含字母、数字、下划线，2-20位）",
            "data": None
        }

    # 3. 验证验证码
    if not await verify_code(request.phone, request.code):
        return {
            "code": 400,
            "message": "验证码错误或已过期",
            "data": None
        }

    # 4. 检查用户名是否已存在
    if request.username in fake_users_db:
        return {
            "code": 400,
            "message": "用户名已存在",
            "data": None
        }

    # 5. 检查手机号是否已注册
    for user in fake_users_db.values():
        if user["phone"] == request.phone:
            return {
                "code": 400,
                "message": "手机号已注册",
                "data": None
            }

    # 6. 创建新用户
    user = create_user(request.username, request.phone, request.password)

    return {
        "code": 200,
        "message": "注册成功",
        "data": {
            "user_id": user["user_id"],
            "username": user["username"],
            "phone": user["phone"]
        }
    }

# ==================== 开发测试接口 ====================

@router.get("/test-code", include_in_schema=False)
async def test_get_code(phone: str):
    """开发环境测试接口：直接返回验证码（仅用于开发）"""
    if not validate_phone(phone):
        return {"code": 400, "message": "手机号格式不正确"}

    code = generate_code()
    await store_code(phone, code)

    return {
        "code": 200,
        "message": "测试验证码",
        "data": {
            "phone": phone,
            "code": code,
            "expire_in": 300
        }
    }


# ==================== GET版本测试接口（临时解决前端405） ====================

@router.get("/send-code", include_in_schema=False)
async def send_code_get(phone: Optional[str] = None):
    """【临时】GET方式发送验证码（仅用于开发测试）"""
    if not phone:
        return {
            "code": 400,
            "message": "请提供手机号参数，例如: /api/auth/send-code?phone=13800138000",
            "data": None
        }

    if not validate_phone(phone):
        return {
            "code": 400,
            "message": "手机号格式不正确",
            "data": None
        }

    # 检查发送频率
    import time
    if "last_send_time" not in code_storage:
        code_storage["last_send_time"] = {}

    last_send = code_storage["last_send_time"].get(phone, 0)
    if time.time() - last_send < 60:
        return {
            "code": 429,
            "message": "发送太频繁，请稍后再试",
            "data": None
        }
    code_storage["last_send_time"][phone] = time.time()

    # 生成验证码
    code = generate_code()
    await store_code(phone, code)

    # 调用腾讯云短信（先注释掉，用mock代替）
    # success = tencent_sms.send_sms(phone, code)
    print(f"\n📨 ===== 模拟发送验证码 ======")
    print(f"📱 手机号: {phone}")
    print(f"🔑 验证码: {code}")
    print(f"========================\n")
    success = True

    if not success:
        return {
            "code": 500,
            "message": "短信发送失败，请稍后重试",
            "data": None
        }

    masked_phone = phone[:3] + "****" + phone[7:]
    return {
        "code": 200,
        "message": "验证码发送成功",
        "data": {
            "phone": masked_phone,
            "expire_in": 300
        }
    }


@router.get("/login/code", include_in_schema=False)
async def login_with_code_get(phone: Optional[str] = None, code: Optional[str] = None):
    """【临时】GET方式验证码登录（仅用于开发测试）"""
    if not phone or not code:
        return {
            "code": 400,
            "message": "请提供手机号和验证码，例如: /api/auth/login/code?phone=13800138000&code=123456",
            "data": None
        }

    # 验证手机号
    if not validate_phone(phone):
        return {
            "code": 400,
            "message": "手机号格式不正确",
            "data": None
        }

    # 验证验证码
    if not await verify_code(phone, code):
        return {
            "code": 400,
            "message": "验证码错误或已过期",
            "data": None
        }

    # 查找或创建用户
    user = get_user_by_phone(phone)
    if not user:
        username = f"user_{phone[-4:]}"
        user = create_user(username, phone, "")

    # 创建token
    access_token = create_access_token(
        data={"sub": user["user_id"], "phone": phone},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    # 注意：这个GET接口暂时还返回TokenResponse，因为是临时测试接口
    return {
        "code": 200,
        "message": "登录成功",
        "data": {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user_info": {
                "user_id": user["user_id"],
                "username": user["username"],
                "phone": user["phone"]
            }
        }
    }
