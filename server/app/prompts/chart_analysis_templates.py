# app/prompts/chart_analysis_templates.py
"""
图表 AI 分析 Prompt 模板管理
"""

# 通用汇总模板
GENERAL_TEMPLATE = """
你是一位专业的数据分析专家。请基于以下图表数据进行深度分析：

【图表信息】
- 标题：{chartTitle}
- 类型：{chartType}
- X 轴：{xAxisDescription}

【数据详情】
{seriesDataDescription}

{customPrompt}

【分析要求】
1. 识别主要趋势和模式
2. 指出异常点或关键转折点
3. 分析可能的原因和影响因素
4. 提供可操作的建议

请以结构化的 Markdown 格式输出分析报告，包含以下部分：

## 📊 总体概览
（100 字内总结图表展示的核心内容）

## 🔍 关键发现
（3-5 条带数据支撑的发现，使用 ✅ ⚠️ 🎯 等 emoji）

## ⚠️ 异常警示
（如有明显异常或需要关注的点）

## 💡 优化建议
（2-3 条具体可操作的建议）

注意：
- 使用专业但易懂的语言
- 所有结论必须基于提供的数据
- 避免模糊和不确定的表述
- **回答控制在 300 字以内，简洁明了**
"""

# 趋势分析专用模板（针对折线图、面积图优化）
TREND_TEMPLATE = """
你是一位趋势分析专家。请分析以下趋势图：

【图表信息】
- 标题：{chartTitle}
- 类型：{chartType}
- 时间范围：{xAxisDescription}

【数据详情】
{seriesDataDescription}

{customPrompt}

【分析重点】
1. 整体趋势判断（上升/下降/波动/平稳）
2. 关键转折点和峰值分析
3. 周期性或季节性特征
4. 未来趋势预测

Please按以下结构 output：

## 📈 趋势总结
（用一句话概括整体趋势，如"呈稳步上升趋势"或"波动较大但总体向好"）

## 🎯 关键节点
（列出 2-3 个重要转折点，说明时间和变化幅度）

## 🔮 趋势预测
（基于历史数据推测短期走势）

## 💡 应对策略
（针对趋势提出具体的管理或优化建议）

注意：**回答控制在 300 字以内，简洁明了**
"""

# 柱状图专用模板
BAR_CHART_TEMPLATE = """
你是一位对比分析专家。请分析以下柱状图：

【图表信息】
- 标题：{chartTitle}
- 类型：{chartType}
- 对比维度：{xAxisDescription}

【数据详情】
{seriesDataDescription}

{customPrompt}

【分析重点】
1. 各柱体之间的数值差异
2. 最高值和最低值对比
3. 数据分布特征
4. 排名和差距分析

请按以下结构输出：

## 📊 对比总览
（总结对比的整体情况）

## 🏆 表现排名
（从高到低排序，突出最优和最差）

## 📉 差距分析
（分析最大值与最小值的差距及原因）

## 💪 改进方向
（针对表现较差的项提出改进建议）

注意：**回答控制在 300 字以内，简洁明了**
"""

# 饼图专用模板
PIE_CHART_TEMPLATE = """
你是一位结构分析专家。请分析以下饼图：

【图表信息】
- 标题：{chartTitle}
- 类型：{chartType}

【数据详情】
{seriesDataDescription}

{customPrompt}

【分析重点】
1. 各部分占比情况
2. 主导部分识别
3. 结构合理性评估
4. 优化建议

请按以下结构输出：

## 🥧 结构概览
（描述整体的组成结构）

## 🎯 主导因素
（指出占比最大的部分及其意义）

## ⚖️ 结构评估
（分析当前结构是否合理）

## 🔄 优化建议
（如需调整结构，提出具体建议）

注意：**回答控制在 300 字以内，简洁明了**
"""

# 雷达图专用模板
RADAR_CHART_TEMPLATE = """
你是一位多维度评估专家。请分析以下雷达图：

【图表信息】
- 标题：{chartTitle}
- 类型：{chartType}

【数据详情】
{seriesDataDescription}

{customPrompt}

【分析重点】
1. 各维度得分情况
2. 优势维度识别
3. 短板维度识别
4. 综合平衡性评估

请按以下结构输出：

## 🎯 综合评分
（整体评价各维度的表现）

## ✅ 优势维度
（列出得分较高的 2-3 个维度）

## ⚠️ 待改进维度
（列出得分较低的 2-3 个维度）

## 📈 提升策略
（针对短板提出具体的提升方案）

注意：**回答控制在 300 字以内，简洁明了**
"""

# 散点图专用模板
SCATTER_CHART_TEMPLATE = """
你是一位分布分析专家。请分析以下散点图：

【图表信息】
- 标题：{chartTitle}
- 类型：{chartType}

【数据详情】
{seriesDataDescription}

{customPrompt}

【分析重点】
1. 数据点的分布模式
2. 聚集区域识别
3. 离群点检测
4. 相关性分析

请按以下结构输出：

## 📊 分布特征
（描述数据点的整体分布情况）

## 🎯 聚集区域
（指出数据密集的区域）

## ⚠️ 离群点分析
（识别并分析异常点）

## 🔗 关联性洞察
（如果适用，分析变量之间的关系）

注意：**回答控制在 300 字以内，简洁明了**
"""

# 异常检测专用模板
ANOMALY_TEMPLATE = """
你是一位异常检测专家。请识别以下数据中的异常点：

【图表信息】
- 标题：{chartTitle}
- 类型：{chartType}

【数据详情】
{seriesDataDescription}

{customPrompt}

【分析重点】
1. 识别偏离正常范围的异常点
2. 评估异常严重程度
3. 推测可能的根本原因
4. 提出处置建议

请按以下结构输出：

## ⚠️ 异常点识别
## 🔴 严重程度评估
## 🔍 根因分析
## 🛠️ 处置建议

注意：**回答控制在 300 字以内，简洁明了**
"""

# 对比分析专用模板
COMPARISON_TEMPLATE = """
你是一位对比分析专家。请对比以下多个数据系列：

【图表信息】
- 标题：{chartTitle}
- 类型：{chartType}

【数据详情】
{seriesDataDescription}

{customPrompt}

【分析重点】
1. 各系列之间的差异
2. 表现最优和最差的系列
3. 相关性分析
4. 优劣势对比

请按以下结构输出：

## 📊 对比总览
## 🏆 表现排名
## 🔗 关联性分析
## 📋 优劣势分析

注意：**回答控制在 300 字以内，简洁明了**
"""

# 模板映射
TEMPLATES = {
    "summary": {
        "default": GENERAL_TEMPLATE,
        "line": GENERAL_TEMPLATE,
        "bar": BAR_CHART_TEMPLATE,      # 使用柱状图专用模板
        "pie": PIE_CHART_TEMPLATE,       # 使用饼图专用模板
        "radar": RADAR_CHART_TEMPLATE,   # 使用雷达图专用模板
        "scatter": SCATTER_CHART_TEMPLATE, # 使用散点图专用模板
        "area": GENERAL_TEMPLATE,
    },
    "trend": {
        "default": TREND_TEMPLATE,
        "line": TREND_TEMPLATE,
        "area": TREND_TEMPLATE,
    },
    "anomaly": {
        "default": ANOMALY_TEMPLATE,
    },
    "comparison": {
        "default": COMPARISON_TEMPLATE,
        "bar": COMPARISON_TEMPLATE,
        "radar": COMPARISON_TEMPLATE,
    }
}


def get_prompt_template(chart_type: str, analysis_type: str) -> str:
    """
    根据图表类型和分析类型获取 Prompt 模板
    
    Args:
        chart_type: 图表类型 (line, bar, pie, etc.)
        analysis_type: 分析类型 (summary, trend, anomaly, comparison)
    
    Returns:
        Prompt 模板字符串
    """
    if analysis_type not in TEMPLATES:
        return GENERAL_TEMPLATE
    
    type_templates = TEMPLATES[analysis_type]
    return type_templates.get(chart_type, type_templates.get("default", GENERAL_TEMPLATE))
