# app/api/mcp_api.py
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import json
from app.database.db import Database
from app.services.anomaly_detector import detect_anomalies_3sigma

router = APIRouter(prefix="/mcp", tags=["MCP协议"])


# MCP协议标准请求格式
class MCPToolCall(BaseModel):
    tool: str
    arguments: Dict[str, Any]
    id: Optional[str] = None


class MCPRequest(BaseModel):
    model: str = "energy-ai"
    messages: List[Dict[str, str]]
    tools: List[MCPToolCall]


class MCPResponse(BaseModel):
    choices: List[Dict[str, Any]]


@router.post("/v1/chat/completions", response_model=MCPResponse)
async def mcp_chat(request: MCPRequest):
    """MCP协议标准接口"""
    results = []

    for tool_call in request.tools:
        result = None
        error = None

        try:
            if tool_call.tool == "query_energy_data":
                result = await handle_query_energy(tool_call.arguments)
            elif tool_call.tool == "analyze_anomaly":
                result = await handle_analyze_anomaly(tool_call.arguments)
            elif tool_call.tool == "get_building_info":
                result = await handle_get_building(tool_call.arguments)
            elif tool_call.tool == "get_statistics":
                result = await handle_get_statistics(tool_call.arguments)
            elif tool_call.tool == "get_device_status":
                result = await handle_device_status(tool_call.arguments)
            else:
                error = f"未知工具: {tool_call.tool}"
        except Exception as e:
            error = str(e)

        if error:
            results.append({
                "role": "tool",
                "content": json.dumps({"error": error}, ensure_ascii=False),
                "tool_call_id": tool_call.id
            })
        else:
            results.append({
                "role": "tool",
                "content": json.dumps(result, ensure_ascii=False, default=str),
                "tool_call_id": tool_call.id
            })

    return {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": None,
                "tool_calls": results
            }
        }]
    }


@router.get("/v1/tools")
async def list_tools():
    """列出所有可用工具"""
    return {
        "tools": [
            {
                "name": "query_energy_data",
                "description": "查询建筑能耗数据",
                "parameters": {
                    "building_id": {"type": "string", "description": "建筑编号"},
                    "start_time": {"type": "string", "description": "开始时间 (YYYY-MM-DD)"},
                    "end_time": {"type": "string", "description": "结束时间 (YYYY-MM-DD)"},
                    "metrics": {"type": "array", "description": "查询指标，如 ['electricity', 'water']"}
                }
            },
            {
                "name": "analyze_anomaly",
                "description": "分析能耗异常",
                "parameters": {
                    "building_id": {"type": "string", "description": "建筑编号"},
                    "start_date": {"type": "string", "description": "开始日期"},
                    "end_date": {"type": "string", "description": "结束日期"},
                    "threshold": {"type": "number", "description": "异常阈值（标准差倍数）"}
                }
            },
            {
                "name": "get_building_info",
                "description": "获取建筑信息",
                "parameters": {
                    "building_id": {"type": "string", "description": "建筑编号"}
                }
            },
            {
                "name": "get_statistics",
                "description": "获取能耗统计",
                "parameters": {
                    "building_id": {"type": "string", "description": "建筑编号"},
                    "start_date": {"type": "string", "description": "开始日期"},
                    "end_date": {"type": "string", "description": "结束日期"},
                    "stat_type": {"type": "string", "description": "统计类型: summary/cop/anomaly"}
                }
            },
            {
                "name": "get_device_status",
                "description": "获取设备状态",
                "parameters": {
                    "building_id": {"type": "string", "description": "建筑编号"},
                    "device_type": {"type": "string", "description": "设备类型: 电表/水表/空调"}
                }
            }
        ]
    }


# ========== 工具函数实现 ==========

async def handle_query_energy(args: Dict) -> Dict:
    """处理能耗查询"""
    building_id = args.get("building_id")
    start_time = args.get("start_time")
    end_time = args.get("end_time")
    metrics = args.get("metrics", ["electricity"])

    # 构建SQL
    select_cols = ["timestamp"] + [m for m in metrics if m in ['electricity', 'water', 'supply_temp', 'return_temp']]
    sql = f"SELECT {', '.join(select_cols)} FROM energy_consumption WHERE 1=1"
    params = []

    if building_id:
        sql += " AND building_id = %s"
        params.append(building_id)
    if start_time:
        sql += " AND DATE(timestamp) >= %s"
        params.append(start_time)
    if end_time:
        sql += " AND DATE(timestamp) <= %s"
        params.append(end_time)

    sql += " ORDER BY timestamp DESC LIMIT 1000"

    data = await Database.fetch_all(sql, tuple(params) if params else None)

    return {
        "status": "success",
        "data": data,
        "count": len(data),
        "building_id": building_id,
        "time_range": f"{start_time} 至 {end_time}" if start_time and end_time else "全部时间"
    }


async def handle_analyze_anomaly(args: Dict) -> Dict:
    """分析能耗异常"""
    building_id = args.get("building_id", "B001")
    start_date = args.get("start_date")
    end_date = args.get("end_date")
    threshold = args.get("threshold", 2.0)

    # 查询数据
    sql = """
        SELECT 
            timestamp,
            electricity
        FROM energy_consumption
        WHERE building_id = %s
    """
    params = [building_id]

    if start_date:
        sql += " AND DATE(timestamp) >= %s"
        params.append(start_date)
    if end_date:
        sql += " AND DATE(timestamp) <= %s"
        params.append(end_date)

    sql += " ORDER BY timestamp"

    data = await Database.fetch_all(sql, tuple(params))

    if len(data) < 3:
        return {"status": "error", "message": "数据不足，无法分析"}

    # 提取数值
    values = [d['electricity'] for d in data]
    timestamps = [d['timestamp'] for d in data]

    # 异常检测
    anomalies = detect_anomalies_3sigma(values, timestamps, threshold)

    # 统计信息
    import numpy as np
    mean_val = np.mean(values)
    std_val = np.std(values)

    return {
        "status": "success",
        "building_id": building_id,
        "total_points": len(values),
        "anomaly_count": len(anomalies),
        "mean": float(mean_val),
        "std": float(std_val),
        "threshold": f"{threshold}倍标准差",
        "anomalies": anomalies,
        "suggestion": "建议检查异常时间点的设备运行状况" if anomalies else "无异常"
    }


async def handle_get_building(args: Dict) -> Dict:
    """获取建筑信息"""
    building_id = args.get("building_id")

    if not building_id:
        # 返回所有建筑
        sql = "SELECT id, name, type, area FROM buildings ORDER BY id"
        data = await Database.fetch_all(sql)
        return {
            "status": "success",
            "buildings": data,
            "count": len(data)
        }
    else:
        # 返回单个建筑
        sql = "SELECT id, name, type, area FROM buildings WHERE id = %s"
        data = await Database.fetch_one(sql, (building_id,))

        if not data:
            return {"status": "error", "message": f"建筑 {building_id} 不存在"}

        # 获取该建筑的最新能耗
        sql2 = """
            SELECT 
                COUNT(*) as data_count,
                MAX(timestamp) as latest_data,
                AVG(electricity) as avg_elec
            FROM energy_consumption 
            WHERE building_id = %s
        """
        stats = await Database.fetch_one(sql2, (building_id,))

        return {
            "status": "success",
            "building": data,
            "statistics": stats
        }


async def handle_get_statistics(args: Dict) -> Dict:
    """获取能耗统计"""
    building_id = args.get("building_id")
    start_date = args.get("start_date")
    end_date = args.get("end_date")
    stat_type = args.get("stat_type", "summary")

    if stat_type == "summary":
        # 时段汇总
        sql = """
            SELECT 
                DATE(timestamp) as date,
                SUM(electricity) as total_elec,
                AVG(electricity) as avg_elec,
                MAX(electricity) as max_elec,
                COUNT(*) as data_points
            FROM energy_consumption
            WHERE building_id = %s
                AND DATE(timestamp) BETWEEN %s AND %s
            GROUP BY DATE(timestamp)
            ORDER BY date
        """
        data = await Database.fetch_all(sql, (building_id, start_date, end_date))

        # 总计
        total_sql = """
            SELECT 
                SUM(electricity) as grand_total,
                AVG(electricity) as grand_avg
            FROM energy_consumption
            WHERE building_id = %s
                AND DATE(timestamp) BETWEEN %s AND %s
        """
        total = await Database.fetch_one(total_sql, (building_id, start_date, end_date))

        return {
            "status": "success",
            "type": "时段汇总",
            "daily_data": data,
            "summary": total
        }

    elif stat_type == "cop":
        # COP计算
        sql = """
            SELECT 
                timestamp,
                electricity,
                supply_temp,
                return_temp,
                CASE 
                    WHEN electricity > 0 AND supply_temp IS NOT NULL AND return_temp IS NOT NULL
                    THEN (return_temp - supply_temp) * 4.2 / electricity
                    ELSE 0
                END as cop
            FROM energy_consumption
            WHERE building_id = %s
                AND DATE(timestamp) BETWEEN %s AND %s
                AND electricity > 0
            ORDER BY timestamp
        """
        data = await Database.fetch_all(sql, (building_id, start_date, end_date))

        # 平均COP
        if data:
            avg_cop = sum(d['cop'] for d in data) / len(data)
        else:
            avg_cop = 0

        return {
            "status": "success",
            "type": "能效比(COP)分析",
            "avg_cop": round(avg_cop, 2),
            "data": data
        }

    elif stat_type == "anomaly":
        # 异常分析
        sql = """
            SELECT 
                timestamp,
                electricity,
                is_anomaly
            FROM energy_consumption
            WHERE building_id = %s
                AND DATE(timestamp) BETWEEN %s AND %s
            ORDER BY timestamp
        """
        data = await Database.fetch_all(sql, (building_id, start_date, end_date))

        anomalies = [d for d in data if d['is_anomaly']]

        return {
            "status": "success",
            "type": "异常检测",
            "total_points": len(data),
            "anomaly_count": len(anomalies),
            "anomaly_rate": f"{(len(anomalies) / len(data) * 100):.1f}%" if data else "0%",
            "anomalies": anomalies
        }

    else:
        return {"status": "error", "message": f"未知统计类型: {stat_type}"}


async def handle_device_status(args: Dict) -> Dict:
    """获取设备状态"""
    building_id = args.get("building_id")
    device_type = args.get("device_type")

    sql = """
        SELECT 
            m.id as meter_id,
            m.building_id,
            m.type,
            m.status,
            COUNT(e.id) as data_count,
            MAX(e.timestamp) as last_update,
            AVG(e.electricity) as avg_power,
            SUM(CASE WHEN e.is_anomaly = 1 THEN 1 ELSE 0 END) as anomaly_count
        FROM meters m
        LEFT JOIN energy_consumption e ON m.id = e.meter_id
        WHERE 1=1
    """
    params = []

    if building_id:
        sql += " AND m.building_id = %s"
        params.append(building_id)
    if device_type:
        sql += " AND m.type = %s"
        params.append(device_type)

    sql += " GROUP BY m.id"

    data = await Database.fetch_all(sql, tuple(params) if params else None)

    # 计算健康度
    for item in data:
        total = item['data_count'] or 1
        anomaly = item['anomaly_count'] or 0
        health_score = max(0, 100 - (anomaly / total * 100))
        item['health_score'] = round(health_score, 2)

        # 状态判断
        if item['status'] == 'abnormal':
            item['status_desc'] = '异常'
        elif health_score < 80:
            item['status_desc'] = '需关注'
        else:
            item['status_desc'] = '正常'

    return {
        "status": "success",
        "devices": data,
        "count": len(data),
        "filters": {
            "building_id": building_id,
            "device_type": device_type
        }
    }