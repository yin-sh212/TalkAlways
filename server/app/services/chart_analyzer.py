# app/services/chart_analyzer.py
"""
图表 AI 分析业务逻辑
"""
import json
import time
from typing import Dict, List, Any, Optional
from app.services.llm_client import llm_client
from app.prompts.chart_analysis_templates import get_prompt_template


class ChartAnalyzer:
    """图表 AI 分析器"""
    
    @staticmethod
    def format_xaxis_description(xAxis: Optional[List[str]]) -> str:
        """格式化 X 轴描述"""
        if not xAxis:
            return "无 X 轴数据"
        return f"从 {xAxis[0]} 到 {xAxis[-1]}，共{len(xAxis)}个时间点"
    
    @staticmethod
    def format_series_description(series: List[Dict[str, Any]]) -> str:
        """格式化系列数据描述"""
        descriptions = []
        for s in series:
            data = s.get('data', [])
            if data:
                # 计算统计信息
                numeric_data = [float(x) for x in data if isinstance(x, (int, float))]
                if numeric_data:
                    avg = sum(numeric_data) / len(numeric_data)
                    max_val = max(numeric_data)
                    min_val = min(numeric_data)
                    desc = f"- {s['name']}: 平均值{avg:.2f}, 最大值{max_val}, 最小值{min_val}"
                    descriptions.append(desc)
        
        if not descriptions:
            return "无数值数据"
        
        return "\n".join(descriptions)
    
    @staticmethod
    def build_prompt(
        chart_type: str,
        chart_title: str,
        xAxis: Optional[List[str]],
        series: List[Dict[str, Any]],
        analysis_type: str = "summary",
        custom_prompt: str = ""
    ) -> str:
        """
        构建分析 Prompt
        
        Args:
            chart_type: 图表类型
            chart_title: 图表标题
            xAxis: X 轴数据
            series: 系列数据
            analysis_type: 分析类型
            custom_prompt: 自定义提示
            
        Returns:
            完整的 Prompt
        """
        template = get_prompt_template(chart_type, analysis_type)
        
        prompt = template.format(
            chartTitle=chart_title,
            chartType=chart_type,
            xAxisDescription=ChartAnalyzer.format_xaxis_description(xAxis),
            seriesDataDescription=ChartAnalyzer.format_series_description(series),
            customPrompt=custom_prompt if custom_prompt else ""
        )
        
        return prompt
    
    @staticmethod
    async def analyze_chart_stream_async(
        chart_type: str,
        chart_title: str,
        xAxis: Optional[List[str]],
        series: List[Dict[str, Any]],
        analysis_type: str = "summary",
        custom_prompt: str = ""
    ):
        """
        分析图表（流式）
        
        Args:
            chart_type: 图表类型
            chart_title: 图表标题
            xAxis: X 轴数据
            series: 系列数据
            analysis_type: 分析类型
            custom_prompt: 自定义提示
            
        Yields:
            生成器
        """
        # 构建 Prompt
        full_prompt = ChartAnalyzer.build_prompt(
            chart_type=chart_type,
            chart_title=chart_title,
            xAxis=xAxis,
            series=series,
            analysis_type=analysis_type,
            custom_prompt=custom_prompt
        )
        
        # 添加系统提示
        system_prompt = "你是一位专业的数据分析专家，擅长解读各种图表并提供有价值的洞察。"
        
        async for chunk in ChartAnalyzer._call_llm_stream_async(full_prompt, system_prompt):
            yield chunk

    @staticmethod
    async def _call_llm_stream_async(prompt: str, system_prompt: str):
        """异步调用 LLM 流式接口"""
        full_prompt = f"{system_prompt}\n\n{prompt}"
        for chunk in llm_client.generate_stream(full_prompt):
            yield chunk
    
    @staticmethod
    def _call_llm_stream(prompt: str, system_prompt: str):
        """同步调用 LLM 流式接口（用于非 async 上下文）"""
        full_prompt = f"{system_prompt}\n\n{prompt}"
        yield from llm_client.generate_stream(full_prompt)

    # 创建全局实例
chart_analyzer = ChartAnalyzer()
