# app/api/alarm_api.py
import json
import re
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.database.db import Database
from app.services.anomaly_detector import detect_combined_alarm
from app.services.knowledge_sync import save_knowledge_document, search_knowledge_documents
from datetime import datetime

router = APIRouter(prefix="/api/alarm", tags=["告警管理"])


# ========== 数据模型 ==========

class AlarmBatchRequest(BaseModel):
    """批量操作请求"""
    alarm_ids: List[int]
    resolution: Optional[str] = None


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


def get_default_alarm_solution(alarm_type: str) -> str:
    solution_map = {
        "dynamic_baseline": "1. 对比近 24 小时负荷曲线\n2. 检查控制参数是否偏移\n3. 排查短时异常启停设备",
        "trend_decline": "1. 检查设备效率和关键部件磨损\n2. 对比历史同工况数据\n3. 评估是否需要保养或更换部件",
        "energy": "1. 检查空调系统运行参数\n2. 核对高负荷时段运行策略\n3. 排查异常能耗设备",
        "equipment": "1. 查看设备运行状态和告警代码\n2. 排查故障部件\n3. 结合现场巡检确认处理方式",
        "environment": "1. 校验环境传感器数据\n2. 对比同区域监测点\n3. 检查采集链路是否异常",
    }
    return solution_map.get(
        alarm_type,
        "1. 核对告警触发条件\n2. 检查相关设备和采集链路\n3. 记录处理结果并复盘"
    )


async def prepare_alarm_analysis_context(alarm: Dict[str, Any]) -> Dict[str, Any]:
    building_id = alarm["building_id"]
    start_time = alarm["start_time"]

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

    normal_period_sql = """
        SELECT 
            AVG(electricity) as avg_electricity,
            AVG(ambient_temp) as avg_temp,
            AVG(cooling_load) as avg_cooling,
            AVG(pressure) as avg_pressure
        FROM energy_consumption 
        WHERE building_id = %s 
            AND timestamp BETWEEN DATE_SUB(%s, INTERVAL 30 DAY) AND %s
            AND is_anomaly = 0
            AND HOUR(timestamp) = HOUR(%s)
    """
    normal_stats = await Database.fetch_one(normal_period_sql, (building_id, start_time, start_time, start_time))
    alarm_point = next((e for e in env_data if e["timestamp"] == start_time), None)

    return {
        "alarm_info": {
            "type": alarm["alarm_type"],
            "level": alarm["alarm_level"],
            "description": alarm["description"],
            "start_time": str(start_time)
        },
        "current_data": alarm_point,
        "normal_stats": normal_stats,
        "environment_trend": env_data[:12]
    }


def extract_alarm_keywords(alarm_type: str, cause: str) -> List[str]:
    base_keywords = {
        "dynamic_baseline": ["动态基线", "能耗异常", "负荷波动"],
        "trend_decline": ["趋势下降", "性能衰减", "设备老化"],
        "energy": ["能耗异常", "节能", "空调系统"],
        "equipment": ["设备故障", "维修", "巡检"],
        "environment": ["环境监测", "传感器", "校准"],
    }.get(alarm_type, ["告警处置", "故障复盘"])

    extracted = re.findall(r"[\u4e00-\u9fffA-Za-z0-9_]{2,12}", cause or "")
    return base_keywords + extracted[:5]


async def archive_alarms_to_knowledge(alarm_ids: List[int], action: str) -> int:
    if not alarm_ids:
        return 0

    placeholders = ",".join(["%s"] * len(alarm_ids))
    alarms = await Database.fetch_all(
        f"""
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
        WHERE id IN ({placeholders})
        ORDER BY start_time DESC
        """,
        tuple(alarm_ids)
    )

    synced_count = 0
    for alarm in alarms:
        try:
            analysis_result: Dict[str, Any] = {}
            if action == "resolved":
                try:
                    analysis_context = await prepare_alarm_analysis_context(alarm)
                    analysis_result = await analyze_with_ai(analysis_context)
                except Exception as exc:
                    print(f"⚠️ 告警 {alarm['id']} AI 整理失败，使用基础整理：{exc}")

            solution = (
                alarm.get("solution")
                or analysis_result.get("quick_solution")
                or get_default_alarm_solution(alarm.get("alarm_type", ""))
            )
            main_cause = analysis_result.get("main_cause") or alarm.get("description") or "告警已处理，建议结合现场记录复盘。"
            top_factors = analysis_result.get("top_factors") or []

            status_label = "已解决" if action == "resolved" else "已确认"
            title = f"告警{status_label}复盘 #{alarm['id']} - {alarm['building_id']}"
            summary = f"{alarm['building_id']} 的 {alarm['alarm_type']} 告警已{status_label}，建议纳入运维复盘知识。"
            description = "\n".join([
                f"告警编号：{alarm['id']}",
                f"建筑：{alarm['building_id']}",
                f"设备/测点：{alarm.get('meter_id') or '未记录'}",
                f"告警类型：{alarm.get('alarm_type') or '未记录'}",
                f"告警级别：{alarm.get('alarm_level') or '未记录'}",
                f"触发时间：{alarm.get('start_time')}",
                f"当前状态：{alarm.get('status')}",
                f"告警描述：{alarm.get('description') or '无'}",
                f"解决办法：{solution}",
                f"根因整理：{main_cause}",
            ])
            if alarm.get("value") is not None:
                description += f"\n触发值：{alarm['value']}"
            if alarm.get("threshold") is not None:
                description += f"\n阈值：{alarm['threshold']}"

            notes = [
                f"source_alarm_id={alarm['id']}",
                f"archived_action={action}",
                f"alarm_status={alarm.get('status')}",
            ]
            for factor in top_factors[:3]:
                factor_name = factor.get("factor", "未知因素")
                factor_desc = factor.get("description", "")
                notes.append(f"影响因素：{factor_name} - {factor_desc}")

            await save_knowledge_document({
                "title": title,
                "category": "case",
                "tags": [
                    "alarm-case",
                    alarm.get("alarm_type") or "unknown",
                    status_label,
                    alarm.get("building_id") or "unknown-building",
                ],
                "summary": summary,
                "description": description,
                "solution": solution,
                "notes": notes,
            })
            synced_count += 1
        except Exception as exc:
            print(f"⚠️ 告警 {alarm.get('id')} 落知识库失败：{exc}")

    return synced_count


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
        conn = await pool.acquire()
        try:
            cursor_ctx = conn.cursor()
            async with cursor_ctx as cursor:
                await cursor.execute(update_sql, request.alarm_ids)
                affected_rows = cursor.rowcount
                await conn.commit()
        finally:
            await conn.release()

        print(f"更新影响行数: {affected_rows}")  # 调试用
        knowledge_synced_count = 0

        return {
            "code": 200,
            "message": f"成功确认 {affected_rows} 条告警",
            "data": {
                "confirmed_count": affected_rows,
                "failed_ids": [],  # 简化，不返回失败ID
                "knowledge_synced_count": knowledge_synced_count,
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

    resolution = (request.resolution or "").strip()
    if not resolution:
        return {
            "code": 400,
            "message": "解决告警时必须填写解决办法",
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
            SET status = 'resolved', solution = %s, end_time = NOW(), updated_at = NOW()
            WHERE id IN ({placeholders})
        """
        update_params = (resolution, *request.alarm_ids)

        pool = await Database.get_pool()
        conn = await pool.acquire()
        try:
            cursor_ctx = conn.cursor()
            async with cursor_ctx as cursor:
                await cursor.execute(update_sql, update_params)
                affected_rows = cursor.rowcount
                await conn.commit()
        finally:
            await conn.release()

        print(f"解决影响行数: {affected_rows}")  # 调试用
        knowledge_synced_count = 0
        if affected_rows > 0:
            knowledge_synced_count = await archive_alarms_to_knowledge(request.alarm_ids, "resolved")

        return {
            "code": 200,
            "message": f"成功解决 {affected_rows} 条告警",
            "data": {
                "resolved_count": affected_rows,
                "failed_ids": [],
                "knowledge_synced_count": knowledge_synced_count,
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


# ========== 使用真实算法生成告警（动态基线 + 趋势下降） ==========

@router.post("/generate-real-alarms")
async def generate_real_alarms(
    start_date: str = Query(..., description="开始日期"),
    end_date: str = Query(..., description="结束日期"),
    building_ids: Optional[str] = Query(None, description="建筑 ID 列表，逗号分隔，不传则查询所有建筑"),
    metric: str = Query("electricity", pattern="^(electricity|cooling_load|heating_load)$", 
                        description="检测指标"),
    # 动态基线参数
    dynamic_window: int = Query(24, ge=6, le=168, description="动态基线窗口大小（小时）"),
    dynamic_threshold: float = Query(2.5, ge=1.5, le=4.0, description="动态阈值倍数"),
    # 趋势下降参数
    trend_window: int = Query(6, ge=3, le=24, description="趋势检测窗口大小"),
    min_trend_decline: float = Query(0.15, ge=0.05, le=0.5, description="最小下降率")
):
    """
    使用真实检测算法生成告警 - 基于动态基线 + 趋势下降
    
    与旧的 generate-from-anomalies 接口的区别：
    1. 不使用 is_anomaly 字段，而是实时计算检测
    2. 支持严重程度分级（严重/警告/中等/提示）
    3. 区分告警类型（dynamic_baseline/trend_decline）
    4. 提供详细的检测依据和统计信息
    """
    try:
        # 1. 清空旧告警
        await Database.execute("DELETE FROM alarms")
        print("✅ 已清空旧告警")

        # 2. 构建建筑 ID 列表
        if building_ids:
            target_buildings = [b.strip() for b in building_ids.split(',')]
        else:
            # 查询所有建筑
            buildings_sql = "SELECT DISTINCT building_id FROM energy_consumption"
            buildings_result = await Database.fetch_all(buildings_sql)
            target_buildings = [b['building_id'] for b in buildings_result]
        
        print(f"🏢 待检测建筑数量：{len(target_buildings)}")

        total_alarms = 0
        alarm_stats = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "dynamic_baseline": 0,
            "trend_decline": 0
        }

        # 3. 对每个建筑执行检测
        for building_id in target_buildings:
            # 查询该建筑的能耗数据
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
            
            data = await Database.fetch_all(sql, (building_id, start_date, end_date))
            
            if len(data) < 10:
                print(f"⚠️  {building_id}: 数据量不足 ({len(data)} 条)，跳过")
                continue
            
            # 提取指定指标的数据 - 使用字段名而非索引
            values = [row['electricity'] for row in data if row['electricity'] is not None] if metric == 'electricity' else \
                     [row['cooling_load'] for row in data if row['cooling_load'] is not None] if metric == 'cooling_load' else \
                     [row['heating_load'] for row in data if row['heating_load'] is not None]
            timestamps = [str(row['timestamp']) for row in data if (row['electricity'] if metric == 'electricity' else row['cooling_load'] if metric == 'cooling_load' else row['heating_load']) is not None]
            
            if len(values) < 10:
                print(f"⚠️  {building_id}: 有效数据不足 ({len(values)} 条)，跳过")
                continue
            
            # 执行综合检测
            detection_result = detect_combined_alarm(
                values=values,
                timestamps=timestamps,
                dynamic_window=dynamic_window,
                dynamic_threshold=dynamic_threshold,
                trend_window=trend_window,
                min_trend_decline=min_trend_decline
            )
            
            # 严重程度映射 - 统一为 3 级制（严重/警告/提示）
            severity_map = {
                "critical": {"level": 1, "name": "严重"},
                "high": {"level": 2, "name": "警告"},
                "medium": {"level": 2, "name": "警告"},  # 合并到警告
                "low": {"level": 3, "name": "提示"}
            }

            # 插入动态基线告警
            for anomaly in detection_result['baseline_anomalies']:
                # 根据当前告警的严重程度获取级别
                severity_info = severity_map.get(anomaly['severity'], {"level": 3, "name": "提示"})
                alarm_level = severity_info["level"]
                alarm_type_str = "过高" if anomaly['type'] == "过高" else "过低"
                description = f"{metric} {alarm_type_str}，值为{anomaly['value']:.2f}，超出动态基线范围 [{anomaly['lower_bound']:.2f}, {anomaly['upper_bound']:.2f}]"
                
                insert_sql = """
                    INSERT INTO alarms 
                    (building_id, meter_id, start_time, value, alarm_type, alarm_level, description, status, threshold)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                
                try:
                    await Database.execute(insert_sql, (
                        building_id,
                        f"{building_id}_meter",
                        anomaly['timestamp'],
                        anomaly['value'],
                        'dynamic_baseline',
                        alarm_level,
                        description,
                        'pending',
                        anomaly['upper_bound'] if anomaly['type'] == "过高" else anomaly['lower_bound']
                    ))
                    total_alarms += 1
                    alarm_stats[anomaly['severity']] += 1
                    alarm_stats['dynamic_baseline'] += 1
                except Exception as e:
                    print(f"❌ 插入动态基线告警失败：{e}")
            
            # 插入趋势下降告警
            for anomaly in detection_result['trend_anomalies']:
                alarm_level = severity_info["level"]
                description = f"{metric} 持续下降{anomaly['continuous_points']}个点，从{anomaly['start_value']:.2f}降至{anomaly['end_value']:.2f}，累计下降{anomaly['decline_rate']}"
                
                insert_sql = """
                    INSERT INTO alarms 
                    (building_id, meter_id, start_time, end_time, value, alarm_type, alarm_level, description, status, threshold)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                
                try:
                    await Database.execute(insert_sql, (
                        building_id,
                        f"{building_id}_meter",
                        anomaly['start_timestamp'],
                        anomaly['end_timestamp'],
                        anomaly['end_value'],
                        'trend_decline',
                        alarm_level,
                        description,
                        'pending',
                        anomaly['start_value'] * (1 - min_trend_decline)  # 阈值
                    ))
                    total_alarms += 1
                    alarm_stats[anomaly['severity']] += 1
                    alarm_stats['trend_decline'] += 1
                except Exception as e:
                    print(f"❌ 插入趋势下降告警失败：{e}")
            
            if total_alarms % 50 == 0 and total_alarms > 0:
                print(f"  已插入 {total_alarms} 条告警...")
        
        return {
            "code": 200,
            "message": f"成功生成 {total_alarms} 条真实告警",
            "data": {
                "generated_count": total_alarms,
                "period": f"{start_date} 至 {end_date}",
                "metric": metric,
                "buildings_checked": len(target_buildings),
                "algorithm_params": {
                    "dynamic_window": dynamic_window,
                    "dynamic_threshold": dynamic_threshold,
                    "trend_window": trend_window,
                    "min_trend_decline": min_trend_decline
                },
                "severity_distribution": {
                    "critical": alarm_stats['critical'],
                    "high": alarm_stats['high'],
                    "medium": alarm_stats['medium'],
                    "low": alarm_stats['low']
                },
                "method_distribution": {
                    "dynamic_baseline": alarm_stats['dynamic_baseline'],
                    "trend_decline": alarm_stats['trend_decline']
                }
            }
        }

    except Exception as e:
        print(f"❌ 生成真实告警失败：{e}")
        import traceback
        traceback.print_exc()
        return {
            "code": 500,
            "message": f"生成告警失败：{str(e)}",
            "data": None
        }


# ========== 获取告警统计指标 ==========

@router.get("/stats")
async def get_alarm_stats(
        building_id: Optional[str] = Query(None, description="建筑编号，支持逗号分隔多个ID"),
        start_date: Optional[str] = Query(None, description="开始日期（YYYY-MM-DD）"),
        end_date: Optional[str] = Query(None, description="结束日期（YYYY-MM-DD）")
):
    """获取告警统计指标（总数、未解决、紧急、已确认）"""
    try:
        # 构建查询条件
        conditions = ["1=1"]
        params = []
        
        # 支持多建筑查询
        if building_id:
            building_ids = [bid.strip() for bid in building_id.split(',') if bid.strip()]
            if len(building_ids) == 1:
                conditions.append("building_id = %s")
                params.append(building_ids[0])
            elif len(building_ids) > 1:
                placeholders = ','.join(['%s'] * len(building_ids))
                conditions.append(f"building_id IN ({placeholders})")
                params.extend(building_ids)
        
        # 时间范围
        if start_date:
            conditions.append("DATE(start_time) >= %s")
            params.append(start_date)
        if end_date:
            conditions.append("DATE(start_time) <= %s")
            params.append(end_date)
        
        where_clause = " AND ".join(conditions)
        query_params = tuple(params) if params else None
        
        # 查询总告警数
        total_sql = f"SELECT COUNT(*) as total FROM alarms WHERE {where_clause}"
        total_result = await Database.fetch_one(total_sql, query_params)
        totalAlarms = total_result['total'] if total_result else 0
        
        # 查询未解决告警（pending + confirmed）
        unresolved_sql = f"SELECT COUNT(*) as count FROM alarms WHERE {where_clause} AND status IN ('pending', 'confirmed')"
        unresolved_result = await Database.fetch_one(unresolved_sql, query_params)
        unresolvedCount = unresolved_result['count'] if unresolved_result else 0
        
        # 查询紧急告警（alarm_level <= 2）
        critical_sql = f"SELECT COUNT(*) as count FROM alarms WHERE {where_clause} AND alarm_level <= 2"
        critical_result = await Database.fetch_one(critical_sql, query_params)
        criticalCount = critical_result['count'] if critical_result else 0
        
        # 查询已确认告警（confirmed + resolved）
        acknowledged_sql = f"SELECT COUNT(*) as count FROM alarms WHERE {where_clause} AND status IN ('confirmed', 'resolved')"
        acknowledged_result = await Database.fetch_one(acknowledged_sql, query_params)
        acknowledgedCount = acknowledged_result['count'] if acknowledged_result else 0
        
        return {
            "code": 200,
            "message": "成功",
            "data": {
                "totalAlarms": totalAlarms,
                "unresolvedCount": unresolvedCount,
                "criticalCount": criticalCount,
                "acknowledgedCount": acknowledgedCount
            }
        }
        
    except Exception as e:
        print(f"❌ 查询告警统计失败: {e}")
        return {
            "code": 500,
            "message": f"查询失败: {str(e)}",
            "data": None
        }


# ========== 获取告警列表 ==========

@router.get("/list")
async def get_alarm_list(
        status: Optional[str] = Query(None, description="过滤状态：pending/confirmed/resolved"),
        building_id: Optional[str] = Query(None, description="建筑编号，支持逗号分隔多个ID"),
        alarm_level: Optional[int] = Query(None, description="告警级别"),
        start_date: Optional[str] = Query(None, description="开始日期（YYYY-MM-DD）"),
        end_date: Optional[str] = Query(None, description="结束日期（YYYY-MM-DD）"),
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(10, ge=1, le=100, description="每页数量")
):
    """获取告警列表"""
    try:
        # 构建查询条件
        conditions = ["1=1"]
        params = []

        if status:
            conditions.append("status = %s")
            params.append(status)
        
        # 支持多建筑查询（逗号分隔）
        if building_id:
            building_ids = [bid.strip() for bid in building_id.split(',') if bid.strip()]
            if len(building_ids) == 1:
                conditions.append("building_id = %s")
                params.append(building_ids[0])
            elif len(building_ids) > 1:
                placeholders = ','.join(['%s'] * len(building_ids))
                conditions.append(f"building_id IN ({placeholders})")
                params.extend(building_ids)
        
        if alarm_level:
            conditions.append("alarm_level = %s")
            params.append(alarm_level)
        
        # 添加时间范围过滤
        if start_date:
            conditions.append("DATE(start_time) >= %s")
            params.append(start_date)
        if end_date:
            conditions.append("DATE(start_time) <= %s")
            params.append(end_date)

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
    pool = await Database.get_pool()
    conn = await pool.acquire()
    try:
        cursor_ctx = conn.cursor()
        async with cursor_ctx as cursor:
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

            # 插入默认级别 - 统一为 3 级制（严重/警告/提示）
            await cursor.execute("""
                INSERT IGNORE INTO alarm_levels (level, name, color, description) VALUES
                (1, '严重', 'red', '需要立即处理'),
                (2, '警告', 'orange', '需要关注'),
                (3, '提示', 'blue', '仅供参考'),
                (4, '提示', 'green', '轻微告警')
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
    finally:
        await conn.release()


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
                            "description": "能耗异常，值为 1150kW",
                            "start_time": "2016-07-03T01:00:00",
                            "main_cause": "当日气温较高（28.3℃），空调系统负荷增大导致能耗飙升",
                            "top_factors": [
                                {"factor": "气温", "value": 28.3, "impact": "high",
                                 "description": "气温比正常值高 5.2℃"},
                                {"factor": "设备效率", "value": 0.72, "impact": "medium",
                                 "description": "COP 低于正常值 0.85"},
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
    分析告警：使用 AI Agent 进行智能根因分析
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
        data_context = await prepare_alarm_analysis_context(alarm)

        # 5. 调用 AI Agent 进行智能分析
        ai_analysis = await analyze_with_ai(data_context)
        related_knowledge = await search_related_knowledge(
            alarm['alarm_type'],
            ai_analysis.get('main_cause', alarm.get('description', ''))
        )

        # 6. 返回 AI 分析结果
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
                "main_cause": ai_analysis.get('main_cause', '分析中...'),
                "top_factors": ai_analysis.get('top_factors', []),
                "quick_solution": ai_analysis.get('quick_solution', '建议进一步分析'),
                "related_knowledge": related_knowledge
            }
        }

    except Exception as e:
        print(f"告警分析错误：{e}")
        import traceback
        traceback.print_exc()
        return {
            "code": 500,
            "message": f"分析失败：{str(e)}",
            "data": None
        }


async def analyze_with_ai(data_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    使用 AI 对告警进行智能根因分析
    
    Args:
        data_context: 包含告警信息和环境数据的上下文
        
    Returns:
        AI 分析结果，包含主要原因、影响因素、解决方案
    """
    try:
        from app.services.ai_agent import AIAgent
        ai_agent = AIAgent()
        
        # 构建 AI 分析提示词
        prompt = f"""你是一个专业的建筑能源管理系统 AI 分析师，请分析以下告警并提供深度根因分析。

【重要约束】
1. **禁止简单重复告警描述**：不要把告警 description 原封不动抄过来
2. **必须深入分析原因**：解释"为什么"会发生这个告警，而不是"是什么"
3. **提供且只提供 3 个影响因素**：从天气、设备、控制系统等多角度分析
4. **解决方案要具体**：给出可执行的维护步骤，不是泛泛而谈

【告警信息】
- 类型：{data_context['alarm_info']['type']}
- 级别：{data_context['alarm_info']['level']}
- 时间：{data_context['alarm_info']['start_time']}
- 描述：{data_context['alarm_info']['description']}

【当前运行数据】
{json.dumps(data_context['current_data'], indent=2, default=str) if data_context['current_data'] else '暂无数据'}

【历史同期正常值】
{json.dumps(data_context['normal_stats'], indent=2, default=str) if data_context['normal_stats'] else '暂无数据'}

【分析任务】

**步骤 1：识别异常模式**
- 如果是"趋势下降"（trend_decline）：分析性能衰减的根本原因（如设备老化、冷媒泄漏、部件磨损）
- 如果是"能耗突增"（energy）：分析导致能耗增加的因素（如气温异常、负荷增加、设备故障）
- 如果是"设备故障"（equipment）：分析可能的故障类型和影响

**步骤 2：因果推理**
使用以下推理链：
- 气温异常 → 制冷负荷变化 → COP 值变化 → 能耗变化
- 设备老化/磨损 → 效率下降 → COP 值降低 → 能耗增加
- 冷媒泄漏 → 系统压力下降 → 制冷效率降低 → COP 值下降
- 控制系统故障 → 运行参数偏离 → 设备非最优运行 → 能耗异常

**步骤 3：量化影响**
计算关键指标的偏差百分比：
- 气温偏差 = (当前气温 - 正常气温) / 正常气温 × 100%
- COP 偏差 = (当前 COP - 正常 COP) / 正常 COP × 100%
- 能耗偏差 = (当前能耗 - 正常能耗) / 正常能耗 × 100%

【输出格式】
必须严格按以下 JSON 格式返回：

```json
{{
  "main_cause": "用 1-2 句话说明根本原因，例如：'冷媒泄漏导致系统压力不足（1.8bar vs 正常 2.5bar），制冷效率下降 35%'（不要重复告警描述）",
  "top_factors": [
    {{
      "factor": "因素名称（如'冷媒不足'、'气温异常偏高'、'设备效率下降'）",
      "value": 当前值（数字）,
      "normal": 正常值（数字）,
      "impact": "high|medium|low",
      "description": "因果分析（如'系统压力下降 28%，导致制冷效率严重下降'）"
    }},
    // 至少 3 个因素
  ],
  "quick_solution": "3-5 条具体可执行的维护建议，每条包含具体操作和目标值"
}}
```

【示例参考】

❌ **错误示例**（不要这样写）：
```json
{{
  "main_cause": "检测到 electricity 持续下降 6 个点，从 394.00 降至 333.00，累计下降 15.5%",
  "top_factors": [],
  "quick_solution": "1. 检查设备运行状态 2. 查看监控数据"
}}
```

✅ **正确示例**（参考这种深度）：
```json
{{
  "main_cause": "冷媒泄漏导致系统压力严重不足（1.8bar vs 正常 2.5bar），制冷效率下降 35%，COP 值从 2.8 降至 0.76",
  "top_factors": [
    {{
      "factor": "冷媒不足",
      "value": 1.8,
      "normal": 2.5,
      "impact": "high",
      "description": "系统压力下降 28%，导致制冷循环效率严重下降"
    }},
    {{
      "factor": "气温异常偏高",
      "value": 28.3,
      "normal": 22.0,
      "impact": "medium",
      "description": "气温升高 6.3℃，制冷负荷增加 35%"
    }},
    {{
      "factor": "设备效率下降",
      "value": 0.76,
      "normal": 2.8,
      "impact": "high",
      "description": "COP 值仅为正常值的 27%，需立即检修"
    }}
  ],
  "quick_solution": "1. 立即检测冷媒系统压力和密封性，定位并修复泄漏点\\n2. 补充 R410A 制冷剂至标准压力（2.5bar）\\n3. 检查压缩机运行电流和噪音，评估是否过载\\n4. 清洗冷凝器，改善散热条件\\n5. 建议 24 小时内完成检修，避免故障扩大"
}}
```

现在请分析上述告警数据，提供专业的根因分析。"""

        # 调用 LLM 进行分析
        response = ai_agent.llm.generate(prompt, max_tokens=1024)
        
        # 解析 AI 响应
        try:
            # 尝试提取 JSON
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                analysis_result = json.loads(json_match.group())
            else:
                analysis_result = json.loads(response)
            
            # 验证结果质量
            if not analysis_result.get('top_factors') or len(analysis_result['top_factors']) == 0:
                print(f"⚠️ AI 分析结果为空，使用默认分析")
                analysis_result = {
                    "main_cause": f"基于运行数据分析，{data_context['alarm_info']['description']}。可能原因：设备性能衰退、控制系统故障或传感器失准",
                    "top_factors": [
                        {
                            "factor": "设备效率下降",
                            "value": data_context['current_data'].get('electricity', 0) if data_context['current_data'] else 0,
                            "normal": data_context['normal_stats']['avg_electricity'] if data_context['normal_stats'] else 0,
                            "impact": "high",
                            "description": "运行效率低于正常水平"
                        }
                    ],
                    "quick_solution": "1. 检查设备运行状态和参数\\n2. 校准传感器\\n3. 查看历史数据趋势\\n4. 联系专业人员诊断"
                }
        except Exception as e:
            print(f"⚠️ AI 响应解析失败：{e}")
            # 如果解析失败，返回默认结果
            analysis_result = {
                "main_cause": f"基于数据分析，{data_context['alarm_info']['description']} 可能由多种因素导致，建议结合现场情况进一步排查",
                "top_factors": [
                    {
                        "factor": "运行参数异常",
                        "value": data_context['alarm_info'].get('level', 0),
                        "normal": 1,
                        "impact": "medium",
                        "description": "检测到异常运行模式"
                    }
                ],
                "quick_solution": "1. 检查相关设备运行状态\\n2. 查看历史数据趋势\\n3. 联系专业人员现场诊断"
            }
        
        return analysis_result
        
    except Exception as e:
        print(f"AI 分析失败：{e}")
        # AI 分析失败时返回基础分析
        return {
            "main_cause": f"检测到{data_context['alarm_info']['description']}，建议立即检查相关设备",
            "top_factors": [
                {
                    "factor": "运行异常",
                    "value": 0,
                    "normal": 1,
                    "impact": "medium",
                    "description": "检测到异常模式"
                }
            ],
            "quick_solution": "1. 检查设备运行状态\\n2. 查看监控数据\\n3. 联系运维人员"
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
    搜索相关知识库条目
    """
    try:
        keywords = extract_alarm_keywords(alarm_type, cause)
        return await search_knowledge_documents(keywords, limit=5)

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
            # 严重程度映射 - 统一为 3 级制（严重/警告/提示）
            severity_map = {
                "critical": {"level": 1, "name": "严重"},
                "high": {"level": 2, "name": "警告"},
                "medium": {"level": 2, "name": "警告"},  # 合并到警告
                "low": {"level": 3, "name": "提示"}
            }
            severity_info = severity_map.get(anomaly['severity'], {"level": 3, "name": "提示"})
            
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
            # 严重程度映射 - 统一为 3 级制（严重/警告/提示）
            severity_map = {
                "critical": {"level": 1, "name": "严重"},
                "high": {"level": 2, "name": "警告"},
                "medium": {"level": 2, "name": "警告"},  # 合并到警告
                "low": {"level": 3, "name": "提示"}
            }
            severity_info = severity_map.get(anomaly['severity'], {"level": 3, "name": "提示"})
            
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


@router.get("/space/active-alarms")
async def get_space_active_alarms(floor_id: str = Query(..., description="楼层ID")):
    """获取楼层下所有空间的活跃告警,用于平面图告警联动"""
    sql = """
        SELECT 
            smb.space_id,
            a.id as alarm_id,
            a.alarm_level,
            a.alarm_type,
            a.description,
            a.start_time,
            a.status
        FROM space_meter_binding smb
        INNER JOIN alarms a ON a.meter_id = smb.meter_id
        WHERE smb.space_id IN (
            SELECT id FROM spaces WHERE floor_id = %s
        )
        AND a.status IN ('pending', 'confirmed')
        ORDER BY a.alarm_level DESC, a.start_time DESC
    """
    
    alarms = await Database.fetch_all(sql, (floor_id,))
    
    # 按space_id分组
    space_alarms = {}
    for alarm in alarms:
        space_id = alarm['space_id']
        if space_id not in space_alarms:
            space_alarms[space_id] = []
        space_alarms[space_id].append(dict(alarm))
    
    return {
        "code": 200,
        "message": "成功",
        "data": space_alarms
    }


@router.get("/floor/stats")
async def get_floor_stats(floor_id: str = Query(..., description="楼层ID")):
    """获取楼层统计数据"""
    # 先查询该楼层所有空间的单位面积能耗
    space_energy_sql = """
        SELECT 
            s.id,
            s.area_sqm,
            COALESCE(SUM(ec.electricity), 0) as total_energy,
            CASE 
                WHEN s.area_sqm > 0 THEN COALESCE(SUM(ec.electricity), 0) / s.area_sqm
                ELSE COALESCE(SUM(ec.electricity), 0)
            END as energy_per_sqm
        FROM spaces s
        LEFT JOIN space_meter_binding smb ON smb.space_id = s.id
        LEFT JOIN energy_consumption ec ON ec.meter_id = smb.meter_id 
            AND ec.timestamp >= DATE_SUB(NOW(), INTERVAL 1 DAY)
        WHERE s.floor_id = %s
        GROUP BY s.id, s.area_sqm
    """
    space_energy_list = await Database.fetch_all(space_energy_sql, (floor_id,))
    
    # 在 Python 中计算统计数据
    total_spaces = len(space_energy_list)
    high_energy_spaces = sum(1 for row in space_energy_list if row['energy_per_sqm'] > 5)
    abnormal_spaces = sum(1 for row in space_energy_list if row['energy_per_sqm'] > 10)
    total_energy = sum(row['total_energy'] for row in space_energy_list)
    
    # 查询活跃告警数量
    alarm_sql = """
        SELECT COUNT(DISTINCT a.id) as active_alarms
        FROM alarms a
        INNER JOIN space_meter_binding smb ON smb.meter_id = a.meter_id
        INNER JOIN spaces s ON s.id = smb.space_id
        WHERE s.floor_id = %s
        AND a.status IN ('pending', 'confirmed')
    """
    alarm_stats = await Database.fetch_one(alarm_sql, (floor_id,))
    
    return {
        "code": 200,
        "message": "成功",
        "data": {
            "total_spaces": total_spaces,
            "high_energy_spaces": high_energy_spaces,
            "abnormal_spaces": abnormal_spaces,
            "total_energy": round(total_energy, 2) if total_energy else 0,
            "active_alarms": alarm_stats['active_alarms'] if alarm_stats else 0
        }
    }
