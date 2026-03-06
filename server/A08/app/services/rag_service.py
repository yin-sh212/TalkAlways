# app/services/rag_service.py
import os
import sys
import pickle
import numpy as np
from typing import List, Dict, Any, Optional

# 解决 Windows 上 pwd 模块缺失的问题
import builtins
if not hasattr(builtins, 'pwd'):
    # 创建一个虚拟的 pwd 模块
    import types
    pwd = types.ModuleType('pwd')
    def mock_getpwuid(uid):
        class MockPwuid:
            pw_name = 'unknown'
        return MockPwuid()
    pwd.getpwuid = mock_getpwuid
    sys.modules['pwd'] = pwd

# 正确的导入方式
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

# 其余的代码保持不变...

class FaissRAGService:
    """使用 FAISS 的 RAG 服务"""

    def __init__(self, persist_directory="./data/faiss_index"):
        self.persist_directory = persist_directory
        self.embeddings = HuggingFaceEmbeddings(
            model_name="BAAI/bge-small-zh",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        self.vectorstore = None
        self.documents = []

    def init_knowledge_base(self):
        """初始化知识库"""
        if os.path.exists(self.persist_directory):
            try:
                # 加载已有索引
                self.vectorstore = FAISS.load_local(
                    self.persist_directory,
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
                print(f"✅ 加载已有 FAISS 索引: {self.persist_directory}")
            except Exception as e:
                print(f"⚠️ 加载索引失败，将创建新的: {e}")
                self.vectorstore = None
        else:
            print(f"📁 将创建新的 FAISS 索引: {self.persist_directory}")
            os.makedirs(self.persist_directory, exist_ok=True)

    def add_documents(self, file_paths: List[str]) -> int:
        """添加文档到知识库"""
        documents = []

        for file_path in file_paths:
            if not os.path.exists(file_path):
                print(f"⚠️ 文件不存在: {file_path}")
                continue

            print(f"📄 加载文档: {file_path}")

            try:
                # 根据文件类型选择加载器
                if file_path.endswith('.txt'):
                    loader = TextLoader(file_path, encoding='utf-8')
                elif file_path.endswith('.pdf'):
                    loader = PyPDFLoader(file_path)
                else:
                    print(f"❌ 不支持的文件类型: {file_path}")
                    continue

                docs = loader.load()
                documents.extend(docs)
                print(f"   - 加载了 {len(docs)} 个文档块")

            except Exception as e:
                print(f"❌ 加载文档失败 {file_path}: {e}")
                continue

        if not documents:
            print("⚠️ 没有成功加载任何文档")
            return 0

        # 文本分块
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n", "\n", "。", "；", "，", " ", ""]
        )
        texts = text_splitter.split_documents(documents)

        print(f"📊 共加载 {len(documents)} 个文档，分割为 {len(texts)} 个文本块")

        # 添加到向量库
        try:
            if self.vectorstore is None:
                # 创建新索引
                self.vectorstore = FAISS.from_documents(
                    documents=texts,
                    embedding=self.embeddings
                )
                print("✅ 创建新的 FAISS 索引")
            else:
                # 添加到现有索引
                self.vectorstore.add_documents(texts)
                print("✅ 添加到现有 FAISS 索引")

            # 保存索引
            os.makedirs(self.persist_directory, exist_ok=True)
            self.vectorstore.save_local(self.persist_directory)
            print(f"✅ FAISS 索引已保存到 {self.persist_directory}")

            return len(texts)

        except Exception as e:
            print(f"❌ 添加文档到 FAISS 失败: {e}")
            return 0

    def search(self, query: str, k: int = 3) -> List[Dict]:
        """搜索相关文档"""
        if self.vectorstore is None:
            print("⚠️ 向量库未初始化")
            return []

        try:
            docs = self.vectorstore.similarity_search_with_score(query, k=k)

            results = []
            for doc, score in docs:
                results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": float(score)
                })

            return results

        except Exception as e:
            print(f"❌ 搜索失败: {e}")
            return []

    def answer(self, question: str) -> Dict:
        """回答问题"""
        results = self.search(question, k=3)

        if not results:
            return {
                "answer": "抱歉，知识库中没有找到相关信息。",
                "sources": []
            }

        # 构造回答
        answer = f"📚 找到 {len(results)} 条相关信息：\n\n"
        for i, r in enumerate(results, 1):
            answer += f"{i}. {r['content'][:200]}...\n"
            if r.get('metadata', {}).get('source'):
                answer += f"   (来源: {os.path.basename(r['metadata']['source'])})\n"
            answer += "\n"

        return {
            "answer": answer,
            "sources": results
        }

    def get_stats(self) -> Dict:
        """获取知识库统计信息"""
        if self.vectorstore is None:
            return {"status": "未初始化", "doc_count": 0}

        try:
            # FAISS 没有直接的方法获取文档数，可以通过 index 的 ntotal 获取向量数
            index = self.vectorstore.index
            vector_count = index.ntotal if index else 0
            return {
                "status": "正常",
                "vector_count": vector_count,
                "index_path": self.persist_directory
            }
        except Exception as e:
            return {"status": f"错误: {e}", "doc_count": 0}


# 创建全局实例
rag_service = FaissRAGService()