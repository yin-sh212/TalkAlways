# app/api/alarm_api.py
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel
from typing import List, Optional, Dict,Any
from app.database.db import Database
from app.services.anomaly_detector import detect_combined_alarm
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


# ========== 告警分析接口 ==========

class AlarmAnalysisResponse(BaseModel):
    """告警分析响应"""
    alarm_id: int
    building_id: str
    alarm_type: str
    alarm_level: int
    description: str
    start_time: datetime

    # 分析结果
    main_cause: str  # 主要原因
    top_factors: List[Dict[str, Any]]  # TOP3影响因素
    quick_solution: str  # 快速解决方案
    related_knowledge: Optional[List[Dict]] = None  # 相关知识库条目


@router.get(
    "/{alarm_id}/analysis",
    responses={
        200: {
            "description": "成功获取告警分析",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "成功",
                        "data": {
                            "alarm_id": 123,
                            "building_id": "Eagle_education_Wesley",
                            "alarm_type": "energy",
                            "alarm_level": 2,
                            "description": "能耗异常，值为1150kW",
                            "start_time": "2016-07-03T01:00:00",
                            "main_cause": "当日气温较高（28.3℃），空调系统负荷增大导致能耗飙升",
                            "top_factors": [
                                {"factor": "气温", "value": 28.3, "impact": "high",
                                 "description": "气温比正常值高5.2℃"},
                                {"factor": "设备效率", "value": 0.72, "impact": "medium",
                                 "description": "COP低于正常值0.85"},
                                {"factor": "运行时段", "value": "11:00", "impact": "high",
                                 "description": "处于用电高峰期"}
                            ],
                            "quick_solution": "1. 检查空调系统运行参数\n2. 清洗冷凝器\n3. 调整设定温度",
                            "related_knowledge": [
                                {"title": "空调系统节能运行规范", "url": "/knowledge/123"},
                                {"title": "能耗异常排查指南", "url": "/knowledge/456"}
                            ]
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
async def analyze_alarm(alarm_id: int):
    """
    分析告警：返回主要原因、TOP3影响因素、快速解决方案
    """
    try:
        # 1. 获取告警基本信息
        alarm_sql = """
            SELECT 
                id,
                building_id,
                meter_id,
                alarm_type,
                alarm_level,
                description,
                start_time,
                value,
                status
            FROM alarms 
            WHERE id = %s
        """
        alarm = await Database.fetch_one(alarm_sql, (alarm_id,))

        if not alarm:
            return {
                "code": 404,
                "message": "告警不存在",
                "data": None
            }

        building_id = alarm['building_id']
        start_time = alarm['start_time']

        # 2. 查询告警发生时的环境数据（从energy_consumption表）
        env_sql = """
            SELECT 
                timestamp,
                electricity,
                ambient_temp,
                pressure,
                cooling_load,
                heating_load
            FROM energy_consumption 
            WHERE building_id = %s 
                AND timestamp BETWEEN DATE_SUB(%s, INTERVAL 6 HOUR) AND DATE_ADD(%s, INTERVAL 6 HOUR)
            ORDER BY timestamp
        """
        env_data = await Database.fetch_all(env_sql, (building_id, start_time, start_time))

        # 3. 计算对比数据（正常时段 vs 异常时段）
        normal_period_sql = """
            SELECT 
                AVG(electricity) as avg_electricity,
                AVG(ambient_temp) as avg_temp,
                AVG(cooling_load) as avg_cooling
            FROM energy_consumption 
            WHERE building_id = %s 
                AND timestamp BETWEEN DATE_SUB(%s, INTERVAL 30 DAY) AND %s
                AND is_anomaly = 0
                AND HOUR(timestamp) = HOUR(%s)
        """
        normal_stats = await Database.fetch_one(normal_period_sql, (building_id, start_time, start_time, start_time))

        # 4. 分析影响因素
        factors = []
        main_cause = ""
        quick_solution = ""

        # 获取告警时的数据点
        alarm_point = next((e for e in env_data if e['timestamp'] == start_time), None)

        if alarm_point:
            current_elec = alarm_point['electricity']
            current_temp = alarm_point['ambient_temp']

            # 计算与正常值的差异
            if normal_stats:
                avg_elec = normal_stats['avg_electricity'] or current_elec
                avg_temp = normal_stats['avg_temp'] or current_temp

                elec_diff = ((current_elec - avg_elec) / avg_elec) * 100 if avg_elec > 0 else 0
                temp_diff = current_temp - avg_temp

                # 因素1：气温影响
                if temp_diff > 3:
                    factors.append({
                        "factor": "气温异常",
                        "value": round(current_temp, 1),
                        "normal": round(avg_temp, 1),
                        "impact": "high",
                        "description": f"气温比正常值高{round(temp_diff, 1)}℃，导致制冷负荷增加"
                    })
                elif temp_diff > 1:
                    factors.append({
                        "factor": "气温偏高",
                        "value": round(current_temp, 1),
                        "normal": round(avg_temp, 1),
                        "impact": "medium",
                        "description": f"气温比正常值高{round(temp_diff, 1)}℃"
                    })

                # 因素2：能耗突增
                if elec_diff > 50:
                    factors.append({
                        "factor": "能耗突增",
                        "value": round(current_elec, 1),
                        "normal": round(avg_elec, 1),
                        "impact": "high",
                        "description": f"能耗比正常值高出{round(elec_diff)}%"
                    })
                elif elec_diff > 30:
                    factors.append({
                        "factor": "能耗偏高",
                        "value": round(current_elec, 1),
                        "normal": round(avg_elec, 1),
                        "impact": "medium",
                        "description": f"能耗比正常值高出{round(elec_diff)}%"
                    })

                # 因素3：设备效率（如果冷却负荷数据可用）
                if alarm_point.get('cooling_load') and alarm_point['cooling_load'] > 0:
                    cop = alarm_point['cooling_load'] / current_elec if current_elec > 0 else 0
                    normal_cop = normal_stats['avg_cooling'] / avg_elec if avg_elec > 0 and normal_stats[
                        'avg_cooling'] > 0 else 3.5

                    if cop < normal_cop * 0.8:
                        factors.append({
                            "factor": "设备效率下降",
                            "value": round(cop, 2),
                            "normal": round(normal_cop, 2),
                            "impact": "high",
                            "description": f"COP值{round(cop, 2)}低于正常值{round(normal_cop, 2)}"
                        })

        # 5. 根据告警类型和级别生成主要原因和解决方案
        alarm_level = alarm['alarm_level']
        alarm_type = alarm['alarm_type']

        # 主要原因分析
        if alarm_type == 'energy':
            if any(f['impact'] == 'high' for f in factors):
                main_cause = "高温导致制冷负荷剧增，同时设备运行效率下降"
            elif temp_diff > 2:
                main_cause = f"气温升高{round(temp_diff, 1)}℃，空调系统负荷增大"
            else:
                main_cause = "设备运行异常导致能耗突增"
        elif alarm_type == 'equipment':
            main_cause = "设备故障或运行参数异常"
        elif alarm_type == 'environment':
            main_cause = "环境因素超出正常范围"
        else:
            main_cause = "未知原因，建议检查设备运行日志"

        # 快速解决方案
        if alarm_type == 'energy':
            quick_solution = "1. 检查空调系统运行参数\n2. 清洗冷凝器滤网\n3. 优化运行时段\n4. 检查是否有设备异常运行"
        elif alarm_type == 'equipment':
            quick_solution = "1. 查看设备故障代码\n2. 重启设备\n3. 联系运维人员检查\n4. 参考设备手册排查"
        else:
            quick_solution = "1. 检查环境监测设备\n2. 校准传感器\n3. 查看历史数据对比"

        # 取TOP3影响因素
        top_factors = sorted(factors, key=lambda x: {'high': 3, 'medium': 2, 'low': 1}[x['impact']], reverse=True)[:3]

        # 6. 关联知识库（如果有）
        related_knowledge = await search_related_knowledge(alarm_type, main_cause)

        return {
            "code": 200,
            "message": "成功",
            "data": {
                "alarm_id": alarm['id'],
                "building_id": alarm['building_id'],
                "alarm_type": alarm['alarm_type'],
                "alarm_level": alarm['alarm_level'],
                "description": alarm['description'],
                "start_time": alarm['start_time'],
                "main_cause": main_cause,
                "top_factors": top_factors,
                "quick_solution": quick_solution,
                "related_knowledge": related_knowledge
            }
        }

    except Exception as e:
        print(f"告警分析错误: {e}")
        return {
            "code": 500,
            "message": f"分析失败: {str(e)}",
            "data": None
        }


# ========== 批量告警分析接口 ==========

class BatchAnalysisRequest(BaseModel):
    alarm_ids: List[int]


@router.post(
    "/batch-analysis",
    responses={
        200: {
            "description": "成功获取批量告警分析",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "成功",
                        "data": {
                            "total": 3,
                            "summaries": [
                                {
                                    "alarm_id": 123,
                                    "main_cause": "气温过高",
                                    "quick_solution": "检查空调系统"
                                }
                            ]
                        }
                    }
                }
            }
        }
    }
)
async def batch_analyze_alarms(request: BatchAnalysisRequest):
    """
    批量分析告警（返回简要分析结果）
    """
    if not request.alarm_ids:
        return {
            "code": 400,
            "message": "告警ID列表不能为空",
            "data": None
        }

    try:
        placeholders = ','.join(['%s'] * len(request.alarm_ids))

        # 查询告警基本信息
        sql = f"""
            SELECT 
                id,
                building_id,
                alarm_type,
                alarm_level,
                description,
                start_time
            FROM alarms 
            WHERE id IN ({placeholders})
            ORDER BY start_time DESC
        """

        alarms = await Database.fetch_all(sql, tuple(request.alarm_ids))

        summaries = []
        for alarm in alarms:
            # 简单分析（不查详细数据，提高性能）
            alarm_type = alarm['alarm_type']

            if alarm_type == 'energy':
                main_cause = "能耗异常，建议检查空调系统和运行时段"
                quick_solution = "1.检查空调参数 2.优化运行时间"
            elif alarm_type == 'equipment':
                main_cause = "设备异常，建议查看故障代码"
                quick_solution = "1.重启设备 2.联系运维"
            else:
                main_cause = "环境异常，检查传感器"
                quick_solution = "1.校准传感器 2.查看环境数据"

            summaries.append({
                "alarm_id": alarm['id'],
                "building_id": alarm['building_id'],
                "main_cause": main_cause,
                "quick_solution": quick_solution
            })

        return {
            "code": 200,
            "message": "成功",
            "data": {
                "total": len(summaries),
                "summaries": summaries
            }
        }

    except Exception as e:
        return {
            "code": 500,
            "message": f"批量分析失败: {str(e)}",
            "data": None
        }


# ========== 辅助函数：搜索相关知识库 ==========

async def search_related_knowledge(alarm_type: str, cause: str) -> List[Dict]:
    """
    搜索相关知识库条目（需要接入 RAG）
    """
    try:
        # 这里可以调用你的 RAG 服务
        # 暂时返回模拟数据
        knowledge_base = {
            "energy": [
                {"title": "空调系统节能运行规范", "url": "/knowledge/1"},
                {"title": "能耗异常排查指南", "url": "/knowledge/2"},
                {"title": "制冷系统维护手册", "url": "/knowledge/3"}
            ],
            "equipment": [
                {"title": "设备故障代码对照表", "url": "/knowledge/4"},
                {"title": "冷水机组维修手册", "url": "/knowledge/5"}
            ],
            "environment": [
                {"title": "环境监测规范", "url": "/knowledge/6"},
                {"title": "传感器校准指南", "url": "/knowledge/7"}
            ]
        }

        return knowledge_base.get(alarm_type, [])

    except Exception as e:
        print(f"知识库搜索失败：{e}")
        return []


# ========== 实时告警检测接口（动态基线 + 趋势下降） ==========

class AlarmDetectionRequest(BaseModel):
    """告警检测请求"""
    building_id: str
    start_date: str
    end_date: str
    metric: str = Query("electricity", pattern="^(electricity|cooling_load|heating_load)$", 
                        description="检测指标")
    # 动态基线参数
    dynamic_window: int = Query(24, ge=6, le=168, description="动态基线窗口大小（小时）")
    dynamic_threshold: float = Query(2.5, ge=1.5, le=4.0, description="动态基线阈值倍数")
    # 趋势下降参数
    trend_window: int = Query(6, ge=3, le=24, description="趋势检测窗口大小")
    trend_threshold: float = Query(0.3, ge=0.1, le=1.0, description="趋势下降阈值")
    min_trend_decline: float = Query(0.15, ge=0.05, le=0.5, description="最小下降率")


@router.post("/detect")
async def detect_real_alarms(request: AlarmDetectionRequest):
    """
    实时告警检测 - 基于动态基线 + 趋势下降算法
    
    与数据集异常点的区别：
    1. 数据集异常点（is_anomaly）：用于标记历史数据中的统计异常，适合数据分析
    2. 真实告警：基于业务规则的动态检测，考虑时间序列特征和趋势变化，直接触发告警流程
    
    算法特点：
    - 动态基线：根据滑动窗口自动调整阈值，适应数据的周期性变化
    - 趋势下降：检测持续下降趋势，预防设备性能衰退
    """
    try:
        # 1. 查询能耗数据
        sql = """
            SELECT 
                timestamp,
                electricity,
                cooling_load,
                heating_load
            FROM energy_consumption
            WHERE building_id = %s 
                AND DATE(timestamp) BETWEEN %s AND %s
            ORDER BY timestamp
        """
        
        data = await Database.fetch_all(sql, (request.building_id, request.start_date, request.end_date))
        
        if not data:
            return {
                "code": 200,
                "message": "未找到数据",
                "data": {
                    "building_id": request.building_id,
                    "period": f"{request.start_date} 至 {request.end_date}",
                    "total_alarms": 0,
                    "alarms": []
                }
            }
        
        # 2. 提取指定指标的数据
        metric = request.metric
        values = [row[metric] for row in data if row[metric] is not None]
        timestamps = [str(row['timestamp']) for row in data if row[metric] is not None]
        
        if len(values) < 10:
            return {
                "code": 200,
                "message": "数据量不足，无法检测",
                "data": {
                    "building_id": request.building_id,
                    "period": f"{request.start_date} 至 {request.end_date}",
                    "metric": metric,
                    "data_points": len(values),
                    "total_alarms": 0,
                    "alarms": []
                }
            }
        
        # 3. 执行综合告警检测
        detection_result = detect_combined_alarm(
            values=values,
            timestamps=timestamps,
            dynamic_window=request.dynamic_window,
            dynamic_threshold=request.dynamic_threshold,
            trend_window=request.trend_window,
            trend_threshold=request.trend_threshold,
            min_trend_decline=request.min_trend_decline
        )
        
        # 4. 构建告警列表
        alarms = []
        
        # 添加动态基线告警
        for anomaly in detection_result['baseline_anomalies']:
            alarm_type = "过高" if anomaly['type'] == "过高" else "过低"
            severity_map = {
                "critical": {"level": 1, "name": "严重"},
                "high": {"level": 2, "name": "警告"},
                "medium": {"level": 3, "name": "中等"},
                "low": {"level": 4, "name": "提示"}
            }
            severity_info = severity_map.get(anomaly['severity'], {"level": 3, "name": "中等"})
            
            alarms.append({
                "alarm_type": "dynamic_baseline",
                "alarm_level": severity_info["level"],
                "alarm_level_name": severity_info["name"],
                "timestamp": anomaly['timestamp'],
                "metric": metric,
                "value": anomaly['value'],
                "baseline_mean": anomaly['baseline_mean'],
                "baseline_std": anomaly['baseline_std'],
                "upper_bound": anomaly['upper_bound'],
                "lower_bound": anomaly['lower_bound'],
                "deviation": anomaly['deviation'],
                "description": f"{metric} {alarm_type}，值为{anomaly['value']:.2f}，超出动态基线范围[{anomaly['lower_bound']:.2f}, {anomaly['upper_bound']:.2f}]",
                "detection_method": "动态基线",
                "severity": anomaly['severity']
            })
        
        # 添加趋势下降告警
        for anomaly in detection_result['trend_anomalies']:
            severity_map = {
                "critical": {"level": 1, "name": "严重"},
                "high": {"level": 2, "name": "警告"},
                "medium": {"level": 3, "name": "中等"},
                "low": {"level": 4, "name": "提示"}
            }
            severity_info = severity_map.get(anomaly['severity'], {"level": 3, "name": "中等"})
            
            alarms.append({
                "alarm_type": "trend_decline",
                "alarm_level": severity_info["level"],
                "alarm_level_name": severity_info["name"],
                "start_timestamp": anomaly['start_timestamp'],
                "end_timestamp": anomaly['end_timestamp'],
                "metric": metric,
                "start_value": anomaly['start_value'],
                "end_value": anomaly['end_value'],
                "decline_amount": anomaly['decline_amount'],
                "decline_rate": anomaly['decline_rate'],
                "continuous_points": anomaly['continuous_points'],
                "description": f"{metric} 持续下降{anomaly['continuous_points']}个点，从{anomaly['start_value']:.2f}降至{anomaly['end_value']:.2f}，累计下降{anomaly['decline_rate']}",
                "detection_method": "趋势下降",
                "severity": anomaly['severity']
            })
        
        # 按时间排序
        alarms.sort(key=lambda x: x.get('timestamp', x.get('end_timestamp', '')), reverse=True)
        
        return {
            "code": 200,
            "message": "成功",
            "data": {
                "building_id": request.building_id,
                "period": f"{request.start_date} 至 {request.end_date}",
                "metric": metric,
                "algorithm_params": {
                    "dynamic_window": request.dynamic_window,
                    "dynamic_threshold": request.dynamic_threshold,
                    "trend_window": request.trend_window,
                    "trend_threshold": request.trend_threshold,
                    "min_trend_decline": request.min_trend_decline
                },
                "summary": detection_result['summary'],
                "total_alarms": len(alarms),
                "severity_distribution": {
                    "critical": len([a for a in alarms if a['severity'] == 'critical']),
                    "high": len([a for a in alarms if a['severity'] == 'high']),
                    "medium": len([a for a in alarms if a['severity'] == 'medium']),
                    "low": len([a for a in alarms if a['severity'] == 'low'])
                },
                "method_distribution": {
                    "dynamic_baseline": len(detection_result['baseline_anomalies']),
                    "trend_decline": len(detection_result['trend_anomalies'])
                },
                "alarms": alarms
            }
        }
        
    except Exception as e:
        print(f"告警检测错误：{e}")
        return {
            "code": 500,
            "message": f"检测失败：{str(e)}",
            "data": None
        }


@router.get("/detect/quick")
async def quick_detect_alarm(
    building_id: str = Query(..., description="建筑编号"),
    start_date: str = Query(..., description="开始日期"),
    end_date: str = Query(..., description="结束日期"),
    metric: str = Query("electricity", pattern="^(electricity|cooling_load|heating_load)$", 
                        description="检测指标")
):
    """
    快速告警检测 - 使用默认参数的简化版本
    
    适用于前端快速展示或定时任务批量检测
    """
    # 构造默认参数的请求
    request = AlarmDetectionRequest(
        building_id=building_id,
        start_date=start_date,
        end_date=end_date,
        metric=metric
    )
    
    # 调用完整的检测接口
    return await detect_real_alarms(request)
