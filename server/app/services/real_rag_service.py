# app/services/real_rag_service.py
import os
import pickle
import numpy as np
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings


class RealRAGService:
    """真正的RAG服务（向量检索 + 本地LLM）"""

    def __init__(self, persist_directory="./data/real_rag"):
        self.persist_directory = persist_directory
        os.makedirs(persist_directory, exist_ok=True)

        # 1. 初始化embedding模型（将文本转为向量）
        print("🔄 加载embedding模型...")
        self.embedder = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

        # 2. 初始化向量数据库
        self.chroma_client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=persist_directory
        ))

        # 创建或获取集合
        collection_name = "building_knowledge"
        try:
            self.collection = self.chroma_client.get_collection(collection_name)
            print(f"✅ 加载已有向量库，包含 {self.collection.count()} 个文档")
        except:
            self.collection = self.chroma_client.create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}  # 用余弦相似度
            )
            print("✅ 创建新向量库")

        # 3. 初始化本地LLM（可以用Qwen/ChatGLM等）
        # 这里用简单模拟，实际应该加载真实模型
        self.llm_available = False
        try:
            # 尝试加载本地模型（如果有）
            from transformers import AutoTokenizer, AutoModelForCausalLM
            self.tokenizer = AutoTokenizer.from_pretrained(
                "Qwen/Qwen2-1.5B-Instruct",
                trust_remote_code=True
            )
            self.model = AutoModelForCausalLM.from_pretrained(
                "Qwen/Qwen2-1.5B-Instruct",
                trust_remote_code=True
            )
            self.llm_available = True
            print("✅ 加载本地LLM成功")
        except Exception as e:
            print(f"⚠️ 未找到本地LLM，使用模拟模式: {e}")
            self.llm_available = False

    def add_documents(self, file_paths: List[str]) -> int:
        """添加文档到向量库"""
        all_chunks = []
        all_metadatas = []
        all_ids = []

        for file_path in file_paths:
            if not os.path.exists(file_path):
                print(f"⚠️ 文件不存在: {file_path}")
                continue

            print(f"📄 处理文档: {file_path}")

            # 读取文档
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 分块（按段落分割）
            chunks = []
            current_chunk = []
            for line in content.split('\n'):
                if line.strip():
                    current_chunk.append(line)
                elif current_chunk:
                    chunks.append('\n'.join(current_chunk))
                    current_chunk = []

            if current_chunk:
                chunks.append('\n'.join(current_chunk))

            # 过滤太短的块
            chunks = [c for c in chunks if len(c) > 20]

            print(f"  分割为 {len(chunks)} 个文本块")

            # 生成向量并添加到集合
            for i, chunk in enumerate(chunks):
                # 生成唯一ID
                chunk_id = f"{os.path.basename(file_path)}_{i}"

                # 存储文本和元数据
                all_chunks.append(chunk)
                all_metadatas.append({
                    "source": file_path,
                    "chunk": i,
                    "text": chunk  # 存一份原文
                })
                all_ids.append(chunk_id)

        if not all_chunks:
            return 0

        # 批量生成向量
        print(f"🔄 生成 {len(all_chunks)} 个文本的向量...")
        embeddings = self.embedder.encode(all_chunks).tolist()

        # 添加到ChromaDB
        self.collection.add(
            embeddings=embeddings,
            documents=all_chunks,
            metadatas=all_metadatas,
            ids=all_ids
        )

        # 持久化
        self.chroma_client.persist()

        print(f"✅ 已添加 {len(all_chunks)} 个文档块到向量库")
        return len(all_chunks)

    def search(self, query: str, k: int = 5) -> List[Dict]:
        """向量检索"""
        # 生成查询向量
        query_embedding = self.embedder.encode(query).tolist()

        # 检索相似文档
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k
        )

        # 格式化结果
        formatted_results = []
        if results['documents'] and results['documents'][0]:
            for i in range(len(results['documents'][0])):
                formatted_results.append({
                    "content": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                    "distance": results['distances'][0][i] if results['distances'] else 0,
                    "score": 1 - results['distances'][0][i] if results['distances'] else 0
                })

        return formatted_results

    def generate_prompt(self, query: str, contexts: List[str]) -> str:
        """生成提示词"""
        context_text = "\n\n".join(contexts)

        prompt = f"""你是一个建筑能源管理专家，请基于以下参考资料回答用户的问题。

参考资料：
{context_text}

问题：{query}

请给出专业、准确、简洁的回答。如果参考资料中没有相关信息，请直接说明不知道，不要编造。
"""
        return prompt

    def answer(self, question: str) -> Dict:
        """RAG完整流程：检索 + 生成"""
        # 1. 检索相关文档
        contexts = self.search(question, k=3)

        if not contexts:
            return {
                "answer": "抱歉，知识库中没有找到相关信息。",
                "sources": [],
                "type": "knowledge"
            }

        # 2. 生成提示词
        context_texts = [c['content'] for c in contexts]
        prompt = self.generate_prompt(question, context_texts)

        # 3. 调用LLM生成回答
        if self.llm_available:
            # 真实LLM调用
            inputs = self.tokenizer(prompt, return_tensors="pt")
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=512,
                temperature=0.7,
                do_sample=True
            )
            answer = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            # 去掉prompt部分
            answer = answer[len(prompt):].strip()
        else:
            # 模拟LLM（简单拼接）
            answer = f"📚 找到 {len(contexts)} 条相关信息：\n\n"
            for i, ctx in enumerate(contexts, 1):
                answer += f"{i}. {ctx['content'][:200]}...\n\n"
            answer += "\n💡 建议：基于以上信息，您可能需要检查相关设备。"

        return {
            "answer": answer,
            "sources": contexts,
            "type": "knowledge"
        }

    def hybrid_search(self, query: str, k: int = 5) -> List[Dict]:
        """混合检索（向量 + 关键词）"""
        # 向量检索
        vector_results = self.search(query, k)

        # 简单关键词匹配（作为补充）
        keyword_results = []
        query_words = set(query.lower().split())

        # 这里可以添加BM25等算法

        # 合并去重
        seen = set()
        combined = []

        for r in vector_results:
            if r['content'] not in seen:
                combined.append(r)
                seen.add(r['content'])

        return combined[:k]

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "total_documents": self.collection.count(),
            "embedding_model": "paraphrase-multilingual-MiniLM-L12-v2",
            "vector_dimension": 384,
            "llm_available": self.llm_available,
            "persist_directory": self.persist_directory
        }


# 全局实例
rag_service = RealRAGService()