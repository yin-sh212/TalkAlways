# app/api/chat_api.py
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
import os
import traceback
from app.services.rag_pipeline import rag_pipeline
from app.services.llm_client import llm_client
from app.database.db import Database
import datetime

router = APIRouter(prefix="/api/chat", tags=["智能问答"])


class Question(BaseModel):
    """问答请求模型"""
    query: str = Field(
        ...,
        description="用户问题（必填）",
        example="冷水机组故障怎么处理"
    )


class ApiResponse(BaseModel):
    """统一 API 响应结构"""
    code: int = Field(..., description="状态码：200 成功，其他表示失败")
    message: str = Field(..., description="响应消息")
    data: Optional[Dict] = Field(None, description="响应数据")


# RAG 初始化标志
_rag_initialized = False


async def init_rag():
    """初始化 RAG（在首次使用时）"""
    global _rag_initialized
    if not _rag_initialized:
        count = rag_pipeline.initialize_knowledge_base()
        print(f"✅ RAG 初始化完成，加载 {count} 个文档块")
        _rag_initialized = True


@router.post(
    "/ask",
    response_model=ApiResponse,
    summary="智能问答",
    description="所有问题都通过 RAGFlow 助手回答"
)
async def ask_question(question: Question):
    """
    RAG 问答接口 - 统一调用 ML 同学的 RAGFlow 助手

    ## 使用示例

    ### 基础问答
    ```json
    {
        "query": "冷水机组故障怎么处理"
    }
    ```
    """
    # 确保 RAG 已初始化
    await init_rag()

    print(f"📝 收到问题：{question.query}")

    try:
        # 获取原始问题
        original_query = question.query
        building_id = "B001"  # 默认建筑编号

        # ========== 步骤 1：处理数据查询类问题 ==========
        # 检查问题是否涉及数据查询
        data_keywords = ['用电', '电量', '能耗', '多少', '统计', 'kwh', '度', '水耗', '用水',
                         '7 月', '8 月', '9 月', '昨天', '今天', '上周', '本月', '上月',
                         '日能耗', '月能耗', '年能耗', '用电量', '用水量']
        is_data_query = any(keyword in original_query for keyword in data_keywords)

        enhanced_query = original_query

        if is_data_query:
            # 查询数据库获取实时数据
            try:
                # 查询总用电量
                sql_total = "SELECT SUM(electricity) as total FROM energy_consumption WHERE building_id = %s"
                result_total = await Database.fetch_one(sql_total, (building_id,))
                total_value = result_total['total'] if result_total else 0

                # 查询最近 7 天趋势
                sql_trend = """
                    SELECT 
                        DATE(timestamp) as date,
                        SUM(electricity) as daily_total
                    FROM energy_consumption 
                    WHERE building_id = %s 
                        AND timestamp >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                    GROUP BY DATE(timestamp)
                    ORDER BY date DESC
                """
                trend_data = await Database.fetch_all(sql_trend, (building_id,))

                # 构建数据上下文
                data_context = f"""
【实时数据】
- 建筑编号：{building_id}
- 总用电量：{float(total_value):.2f} kWh
- 最近 7 天趋势：
"""
                for item in trend_data[:7]:
                    data_context += f"  - {item['date']}: {float(item['daily_total']):.2f} kWh\n"

                # 增强问题
                enhanced_query = f"{original_query}\n\n{data_context}"
                print(f"📊 数据查询增强完成")

            except Exception as db_error:
                print(f"⚠️ 数据库查询失败：{db_error}")
                # 即使数据库查询失败，也继续处理
                enhanced_query = f"{original_query}\n\n【提示】数据库查询失败，请检查数据源"

        # ========== 步骤 2：调用 RAGFlow 助手 ==========
        # 使用主助手回答问题
        result = rag_pipeline.answer(enhanced_query, use_alt=False)

        # ========== 步骤 3：返回结果 ==========
        print(f"✅ 回答成功，长度：{len(result['answer'])} 字符")

        return ApiResponse(
            code=200,
            message="回答成功",
            data={
                "answer": result['answer'],
                "type": "knowledge",
                "sources": result.get('sources')
            }
        )

    except Exception as e:
        # ========== 错误处理 ==========
        print(f"❌ 处理失败：{e}")
        traceback.print_exc()

        # 友好的错误提示
        error_message = str(e)
        if "ConnectionError" in error_message or "timeout" in error_message.lower():
            user_message = "网络连接失败，请稍后重试。"
        elif "404" in error_message:
            user_message = "RAGFlow 服务未找到，请联系管理员检查服务状态。"
        elif "500" in error_message:
            user_message = "服务器内部错误，请稍后重试。"
        elif "Unauthorized" in error_message or "401" in error_message:
            user_message = "API 认证失败，请联系管理员检查配置。"
        else:
            user_message = f"处理失败：{error_message[:100]}"

        return ApiResponse(
            code=500,
            message=f"抱歉，{user_message}",
            data=None
        )


@router.get("/health")
async def health():
    """健康检查"""
    stats = rag_pipeline.get_stats()
    return {
        "status": "ok",
        "service": "chat_api",
        "rag_stats": stats
    }


@router.get("/assistants")
async def list_assistants():
    """列出可用的聊天助手"""
    return {
        "assistants": [
            {
                "name": "main",
                "description": "主聊天助手",
                "chat_id": llm_client.chat_id_main
            },
            {
                "name": "alt",
                "description": "备用聊天助手",
                "chat_id": llm_client.chat_id_alt
            }
        ],
        "default": "main"
    }