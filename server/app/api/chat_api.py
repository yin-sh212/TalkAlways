# app/api/chat_api.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Dict, Any
import functools
import traceback
from starlette.concurrency import run_in_threadpool, iterate_in_threadpool
from app.config import config
from app.services.llm_client import llm_client
from app.services import rag_answer
from app.services import query_rewrite
from app.services import query_router
from app.services.answer_quality import is_invalid_answer
import datetime
import json
import asyncio

router = APIRouter(prefix="/api/chat", tags=["智能问答"])


class Turn(BaseModel):
    role: str = Field(..., description="user | assistant")
    # 限长：改写会把内容拼进 prompt，无上限等于把成本/超时外包给客户端
    content: str = Field(..., max_length=2000, description="该轮的文字内容")


class QuestionRequest(BaseModel):
    query: str = Field(..., description="用户输入的问题文字")
    # 可选：老客户端只发 query 也照常通过（默认空列表）。给了历史才可能触发指代消解。
    history: list[Turn] = Field(default_factory=list, max_length=20, description="最近若干轮对话")


class StreamQuestionRequest(BaseModel):
    query: str = Field(..., description="用户输入的问题文字")
    history: list[Turn] = Field(default_factory=list, max_length=20, description="最近若干轮对话")


def _log_route(query: str) -> None:
    """影子路由（#13）：只打分打日志，不改变端点行为。"""
    if not config.ROUTE_ENABLED:
        return
    try:
        print(f"[route] {query_router.route(query)}")
    except Exception as exc:
        print(f"[route] 失败：{exc}")


def _effective_query(query: str, history) -> str:
    """检索前做指代消解；不触发时逐字返回原 query。"""
    if config.RAG_REWRITE_ENABLED and history:
        return query_rewrite.rewrite_if_needed(query, history)
    return query


def _require_query(query: str) -> str:
    """取出非空 query；空/纯空白直接 400。

    检索 + rerank 是本系统最贵的操作（rerank 独占约 96%），不该被空串触发；
    前端有守卫，但 API 层必须自己兜住（直连接口 / 其它客户端）。
    """
    q = query.strip()
    if not q:
        raise HTTPException(status_code=400, detail="query 不能为空")
    return q


def _plain_prompt(query: str) -> str:
    """不检索时的提示词（原有版本，未改动）。"""
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    system_prompt = """你是一位专业的建筑能源管理和设备运维专家。请针对用户的具体问题给出专业、简洁的回答。
注意：
1. 直接回答问题，不要重复自我介绍
2. 如果是查询类问题，说明需要的数据维度
3. 如果是故障处理，给出具体的排查步骤
4. 保持回答在 200-500 字之间"""
    return f"{system_prompt}\n\n当前时间：{current_time}\n\n用户问题：{query}"


def _generate_plain(query: str) -> Dict[str, Any]:
    """无检索时的回答：主助手 → 备用助手 → 通用模板（逻辑与接入前一致）。"""
    full_prompt = _plain_prompt(query)
    answer = llm_client.generate(full_prompt, use_alt=False)

    if is_invalid_answer(answer):
        print("⚠️ 主助手无效，尝试使用备用助手...")
        answer = llm_client.generate(full_prompt, use_alt=True)

    if is_invalid_answer(answer):
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


async def generate_answer_with_rag(query: str, history=None) -> Dict[str, Any]:
    """优先用 hybrid RAG 回答（检索国标语料），未命中或出错时降级普通 LLM。"""
    if config.RAG_ENABLED:
        effective = await run_in_threadpool(_effective_query, query, history)
        try:
            hits = await run_in_threadpool(rag_answer.retrieve, effective)
            if hits:
                prompt = rag_answer.build_prompt(effective, hits)
                answer = await run_in_threadpool(
                    functools.partial(llm_client.generate, prompt, use_alt=False)
                )
                if is_invalid_answer(answer):
                    answer = await run_in_threadpool(
                        functools.partial(llm_client.generate, prompt, use_alt=True)
                    )
                if not is_invalid_answer(answer):
                    return {
                        "answer": answer,
                        "sources": rag_answer.to_sources(hits),
                        "mode": "rag",
                    }
                print("⚠️ RAG 回答无效，降级到普通 LLM")
        except Exception as exc:
            print(f"RAG 回答失败，降级到普通 LLM：{exc}")

    return await run_in_threadpool(_generate_plain, query)


async def stream_generator(query: str, history=None):
    """SSE 流式生成器：先发心跳帧冲掉响应头，再检索，再流式回答。"""
    try:
        # 先发一帧空 content：让响应头立即下发，避免检索的十几秒里客户端
        # 一直等不到首字节。前端只读 data.content，空串追加无副作用。
        yield f"data: {json.dumps({'code': 200, 'data': {'content': ''}}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0)

        prompt = _plain_prompt(query)
        sources = []
        if config.RAG_ENABLED:
            # 改写放在心跳帧之后、检索之前：首字节延迟不受影响。
            effective = await run_in_threadpool(_effective_query, query, history)
            try:
                hits = await run_in_threadpool(rag_answer.retrieve, effective)
                if hits:
                    prompt = rag_answer.build_prompt(effective, hits)
                    sources = rag_answer.to_sources(hits)
            except Exception as exc:
                print(f"流式 RAG 检索失败，降级普通 LLM：{exc}")

        # 直接迭代LLM的流式输出，每获取一个chunk就立即yield。
        # generate_stream 是**同步生成器**（内部用 requests），直接 for 迭代会把
        # 事件循环**阻塞到整段流结束** —— 期间 /api/health 等所有接口都不响应，
        # 而接上 RAG 后单次流更长（检索十几秒 + 生成）。故用 iterate_in_threadpool
        # 把每次 next() 丢进线程池；SSE 帧格式不变。
        async for chunk in iterate_in_threadpool(llm_client.generate_stream(prompt)):
            sse_data = json.dumps({
                "code": 200,
                "data": {
                    "content": chunk
                }
            }, ensure_ascii=False)
            yield f"data: {sse_data}\n\n"

        # 引用帧：该帧**无 content 字段** ⇒ 老前端只读 data.content 会自动忽略，
        # 零破坏；新前端读 data.sources 展示引用块。必须放在 [DONE] 之前。
        if sources:
            sse_sources = json.dumps({
                "code": 200,
                "data": {"sources": sources}
            }, ensure_ascii=False)
            yield f"data: {sse_sources}\n\n"

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
    query = _require_query(question.query)  # 空/空白直接 400，先于最贵的检索
    print(f"收到问题：{query}")
    _log_route(query)

    history = [t.model_dump() for t in question.history]
    try:
        result = await generate_answer_with_rag(query, history)
        # generate() 可能返回 None（网络/API 异常时），len(None) 会 TypeError
        answer = result["answer"] or ""

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
    # 校验必须在 try 之外：否则 HTTPException 会被下面 except Exception 吞成 200。
    query = _require_query(question.query)
    print(f"收到流式问题：{query}")
    _log_route(query)

    history = [t.model_dump() for t in question.history]
    try:
        # 检索与 prompt 拼装都放进生成器内部：否则响应头要等检索完（十几秒）
        # 才下发，客户端首字节超时。生成器会先发心跳帧冲掉响应头。
        return StreamingResponse(
            stream_generator(query, history),
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
