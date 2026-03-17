# app/api/nl2sql_api.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from app.services.nl2sql_service import nl2sql
from app.database.db import Database

router = APIRouter(prefix="/api/nl2sql", tags=["自然语言查询"])


class NLQueryRequest(BaseModel):
    query: str


class NLQueryResponse(BaseModel):
    code: int
    message: str
    data: Optional[Dict[str, Any]] = None
    # 去掉 sql 字段


@router.post("/query", response_model=NLQueryResponse)
async def natural_language_query(request: NLQueryRequest):
    """
    自然语言查询接口

    支持的查询类型：
    - 能耗查询： "Eagle_education_Wesley昨天用电量多少？"
    - 统计查询： "7月份的平均用电量"
    - 异常查询： "本周的异常数据"
    - 对比查询： "哪个建筑能耗最高？"
    """
    try:
        # 1. 解析自然语言
        parsed = nl2sql.parse(request.query)

        if not parsed['sql']:
            return {
                "code": 400,
                "message": parsed.get('message', '无法理解您的查询'),
                "data": None
            }

        print(f"📝 生成的SQL: {parsed['sql']}")
        print(f"📝 参数: {parsed.get('params', [])}")

        # 2. 执行SQL
        result = await Database.fetch_all(
            parsed['sql'],
            tuple(parsed.get('params', [])) if parsed.get('params') else None
        )

        # 3. 格式化结果
        formatted = format_result(parsed['type'], result, request.query)

        return {
            "code": 200,
            "message": "成功",
            "data": formatted
        }

    except Exception as e:
        return {
            "code": 500,
            "message": f"查询失败: {str(e)}",
            "data": None
        }


def format_result(query_type: str, result: List[Dict], query: str) -> Dict:
    """格式化查询结果 - 添加智能单位说明"""
    if not result:
        return {"answer": "没有找到相关数据", "data": []}

    if query_type == "energy":
        value = result[0]['value'] if result else 0

        # 智能判断时间粒度
        if any(k in query for k in ['今天', '昨天', '前天', '日']):
            period = "日累计"
            # 24小时总和
            avg_per_hour = value / 24
            answer = f"查询结果: {value:.2f} kWh ({period})，平均每小时 {avg_per_hour:.2f} kWh"
        elif any(k in query for k in ['月', '月份']):
            period = "月累计"
            # 估算天数（7月31天，8月31天）
            days = 31 if '7月' in query or '8月' in query else 30
            avg_per_day = value / days
            answer = f"查询结果: {value:.2f} kWh ({period})，平均每天 {avg_per_day:.2f} kWh"
        else:
            answer = f"查询结果: {value:.2f} kWh"

        return {
            "answer": answer,
            "data": result
        }

    elif query_type == "cooling":
        value = result[0]['value'] if result else 0
        return {
            "answer": f"冷冻水冷量: {value:.2f}",
            "data": result
        }

    elif query_type == "heating":
        value = result[0]['value'] if result else 0
        return {
            "answer": f"供热能耗: {value:.2f}",
            "data": result
        }

    elif query_type == "temperature":
        value = result[0]['value'] if result else 0
        # 温度一般用平均
        return {
            "answer": f"平均气温: {value:.1f}℃",
            "data": result
        }

    elif query_type == "statistics":
        days = len(result)
        total = sum(r['total_elec'] for r in result)
        return {
            "answer": f"共 {days} 天数据，总用电量 {total:.2f} kWh，平均每天 {total / days:.2f} kWh",
            "data": result
        }

    elif query_type == "anomaly":
        return {
            "answer": f"找到 {len(result)} 个异常点",
            "data": result
        }

    elif query_type == "comparison":
        if result:
            top = result[0]
            return {
                "answer": f"能耗最高的建筑是 {top['building_id']}，总用电量 {top['total_elec']:.2f} kWh",
                "data": result
            }

    return {"answer": "查询完成", "data": result}

@router.get("/examples")
async def get_examples():
    """获取示例查询"""
    return {
        "code": 200,
        "message": "成功",
        "data": [
            "Eagle_education_Wesley昨天用电量多少？",
            "7月份的平均用电量",
            "本周的异常数据",
            "哪个建筑能耗最高？",
            "对比各建筑的冷冻水冷量",
            "8月15日的气温是多少？"
        ]
    }