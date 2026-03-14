# app/services/knowledge_base.py
import os
from typing import List, Dict, Any
import glob
import PyPDF2  # 需要安装
from docx import Document  # 需要安装


class KnowledgeBaseService:
    """知识库管理服务 - 支持多种文档格式"""

    def __init__(self, knowledge_dir="./data/knowledge"):
        self.knowledge_dir = knowledge_dir
        os.makedirs(knowledge_dir, exist_ok=True)

    def load_all_documents(self) -> List[Dict[str, Any]]:
        """加载所有文档（支持多种格式）"""
        documents = []

        # 获取所有支持的文件
        file_patterns = ["*.txt", "*.pdf", "*.docx", "*.md"]
        for pattern in file_patterns:
            files = glob.glob(os.path.join(self.knowledge_dir, pattern))
            for file_path in files:
                docs = self.load_document(file_path)
                documents.extend(docs)

        return documents

    def load_document(self, file_path: str) -> List[Dict[str, Any]]:
        """根据文件类型加载文档"""
        ext = os.path.splitext(file_path)[1].lower()

        if ext == '.txt' or ext == '.md':
            return self._load_text_file(file_path)
        elif ext == '.pdf':
            return self._load_pdf_file(file_path)
        elif ext == '.docx':
            return self._load_docx_file(file_path)
        else:
            print(f"⚠️ 不支持的文件格式: {ext}")
            return []

    def _load_text_file(self, file_path: str) -> List[Dict[str, Any]]:
        """加载文本文件"""
        documents = []
        filename = os.path.basename(file_path)

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 按空行分割段落
        paragraphs = content.split('\n\n')

        for i, para in enumerate(paragraphs):
            para = para.strip()
            if len(para) > 20:
                documents.append({
                    'content': para,
                    'metadata': {
                        'source': filename,
                        'chunk': i,
                        'type': 'text',
                        'title': para.split('\n')[0][:50]
                    }
                })

        return documents

    def _load_pdf_file(self, file_path: str) -> List[Dict[str, Any]]:
        """加载PDF文件"""
        documents = []
        filename = os.path.basename(file_path)

        try:
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page_num, page in enumerate(pdf_reader.pages):
                    text = page.extract_text()
                    # 按段落分割
                    paragraphs = text.split('\n\n')
                    for para_num, para in enumerate(paragraphs):
                        para = para.strip()
                        if len(para) > 20:
                            documents.append({
                                'content': para,
                                'metadata': {
                                    'source': filename,
                                    'page': page_num + 1,
                                    'paragraph': para_num,
                                    'type': 'pdf',
                                    'title': f"{filename} - 第{page_num + 1}页"
                                }
                            })
        except Exception as e:
            print(f"❌ PDF解析失败 {file_path}: {e}")

        return documents

    def _load_docx_file(self, file_path: str) -> List[Dict[str, Any]]:
        """加载Word文档"""
        documents = []
        filename = os.path.basename(file_path)

        try:
            doc = Document(file_path)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]

            for i, para in enumerate(paragraphs):
                if len(para) > 20:
                    documents.append({
                        'content': para,
                        'metadata': {
                            'source': filename,
                            'paragraph': i,
                            'type': 'docx',
                            'title': para[:50]
                        }
                    })
        except Exception as e:
            print(f"❌ DOCX解析失败 {file_path}: {e}")

        return documents

    def add_document(self, filename: str, content: bytes):
        """添加新文档（二进制内容）"""
        file_path = os.path.join(self.knowledge_dir, filename)
        with open(file_path, 'wb') as f:
            f.write(content)
        print(f"✅ 已添加文档: {filename}")
        return file_path

    def list_documents(self) -> List[str]:
        """列出所有文档"""
        documents = []
        for pattern in ["*.txt", "*.pdf", "*.docx", "*.md"]:
            documents.extend([os.path.basename(f) for f in glob.glob(os.path.join(self.knowledge_dir, pattern))])
        return documents

    def get_document(self, filename: str) -> str:
        """获取文档内容（文本）"""
        file_path = os.path.join(self.knowledge_dir, filename)
        ext = os.path.splitext(filename)[1].lower()

        if ext in ['.txt', '.md']:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            return f"【二进制文件】{filename}，请下载查看"


# 全局实例
knowledge_base = KnowledgeBaseService()
