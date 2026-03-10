# app/api/upload_api.py
from fastapi import APIRouter, UploadFile, File, HTTPException,Response
import pandas as pd
from io import BytesIO, StringIO
from app.database.db import Database
import os
from datetime import datetime
from typing import List

router = APIRouter(prefix="/api/admin", tags=["数据管理"])


@router.post(
    "/upload",
   responses={
       200: {
            "description": "成功上传并导入数据",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "filename": "data.csv",
                        "stats": {
                            "original_rows": 1500,
                            "after_cleaning": 1485,
                            "duplicates_removed": 15,
                            "inserted": 1485
                        },
                        "message": "成功导入 1485 条数据"
                    }
                }
            }
        },
        400: {
            "description": "文件格式错误",
            "content": {
                "application/json": {
                    "example": {"detail": "只支持 CSV 文件"}
                }
            }
        }
    }
)
async def upload_csv(file: UploadFile = File(..., description="CSV 格式的数据文件")):
    """
    上传 CSV 文件并导入数据库
    支持字段：building_id, timestamp, electricity, water, ambient_temp 等
    """
    # 1. 验证文件格式
    if not file.filename.endswith('.csv'):
        raise HTTPException(400, "只支持 CSV 文件")

    try:
        # 读取文件内容
        content = await file.read()
        df = pd.read_csv(BytesIO(content))

        # 数据清洗（赛题要求！）
        original_count = len(df)

        # 去除完全重复的行
        df = df.drop_duplicates()

        # 处理空值
        df = df.dropna(subset=['building_id', 'timestamp'])  # 必需字段不能为空

        # 填充可选字段的空值
        if 'water' in df.columns:
            df['water'] = df['water'].fillna(0)
        if 'ambient_temp' in df.columns:
            df['ambient_temp'] = df['ambient_temp'].fillna(20)  # 默认温度

        # 格式转换
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        cleaned_count = len(df)

        # 4. 写入数据库
        async with Database.get_pool() as conn:
            async with conn.cursor() as cursor:
                inserted = 0
                for _, row in df.iterrows():
                    try:
                        sql = """
                            INSERT INTO energy_consumption 
                            (building_id, meter_id, timestamp, electricity, water, ambient_temp, is_anomaly)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """
                        await cursor.execute(sql, (
                            row.get('building_id'),
                            row.get('meter_id', f"{row.get('building_id')}_M1"),
                            row['timestamp'],
                            float(row.get('electricity', 0)),
                            float(row.get('water', 0)),
                            float(row.get('ambient_temp', 20)),
                            0  # 默认正常
                        ))
                        inserted += 1
                    except Exception as e:
                        print(f"插入失败：{e}")

                await conn.commit()

        # 5. 返回统计结果
        return {
            "success": True,
            "filename": file.filename,
            "stats": {
                "original_rows": original_count,
                "after_cleaning": cleaned_count,
                "duplicates_removed": original_count - cleaned_count,
                "inserted": inserted
            },
            "message": f"成功导入 {inserted} 条数据"
        }

    except Exception as e:
        raise HTTPException(500, f"处理失败：{str(e)}")


@router.get(
    "/upload/template",
    responses={
        200: {
            "description": "成功下载 CSV 模板",
            "content": {"text/csv": {}}
        }
    }
)
async def download_template():
    """下载 CSV 模板"""
    template = """building_id,timestamp,electricity,water,ambient_temp
B001,2025-03-01 08:00:00,156.3,12.5,22.5
B001,2025-03-01 09:00:00,178.2,13.1,23.1
B002,2025-03-01 08:00:00,89.7,8.2,22.3"""

    return Response(
        content=template,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=template.csv"}
    )


# 知识库文档上传路由
knowledge_router = APIRouter(prefix="/api/upload", tags=["知识库管理"])

@knowledge_router.post("/document")
async def upload_document(file: UploadFile = File(..., description="知识库文档文件（支持 PDF、TXT、DOC、DOCX）")):
    """
    上传文档到知识库并建立向量索引
    """
    import tempfile
    from app.services.rag_service import rag_service
    
    # 验证文件类型
    valid_extensions = ['.pdf', '.txt', '.doc', '.docx']
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in valid_extensions:
        raise HTTPException(400, detail=f"不支持的文件类型，仅支持：{', '.join(valid_extensions)}")
    
    try:
        # 保存临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        # 添加到 RAG 知识库
        inserted_count = rag_service.add_documents([tmp_path])
        
        # 清理临时文件
        try:
            os.unlink(tmp_path)
        except Exception as e:
            print(f"清理临时文件失败：{e}")
        
        if inserted_count == 0:
            raise HTTPException(500, detail="文档处理失败，未能提取到有效内容")
        
        return {
            "success": True,
            "filename": file.filename,
            "message": f"成功上传并处理 {inserted_count} 个文档块",
            "stats": {
                "blocks_indexed": inserted_count
            }
        }
        
    except Exception as e:
        raise HTTPException(500, detail=f"处理失败：{str(e)}")
