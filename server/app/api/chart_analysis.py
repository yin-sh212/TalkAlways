# app/api/chart_analysis.py
"""
图表 AI 分析接口
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
import json
import time
import traceback
from app.services.chart_analyzer import chart_analyzer

router = APIRouter(prefix="/api/chart", tags=["图表 AI 分析"])


class ChartAnalysisRequest(BaseModel):
    """图表分析请求体"""
    chartType: str = Field(..., description="图表类型：line, bar, pie, radar, scatter, area")
    chartTitle: str = Field(..., description="图表标题")
    xAxis: Optional[List[str]] = Field(default=[], description="X 轴数据")
    yAxisLabel: Optional[str] = Field(default="", description="Y 轴标签")
    series: List[Dict[str, Any]] = Field(..., description="系列数据")
    analysisType: Optional[str] = Field(default="summary", description="分析类型：summary, trend, anomaly, comparison")
    customPrompt: Optional[str] = Field(default="", description="自定义提示")
    context: Optional[Dict[str, Any]] = Field(default={}, description="上下文信息")


@router.post("/analyze/stream")
async def analyze_chart_stream(request: ChartAnalysisRequest):
    """
    AI 分析图表数据（流式）
    """
    try:
        # 创建 SSE 流式生成器
        return StreamingResponse(
            stream_generator(request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"流式分析失败：{str(e)}")


async def stream_generator(request: ChartAnalysisRequest):
    """SSE 流式生成器"""
    try:
        # 发送开始消息
        yield format_sse_message("status", {
            "message": "开始分析...",
            "progress": 0
        })
        
        # 调用分析服务（流式）
        async for chunk in chart_analyzer.analyze_chart_stream_async(
            chart_type=request.chartType,
            chart_title=request.chartTitle,
            xAxis=request.xAxis,
            series=request.series,
            analysis_type=request.analysisType,
            custom_prompt=request.customPrompt
        ):
            yield format_sse_message("result", {
                "content": chunk
            })
        
        # 发送完成消息
        yield format_sse_message("done", {
            "message": "分析完成"
        })
        
    except Exception as e:
        print(f"流式分析失败：{e}")
        traceback.print_exc()
        # 发送错误消息
        yield format_sse_message("error", {
            "message": f"分析失败：{str(e)}"
        })


def format_sse_message(event_type: str, data: Any) -> str:
    """格式化 SSE 消息"""
    sse_data = json.dumps({
        "type": event_type,
        "data": data
    }, ensure_ascii=False)
    return f"data: {sse_data}\n\n"
