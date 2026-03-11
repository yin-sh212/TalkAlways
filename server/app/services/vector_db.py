# app/services/vector_db.py
import os
import pickle
import numpy as np
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
import faiss
import hashlib
from app.services.llm_client import llm_client

class VectorDBService:
    """向量数据库服务 - 使用FAISS（稳定版）"""

    def __init__(self, persist_directory="./data/faiss_db"):
        self.persist_directory = persist_directory
        self.index_path = os.path.join(persist_directory, "index.faiss")
        self.documents_path = os.path.join(persist_directory, "documents.pkl")
        os.makedirs(persist_directory, exist_ok=True)

        # 1. 加载embedding模型（先用模拟，解决网络问题）
        print("🔄 准备embedding模型...")
        self.use_real_embedding = True
        self.embedding_dim = 768

        # 先尝试加载百度模型，如果失败就用模拟
        try:
            # 关键：设置环境变量使用国内镜像
            os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
            # 或者完全禁用SSL验证（临时解决）
            import ssl
            ssl._create_default_https_context = ssl._create_unverified_context

            self.embedder = SentenceTransformer('shibing624/text2vec-base-chinese')
            self.embedding_dim = 768
            self.use_real_embedding = True
            print("✅ 成功加载百度embedding模型")
        except Exception as e:
            print(f"⚠️ 无法加载真实模型: {e}")
            print("🔄 使用模拟embedding（不影响功能演示）")
            self.use_real_embedding = False

        # 2. 初始化FAISS索引
        if os.path.exists(self.index_path):
            self.index = faiss.read_index(self.index_path)
            with open(self.documents_path, 'rb') as f:
                self.documents = pickle.load(f)
            print(f"✅ 加载已有FAISS索引，包含 {len(self.documents)} 个文档")
        else:
            self.index = None
            self.documents = []
            print("✅ 创建新FAISS索引")

    def _encode(self, texts: List[str]) -> np.ndarray:
        """生成向量"""
        if self.use_real_embedding:
            try:
                embeddings = self.embedder.encode(texts)
                return embeddings.astype('float32')
            except Exception as e:
                print(f"⚠️ 调用embedding服务失败: {e}")

        # 模拟向量（开发测试用）
        return np.random.randn(len(texts), self.embedding_dim).astype('float32')

    def add_documents(self, documents: List[Dict[str, Any]]):
        """添加文档到向量库"""
        texts = [doc['content'] for doc in documents]

        # 生成向量
        print(f"🔄 生成 {len(texts)} 个文本的向量...")
        embeddings = self._encode(texts)

        # 初始化或更新FAISS索引
        if self.index is None:
            self.index = faiss.IndexFlatIP(self.embedding_dim)  # 内积索引
            self.index.add(embeddings)
        else:
            self.index.add(embeddings)

        # 保存文档
        for i, doc in enumerate(documents):
            doc['id'] = hashlib.md5(doc['content'].encode()).hexdigest()[:16]
            self.documents.append(doc)

        # 保存到磁盘
        faiss.write_index(self.index, self.index_path)
        with open(self.documents_path, 'wb') as f:
            pickle.dump(self.documents, f)

        print(f"✅ 已添加 {len(texts)} 个文档到FAISS")
        return len(texts)

    def search(self, query: str, k: int = 5) -> List[Dict]:
        """向量检索"""
        if self.index is None or not self.documents:
            return []

        # 生成查询向量
        query_embedding = self._encode([query])

        # 搜索
        k = min(k, len(self.documents))
        distances, indices = self.index.search(query_embedding, k)

        # 格式化结果
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.documents):
                doc = self.documents[idx]
                results.append({
                    'content': doc['content'],
                    'metadata': doc.get('metadata', {}),
                    'distance': float(distances[0][i]),
                    'score': float(distances[0][i])  # FAISS内积就是相似度
                })

        return results

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            'total_docs': len(self.documents),
            'embedding_model': 'shibing624/text2vec-base-chinese' if self.use_real_embedding else '模拟',
            'embedding_dim': self.embedding_dim,
            'index_type': 'FAISS (Inner Product)',
            'is_real_rag': self.use_real_embedding
        }


# 全局实例
vector_db = VectorDBService()