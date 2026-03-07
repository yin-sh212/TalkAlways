# app/services/rag_service_win.py - Windows专用简化版
import os
import numpy as np
from typing import List, Dict, Any, Optional


class SimpleEmbeddings:
    """简单的嵌入模拟器（不依赖任何外部库）"""

    def __init__(self, dimension=384):
        self.dimension = dimension

    def embed_query(self, text):
        # 用文本的hash生成稳定的伪随机向量
        np.random.seed(hash(text) % 2 ** 32)
        return np.random.randn(self.dimension).tolist()

    def embed_documents(self, texts):
        return [self.embed_query(text) for text in texts]


class SimpleVectorStore:
    """简单的向量存储"""

    def __init__(self):
        self.documents = []
        self.embeddings = []

    def add_documents(self, docs, embeddings):
        self.documents.extend(docs)
        self.embeddings.extend(embeddings)

    def similarity_search_with_score(self, query_embedding, k=3):
        if not self.embeddings:
            return []

        # 计算余弦相似度
        query = np.array(query_embedding)
        similarities = []
        for i, emb in enumerate(self.embeddings):
            emb_array = np.array(emb)
            cos_sim = np.dot(query, emb_array) / (np.linalg.norm(query) * np.linalg.norm(emb_array) + 1e-8)
            similarities.append((i, cos_sim))

        # 排序取top-k
        similarities.sort(key=lambda x: x[1], reverse=True)

        results = []
        for idx, score in similarities[:k]:
            results.append((self.documents[idx], float(score)))

        return results


class WindowsRAGService:
    """Windows专用RAG服务"""

    def __init__(self, persist_directory="./data/faiss_index"):
        self.persist_directory = persist_directory
        self.embeddings_model = SimpleEmbeddings()
        self.vectorstore = SimpleVectorStore()
        self.documents = []
        self.document_texts = []

    def init_knowledge_base(self):
        """初始化知识库"""
        os.makedirs(self.persist_directory, exist_ok=True)
        print("✅ Windows版RAG服务初始化成功")

    def add_documents(self, file_paths: List[str]) -> int:
        """添加文档"""
        all_texts = []

        for file_path in file_paths:
            if not os.path.exists(file_path):
                print(f"⚠️ 文件不存在: {file_path}")
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 简单分段
                paragraphs = content.split('\n\n')
                for para in paragraphs:
                    para = para.strip()
                    if len(para) > 20:
                        all_texts.append(para)

            except Exception as e:
                print(f"❌ 读取文件失败 {file_path}: {e}")

        if not all_texts:
            return 0

        # 创建文档对象
        docs = []
        for text in all_texts:
            doc = type('Document', (), {
                'page_content': text,
                'metadata': {'source': 'knowledge_base'}
            })()
            docs.append(doc)

        # 生成嵌入
        embeddings = self.embeddings_model.embed_documents(all_texts)

        # 添加到向量库
        self.vectorstore.add_documents(docs, embeddings)
        self.documents = docs
        self.document_texts = all_texts

        print(f"✅ 已加载 {len(all_texts)} 个文档段落")
        return len(all_texts)

    def search(self, query: str, k: int = 3) -> List[Dict]:
        """搜索相关文档"""
        if not self.documents:
            return []

        query_embedding = self.embeddings_model.embed_query(query)
        results = self.vectorstore.similarity_search_with_score(query_embedding, k)

        return [
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": score
            }
            for doc, score in results
        ]

    def answer(self, question: str) -> Dict:
        """回答问题"""
        results = self.search(question, k=3)

        if results:
            answer = "📚 找到相关信息：\n\n"
            for i, r in enumerate(results, 1):
                answer += f"{i}. {r['content'][:200]}...\n\n"
        else:
            answer = "抱歉，知识库中没有找到相关信息。"

        return {
            "answer": answer,
            "sources": results
        }


# 创建全局实例
rag_service = WindowsRAGService()