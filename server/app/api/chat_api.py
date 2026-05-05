# app/api/chat_api.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Dict, Any
import traceback
from app.services.rag_pipeline import rag_pipeline
from app.services.llm_client import llm_client
import datetime
import json
import asyncio

router = APIRouter(prefix="/api/chat", tags=["智能问答"])


class QuestionRequest(BaseModel):
    query: str = Field(..., description="用户输入的问题文字")


class StreamQuestionRequest(BaseModel):
    query: str = Field(..., description="用户输入的问题文字")


def generate_answer_with_rag(query: str) -> Dict[str, Any]:
    """优先使用 RAG，未命中时降级到普通 LLM。"""
    rag_result: Dict[str, Any] = {}

    # try:
    #     rag_result = rag_pipeline.answer(query)
    #     if rag_result.get("sources"):
    #         return {
    #             "answer": rag_result.get("answer", ""),
    #             "sources": rag_result.get("sources", []),
    #             "mode": "rag",
    #         }
    # except Exception as exc:
    #     print(f"RAG 回答失败，降级到普通 LLM：{exc}")

    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    system_prompt = """你是一位专业的建筑能源管理和设备运维专家。请针对用户的具体问题给出专业、简洁的回答。
注意：
1. 直接回答问题，不要重复自我介绍
2. 如果是查询类问题，说明需要的数据维度
3. 如果是故障处理，给出具体的排查步骤
4. 保持回答在 200-500 字之间"""

    full_prompt = f"{system_prompt}\n\n当前时间：{current_time}\n\n用户问题：{query}"
    answer = llm_client.generate(full_prompt, use_alt=False)

    if answer is None or (len(answer) > 300 and ("中建八局二建" in answer or "擎翼数字中枢" in answer)):
        print("⚠️ 主助手无效，尝试使用备用助手...")
        answer = llm_client.generate(full_prompt, use_alt=True)

    if answer is None or (len(answer) > 300 and ("中建八局二建" in answer or "擎翼数字中枢" in answer)):
        print("⚠️ 备用助手也无效，使用通用回答模板...")
        answer = f"""您好！关于"{query}"这个问题，我需要更多上下文信息才能给您准确的回答。

建议您：
1. **明确建筑/设备编号**：如"A 栋教学楼"、"3 号配电箱"
2. **指定时间范围**：如"昨天"、"最近一周"、"2024 年 10 月"
3. **描述具体问题**：如"用电量异常偏高"、"设备频繁报警"

示例提问：
- "A 栋教学楼昨天的单位建筑面积能耗是多少？"
- "冷水机组高压报警怎么处理？请给出具体步骤"
- "分析最近一周 3 号配电箱的用电异常"

我会根据您提供的详细信息，给出更精准的专业建议。"""

    return {
        "answer": answer,
        "sources": [],
        "mode": "llm",
    }


async def stream_generator(full_prompt: str):
    """SSE 流式生成器 - 真正的异步流式版本"""
    try:
        from app.services.llm_client import llm_client
        
        # 直接迭代LLM的流式输出，每获取一个chunk就立即yield
        for chunk in llm_client.generate_stream(full_prompt):
            sse_data = json.dumps({
                "code": 200,
                "data": {
                    "content": chunk
                }
            }, ensure_ascii=False)
            yield f"data: {sse_data}\n\n"
            # 让出事件循环控制权，确保数据立即发送
            await asyncio.sleep(0)
        
        # 发送结束标记
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        print(f"流式生成失败：{e}")
        traceback.print_exc()
        # 发送错误消息
        sse_error = json.dumps({
            "code": 500,
            "data": {
                "content": f"生成失败：{str(e)}"
            }
        }, ensure_ascii=False)
        yield f"data: {sse_error}\n\n"
        yield "data: [DONE]\n\n"


@router.post(
    "/ask",
    summary="智能问答",
    description="所有问题都通过 RAGFlow 助手回答"
)
async def ask_question(question: QuestionRequest):
    """智能问答接口 - 调用真实 AI API"""
    print(f"收到问题：{question.query}")

    try:
        result = generate_answer_with_rag(question.query)
        answer = result["answer"]

        print(f"✅ 回答成功，长度：{len(answer)} 字符")
        
        # 统一响应格式
        return {
            "code": 200,
            "message": "success",
            "data": {
                "answer": answer,
                "mode": result.get("mode", "llm"),
                "sources": result.get("sources", []),
            }
        }

    except Exception as e:
        print(f"处理失败：{e}")
        traceback.print_exc()
        return {
            "code": 500,
            "message": f"处理失败：{str(e)}",
            "data": {
                "answer": "抱歉，服务器内部错误，请稍后再试。"
            }
        }


@router.post(
    "/ask/stream",
    summary="智能问答（流式输出）",
    description="使用 SSE 流式输出 AI 回答"
)
async def ask_question_stream(question: StreamQuestionRequest):
    """智能问答接口 - 流式版本,直接使用 DeepSeek"""
    print(f"收到流式问题：{question.query}")

    try:
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        system_prompt = """你是一位专业的建筑能源管理和设备运维专家。请针对用户的具体问题给出专业、简洁的回答。
注意：
1. 直接回答问题，不要重复自我介绍
2. 如果是查询类问题，说明需要的数据维度
3. 如果是故障处理，给出具体的排查步骤
4. 保持回答在 200-500 字之间"""

        full_prompt = f"{system_prompt}\n\n当前时间：{current_time}\n\n用户问题：{question.query}"
        
        # 返回 SSE 流
        return StreamingResponse(
            stream_generator(full_prompt),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    except Exception as e:
        print(f"流式接口失败：{e}")
        traceback.print_exc()
        return {
            "code": 500,
            "message": f"处理失败：{str(e)}",
            "data": {
                "answer": "抱歉，服务器内部错误，请稍后再试。"
            }
        }
