"""
AI Agent 服务 - 智能数据分析引擎
基于 LLM 实现数据查询计划生成、分析结果输出、洞察建议等功能
"""
import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.services.llm_client import LLMClient, extract_json
from app.tools.database_query import DatabaseQueryTool


class QuerySpec(BaseModel):
    """查询计划里的一条：表名 + SELECT 语句。"""
    model_config = ConfigDict(extra="ignore")
    table: str = ""
    sql: str = ""
    purpose: str = ""


class QueryPlan(BaseModel):
    """generate_query_plan 的输出契约。默认值与下游 `query_plan.get(...)` 的默认值一致。"""
    model_config = ConfigDict(extra="ignore")
    queries: List[QuerySpec] = Field(default_factory=list)
    reasoning: str = ""


class Analysis(BaseModel):
    """analyze_data 的输出契约。默认值 = ai_analyst.py 里 `.get(key, default)` 的默认值。"""
    model_config = ConfigDict(extra="ignore")
    answer: str = "未获取到分析结果"
    follow_ups: List[str] = Field(default_factory=list)
    chart_type: str = "table"
    confidence: float = 0.8


class Insight(BaseModel):
    """generate_insight 的输出契约。默认值 = 原来的兜底洞察。"""
    model_config = ConfigDict(extra="ignore")
    title: str = "发现异常"
    description: str = ""
    category: str = "other"
    priority: str = "medium"
    estimated_savings_kwh: float = 0.0
    estimated_savings_cny: float = 0.0
    action: str = "请进一步检查"


def _coerce(model, data: Dict[str, Any]) -> Dict[str, Any]:
    """按 model 规范化 data；校验失败就原样返回 data（保证不劣于「不校验」的修前行为）。

    单个字段类型走样不应该把整段回答变成一句报错——所以这里退回原始 dict，交由下游 .get() 兜底。
    """
    try:
        return model.model_validate(data).model_dump()
    except ValidationError:
        return data


class AIAgent:
    """AI 数据分析师 Agent"""
    
    def __init__(self):
        self.llm = LLMClient()
        self.db_tool = DatabaseQueryTool()
        
        # 可用的数据表信息（用于提示 AI）
        self.available_tables = [
            {
                "name": "energy_consumption",
                "description": "能耗数据表，包含电/水/空调的实时监测数据",
                "key_fields": ["building_id", "meter_id", "timestamp", "electricity", "is_anomaly"]
            },
            {
                "name": "meters",
                "description": "监测点信息表，包含传感器设备的基本信息和状态",
                "key_fields": ["id", "building_id", "type", "status"]
            },
            {
                "name": "buildings",
                "description": "建筑信息表，包含建筑的基本属性",
                "key_fields": ["id", "name", "type", "area"]
            },
            {
                "name": "alarms",
                "description": "告警记录表，包含历史告警和处理状态",
                "key_fields": ["building_id", "alarm_type", "start_time", "status"]
            },
            {
                "name": "devices",
                "description": "固定资产设备台账表",
                "key_fields": ["id", "name", "type", "building_id", "status"]
            }
        ]
    
    async def generate_query_plan(self, question: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        根据用户问题生成查询计划
        
        Args:
            question: 用户的问题
            context: 页面上下文信息
            
        Returns:
            查询计划，包含需要执行的 SQL 列表
        """
        tables_info = json.dumps(self.available_tables, ensure_ascii=False)
        
        prompt = f"""
你是一个智能数据分析师，需要根据用户问题生成 SQL 查询计划。

【可用数据表】
{tables_info}

【用户问题】
{question}

【页面上下文】
{json.dumps(context, ensure_ascii=False)}

请分析需要查询哪些表来获取支撑数据，返回 JSON 格式：
{{
    "queries": [
        {{
            "table": "表名",
            "sql": "SELECT 语句",
            "purpose": "查询目的说明"
        }}
    ],
    "reasoning": "分析思路说明"
}}

注意：
1. SQL 必须是 SELECT 语句
2. 使用参数化查询，避免 SQL 注入
3. 合理设置 LIMIT（默认不超过 1000 条）
4. 优先查询聚合数据，减少数据传输量
"""
        
        try:
            response = self.llm.generate(prompt, max_tokens=1024, json_mode=True)

            data = extract_json(response)
            if data is None:
                print("[AIAgent] JSON 解析失败，使用默认查询计划")
                return {
                    "queries": [],
                    "reasoning": "无法生成查询计划"
                }

            result = _coerce(QueryPlan, data)
            # 丢掉没有 sql 的条目：留着只会换来一次无意义的 DB 调用（或下游 KeyError）
            result["queries"] = [
                q for q in result.get("queries", [])
                if isinstance(q, dict) and str(q.get("sql", "")).strip()
            ]
            return result

        except Exception as e:
            print(f"[AIAgent] 生成查询计划失败：{e}")
            return {
                "queries": [],
                "reasoning": f"生成查询计划出错：{str(e)}"
            }
    
    async def analyze_data(self, question: str, query_results: Dict[str, List[Dict]], 
                          context: Dict[str, Any]) -> Dict[str, Any]:
        """
        基于查询结果进行深度分析
        
        Args:
            question: 用户问题
            query_results: 各表的查询结果
            context: 页面上下文
            
        Returns:
            分析结果
        """
        results_summary = {}
        for table_name, data in query_results.items():
            results_summary[table_name] = {
                "count": len(data),
                "sample": data[:3] if data else []  # 只保留前 3 条作为样本
            }
        
        prompt = f"""
你是专业的能源管理数据分析师，请基于查询结果回答用户问题。

【用户问题】
{question}

【查询到的数据】
{json.dumps(results_summary, ensure_ascii=False, indent=2)}

【完整原始数据（供参考）】
{json.dumps(query_results, ensure_ascii=False, indent=2)[:5000]}  # 限制长度

【页面上下文】
{json.dumps(context, ensure_ascii=False)}

请生成一份专业的分析报告，包含：
1. 直接回答问题
2. 数据支撑和计算过程
3. 发现的问题或趋势
4. 可落地的优化建议
5. 推荐的后续问题（2-3 个）

返回 JSON 格式：
{{
    "answer": "分析回答文本（支持 Markdown 格式）",
    "follow_ups": ["推荐问题 1", "推荐问题 2"],
    "chart_type": "bar|line|pie|table",  // 建议的可视化类型
    "confidence": 0.95  // 置信度 0-1
}}
"""
        
        try:
            response = self.llm.generate(prompt, max_tokens=2048, json_mode=True)

            data = extract_json(response)
            if data is None:
                # 没解析出 JSON：把原文当回答（与修前一致）
                return {
                    "answer": response,
                    "follow_ups": [],
                    "chart_type": "table",
                    "confidence": 0.8
                }

            return _coerce(Analysis, data)

        except Exception as e:
            print(f"[AIAgent] 数据分析失败：{e}")
            return {
                "answer": f"分析过程中出现错误：{str(e)}",
                "follow_ups": [],
                "chart_type": "table",
                "confidence": 0.5
            }
    
    async def generate_insight(self, anomaly_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        主动生成洞察建议
        
        Args:
            anomaly_data: 异常检测数据
            
        Returns:
            洞察建议
        """
        prompt = f"""
你是能源管理专家，请根据以下异常数据生成优化建议。

【异常数据】
{json.dumps(anomaly_data, ensure_ascii=False, indent=2)}

请按以下格式返回洞察（JSON）：
{{
    "title": "洞察标题（简短有力）",
    "description": "详细描述（包含数据支撑）",
    "category": "hvac|lighting|equipment|other",
    "priority": "high|medium|low",
    "estimated_savings_kwh": 预计节能度数，
    "estimated_savings_cny": 预计节省金额，
    "action": "建议采取的具体行动"
}}
"""
        
        try:
            response = self.llm.generate(prompt, max_tokens=512, json_mode=True)

            data = extract_json(response)
            if data is None:
                return {
                    "title": "发现异常",
                    "description": anomaly_data.get('description', '检测到异常情况'),
                    "category": "other",
                    "priority": "medium",
                    "estimated_savings_kwh": 0,
                    "estimated_savings_cny": 0,
                    "action": "请进一步检查"
                }

            insight = _coerce(Insight, data)
            if not insight.get("description"):
                insight["description"] = anomaly_data.get('description', '检测到异常情况')
            return insight

        except Exception as e:
            print(f"[AIAgent] 生成洞察失败：{e}")
            return {
                "title": "分析失败",
                "description": f"无法生成洞察：{str(e)}",
                "category": "other",
                "priority": "low",
                "estimated_savings_kwh": 0,
                "estimated_savings_cny": 0,
                "action": "请稍后重试"
            }


# 全局实例
ai_agent = AIAgent()