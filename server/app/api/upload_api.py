# app/api/upload_api.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Response, Query
import pandas as pd
from io import BytesIO, StringIO
from app.database.db import Database
import os
from datetime import datetime
from typing import Optional

router = APIRouter(prefix="/api/admin", tags=["数据管理"])


@router.post(
    "/upload",
    responses={
        200: {
            "description": "成功上传并导入数据",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "成功",
                        "data": {
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
            }
        },
        400: {
            "description": "文件格式错误",
            "content": {
                "application/json": {
                    "example": {
                        "code": 400,
                        "message": "只支持CSV文件",
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
                        "message": "处理失败: 数据库连接错误",
                        "data": None
                    }
                }
            }
        }
    }
)
async def upload_csv(file: UploadFile = File(..., description="CSV格式的数据文件")):
    """
    上传CSV文件并导入数据库

    - 支持字段：building_id, timestamp, electricity, water, ambient_temp等
    - 自动清洗数据：去重、处理空值
    """
    try:
        # 1. 验证文件格式
        if not file.filename.endswith('.csv'):
            return {
                "code": 400,
                "message": "只支持CSV文件",
                "data": None
            }

        # 2. 读取文件内容
        content = await file.read()
        df = pd.read_csv(BytesIO(content))

        # 3. 数据清洗
        original_count = len(df)

        # 3.1 去除完全重复的行
        df = df.drop_duplicates()

        # 3.2 处理空值 - 必需字段不能为空
        df = df.dropna(subset=['building_id', 'timestamp'])

        # 3.3 填充可选字段的空值
        if 'water' in df.columns:
            df['water'] = df['water'].fillna(0)
        if 'ambient_temp' in df.columns:
            df['ambient_temp'] = df['ambient_temp'].fillna(20)
        if 'electricity' not in df.columns:
            df['electricity'] = 0

        # 3.4 格式转换
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
                            str(row.get('building_id')),
                            str(row.get('meter_id', f"{row.get('building_id')}_M1")),
                            row['timestamp'],
                            float(row.get('electricity', 0)),
                            float(row.get('water', 0)),
                            float(row.get('ambient_temp', 20)),
                            0
                        ))
                        inserted += 1
                    except Exception as e:
                        print(f"插入失败: {e}")
                        continue

                await conn.commit()

        # 5. 返回统计结果
        return {
            "code": 200,
            "message": "成功",
            "data": {
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
        }

    except pd.errors.EmptyDataError:
        return {
            "code": 400,
            "message": "文件为空",
            "data": None
        }
    except pd.errors.ParserError as e:
        return {
            "code": 400,
            "message": f"CSV解析错误: {str(e)}",
            "data": None
        }
    except Exception as e:
        return {
            "code": 500,
            "message": f"处理失败: {str(e)}",
            "data": None
        }


@router.get(
    "/upload/template",
    responses={
        200: {
            "description": "成功下载CSV模板",
            "content": {
                "text/csv": {
                    "example": "building_id,timestamp,electricity,water,ambient_temp\nB001,2025-03-01 08:00:00,156.3,12.5,22.5\nB001,2025-03-01 09:00:00,178.2,13.1,23.1"
                }
            }
        },
        500: {
            "description": "服务器内部错误",
            "content": {
                "application/json": {
                    "example": {
                        "code": 500,
                        "message": "生成模板失败",
                        "data": None
                    }
                }
            }
        }
    }
)
async def download_template():
    """下载CSV模板文件"""
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
            "message": f"生成模板失败: {str(e)}",
            "data": None
        }


# 可选：添加一个获取上传历史接口
@router.get(
    "/upload/history",
    responses={
        200: {
            "description": "成功获取上传历史",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "成功",
                        "data": {
                            "total_uploads": 5,
                            "total_rows": 12500,
                            "last_upload": "2025-03-11 15:30:00"
                        }
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
                        "message": "获取历史失败",
                        "data": None
                    }
                }
            }
        }
    }
)
async def get_upload_history():
    """获取上传历史统计（示例接口）"""
    try:
        # 这里可以查询数据库统计上传记录
        # 由于没有专门的上传记录表，返回模拟数据
        return {
            "code": 200,
            "message": "成功",
            "data": {
                "total_uploads": 5,
                "total_rows": 12500,
                "last_upload": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }
    except Exception as e:
        return {
            "code": 500,
            "message": f"获取历史失败: {str(e)}",
            "data": None
        }