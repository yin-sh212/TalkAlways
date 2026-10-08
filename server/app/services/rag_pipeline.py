# app/services/rag_pipeline.py
from app.services.vector_db import vector_db
from app.services.knowledge_base import knowledge_base
from app.services.llm_client import llm_client
from typing import List, Dict


class RAGPipeline:
    """真正的RAG完整流程"""

    def __init__(self):
        self.vector_db = vector_db
        self.knowledge_base = knowledge_base
        self.llm_client = llm_client
        self.initialized = False

    def generate_prompt(self, query: str, contexts: List[Dict]) -> str:
        """生成提示词"""
        context_text = "\n\n".join([f"[{i + 1}] {ctx['content']}" for i, ctx in enumerate(contexts)])

        prompt = f"""你是一个建筑能源管理专家，请基于以下参考资料回答用户的问题。

参考资料：
{context_text}

问题：{query}

请给出专业、准确、简洁的回答。要求：
1. 只基于参考资料回答
2. 如果参考资料不足，请说明
3. 回答要结构化、清晰
4. 可以引用参考资料编号

回答："""
        return prompt


# 全局实例
rag_pipeline = RAGPipeline()
