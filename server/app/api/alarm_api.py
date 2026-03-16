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

@router.post("/batch-confirm")
async def batch_confirm_alarms(request: AlarmBatchRequest):
    """
    批量确认告警 - 修复版
    """
    if not request.alarm_ids:
        return {
            "code": 400,
            "message": "告警ID列表不能为空",
            "data": None
        }

    try:
        placeholders = ','.join(['%s'] * len(request.alarm_ids))

        # 1. 先查看要更新的告警当前状态
        check_sql = f"""
            SELECT id, status FROM alarms 
            WHERE id IN ({placeholders})
        """
        check_result = await Database.fetch_all(check_sql, tuple(request.alarm_ids))

        print(f"要更新的告警: {check_result}")  # 调试用

        # 2. 执行更新（更宽松的条件）
        update_sql = f"""
            UPDATE alarms 
            SET status = 'confirmed', updated_at = NOW()
            WHERE id IN ({placeholders})
        """

        pool = await Database.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(update_sql, request.alarm_ids)
                affected_rows = cursor.rowcount
                await conn.commit()

        print(f"更新影响行数: {affected_rows}")  # 调试用

        return {
            "code": 200,
            "message": f"成功确认 {affected_rows} 条告警",
            "data": {
                "confirmed_count": affected_rows,
                "failed_ids": []  # 简化，不返回失败ID
            }
        }

    except Exception as e:
        print(f"批量确认错误: {e}")
        return {
            "code": 500,
            "message": f"数据库更新失败: {str(e)}",
            "data": None
        }


@router.post("/batch-resolve")
async def batch_resolve_alarms(request: AlarmBatchRequest):
    """
    批量解决告警 - 修复版
    """
    if not request.alarm_ids:
        return {
            "code": 400,
            "message": "告警ID列表不能为空",
            "data": None
        }

    try:
        placeholders = ','.join(['%s'] * len(request.alarm_ids))

        # 1. 先查看要更新的告警
        check_sql = f"""
            SELECT id, status FROM alarms 
            WHERE id IN ({placeholders})
        """
        check_result = await Database.fetch_all(check_sql, tuple(request.alarm_ids))
        print(f"要解决的告警: {check_result}")  # 调试用

        # 2. 执行更新（所有告警都可以被解决，不管当前状态）
        update_sql = f"""
            UPDATE alarms 
            SET status = 'resolved', end_time = NOW(), updated_at = NOW()
            WHERE id IN ({placeholders})
        """

        pool = await Database.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(update_sql, request.alarm_ids)
                affected_rows = cursor.rowcount
                await conn.commit()

        print(f"解决影响行数: {affected_rows}")  # 调试用

        return {
            "code": 200,
            "message": f"成功解决 {affected_rows} 条告警",
            "data": {
                "resolved_count": affected_rows,
                "failed_ids": []
            }
        }

    except Exception as e:
        print(f"批量解决错误: {e}")
        return {
            "code": 500,
            "message": f"数据库更新失败: {str(e)}",
            "data": None
        }

# ========== 批量解决告警 ==========

@router.post("/batch-resolve")
async def batch_resolve_alarms(request: AlarmBatchRequest):
    """
    批量解决告警
    将选中的多条告警状态更新为 "已解决" (resolved)，并记录解决时间
    """
    if not request.alarm_ids:
        return {
            "code": 400,
            "message": "告警ID列表不能为空",
            "data": None
        }

    try:
        placeholders = ','.join(['%s'] * len(request.alarm_ids))
        sql = f"""
            UPDATE alarms 
            SET status = 'resolved', end_time = NOW(), updated_at = NOW()
            WHERE id IN ({placeholders}) AND status != 'resolved'
        """

        pool = await Database.get_pool()  # 修复：先 await
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(sql, request.alarm_ids)
                affected_rows = cursor.rowcount
                await conn.commit()

        # 找出可能失败的ID
        failed_ids = []
        if affected_rows < len(request.alarm_ids):
            check_sql = f"""
                SELECT id FROM alarms 
                WHERE id IN ({placeholders}) AND status = 'resolved'
            """
            pool = await Database.get_pool()
            async with pool.acquire() as conn:
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
            "message": f"数据库更新失败: {str(e)}",
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
        # 检查表是否存在，如果不存在则创建默认数据
        try:
            sql = "SELECT code, name, description FROM alarm_types ORDER BY sort_order"
            data = await Database.fetch_all(sql)
        except Exception:
            # 表不存在，创建默认字典数据
            await init_alarm_dict_tables()
            sql = "SELECT code, name, description FROM alarm_types ORDER BY sort_order"
            data = await Database.fetch_all(sql)

        return {
            "code": 200,
            "message": "成功",
            "data": data
        }
    except Exception as e:
        return {
            "code": 500,
            "message": f"查询失败: {str(e)}",
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
        # 检查表是否存在
        try:
            sql = "SELECT level, name, color, description FROM alarm_levels ORDER BY level"
            data = await Database.fetch_all(sql)
        except Exception:
            # 表不存在，创建默认字典数据
            await init_alarm_dict_tables()
            sql = "SELECT level, name, color, description FROM alarm_levels ORDER BY level"
            data = await Database.fetch_all(sql)

        return {
            "code": 200,
            "message": "成功",
            "data": data
        }
    except Exception as e:
        return {
            "code": 500,
            "message": f"查询失败: {str(e)}",
            "data": None
        }


# ========== 从异常节点分析表生成告警 ==========

@router.post("/generate-from-anomalies")
async def generate_alarms_from_anomalies():
    """从异常节点分析表生成告警记录 - 使用新数据"""
    try:
        # 先清空旧告警
        pool = await Database.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("DELETE FROM alarms")
                await conn.commit()
                print("✅ 已清空旧告警")

        # 查询所有异常数据（从新数据中）
        sql = """
            SELECT 
                building_id,
                meter_id,
                timestamp,
                electricity,
                'energy' as alarm_type,
                2 as alarm_level,
                CONCAT('能耗异常，值为 ', ROUND(electricity, 2), ' kW') as description,
                'pending' as status
            FROM energy_consumption
            WHERE is_anomaly = 1
        """

        anomalies = await Database.fetch_all(sql)

        print(f"📊 找到 {len(anomalies)} 条异常数据")

        if not anomalies:
            return {
                "code": 200,
                "message": "没有发现异常数据",
                "data": {
                    "generated_count": 0
                }
            }

        # 批量插入告警
        inserted = 0
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                for item in anomalies:
                    insert_sql = """
                        INSERT INTO alarms 
                        (building_id, meter_id, start_time, value, alarm_type, alarm_level, description, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    try:
                        await cursor.execute(insert_sql, (
                            item['building_id'],
                            item['meter_id'],
                            item['timestamp'],
                            item['electricity'],
                            'energy',
                            2,
                            item['description'],
                            'pending'
                        ))
                        inserted += 1
                        if inserted % 20 == 0:
                            print(f"  已插入 {inserted} 条...")
                    except Exception as e:
                        print(f"❌ 插入告警失败: {e}")

                await conn.commit()

        return {
            "code": 200,
            "message": f"成功生成 {inserted} 条告警",
            "data": {
                "generated_count": inserted,
                "sample_buildings": list(set([a['building_id'] for a in anomalies[:5]]))  # 返回几个示例建筑
            }
        }

    except Exception as e:
        print(f"❌ 生成告警失败: {e}")
        return {
            "code": 500,
            "message": f"生成告警失败: {str(e)}",
            "data": None
        }


# ========== 获取告警列表 ==========

@router.get("/list")
async def get_alarm_list(
        status: Optional[str] = Query(None, description="过滤状态：pending/confirmed/resolved"),
        building_id: Optional[str] = Query(None, description="建筑编号"),
        alarm_level: Optional[int] = Query(None, description="告警级别"),
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    """获取告警列表"""
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
        count_result = await Database.fetch_one(count_sql, tuple(params) if params else None)
        total = count_result['total'] if count_result else 0

        # 查询数据
        offset = (page - 1) * page_size
        sql = f"""
            SELECT 
                id,
                building_id,
                meter_id,
                alarm_type,
                alarm_level,
                description,
                start_time,
                end_time,
                status,
                value,
                threshold,
                solution
            FROM alarms 
            WHERE {where_clause}
            ORDER BY start_time DESC
            LIMIT %s OFFSET %s
        """
        query_params = params + [page_size, offset]

        # 修复：fetch_all 内部已经处理了连接池，不需要再管
        items = await Database.fetch_all(sql, tuple(query_params))

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


# ========== 获取单个告警详情 ==========

@router.get(
    "/{alarm_id}",
    responses={
        200: {
            "description": "成功获取告警详情",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "成功",
                        "data": {
                            "id": 1,
                            "building_id": "Eagle_education_Cassie",
                            "meter_id": "Eagle_education_Cassie_machine",
                            "alarm_type": "energy",
                            "alarm_level": 2,
                            "description": "能耗异常，值为 1150 kW",
                            "start_time": "2016-07-03T01:00:00",
                            "end_time": None,
                            "status": "pending",
                            "value": 1150.0,
                            "threshold": None,
                            "solution": None
                        }
                    }
                }
            }
        },
        404: {
            "description": "告警不存在",
            "content": {
                "application/json": {
                    "example": {
                        "code": 404,
                        "message": "告警不存在",
                        "data": None
                    }
                }
            }
        }
    }
)
async def get_alarm_detail(alarm_id: int):
    """获取单个告警详情"""
    try:
        sql = """
            SELECT 
                id,
                building_id,
                meter_id,
                alarm_type,
                alarm_level,
                description,
                start_time,
                end_time,
                status,
                value,
                threshold,
                solution
            FROM alarms 
            WHERE id = %s
        """

        item = await Database.fetch_one(sql, (alarm_id,))

        if not item:
            return {
                "code": 404,
                "message": "告警不存在",
                "data": None
            }

        return {
            "code": 200,
            "message": "成功",
            "data": item
        }

    except Exception as e:
        return {
            "code": 500,
            "message": f"查询失败: {str(e)}",
            "data": None
        }


# ========== 初始化字典表 ==========

async def init_alarm_dict_tables():
    """初始化告警字典表"""
    pool = await Database.get_pool()  # 修复：先 await
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # 创建告警类型表（如果不存在）
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS alarm_types (
                    code VARCHAR(50) PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    description VARCHAR(255),
                    sort_order INT DEFAULT 0
                )
            """)

            # 插入默认类型
            await cursor.execute("""
                INSERT IGNORE INTO alarm_types (code, name, description, sort_order) VALUES
                ('equipment', '设备告警', '设备运行异常', 1),
                ('energy', '能耗告警', '能耗数据异常', 2),
                ('environment', '环境告警', '环境参数异常', 3)
            """)

            # 创建告警级别表
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS alarm_levels (
                    level INT PRIMARY KEY,
                    name VARCHAR(50) NOT NULL,
                    color VARCHAR(20),
                    description VARCHAR(255)
                )
            """)

            # 插入默认级别
            await cursor.execute("""
                INSERT IGNORE INTO alarm_levels (level, name, color, description) VALUES
                (1, '严重', 'red', '需要立即处理'),
                (2, '警告', 'orange', '需要关注'),
                (3, '提示', 'blue', '仅供参考')
            """)

            # 创建告警表（如果不存在）
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS alarms (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    building_id VARCHAR(100) NOT NULL,
                    meter_id VARCHAR(100),
                    alarm_type VARCHAR(50),
                    alarm_level INT,
                    description TEXT,
                    start_time DATETIME NOT NULL,
                    end_time DATETIME,
                    status VARCHAR(20) DEFAULT 'pending',
                    value FLOAT,
                    threshold FLOAT,
                    solution TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_building (building_id),
                    INDEX idx_status (status),
                    INDEX idx_time (start_time)
                )
            """)

            await conn.commit()
