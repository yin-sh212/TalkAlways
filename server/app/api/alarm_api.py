# app/api/alarm_api.py
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.database.db import Database
from datetime import datetime

router = APIRouter(prefix="/api/alarm", tags=["告警管理"])


# ========== 数据模型 ==========

class BatchAlarmRequest(BaseModel):
    """批量操作请求"""
    errorId: List[int]


class BatchAlarmResponse(BaseModel):
    """批量操作响应"""
    isSuccess: bool
    successCount: int
    failedIds: List[int]


class AlarmListResponse(BaseModel):
    """告警列表响应"""
    errorTime: str
    errorType: str
    errorStatus: str


class AlarmDetailResponse(BaseModel):
    """告警详情响应"""
    errorId: int
    building: str
    device: str
    alarmType: str
    errorType: str
    errorStatus: str


class AlarmAnalysisResponse(BaseModel):
    """原因分析响应"""
    mainCause: str
    factors: List[Dict[str, Any]]
    solution: str

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

@router.get("/list1")
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


# ========== 5. 实时异常报警 & 告警事件分布趋势 & 告警类型统计 ==========

@router.get("/list")
async def list_alarms(
        startTime: str = Query(..., description="开始时间，格式：YYYY-MM-DD"),
        endTime: str = Query(..., description="结束时间，格式：YYYY-MM-DD"),
        errorType: Optional[str] = Query(None, description="告警类型过滤"),
        errorStatus: Optional[str] = Query(None, description="告警状态过滤"),
        groupBy: Optional[str] = Query(None, description="分组方式：errorTime/errorType")
):
    """
    告警列出接口

    入参：
    - startTime: 开始时间
    - endTime: 结束时间
    - errorType: 可选，告警类型过滤
    - errorStatus: 可选，告警状态过滤
    - groupBy: 可选，分组方式（errorTime/errorType）

    出参：
    - errorTime: 告警时间
    - errorType: 告警类型
    - errorStatus: 告警状态
    """
    try:
        # 构建基础查询条件
        conditions = ["DATE(start_time) BETWEEN %s AND %s"]
        params = [startTime, endTime]

        if errorType:
            conditions.append("alarm_type = %s")
            params.append(errorType)
        if errorStatus:
            conditions.append("status = %s")
            params.append(errorStatus)

        where_clause = " AND ".join(conditions)

        # 处理分组查询
        if groupBy == "errorTime":
            # 按时间分组统计
            sql = f"""
                SELECT 
                    DATE(start_time) as errorTime,
                    alarm_type as errorType,
                    status as errorStatus,
                    COUNT(*) as count
                FROM alarms
                WHERE {where_clause}
                GROUP BY DATE(start_time), alarm_type, status
                ORDER BY errorTime DESC
            """
            data = await Database.fetch_all(sql, tuple(params))

            # 格式化结果
            result = []
            for item in data:
                result.append({
                    "errorTime": item['errorTime'].isoformat() if item['errorTime'] else None,
                    "errorType": item['errorType'],
                    "errorStatus": item['errorStatus']
                })

            return {
                "code": 200,
                "message": "成功",
                "data": result
            }

        elif groupBy == "errorType":
            # 按类型分组统计
            sql = f"""
                SELECT 
                    alarm_type as errorType,
                    status as errorStatus,
                    COUNT(*) as count,
                    MIN(start_time) as firstTime,
                    MAX(start_time) as lastTime
                FROM alarms
                WHERE {where_clause}
                GROUP BY alarm_type, status
                ORDER BY errorType
            """
            data = await Database.fetch_all(sql, tuple(params))

            # 格式化结果
            result = []
            for item in data:
                result.append({
                    "errorType": item['errorType'],
                    "errorStatus": item['errorStatus']
                })

            return {
                "code": 200,
                "message": "成功",
                "data": result
            }

        else:
            # 不分组，返回详细列表
            sql = f"""
                SELECT 
                    start_time as errorTime,
                    alarm_type as errorType,
                    status as errorStatus,
                    id,
                    building_id,
                    description
                FROM alarms
                WHERE {where_clause}
                ORDER BY start_time DESC
            """
            data = await Database.fetch_all(sql, tuple(params))

            # 格式化结果
            result = []
            for item in data:
                result.append({
                    "errorTime": item['errorTime'].isoformat() if item['errorTime'] else None,
                    "errorType": item['errorType'],
                    "errorStatus": item['errorStatus']
                })

            return {
                "code": 200,
                "message": "成功",
                "data": result
            }

    except Exception as e:
        return {
            "code": 500,
            "message": f"查询失败: {str(e)}",
            "data": None
        }


@router.get("/realtime")
async def get_realtime_alarms(
        limit: int = Query(10, ge=1, le=50, description="返回条数")
):
    """
    实时异常报警（最新的未处理告警）

    入参：
    - limit: 返回条数

    出参：
    - errorTime: 告警时间
    - errorType: 告警类型
    - errorStatus: 告警状态
    """
    try:
        sql = """
            SELECT 
                start_time as errorTime,
                alarm_type as errorType,
                status as errorStatus
            FROM alarms
            WHERE status IN ('pending', 'confirmed')
            ORDER BY start_time DESC
            LIMIT %s
        """

        data = await Database.fetch_all(sql, (limit,))

        # 格式化结果
        result = []
        for item in data:
            result.append({
                "errorTime": item['errorTime'].isoformat() if item['errorTime'] else None,
                "errorType": item['errorType'],
                "errorStatus": item['errorStatus']
            })

        return {
            "code": 200,
            "message": "成功",
            "data": result
        }

    except Exception as e:
        return {
            "code": 500,
            "message": f"查询失败: {str(e)}",
            "data": None
        }


# ========== 6. 针对具体异常分析异常原因 ==========

@router.get("/{errorId}/analysis")
async def analyze_alarm(errorId: int):
    """
    原因分析接口

    入参：
    - errorId: 告警ID

    出参：
    - mainCause: 主要原因
    - factors: 影响因素列表
    - solution: 解决方案
    """
    try:
        # 1. 获取告警基本信息
        alarm_sql = """
            SELECT 
                id,
                building_id,
                alarm_type,
                alarm_level,
                description,
                start_time,
                value
            FROM alarms 
            WHERE id = %s
        """
        alarm = await Database.fetch_one(alarm_sql, (errorId,))

        if not alarm:
            return {
                "code": 404,
                "message": "告警不存在",
                "data": None
            }

        building_id = alarm['building_id']
        start_time = alarm['start_time']
        alarm_type = alarm['alarm_type']
        alarm_level = alarm['alarm_level']

        # 2. 查询告警发生时的环境数据
        env_sql = """
            SELECT 
                timestamp,
                electricity,
                ambient_temp,
                cooling_load,
                heating_load
            FROM energy_consumption 
            WHERE building_id = %s 
                AND timestamp BETWEEN DATE_SUB(%s, INTERVAL 6 HOUR) AND DATE_ADD(%s, INTERVAL 6 HOUR)
            ORDER BY timestamp
        """
        env_data = await Database.fetch_all(env_sql, (building_id, start_time, start_time))

        # 3. 查询正常时段对比数据
        normal_sql = """
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
        normal_stats = await Database.fetch_one(normal_sql, (building_id, start_time, start_time, start_time))

        # 4. 分析影响因素
        factors = []
        main_cause = ""
        solution = ""

        # 获取告警时刻的数据点
        alarm_point = next((e for e in env_data if e['timestamp'] == start_time), None)

        if alarm_point and normal_stats:
            current_elec = alarm_point['electricity']
            current_temp = alarm_point['ambient_temp']

            avg_elec = normal_stats['avg_electricity'] or current_elec
            avg_temp = normal_stats['avg_temp'] or current_temp

            elec_diff = ((current_elec - avg_elec) / avg_elec * 100) if avg_elec > 0 else 0
            temp_diff = current_temp - avg_temp

            # 气温影响因素
            if temp_diff > 3:
                factors.append({
                    "factor": "temperature",
                    "value": round(current_temp, 1),
                    "normal": round(avg_temp, 1),
                    "impact": "high",
                    "description": f"气温比正常值高{round(temp_diff, 1)}℃"
                })
            elif temp_diff > 1:
                factors.append({
                    "factor": "temperature",
                    "value": round(current_temp, 1),
                    "normal": round(avg_temp, 1),
                    "impact": "medium",
                    "description": f"气温比正常值高{round(temp_diff, 1)}℃"
                })

            # 能耗影响因素
            if elec_diff > 50:
                factors.append({
                    "factor": "power_consumption",
                    "value": round(current_elec, 1),
                    "normal": round(avg_elec, 1),
                    "impact": "high",
                    "description": f"能耗比正常值高出{round(elec_diff)}%"
                })
            elif elec_diff > 30:
                factors.append({
                    "factor": "power_consumption",
                    "value": round(current_elec, 1),
                    "normal": round(avg_elec, 1),
                    "impact": "medium",
                    "description": f"能耗比正常值高出{round(elec_diff)}%"
                })

        # 根据告警类型生成主要原因和解决方案
        if alarm_type == 'energy':
            if temp_diff > 2:
                main_cause = f"气温升高{round(temp_diff, 1)}℃导致空调系统负荷增大"
            elif elec_diff > 30:
                main_cause = f"能耗突增{round(elec_diff)}%，可能设备运行异常"
            else:
                main_cause = "设备运行效率下降导致能耗异常"

            solution = "1. 检查空调系统运行参数\n2. 清洗冷凝器滤网\n3. 优化运行时段"

        elif alarm_type == 'equipment':
            main_cause = "设备故障或运行参数异常"
            solution = "1. 查看设备故障代码\n2. 重启设备\n3. 联系运维人员"

        elif alarm_type == 'environment':
            main_cause = "环境因素超出正常范围"
            solution = "1. 检查环境监测设备\n2. 校准传感器\n3. 查看历史数据"
        else:
            main_cause = "未知原因，建议检查设备运行日志"
            solution = "1. 查看详细日志\n2. 联系技术支持"

        # 取TOP3影响因素
        top_factors = sorted(factors,
                             key=lambda x: {'high': 3, 'medium': 2, 'low': 1}[x['impact']],
                             reverse=True)[:3]

        return {
            "code": 200,
            "message": "成功",
            "data": {
                "mainCause": main_cause,
                "factors": top_factors,
                "solution": solution
            }
        }

    except Exception as e:
        return {
            "code": 500,
            "message": f"分析失败: {str(e)}",
            "data": None
        }


# ========== 7. 查询告警（获取告警详情） ==========

@router.get("/{errorId}")
async def get_alarm_detail(errorId: int):
    """
    获取告警详情

    入参：
    - errorId: 告警ID

    出参：
    - errorId: 告警ID
    - building: 建筑名称/ID
    - device: 设备ID
    - alarmType: 告警类型
    - errorType: 错误类型（1-严重/2-警告/3-提示）
    - errorStatus: 告警状态
    """
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
                status
            FROM alarms 
            WHERE id = %s
        """
        item = await Database.fetch_one(sql, (errorId,))

        if not item:
            return {
                "code": 404,
                "message": "告警不存在",
                "data": None
            }

        # 错误类型映射
        error_type_map = {
            1: "严重",
            2: "警告",
            3: "提示"
        }

        return {
            "code": 200,
            "message": "成功",
            "data": {
                "errorId": item['id'],
                "building": item['building_id'],
                "device": item['meter_id'],
                "alarmType": item['alarm_type'],
                "errorType": error_type_map.get(item['alarm_level'], "未知"),
                "errorStatus": item['status']
            }
        }

    except Exception as e:
        return {
            "code": 500,
            "message": f"查询失败: {str(e)}",
            "data": None
        }


# ========== 8. 告警确认/解决 ==========

@router.post("/batch-confirm")
async def batch_confirm_alarms(request: BatchAlarmRequest):
    """
    批量确认告警

    入参：
    - errorId: 告警ID列表

    出参：
    - isSuccess: 是否全部成功
    """
    if not request.errorId:
        return {
            "code": 400,
            "message": "告警ID列表不能为空",
            "data": None
        }

    try:
        placeholders = ','.join(['%s'] * len(request.errorId))

        # 更新告警状态
        update_sql = f"""
            UPDATE alarms 
            SET status = 'confirmed', updated_at = NOW()
            WHERE id IN ({placeholders})
        """

        pool = await Database.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(update_sql, request.errorId)
                affected_rows = cursor.rowcount
                await conn.commit()

        # 找出失败的ID
        failed_ids = []
        if affected_rows < len(request.errorId):
            check_sql = f"""
                SELECT id FROM alarms 
                WHERE id IN ({placeholders}) AND status != 'confirmed'
            """
            async with pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(check_sql, request.errorId)
                    failed = await cursor.fetchall()
                    failed_ids = [f[0] for f in failed]

        return {
            "code": 200,
            "message": "成功",
            "data": {
                "isSuccess": affected_rows == len(request.errorId),
                "successCount": affected_rows,
                "failedIds": failed_ids
            }
        }

    except Exception as e:
        return {
            "code": 500,
            "message": f"操作失败: {str(e)}",
            "data": None
        }


@router.post("/batch-resolve")
async def batch_resolve_alarms(request: BatchAlarmRequest):
    """
    批量解决告警

    入参：
    - errorId: 告警ID列表

    出参：
    - isSuccess: 是否全部成功
    """
    if not request.errorId:
        return {
            "code": 400,
            "message": "告警ID列表不能为空",
            "data": None
        }

    try:
        placeholders = ','.join(['%s'] * len(request.errorId))

        # 更新告警状态
        update_sql = f"""
            UPDATE alarms 
            SET status = 'resolved', end_time = NOW(), updated_at = NOW()
            WHERE id IN ({placeholders})
        """

        pool = await Database.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(update_sql, request.errorId)
                affected_rows = cursor.rowcount
                await conn.commit()

        # 找出失败的ID
        failed_ids = []
        if affected_rows < len(request.errorId):
            check_sql = f"""
                SELECT id FROM alarms 
                WHERE id IN ({placeholders}) AND status != 'resolved'
            """
            async with pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(check_sql, request.errorId)
                    failed = await cursor.fetchall()
                    failed_ids = [f[0] for f in failed]

        return {
            "code": 200,
            "message": "成功",
            "data": {
                "isSuccess": affected_rows == len(request.errorId),
                "successCount": affected_rows,
                "failedIds": failed_ids
            }
        }

    except Exception as e:
        return {
            "code": 500,
            "message": f"操作失败: {str(e)}",
            "data": None
        }


# ========== 初始化告警表（辅助函数） ==========

async def init_alarm_tables():
    """初始化告警表（仅用于首次部署）"""
    pool = await Database.get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # 创建告警表
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
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_building (building_id),
                    INDEX idx_status (status),
                    INDEX idx_time (start_time)
                )
            """)
            await conn.commit()