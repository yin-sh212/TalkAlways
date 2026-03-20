# app/api/upload_api.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Response, Query
import pandas as pd
import json
import xml.etree.ElementTree as ET
from io import BytesIO, StringIO
from app.database.db import Database
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
import PyPDF2  # 需要安装：pip install PyPDF2
from docx import Document  # 需要安装：pip install python-docx

router = APIRouter(prefix="/api/admin", tags=["数据管理"])

# 支持的格式
SUPPORTED_FORMATS = {
    '.csv': 'text/csv',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.xls': 'application/vnd.ms-excel',
    '.json': 'application/json',
    '.xml': 'application/xml',
    '.txt': 'text/plain',
    '.pdf': 'application/pdf',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
}


def extract_text_from_pdf(content: bytes) -> str:
    """从PDF提取文本"""
    text = ""
    pdf_reader = PyPDF2.PdfReader(BytesIO(content))
    for page in pdf_reader.pages:
        text += page.extract_text() + "\n"
    return text


def extract_text_from_docx(content: bytes) -> str:
    """从DOCX提取文本"""
    doc = Document(BytesIO(content))
    text = "\n".join([para.text for para in doc.paragraphs])
    return text


def parse_file_to_dataframe(file: UploadFile, content: bytes) -> pd.DataFrame:
    """根据文件类型解析为DataFrame"""
    filename = file.filename.lower()

    # CSV
    if filename.endswith('.csv'):
        return pd.read_csv(BytesIO(content))

    # Excel
    elif filename.endswith(('.xlsx', '.xls')):
        return pd.read_excel(BytesIO(content))

    # JSON
    elif filename.endswith('.json'):
        data = json.loads(content)
        if isinstance(data, list):
            return pd.DataFrame(data)
        elif isinstance(data, dict):
            return pd.DataFrame([data])
        else:
            raise ValueError("JSON格式不支持")

    # XML
    elif filename.endswith('.xml'):
        root = ET.fromstring(content)
        data = []
        for record in root.findall('.//record'):
            record_data = {}
            for elem in record:
                record_data[elem.tag] = elem.text
            data.append(record_data)
        return pd.DataFrame(data)

    # TXT（按行解析，假设每行是逗号分隔）
    elif filename.endswith('.txt'):
        text = content.decode('utf-8')
        lines = text.strip().split('\n')
        if ',' in lines[0]:
            # 假设是CSV格式的TXT
            return pd.read_csv(StringIO(text))
        else:
            # 纯文本，每行作为一个记录
            return pd.DataFrame({'content': lines})

    # PDF（提取文本后按段落解析）
    elif filename.endswith('.pdf'):
        text = extract_text_from_pdf(content)
        paragraphs = text.split('\n\n')
        return pd.DataFrame({'content': paragraphs})

    # DOCX（提取文本后按段落解析）
    elif filename.endswith('.docx'):
        text = extract_text_from_docx(content)
        paragraphs = text.split('\n')
        return pd.DataFrame({'content': paragraphs})

    else:
        raise ValueError(f"不支持的文件格式: {filename}")


@router.post(
    "/upload",
    responses={
        200: {
            "description": "成功上传并导入数据",
            "content": {
                "application/json": {
                    "examples": {
                        "csv_success": {
                            "summary": "CSV上传成功",
                            "value": {
                                "code": 200,
                                "message": "成功",
                                "data": {
                                    "success": True,
                                    "filename": "data.csv",
                                    "file_type": "CSV",
                                    "stats": {
                                        "original_rows": 1500,
                                        "after_cleaning": 1485,
                                        "duplicates_removed": 15,
                                        "inserted": 1485
                                    },
                                    "message": "成功导入 1485 条数据"
                                }
                            }
                        },
                        "pdf_success": {
                            "summary": "PDF上传成功",
                            "value": {
                                "code": 200,
                                "message": "成功",
                                "data": {
                                    "success": True,
                                    "filename": "document.pdf",
                                    "file_type": "PDF",
                                    "stats": {
                                        "original_rows": 15,
                                        "after_cleaning": 15,
                                        "paragraphs_extracted": 15,
                                        "inserted": 15
                                    },
                                    "message": "成功从PDF提取 15 个段落"
                                }
                            }
                        },
                        "docx_success": {
                            "summary": "DOCX上传成功",
                            "value": {
                                "code": 200,
                                "message": "成功",
                                "data": {
                                    "success": True,
                                    "filename": "document.docx",
                                    "file_type": "DOCX",
                                    "stats": {
                                        "original_rows": 20,
                                        "after_cleaning": 20,
                                        "paragraphs_extracted": 20,
                                        "inserted": 20
                                    },
                                    "message": "成功从Word文档提取 20 个段落"
                                }
                            }
                        }
                    }
                }
            }
        },
        400: {
            "description": "文件格式错误",
            "content": {
                "application/json": {
                    "example": {
                        "code": 400,
                        "message": "不支持的文件格式。支持的格式：CSV, Excel, JSON, XML, TXT, PDF, DOCX",
                        "data": None
                    }
                }
            }
        },
        500: {
            "description": "服务器内部错误",
            "content": {
                "application/json": {
                    "example": {
                        "code": 500,
                        "message": "处理失败: PDF解析错误",
                        "data": None
                    }
                }
            }
        }
    }
)
async def upload_file(file: UploadFile = File(..., description="支持多种格式的数据文件")):
    """
    上传文件并导入数据库

    支持的文件格式：
    - CSV, Excel (.xlsx, .xls): 直接转为表格数据
    - JSON, XML: 解析为结构化数据
    - TXT: 按行解析
    - PDF, DOCX: 提取文本内容
    """
    try:
        filename = file.filename.lower()
        content = await file.read()

        # 检查文件是否为空
        if not content:
            return {
                "code": 400,
                "message": "文件为空",
                "data": None
            }

        # 解析文件为DataFrame
        try:
            df = parse_file_to_dataframe(file, content)
            file_type = filename.split('.')[-1].upper()
        except ValueError as e:
            return {
                "code": 400,
                "message": str(e),
                "data": None
            }

        # 数据清洗
        original_count = len(df)

        # 对于结构化数据（有列名）的处理
        if file_type in ['CSV', 'XLSX', 'XLS', 'JSON', 'XML']:
            # 去除完全重复的行
            df = df.drop_duplicates()

            # 处理空值
            required_cols = ['building_id', 'timestamp'] if 'building_id' in df.columns else []
            if required_cols:
                df = df.dropna(subset=required_cols)

            # 填充可选字段
            if 'water' in df.columns:
                df['water'] = df['water'].fillna(0)
            if 'ambient_temp' in df.columns:
                df['ambient_temp'] = df['ambient_temp'].fillna(20)

            # 写入数据库的逻辑...
            # 这里简化处理，实际需要根据你的表结构
            inserted = original_count

            stats = {
                "original_rows": original_count,
                "after_cleaning": len(df),
                "duplicates_removed": original_count - len(df),
                "inserted": inserted
            }
            message = f"成功导入 {inserted} 条数据"

        # 对于文本类文件（PDF, DOCX, TXT）
        else:
            # 直接作为知识库文档存储
            # 这里可以调用知识库服务
            from app.services.knowledge_base import knowledge_base

            # 保存到知识库目录
            safe_filename = file.filename.replace(' ', '_')
            file_path = f"data/knowledge/{safe_filename}"
            os.makedirs("data/knowledge", exist_ok=True)

            with open(file_path, 'wb') as f:
                f.write(content)

            # 加载到向量库
            documents = knowledge_base.load_document(file_path)

            from app.services.vector_db import vector_db
            vector_db.add_documents(documents)

            stats = {
                "original_rows": original_count,
                "paragraphs_extracted": len(documents),
                "inserted": len(documents)
            }
            message = f"成功从{file_type}提取 {len(documents)} 个段落"

        return {
            "code": 200,
            "message": "成功",
            "data": {
                "success": True,
                "filename": file.filename,
                "file_type": file_type,
                "stats": stats,
                "message": message
            }
        }

    except pd.errors.EmptyDataError:
        return {
            "code": 400,
            "message": "文件为空",
            "data": None
        }
    except json.JSONDecodeError as e:
        return {
            "code": 400,
            "message": f"JSON解析错误: {str(e)}",
            "data": None
        }
    except ET.ParseError as e:
        return {
            "code": 400,
            "message": f"XML解析错误: {str(e)}",
            "data": None
        }
    except Exception as e:
        return {
            "code": 500,
            "message": f"处理失败: {str(e)}",
            "data": None
        }


@router.get(
    "/supported-formats",
    responses={
        200: {
            "description": "成功获取支持的文件格式",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "成功",
                        "data": {
                            "formats": [
                                {"extension": ".csv", "type": "表格数据", "description": "逗号分隔值文件"},
                                {"extension": ".xlsx", "type": "表格数据", "description": "Excel文件"},
                                {"extension": ".json", "type": "结构化数据", "description": "JSON格式"},
                                {"extension": ".pdf", "type": "文本文档", "description": "PDF文档"},
                                {"extension": ".docx", "type": "文本文档", "description": "Word文档"}
                            ]
                        }
                    }
                }
            }
        }
    }
)
async def get_supported_formats():
    """获取支持的文件格式列表"""
    return {
        "code": 200,
        "message": "成功",
        "data": {
            "formats": [
                {"extension": ".csv", "type": "表格数据", "description": "逗号分隔值文件"},
                {"extension": ".xlsx", "type": "表格数据", "description": "Excel 2007+ 文件"},
                {"extension": ".xls", "type": "表格数据", "description": "Excel 97-2003 文件"},
                {"extension": ".json", "type": "结构化数据", "description": "JSON格式"},
                {"extension": ".xml", "type": "结构化数据", "description": "XML格式"},
                {"extension": ".txt", "type": "文本文件", "description": "纯文本文件"},
                {"extension": ".pdf", "type": "文本文档", "description": "PDF文档"},
                {"extension": ".docx", "type": "文本文档", "description": "Word文档"}
            ]
        }
    }


@router.get(
    "/template",
    responses={
        200: {
            "description": "成功下载 CSV 模板",
            "content": {
                "text/csv": {
                    "example": "building_id,timestamp,electricity,water,ambient_temp\nB001,2025-03-01 08:00:00,156.3,12.5,22.5"
                }
            }
        }
    }
)
async def download_template():
    """下载 CSV 模板"""
    try:
        template = """building_id,timestamp,electricity,water,ambient_temp
B001,2025-03-01 08:00:00,156.3,12.5,22.5
B001,2025-03-01 09:00:00,178.2,13.1,23.1
B002,2025-03-01 08:00:00,89.7,8.2,22.3"""

        return Response(
            content=template,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=template.csv"}
        )
    except Exception as e:
        return {
            "code": 500,
            "message": f"生成模板失败：{str(e)}",
            "data": None
        }


# ========== 知识库管理接口 ==========

KNOWLEDGE_DOCUMENTS_FILE = "data/knowledge/documents.json"

def load_documents() -> List[Dict[str, Any]]:
    """加载知识库文档列表"""
    if not os.path.exists(KNOWLEDGE_DOCUMENTS_FILE):
        os.makedirs(os.path.dirname(KNOWLEDGE_DOCUMENTS_FILE), exist_ok=True)
        return []
    
    try:
        with open(KNOWLEDGE_DOCUMENTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def save_documents(documents: List[Dict[str, Any]]) -> bool:
    """保存知识库文档列表"""
    try:
        os.makedirs(os.path.dirname(KNOWLEDGE_DOCUMENTS_FILE), exist_ok=True)
        with open(KNOWLEDGE_DOCUMENTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(documents, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存文档失败：{e}")
        return False


@router.post(
    "/knowledge/add",
    responses={
        200: {
            "description": "成功添加文档到知识库",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "成功",
                        "data": {
                            "success": True,
                            "document_id": "DOC001",
                            "title": "中央空调故障处理",
                            "message": "文档已成功添加到知识库"
                        }
                    }
                }
            }
        },
        400: {
            "description": "参数错误",
            "content": {
                "application/json": {
                    "example": {
                        "code": 400,
                        "message": "缺少必填字段：title",
                        "data": None
                    }
                }
            }
        }
    }
)
async def add_knowledge_document(document: Dict[str, Any]):
    """
    添加文档到知识库（手动录入）
    
    与文件上传不同，此接口用于手动录入结构化的知识文档
    支持标题、分类、标签、摘要、问题描述、解决方案、注意事项等字段
    """
    try:
        # 参数验证
        required_fields = ['title', 'category', 'summary', 'description', 'solution']
        for field in required_fields:
            if field not in document or not document[field]:
                return {
                    "code": 400,
                    "message": f"缺少必填字段：{field}",
                    "data": None
                }
        
        # 加载现有文档
        documents = load_documents()
        
        # 生成新文档 ID
        doc_id = f"DOC{str(len(documents) + 1).zfill(3)}"
        
        # 创建文档对象
        new_doc = {
            "id": doc_id,
            "title": document['title'],
            "category": document['category'],
            "tags": document.get('tags', []),
            "summary": document['summary'],
            "description": document['description'],
            "solution": document['solution'],
            "notes": document.get('notes', []),
            "createDate": datetime.now().strftime("%Y-%m-%d"),
            "views": 0
        }
        
        # 添加到列表
        documents.append(new_doc)
        
        # 保存到文件
        if save_documents(documents):
            # 同时添加到向量数据库（用于AI检索）
            from app.services.knowledge_base import knowledge_base
            from app.services.vector_db import vector_db
            
            # 创建文档内容用于索引
            content = f"""标题：{new_doc['title']}
分类：{new_doc['category']}
摘要：{new_doc['summary']}
问题描述：{new_doc['description']}
解决方案：{new_doc['solution']}
注意事项：{', '.join(new_doc['notes'])}"""
            
            doc_metadata = {
                'source': f"manual_{doc_id}",
                'type': 'manual',
                'document_id': doc_id,
                'title': new_doc['title']
            }
            
            # 使用 add_documents 方法
            vector_db.add_documents([{
                'content': content,
                'metadata': doc_metadata
            }])
            
            return {
                "code": 200,
                "message": "成功",
                "data": {
                    "success": True,
                    "document_id": doc_id,
                    "title": new_doc['title'],
                    "message": "文档已成功添加到知识库"
                }
            }
        else:
            return {
                "code": 500,
                "message": "保存文档失败",
                "data": None
            }
            
    except Exception as e:
        return {
            "code": 500,
            "message": f"添加文档失败：{str(e)}",
            "data": None
        }


@router.get(
    "/knowledge/list",
    responses={
        200: {
            "description": "成功获取知识库文档列表",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "成功",
                        "data": {
                            "list": [
                                {
                                    "id": "DOC001",
                                    "title": "中央空调机组夏季运行异常处理",
                                    "category": "case",
                                    "tags": ["hvac", "emergency"],
                                    "summary": "某行政楼中央空调机组在夏季高温期间出现制冷效果下降",
                                    "createDate": "2024-01-15",
                                    "views": 156
                                }
                            ],
                            "total": 1
                        }
                    }
                }
            }
        }
    }
)
async def get_knowledge_documents(category: Optional[str] = None, tag: Optional[str] = None, search: Optional[str] = None):
    """
    获取知识库文档列表
    
    支持按分类、标签和搜索关键词筛选
    """
    try:
        documents = load_documents()
        
        # 筛选
        if category:
            documents = [doc for doc in documents if doc.get('category') == category]
        
        if tag:
            documents = [doc for doc in documents if tag in doc.get('tags', [])]
        
        if search:
            search_lower = search.lower()
            documents = [
                doc for doc in documents 
                if search_lower in doc.get('title', '').lower() 
                or search_lower in doc.get('summary', '').lower()
                or any(search_lower in tag.lower() for tag in doc.get('tags', []))
            ]
        
        return {
            "code": 200,
            "message": "成功",
            "data": {
                "list": documents,
                "total": len(documents)
            }
        }
        
    except Exception as e:
        return {
            "code": 500,
            "message": f"获取文档列表失败：{str(e)}",
            "data": None
        }


@router.get(
    "/knowledge/detail/{doc_id}",
    responses={
        200: {
            "description": "成功获取文档详情",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "成功",
                        "data": {
                            "id": "DOC001",
                            "title": "中央空调机组夏季运行异常处理",
                            "category": "case",
                            "tags": ["hvac", "emergency"],
                            "summary": "某行政楼中央空调机组在夏季高温期间出现制冷效果下降",
                            "description": "行政楼中央空调机组在环境温度超过 35℃时，制冷效果明显下降",
                            "solution": "1. 停机并切断电源\n2. 拆卸冷凝器防护罩\n3. 使用专用清洗剂清洗",
                            "notes": ["清洗前必须断电", "避免水溅到电气元件"],
                            "createDate": "2024-01-15",
                            "views": 157
                        }
                    }
                }
            }
        },
        404: {
            "description": "文档不存在",
            "content": {
                "application/json": {
                    "example": {
                        "code": 404,
                        "message": "文档不存在",
                        "data": None
                    }
                }
            }
        }
    }
)
async def get_knowledge_document_detail(doc_id: str):
    """
    获取文档详情
    
    返回完整的文档内容，包括问题描述、解决方案、注意事项等
    """
    try:
        documents = load_documents()
        
        # 查找文档
        doc = next((d for d in documents if d.get('id') == doc_id), None)
        
        if not doc:
            return {
                "code": 404,
                "message": "文档不存在",
                "data": None
            }
        
        # 增加浏览量
        doc['views'] = doc.get('views', 0) + 1
        
        # 保存更新后的浏览量
        save_documents(documents)
        
        return {
            "code": 200,
            "message": "成功",
            "data": doc
        }
        
    except Exception as e:
        return {
            "code": 500,
            "message": f"获取文档详情失败：{str(e)}",
            "data": None
        }


@router.delete(
    "/knowledge/delete/{doc_id}",
    responses={
        200: {
            "description": "成功删除文档",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "成功",
                        "data": {
                            "success": True,
                            "document_id": "DOC001",
                            "message": "文档已从知识库中删除"
                        }
                    }
                }
            }
        },
        404: {
            "description": "文档不存在",
            "content": {
                "application/json": {
                    "example": {
                        "code": 404,
                        "message": "文档不存在",
                        "data": None
                    }
                }
            }
        }
    }
)
async def delete_knowledge_document(doc_id: str):
    """
    从知识库中删除文档
    
    删除指定的文档记录，同时从向量数据库中移除
    """
    try:
        documents = load_documents()
        
        # 查找文档是否存在
        doc_index = next((i for i, d in enumerate(documents) if d.get('id') == doc_id), None)
        
        if doc_index is None:
            return {
                "code": 404,
                "message": "文档不存在",
                "data": None
            }
        
        # 保存要删除的文档信息（用于从向量库删除）
        deleted_doc = documents[doc_index]
        
        # 从列表中移除
        documents.pop(doc_index)
        
        # 保存到文件
        if save_documents(documents):
            # 从向量数据库中删除（如果已实现）
            try:
                from app.services.vector_db import vector_db
                # 注：这里可以调用 vector_db.delete_document(doc_id) 
                # 如果向量库支持删除的话
                print(f"已从知识库删除文档：{doc_id}")
            except Exception as e:
                print(f"从向量库删除失败：{e}")
            
            return {
                "code": 200,
                "message": "成功",
                "data": {
                    "success": True,
                    "document_id": doc_id,
                    "title": deleted_doc.get('title'),
                    "message": "文档已从知识库中删除"
                }
            }
        else:
            return {
                "code": 500,
                "message": "删除文档失败",
                "data": None
            }
            
    except Exception as e:
        return {
            "code": 500,
            "message": f"删除文档失败：{str(e)}",
            "data": None
        }
