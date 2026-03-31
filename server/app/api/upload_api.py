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
    """从 PDF 提取文本"""
    text = ""
    pdf_reader = PyPDF2.PdfReader(BytesIO(content))
    for page in pdf_reader.pages:
        text += page.extract_text() + "\n"
    return text


def extract_text_from_docx(content: bytes) -> str:
    """从 DOCX 提取文本"""
    try:
        doc = Document(BytesIO(content))
        # 只提取段落文本，过滤空行和页眉页脚
        paragraphs = []
        for para in doc.paragraphs:
            text = para.text.strip()
            # 过滤掉过短的文本（可能是页眉页脚或格式符号）
            if len(text) > 5:
                paragraphs.append(text)
        
        if not paragraphs:
            return ""
        
        return "\n".join(paragraphs)
    except Exception as e:
        raise ValueError(f"DOCX 文件解析失败：{str(e)}")


def parse_file_to_dataframe(file: UploadFile, content: bytes) -> pd.DataFrame:
    """根据文件类型解析为 DataFrame"""
    filename = file.filename.lower()

    # 只支持特定的文件格式
    supported_extensions = ['.csv', '.xlsx', '.xls', '.json', '.xml', '.txt', '.pdf', '.docx']
    
    # 检查文件扩展名
    if not any(filename.endswith(ext) for ext in supported_extensions):
        raise ValueError(f"不支持的文件格式 '{file.filename}'，仅支持：{', '.join(supported_extensions)}")

    # CSV
    if filename.endswith('.csv'):
        return pd.read_csv(BytesIO(content))

    # Excel
    elif filename.endswith(('.xlsx', '.xls')):
        try:
            return pd.read_excel(BytesIO(content))
        except Exception as e:
            raise ValueError(f"Excel 文件解析失败：{str(e)}")

    # JSON
    elif filename.endswith('.json'):
        try:
            data = json.loads(content.decode('utf-8'))
            if isinstance(data, list):
                return pd.DataFrame(data)
            else:
                return pd.DataFrame([data])
        except Exception as e:
            raise ValueError(f"JSON 文件解析失败：{str(e)}")

    # XML
    elif filename.endswith('.xml'):
        try:
            tree = ET.parse(BytesIO(content))
            root = tree.getroot()
            data = []
            for child in root:
                row = {}
                for elem in child:
                    row[elem.tag] = elem.text
                if row:
                    data.append(row)
            if not data:
                raise ValueError("XML 文件中没有有效数据")
            return pd.DataFrame(data)
        except Exception as e:
            raise ValueError(f"XML 文件解析失败：{str(e)}")

    # TXT（纯文本）
    elif filename.endswith('.txt'):
        try:
            text = content.decode('utf-8')
            lines = text.strip().split('\n')
            # 尝试检测是否为 CSV 格式
            if len(lines) > 0 and (',' in lines[0] or '\t' in lines[0]):
                delimiter = '\t' if '\t' in lines[0] else ','
                return pd.read_csv(StringIO(text), delimiter=delimiter)
            else:
                # 纯文本，每行作为一条记录
                if not lines or all(not line.strip() for line in lines):
                    raise ValueError("TXT 文件中没有有效文本")
                return pd.DataFrame({'content': lines})
        except UnicodeDecodeError:
            raise ValueError("TXT 文件编码错误，请使用 UTF-8 编码")

    # PDF（提取文本后按段落解析）
    elif filename.endswith('.pdf'):
        text = extract_text_from_pdf(content)
        # 按段落分割，过滤空行
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        if not paragraphs:
            raise ValueError("PDF 文件中未提取到有效文本")
        return pd.DataFrame({'content': paragraphs})

    # DOCX（提取文本后按段落解析）
    elif filename.endswith('.docx'):
        text = extract_text_from_docx(content)
        # 按段落分割，过滤空行和过短文本
        paragraphs = [p.strip() for p in text.split('\n') if p.strip() and len(p.strip()) > 5]
        if not paragraphs:
            raise ValueError("DOCX 文件中未提取到有效文本")
        return pd.DataFrame({'content': paragraphs})
    
    # 不支持的格式
    else:
        raise ValueError(f"不支持的文件格式：{file.content_type}")


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
):
    """上传文件并解析为 DataFrame"""
    try:
        # 读取文件内容（只读取一次）
        content = await file.read()
        
        if not content:
            raise HTTPException(status_code=400, detail="文件内容为空")
        
        # 检查文件大小（限制 10MB）
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="文件大小不能超过 10MB")
        
        # 解析文件
        df = parse_file_to_dataframe(file, content)
        
        if df.empty:
            raise HTTPException(status_code=400, detail="文件中没有有效数据")
        
        # 返回统计信息
        return {
            "message": "上传成功",
            "stats": {
                "rows": len(df),
                "columns": len(df.columns),
                "column_names": list(df.columns)
            }
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except pd.errors.EmptyDataError:
        raise HTTPException(status_code=400, detail="文件为空或格式错误")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"服务器错误：{str(e)}")
