"""
AI 数据分析师 API - 智能问答与主动洞察
"""
from fastapi import APIRouter, Body, Depends, Query
from typing import Optional, List, Dict, Any
from app.services.ai_agent import AIAgent
from app.tools.database_query import DatabaseQueryTool
import asyncio

router = APIRouter(prefix="/api/ai-analyst", tags=["AI 数据分析师"])


# 模拟用户认证（后续可集成真实鉴权）
async def get_current_user():
    """获取当前用户信息（临时实现）"""
    return {
        "user_id": "demo_user",
        "name": "演示用户",
        "role": "admin"
    }


@router.post("/analyze")
async def analyze_with_context(
    question: str = Body(..., description="用户问题"),
    context: Dict[str, Any] = Body({}, description="页面上下文信息"),
    current_user: dict = Depends(get_current_user)
):
    """
    AI 智能分析接口
    
    工作流程:
    1. 接收用户问题 + 页面上下文（当前建筑 ID、时间范围等）
    2. AI 判断是否需要查询数据库
    3. 调用 DatabaseQueryTool 获取数据
    4. 基于数据进行深度分析并返回
    
    示例:
    POST /api/ai-analyst/analyze
    {
        "question": "为什么行政楼能耗这么高？",
        "context": {
            "current_page": "overview",
            "building_id": "Eagle_education_Cassie",
            "selected_date": "2016-09-05",
            "clicked_element": "kpi_energy_card"
        }
    }
    """
    
    ai_agent = AIAgent()
    db_tool = DatabaseQueryTool()
    
    try:
        # Step 1: AI 理解问题，生成查询计划
        query_plan = await ai_agent.generate_query_plan(
            question=question,
            context=context
        )
        
        print(f"[AI Analyst] 查询计划：{query_plan}")
        
        # Step 2: 执行数据库查询
        data_results = {}
        for query_info in query_plan.get('queries', []):
            table_name = query_info['table']
            sql = query_info['sql']
            
            try:
                result = await db_tool.execute_query(sql)
                data_results[table_name] = result
                print(f"[AI Analyst] 查询 {table_name} 成功，返回 {len(result)} 条记录")
            except Exception as e:
                print(f"[AI Analyst] 查询 {table_name} 失败：{e}")
                data_results[table_name] = []
        
        # Step 3: AI 基于查询结果进行分析
        analysis = await ai_agent.analyze_data(
            question=question,
            query_results=data_results,
            context=context
        )
        
        return {
            "code": 200,
            "message": "分析成功",
            "data": {
                "answer": analysis.get('answer', '分析失败'),
                "supporting_data": data_results,
                "suggested_questions": analysis.get('follow_ups', []),
                "visualization_type": analysis.get('chart_type', 'table'),
                "confidence": analysis.get('confidence', 0.8),
                "reasoning": query_plan.get('reasoning', '')
            }
        }
        
    except Exception as e:
        print(f"[AI Analyst] 分析失败：{e}")
        return {
            "code": 500,
            "message": f"分析失败：{str(e)}",
            "data": {
                "answer": "抱歉，分析过程中出现错误，请稍后再试。",
                "supporting_data": {},
                "suggested_questions": [],
                "visualization_type": "table",
                "confidence": 0.0
            }
        }


@router.get("/quick-insights/{building_id}")
async def get_quick_insights(building_id: str):
    """
    主动推送 AI 洞察（无需用户提问）
    
    自动检测异常情况并生成优化建议
    """
    ai_agent = AIAgent()
    db_tool = DatabaseQueryTool()
    
    try:
        # 自动检测异常
        anomalies = await detect_anomalies(building_id, db_tool)
        
        insights = []
        for anomaly in anomalies:
            insight = await ai_agent.generate_insight(anomaly)
            insights.append(insight)
        
        return {
            "code": 200,
            "message": "获取洞察成功",
            "data": {
                "insights": insights,
                "priority": "high" if len(insights) > 0 else "normal",
                "total_detected": len(anomalies)
            }
        }
        
    except Exception as e:
        print(f"[AI Analyst] 获取洞察失败：{e}")
        return {
            "code": 500,
            "message": f"获取洞察失败：{str(e)}",
            "data": {
                "insights": [],
                "priority": "error",
                "total_detected": 0
            }
        }


async def detect_anomalies(building_id: str, db_tool: DatabaseQueryTool) -> List[Dict[str, Any]]:
    """
    检测建筑用能异常
    
    检测维度：
    1. 夜间基础负荷过高
    2. 周末用能异常
    3. 尖峰负荷突增
    4. 连续偏高用能
    """
    anomalies = []
    
    try:
        # 查询近 7 天的逐时能耗
        sql = """
            SELECT 
                DATE(timestamp) as date,
                HOUR(timestamp) as hour,
                SUM(electricity) as total_electricity
            FROM energy_consumption
            WHERE building_id = %s
              AND timestamp >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            GROUP BY DATE(timestamp), HOUR(timestamp)
            ORDER BY timestamp DESC
        """
        
        hourly_data = await db_tool.execute_query(sql, (building_id,))
        
        if not hourly_data:
            return anomalies
        
        # 简单规则检测
        # 1. 检测夜间（22:00-6:00）基础负荷
        night_hours = [h for h in hourly_data if h['hour'] >= 22 or h['hour'] <= 6]
        if night_hours:
            avg_night = sum(h['total_electricity'] for h in night_hours) / len(night_hours)
            
            # 计算日间平均作为基准
            day_hours = [h for h in hourly_data if 8 <= h['hour'] <= 18]
            if day_hours:
                avg_day = sum(h['total_electricity'] for h in day_hours) / len(day_hours)
                
                # 如果夜间负荷超过日间的 50%，判定为异常
                if avg_night > avg_day * 0.5:
                    anomalies.append({
                        "type": "night_overuse",
                        "building_id": building_id,
                        "description": f"夜间基础负荷偏高，达日间峰值的{round(avg_night/avg_day*100)}%",
                        "severity": "high" if avg_night > avg_day * 0.7 else "medium",
                        "metrics": {
                            "avg_night_kwh": round(avg_night, 2),
                            "avg_day_kwh": round(avg_day, 2),
                            "ratio": round(avg_night / avg_day, 2)
                        }
                    })
        
        # 2. 检测周末用能
        weekend_data = [h for h in hourly_data if h['date'].weekday() >= 5]
        weekday_data = [h for h in hourly_data if h['date'].weekday() < 5]
        
        if weekend_data and weekday_data:
            avg_weekend = sum(h['total_electricity'] for h in weekend_data) / len(weekend_data)
            avg_weekday = sum(h['total_electricity'] for h in weekday_data) / len(weekday_data)
            
            # 周末用能超过工作日的 70% 视为异常
            if avg_weekend > avg_weekday * 0.7:
                anomalies.append({
                    "type": "weekend_overuse",
                    "building_id": building_id,
                    "description": f"周末用能偏高，达工作日的{round(avg_weekend/avg_weekday*100)}%",
                    "severity": "medium",
                    "metrics": {
                        "avg_weekend_kwh": round(avg_weekend, 2),
                        "avg_weekday_kwh": round(avg_weekday, 2),
                        "ratio": round(avg_weekend / avg_weekday, 2)
                    }
                })
        
        # 3. 检测尖峰负荷突增
        recent_peaks = sorted(hourly_data, key=lambda x: x['total_electricity'], reverse=True)[:5]
        if len(recent_peaks) >= 2:
            max_peak = recent_peaks[0]['total_electricity']
            second_peak = recent_peaks[1]['total_electricity']
            
            # 最高峰比第二高峰高出 50% 以上
            if max_peak > second_peak * 1.5:
                anomalies.append({
                    "type": "peak_spike",
                    "building_id": building_id,
                    "description": f"出现尖峰负荷，超出正常峰值{round((max_peak-second_peak)/second_peak*100)}%",
                    "severity": "high",
                    "metrics": {
                        "peak_kwh": round(max_peak, 2),
                        "normal_peak_kwh": round(second_peak, 2),
                        "spike_ratio": round((max_peak - second_peak) / second_peak, 2)
                    }
                })
        
    except Exception as e:
        print(f"[AI Analyst] 异常检测失败：{e}")
    
    return anomalies


@router.get("/tables")
async def get_available_tables():
    """获取 AI 可访问的数据表信息（用于前端展示）"""
    db_tool = DatabaseQueryTool()
    
    try:
        tables = await db_tool.get_available_tables()
        return {
            "code": 200,
            "data": {
                "tables": tables,
                "count": len(tables)
            }
        }
    except Exception as e:
        return {
            "code": 500,
            "message": f"获取表信息失败：{str(e)}",
            "data": {
                "tables": [],
                "count": 0
            }
        }