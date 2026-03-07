# app/api/chat_api.py
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict
import os
# from app.services.rag_service import rag_service
from app.services.rag_service_win import rag_service
from app.database.db import Database
import datetime

router = APIRouter(prefix="/api/chat", tags=["智能问答"])


# 请求模型
class Question(BaseModel):
    query: str
    building_id: Optional[str] = None
    session_id: Optional[str] = None


# 响应模型
class Answer(BaseModel):
    answer: str
    type: str = "general"
    sources: Optional[List[Dict]] = None
    data: Optional[Dict] = None


@router.post("/ask", response_model=Answer)
async def ask_question(question: Question):
    """智能问答接口 - 简化版"""
    print(f"收到问题: {question.query}")

    try:
        # 简单的问题分类
        q = question.query.lower()
        building = question.building_id or "B001"

        # 1. 数据查询类
        if any(k in q for k in ['用电', '电量', '能耗', '多少', '统计']):
            return await handle_data_query_simple(q, building)

        # 2. 知识查询类
        elif any(k in q for k in ['故障', '怎么', '如何', '步骤', '规范', '处理']):
            return await handle_knowledge_query_simple(q)

        # 3. 默认回复
        else:
            return Answer(
                answer="你好！我是智能运维助手。我可以回答：\n"
                       "1. 能耗查询（如'B001昨天用电量'）\n"
                       "2. 运维知识（如'冷水机组故障处理'）\n"
                       "3. 异常分析（如'分析能耗异常'）",
                type="help"
            )

    except Exception as e:
        print(f"处理失败: {e}")
        return Answer(
            answer=f"抱歉，处理您的问题时出现错误: {str(e)}",
            type="error"
        )


async def handle_data_query_simple(query: str, building: str):
    """简化版数据查询"""
    try:
        # 简单的SQL查询
        if "昨天" in query:
            sql = """
                SELECT SUM(electricity) as total 
                FROM energy_consumption 
                WHERE building_id = %s 
                AND DATE(timestamp) = CURDATE() - INTERVAL 1 DAY
            """
        elif "平均" in query:
            sql = """
                SELECT AVG(electricity) as value 
                FROM energy_consumption 
                WHERE building_id = %s
            """
        else:
            sql = """
                SELECT SUM(electricity) as total 
                FROM energy_consumption 
                WHERE building_id = %s
            """

        result = await Database.fetch_one(sql, (building,))

        if result and (result.get('total') or result.get('value')):
            value = result.get('total') or result.get('value')
            return Answer(
                answer=f"建筑 {building} 的查询结果: {float(value):.2f} kWh",
                type="data",
                data={"value": float(value)}
            )
        else:
            return Answer(
                answer=f"未找到建筑 {building} 的相关数据",
                type="data"
            )

    except Exception as e:
        return Answer(
            answer=f"数据查询失败: {str(e)}",
            type="error"
        )


async def handle_knowledge_query_simple(query: str):
    """简化版知识查询"""
    try:
        # 使用RAG服务搜索
        results = rag_service.search(query, k=2)

        if results:
            answer = "📚 找到相关信息：\n\n"
            for i, r in enumerate(results, 1):
                answer += f"{i}. {r['content'][:200]}...\n\n"
            return Answer(
                answer=answer,
                type="knowledge",
                sources=results
            )
        else:
            # 默认知识库
            knowledge_base = {
                "冷水机组": "冷水机组高压报警处理：\n1. 检查冷却水泵\n2. 检查冷却塔\n3. 清洗填料",
                "空调": "空调系统运维：\n1. 定期清洗过滤网\n2. 检查冷媒压力\n3. 监测运行参数",
                "能耗": "能耗异常原因：\n1. 设备效率下降\n2. 运行时间过长\n3. 参数设置不合理"
            }

            for key, value in knowledge_base.items():
                if key in query:
                    return Answer(answer=value, type="knowledge")

            return Answer(
                answer="抱歉，知识库中没有找到相关信息。",
                type="knowledge"
            )

    except Exception as e:
        return Answer(
            answer=f"知识查询失败: {str(e)}",
            type="error"
        )


# 健康检查接口
@router.get("/health")
async def chat_health():
    return {"status": "ok", "service": "chat_api"}