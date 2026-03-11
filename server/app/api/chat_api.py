# app/api/chat_api.py
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel
from typing import Optional, List, Dict
import os
from app.services.rag_pipeline import rag_pipeline
from app.services.llm_client import llm_client
from app.database.db import Database
import datetime

router = APIRouter(prefix="/api/chat", tags=["智能问答"])


class Question(BaseModel):
    query: str
    building_id: Optional[str] = None
    session_id: Optional[str] = None


class AnswerResponse(BaseModel):
    answer: str
    type: str
    sources: Optional[List[Dict]] = None
    data: Optional[Dict] = None


class MLModelConfig(BaseModel):
    """配置ML同学部署的模型"""
    base_url: str = "https://2f34c8d8.r20.cpolar.top"
    embed_model: str = "nomic-embed-text"
    llm_model: str = "gemma3:4b"
    use_real_embedding: bool = True


@router.post(
    "/configure-ml-model",
    responses={
        200: {
            "description": "模型配置成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "成功",
                        "data": {
                            "status": "ok",
                            "message": "已配置ML同学模型: https://335b95bf.r20.cpolar.top",
                            "config": {
                                "base_url": "https://335b95bf.r20.cpolar.top",
                                "embed_model": "nomic-embed-text",
                                "llm_model": "gemma3:4b",
                                "use_real_embedding": True
                            }
                        }
                    }
                }
            }
        },
        500: {
            "description": "配置失败",
            "content": {
                "application/json": {
                    "example": {
                        "code": 500,
                        "message": "配置失败: 连接超时",
                        "data": None
                    }
                }
            }
        }
    }
)
async def configure_ml_model(config: MLModelConfig):
    """配置ML同学部署的模型（Ollama + RAGflow）"""
    try:
        llm_client.base_url = config.base_url
        llm_client.embed_model = config.embed_model
        llm_client.llm_model = config.llm_model
        llm_client.available = True

        from app.services.vector_db import vector_db
        vector_db.use_real_embedding = config.use_real_embedding

        return {
            "code": 200,
            "message": "成功",
            "data": {
                "status": "ok",
                "message": f"已配置ML同学模型: {config.base_url}",
                "config": {
                    "base_url": config.base_url,
                    "embed_model": config.embed_model,
                    "llm_model": config.llm_model,
                    "use_real_embedding": config.use_real_embedding
                }
            }
        }
    except Exception as e:
        return {
            "code": 500,
            "message": f"配置失败: {str(e)}",
            "data": None
        }


@router.get(
    "/model-status",
    responses={
        200: {
            "description": "成功获取模型状态",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "成功",
                        "data": {
                            "status": "ok",
                            "base_url": "https://335b95bf.r20.cpolar.top",
                            "embed_model": "nomic-embed-text",
                            "llm_model": "gemma3:4b",
                            "rag_stats": {
                                "vector_db": {
                                    "total_docs": 297,
                                    "embedding_model": "真实",
                                    "embedding_dim": 768
                                },
                                "knowledge_base": {
                                    "documents": ["运维手册.txt", "节能规范.txt", "故障案例.txt"]
                                },
                                "llm_available": True,
                                "initialized": True
                            }
                        }
                    }
                }
            }
        }
    }
)
async def get_model_status():
    """获取当前模型状态"""
    try:
        stats = rag_pipeline.get_stats()
        return {
            "code": 200,
            "message": "成功",
            "data": {
                "status": "ok" if llm_client.available else "disconnected",
                "base_url": getattr(llm_client, 'base_url', None),
                "embed_model": getattr(llm_client, 'embed_model', None),
                "llm_model": getattr(llm_client, 'llm_model', None),
                "rag_stats": stats
            }
        }
    except Exception as e:
        return {
            "code": 500,
            "message": f"获取状态失败: {str(e)}",
            "data": None
        }


@router.on_event("startup")
async def init_rag():
    """启动时初始化RAG"""
    count = rag_pipeline.initialize_knowledge_base()
    print(f"✅ RAG初始化完成，加载 {count} 个文档块")


@router.post(
    "/ask",
    response_model=AnswerResponse,
    responses={
        200: {
            "description": "成功返回问答结果",
            "content": {
                "application/json": {
                    "examples": {
                        "data_query": {
                            "summary": "数据查询类问题",
                            "value": {
                                "code": 200,
                                "message": "成功",
                                "data": {
                                    "answer": "建筑 OFF-01 的总用电量为 1245.6 kWh",
                                    "type": "data",
                                    "sources": None,
                                    "data": {"value": 1245.6}
                                }
                            }
                        },
                        "knowledge_query": {
                            "summary": "知识查询类问题",
                            "value": {
                                "code": 200,
                                "message": "成功",
                                "data": {
                                    "answer": "📚 找到相关信息：\n\n1. 冷水机组高压报警处理步骤：\n- 检查冷却水泵是否运行正常\n- 检查冷却塔风扇是否运转\n- 清洗冷却塔填料...",
                                    "type": "knowledge",
                                    "sources": [
                                        {
                                            "content": "冷水机组高压报警处理步骤：1. 检查冷却水泵...",
                                            "metadata": {"source": "运维手册.txt"},
                                            "score": 0.89
                                        }
                                    ],
                                    "data": None
                                }
                            }
                        },
                        "diagnosis": {
                            "summary": "异常诊断类问题",
                            "value": {
                                "code": 200,
                                "message": "成功",
                                "data": {
                                    "answer": "🔍 检测到建筑 OFF-01 最近有 3 次异常：\n\n• 2025-01-15 14:00:00: 用电量 345.2 kWh\n\n可能的原因：当日室外温度较高（32℃），制冷负荷增大。",
                                    "type": "diagnosis",
                                    "sources": [
                                        {
                                            "content": "能耗异常的可能原因：\n1. 设备效率下降\n2. 运行时间过长",
                                            "score": 0.92
                                        }
                                    ],
                                    "data": {
                                        "anomalies": [
                                            {
                                                "timestamp": "2025-01-15 14:00:00",
                                                "electricity": 345.2
                                            }
                                        ]
                                    }
                                }
                            }
                        },
                        "help": {
                            "summary": "帮助信息",
                            "value": {
                                "code": 200,
                                "message": "成功",
                                "data": {
                                    "answer": "你好！我是智能运维助手。我可以回答：\n1. 能耗查询（如'OFF-01昨天用电量'）\n2. 运维知识（如'冷水机组故障处理'）\n3. 异常分析（如'分析能耗异常'）",
                                    "type": "help",
                                    "sources": None,
                                    "data": None
                                }
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
                        "message": "问题不能为空",
                        "data": None
                    }
                }
            }
        },
        500: {
            "description": "服务器内部错误",
            "content": {
                "application/json": {
                    "example": {
                        "code": 500,
                        "message": "处理失败: 数据库连接错误",
                        "data": None
                    }
                }
            }
        }
    }
)
async def ask_question(question: Question):
    """真正的RAG问答接口"""
    print(f"收到问题: {question.query}")

    try:
        if not question.query:
            return {
                "code": 400,
                "message": "问题不能为空",
                "data": None
            }

        q = question.query.lower()
        building = question.building_id or "B001"

        # 判断问题类型
        if any(k in q for k in ['用电', '电量', '能耗', '多少', '统计']):
            # 数据查询
            sql = "SELECT SUM(electricity) as total FROM energy_consumption WHERE building_id = %s"
            result = await Database.fetch_one(sql, (building,))
            value = result['total'] if result and result.get('total') else 0

            return {
                "code": 200,
                "message": "成功",
                "data": {
                    "answer": f"建筑 {building} 的总用电量为 {float(value):.2f} kWh",
                    "type": "data",
                    "sources": None,
                    "data": {"value": float(value)}
                }
            }

        elif any(k in q for k in ['故障', '怎么', '如何', '步骤', '规范', '处理']):
            # 知识问答
            result = rag_pipeline.answer(q)
            return {
                "code": 200,
                "message": "成功",
                "data": {
                    "answer": result['answer'],
                    "type": "knowledge",
                    "sources": result.get('sources', []),
                    "data": None
                }
            }

        elif any(k in q for k in ['异常', '为什么', '原因', '分析']):
            # 异常诊断
            sql = """
                SELECT timestamp, electricity 
                FROM energy_consumption 
                WHERE building_id = %s AND is_anomaly = 1
                ORDER BY timestamp DESC LIMIT 5
            """
            anomalies = await Database.fetch_all(sql, (building,))

            result = rag_pipeline.hybrid_answer(
                q,
                data_context={"building": building, "anomalies": anomalies}
            )

            return {
                "code": 200,
                "message": "成功",
                "data": {
                    "answer": result['answer'],
                    "type": "diagnosis",
                    "sources": result.get('sources', []),
                    "data": {"anomalies": anomalies} if anomalies else None
                }
            }

        else:
            return {
                "code": 200,
                "message": "成功",
                "data": {
                    "answer": "你好！我是智能运维助手。我可以回答：\n"
                              "1. 能耗查询（如'OFF-01昨天用电量'）\n"
                              "2. 运维知识（如'冷水机组故障处理'）\n"
                              "3. 异常分析（如'分析能耗异常'）",
                    "type": "help",
                    "sources": None,
                    "data": None
                }
            }

    except Exception as e:
        print(f"处理失败: {e}")
        return {
            "code": 500,
            "message": f"处理失败: {str(e)}",
            "data": None
        }


@router.get(
    "/health",
    responses={
        200: {
            "description": "健康检查成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "成功",
                        "data": {
                            "status": "ok",
                            "service": "chat_api",
                            "rag_stats": {
                                "vector_db": {
                                    "total_docs": 297,
                                    "embedding_model": "真实",
                                    "embedding_dim": 768
                                },
                                "knowledge_base": {
                                    "documents": ["运维手册.txt", "节能规范.txt"]
                                },
                                "llm_available": True,
                                "initialized": True
                            }
                        }
                    }
                }
            }
        }
    }
)
async def health():
    """健康检查"""
    try:
        stats = rag_pipeline.get_stats()
        return {
            "code": 200,
            "message": "成功",
            "data": {
                "status": "ok",
                "service": "chat_api",
                "rag_stats": stats
            }
        }
    except Exception as e:
        return {
            "code": 500,
            "message": f"健康检查失败: {str(e)}",
            "data": None
        }