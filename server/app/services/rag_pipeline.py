# app/services/rag_pipeline.py
import json
from app.services.vector_db import vector_db
from app.services.knowledge_base import knowledge_base
from app.services.llm_client import llm_client
from typing import List, Dict, Any


class RAGPipeline:
    """真正的RAG完整流程"""

    def __init__(self):
        self.vector_db = vector_db
        self.knowledge_base = knowledge_base
        self.llm_client = llm_client
        self.initialized = False

    def initialize_knowledge_base(self):
        """初始化知识库（加载所有文档到向量库）"""
        print("📚 开始初始化知识库...")

        documents = self.knowledge_base.load_all_documents()
        print(f"📄 加载了 {len(documents)} 个文档块")

        if documents:
            # 这步会调用向量化！
            self.vector_db.add_documents(documents)
            self.initialized = True

        return len(documents)

    def retrieve(self, query: str, k: int = 5) -> List[Dict]:
        """检索相关文档（真正的语义检索）"""
        if not self.initialized:
            return []
        return self.vector_db.search(query, k)

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

    def answer(self, query: str) -> Dict:
        """真正的RAG完整流程"""
        try:
            # 1. 检索（语义检索）
            contexts = self.retrieve(query, k=5)

            if not contexts:
                return {
                    'answer': '抱歉，知识库中没有找到相关信息。',
                    'sources': [],
                    'type': 'knowledge'
                }

            # 2. 生成提示词
            prompt = self.generate_prompt(query, contexts)

            # 3. 调用LLM生成回答（你学的RAG课程里的Qwen）
            answer = self.llm_client.generate(prompt)

            return {
                'answer': answer,
                'sources': contexts,
                'type': 'knowledge'
            }
        except Exception as e:
            return {
                'answer': f'处理失败: {str(e)}',
                'sources': [],
                'type': 'error'
            }

    def hybrid_answer(self, query: str, data_context: Dict = None) -> Dict:
        """混合回答（数据+知识）"""
        try:
            contexts = self.retrieve(query, k=3)

            prompt = f"""你是一个建筑能源管理专家，请基于以下数据和知识回答问题。

"""
            if data_context:
                prompt += f"实时数据：\n{json.dumps(data_context, ensure_ascii=False, indent=2)}\n\n"

            if contexts:
                prompt += "相关知识：\n"
                for i, ctx in enumerate(contexts, 1):
                    prompt += f"[{i}] {ctx['content'][:200]}...\n"

            prompt += f"\n问题：{query}\n\n回答："

            answer = self.llm_client.generate(prompt)

            return {
                'answer': answer,
                'sources': contexts,
                'data': data_context,
                'type': 'hybrid'
            }
        except Exception as e:
            return {
                'answer': f'处理失败: {str(e)}',
                'sources': [],
                'type': 'error'
            }

    def get_stats(self) -> Dict:
        """获取统计信息"""
        try:
            return {
                'vector_db': self.vector_db.get_stats(),
                'knowledge_base': {
                    'documents': self.knowledge_base.list_documents()
                },
                'llm_available': self.llm_client.available,
                'initialized': self.initialized
            }
        except:
            return {
                'initialized': False,
                'error': '无法获取统计信息'
            }


# 全局实例
rag_pipeline = RAGPipeline()