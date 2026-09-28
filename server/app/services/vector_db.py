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
        print("准备 embedding 模型...")
        self.use_real_embedding = True
        self.embedding_dim = 768

        # 加载中文 embedding 模型。只用国内镜像，不再全局关闭 SSL 校验：
        # `ssl._create_default_https_context = ssl._create_unverified_context` 是进程级
        # 全局副作用（本模块在 import 期就构造实例），会让**整个应用**所有 HTTPS 请求
        # 都不校验证书 —— 为下载一个模型牺牲全局传输安全，得不偿失。
        try:
            os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
            self.embedder = SentenceTransformer('shibing624/text2vec-base-chinese')
            self.embedding_dim = 768
            self.use_real_embedding = True
            print("成功加载百度 embedding 模型")
        except Exception as e:
            print(f"无法加载真实模型: {e}")
            print("embedding 模型不可用：检索时会在 _encode 明确报错，不再静默用随机向量")
            self.use_real_embedding = False

        # 2. 初始化FAISS索引
        if os.path.exists(self.index_path):
            self.index = faiss.read_index(self.index_path)
            with open(self.documents_path, 'rb') as f:
                self.documents = pickle.load(f)
            print(f"加载已有 FAISS 索引，包含 {len(self.documents)} 个文档")
        else:
            self.index = None
            self.documents = []
            print("创建新 FAISS 索引")

    def _encode(self, texts: List[str]) -> np.ndarray:
        """生成向量（L2 归一化，配合 IndexFlatIP 才等价于余弦相似度）

        旧实现在编码失败时**静默返回随机向量** —— 检索仍会"成功"返回 top-k，
        但结果毫无意义，故障被伪装成正常。现在改为显式抛错（仅在调用期抛，
        构造期不抛，否则 import 期构造的全局实例会让应用起不来）。
        """
        if not self.use_real_embedding:
            raise RuntimeError(
                "embedding 模型未加载成功，无法编码文本（拒绝降级为随机向量）。"
                "请检查模型路径/环境后重启。"
            )
        try:
            embeddings = self.embedder.encode(texts)
        except Exception as e:
            raise RuntimeError(f"embedding 编码失败：{e}") from e

        embeddings = np.ascontiguousarray(embeddings, dtype='float32')
        # 语料与查询走同一函数 ⇒ 两侧都被归一化；否则内积随模长膨胀，
        # 当作相似度会在长短文本间系统性偏移。
        faiss.normalize_L2(embeddings)
        return embeddings

    def add_documents(self, documents: List[Dict[str, Any]]):
        """添加文档到向量库"""
        texts = [doc['content'] for doc in documents]

        # 生成向量
        print(f"生成 {len(texts)} 个文本的向量...")
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

        print(f"已添加 {len(texts)} 个文档到 FAISS")
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
                    'score': float(distances[0][i])  # 已 L2 归一化，内积即余弦相似度
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
