# app/api/alarm_api.py
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel
from typing import List, Optional, Dict
from app.database.db import Database
from datetime import datetime

router = APIRouter(prefix="/api/alarm", tags=["告警管理"])


# ========== 数据模型 ==========

class AlarmBatchRequest(BaseModel):
    """批量操作请求"""
    alarm_ids: List[int]


class AlarmResponse(BaseModel):
    id: int
    building_id: str
    meter_id: Optional[str]
    alarm_type: str
    alarm_level: int
    description: Optional[str]
    start_time: datetime
    end_time: Optional[datetime]
    status: str
    value: Optional[float]
    threshold: Optional[float]
    solution: Optional[str]


# ========== 批量确认告警 ==========

@router.post(
    "/batch-confirm",
    responses={
        200: {
            "description": "批量确认成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "成功确认 5 条告警",
                        "data": {
                            "confirmed_count": 5,
                            "failed_ids": []
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
                        "message": "告警 ID 列表不能为空",
                        "data": None
                    }
                }
            }
        },
        500: {
            "description": "服务器错误",
            "content": {
                "application/json": {
                    "example": {
                        "code": 500,
                        "message": "数据库更新失败",
                        "data": None
                    }
                }
            }
        }
    }
)
async def batch_confirm_alarms(request: AlarmBatchRequest):
    """
    批量确认告警

    将选中的多条告警状态更新为 "已确认" (confirmed)
    """
    if not request.alarm_ids:
        return {
            "code": 400,
            "message": "告警 ID 列表不能为空",
            "data": None
        }

    try:
        # 构建 SQL，批量更新状态
        placeholders = ','.join(['%s'] * len(request.alarm_ids))
        sql = f"""
            UPDATE alarms 
            SET status = 'confirmed', updated_at = NOW()
            WHERE id IN ({placeholders}) AND status = 'pending'
        """

        async with Database.get_pool() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(sql, request.alarm_ids)
                affected_rows = cursor.rowcount
                await conn.commit()

        # 找出可能失败的 ID（已经是 confirmed/resolved 状态的不会更新）
        failed_ids = []
        if affected_rows < len(request.alarm_ids):
            # 查询未更新的 ID
            check_sql = f"""
                SELECT id FROM alarms 
                WHERE id IN ({placeholders}) AND status != 'pending'
            """
            async with Database.get_pool() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(check_sql, request.alarm_ids)
                    failed = await cursor.fetchall()
                    failed_ids = [f[0] for f in failed]

        return {
            "code": 200,
            "message": f"成功确认 {affected_rows} 条告警",
            "data": {
                "confirmed_count": affected_rows,
                "failed_ids": failed_ids
            }
        }

    except Exception as e:
        return {
            "code": 500,
            "message": f"数据库更新失败：{str(e)}",
            "data": None
        }


# ========== 批量解决告警 ==========

@router.post(
    "/batch-resolve",
    responses={
        200: {
            "description": "批量解决成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "成功解决 3 条告警",
                        "data": {
                            "resolved_count": 3,
                            "failed_ids": []
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
                        "message": "告警ID列表不能为空",
                        "data": None
                    }
                }
            }
        },
        500: {
            "description": "服务器错误",
            "content": {
                "application/json": {
                    "example": {
                        "code": 500,
                        "message": "数据库更新失败",
                        "data": None
                    }
                }
            }
        }
    }
)
async def batch_resolve_alarms(request: AlarmBatchRequest):
    """
    批量解决告警

    将选中的多条告警状态更新为 "已解决" (resolved)，并记录解决时间
    """
    if not request.alarm_ids:
        return {
            "code": 400,
            "message": "告警 ID 列表不能为空",
            "data": None
        }

    try:
        placeholders = ','.join(['%s'] * len(request.alarm_ids))
        sql = f"""
            UPDATE alarms 
            SET status = 'resolved', end_time = NOW(), updated_at = NOW()
            WHERE id IN ({placeholders}) AND status != 'resolved'
        """

        async with Database.get_pool() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(sql, request.alarm_ids)
                affected_rows = cursor.rowcount
                await conn.commit()

        # 找出可能失败的 ID
        failed_ids = []
        if affected_rows < len(request.alarm_ids):
            check_sql = f"""
                SELECT id FROM alarms 
                WHERE id IN ({placeholders}) AND status = 'resolved'
            """
            async with Database.get_pool() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(check_sql, request.alarm_ids)
                    failed = await cursor.fetchall()
                    failed_ids = [f[0] for f in failed]

        return {
            "code": 200,
            "message": f"成功解决 {affected_rows} 条告警",
            "data": {
                "resolved_count": affected_rows,
                "failed_ids": failed_ids
            }
        }

    except Exception as e:
        return {
            "code": 500,
            "message": f"数据库更新失败：{str(e)}",
            "data": None
        }


# ========== 告警类型枚举接口 ==========

@router.get(
    "/dict/alarm-types",
    responses={
        200: {
            "description": "成功获取告警类型列表",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "成功",
                        "data": [
                            {"code": "equipment", "name": "设备告警", "description": "设备运行异常"},
                            {"code": "energy", "name": "能耗告警", "description": "能耗数据异常"},
                            {"code": "environment", "name": "环境告警", "description": "环境参数异常"}
                        ]
                    }
                }
            }
        },
        500: {
            "description": "服务器错误",
            "content": {
                "application/json": {
                    "example": {
                        "code": 500,
                        "message": "查询失败",
                        "data": None
                    }
                }
            }
        }
    }
)
async def get_alarm_types():
    """获取告警类型列表（供前端下拉框使用）"""
    try:
        # 返回固定的告警类型（无需数据库表）
        data = [
            {"code": "equipment", "name": "设备告警", "description": "设备运行异常"},
            {"code": "energy", "name": "能耗告警", "description": "能耗数据异常"},
            {"code": "environment", "name": "环境告警", "description": "环境参数异常"}
        ]

        return {
            "code": 200,
            "message": "成功",
            "data": data
        }
    except Exception as e:
        return {
            "code": 500,
            "message": f"查询失败：{str(e)}",
            "data": None
        }


# ========== 告警级别枚举接口 ==========

@router.get(
    "/dict/alarm-levels",
    responses={
        200: {
            "description": "成功获取告警级别列表",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "成功",
                        "data": [
                            {"level": 1, "name": "严重", "color": "red"},
                            {"level": 2, "name": "警告", "color": "orange"},
                            {"level": 3, "name": "提示", "color": "blue"}
                        ]
                    }
                }
            }
        },
        500: {
            "description": "服务器错误",
            "content": {
                "application/json": {
                    "example": {
                        "code": 500,
                        "message": "查询失败",
                        "data": None
                    }
                }
            }
        }
    }
)
async def get_alarm_levels():
    """获取告警级别列表（供前端下拉框使用）"""
    try:
        # 返回固定的告警级别（无需数据库表）
        data = [
            {"level": 1, "name": "严重", "color": "red", "description": "需要立即处理的严重告警"},
            {"level": 2, "name": "警告", "color": "orange", "description": "需要尽快处理的警告"},
            {"level": 3, "name": "提示", "color": "blue", "description": "一般性提示告警"}
        ]

        return {
            "code": 200,
            "message": "成功",
            "data": data
        }
    except Exception as e:
        return {
            "code": 500,
            "message": f"查询失败：{str(e)}",
            "data": None
        }


# ========== 获取告警列表（配套接口） ==========

@router.get(
    "/list",
    responses={
        200: {
            "description": "成功获取告警列表",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "成功",
                        "data": {
                            "total": 100,
                            "items": [
                                {
                                    "id": 1,
                                    "building_id": "B001",
                                    "meter_id": "M001",
                                    "alarm_type": "energy",
                                    "alarm_level": 1,
                                    "description": "能耗异常：250.5 kWh",
                                    "start_time": "2025-03-13T14:30:00",
                                    "status": "pending",
                                    "value": 250.5
                                }
                            ]
                        }
                    }
                }
            }
        }
    }
)
async def get_alarm_list(
        status: Optional[str] = Query(None, description="过滤状态：pending/confirmed/resolved"),
        building_id: Optional[str] = Query(None, description="建筑编号"),
        alarm_level: Optional[int] = Query(None, description="告警级别"),
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    """获取告警列表（配套接口）"""
    try:
        # 构建查询条件
        conditions = ["1=1"]
        params = []

        if status:
            conditions.append("status = %s")
            params.append(status)
        if building_id:
            conditions.append("building_id = %s")
            params.append(building_id)
        if alarm_level:
            conditions.append("alarm_level = %s")
            params.append(alarm_level)

        where_clause = " AND ".join(conditions)

        # 查询总数
        count_sql = f"SELECT COUNT(*) as total FROM alarms WHERE {where_clause}"
        count_result = await Database.fetch_one(count_sql, tuple(params))
        total = count_result['total'] if count_result else 0

        # 查询数据
        offset = (page - 1) * page_size
        sql = f"""
            SELECT * FROM alarms 
            WHERE {where_clause}
            ORDER BY start_time DESC
            LIMIT %s OFFSET %s
        """
        params.extend([page_size, offset])

        items = await Database.fetch_all(sql, tuple(params))

        return {
            "code": 200,
            "message": "成功",
            "data": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "items": items
            }
        }

    except Exception as e:
        return {
            "code": 500,
            "message": f"查询失败: {str(e)}",
            "data": None
        }