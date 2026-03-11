# app/services/knowledge_base.py
import os
from typing import List, Dict, Any
import glob


class KnowledgeBaseService:
    """知识库管理服务"""

    def __init__(self, knowledge_dir="./data/knowledge"):
        self.knowledge_dir = knowledge_dir
        os.makedirs(knowledge_dir, exist_ok=True)

    def load_all_documents(self) -> List[Dict[str, Any]]:
        """加载所有文档"""
        documents = []

        # 获取所有txt文件
        txt_files = glob.glob(os.path.join(self.knowledge_dir, "*.txt"))

        for file_path in txt_files:
            docs = self.load_document(file_path)
            documents.extend(docs)

        return documents

    def load_document(self, file_path: str) -> List[Dict[str, Any]]:
        """加载单个文档，按段落分块"""
        documents = []
        filename = os.path.basename(file_path)

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 按空行分割段落
        paragraphs = content.split('\n\n')

        for i, para in enumerate(paragraphs):
            para = para.strip()
            if len(para) > 20:  # 忽略太短的段落
                documents.append({
                    'content': para,
                    'metadata': {
                        'source': filename,
                        'chunk': i,
                        'title': para.split('\n')[0][:50]  # 第一行作为标题
                    }
                })

        return documents

    def add_document(self, filename: str, content: str):
        """添加新文档"""
        file_path = os.path.join(self.knowledge_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ 已添加文档: {filename}")

    def list_documents(self) -> List[str]:
        """列出所有文档"""
        return [os.path.basename(f) for f in glob.glob(os.path.join(self.knowledge_dir, "*.txt"))]

    def get_document(self, filename: str) -> str:
        """获取文档内容"""
        file_path = os.path.join(self.knowledge_dir, filename)
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()


# 全局实例
knowledge_base = KnowledgeBaseService()