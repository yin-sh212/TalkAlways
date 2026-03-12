# app/api/export_api.py
from fastapi import APIRouter, Response, Query, HTTPException
import pandas as pd
from io import StringIO, BytesIO
from app.database.db import Database
from typing import Optional
import os
import datetime

router = APIRouter(prefix="/api/export", tags=["报表导出"])


@router.get(
    "/csv",
    responses={
        200: {
            "description": "成功导出CSV文件",
            "content": {
                "text/csv": {
                    "example": "building_id,timestamp,electricity,water\nB001,2025-01-01 08:00:00,156.32,12.5\nB001,2025-01-01 09:00:00,178.21,13.2"
                }
            }
        },
        400: {
            "description": "参数错误或无数据",
            "content": {
                "application/json": {
                    "example": {
                        "code": 400,
                        "message": "没有数据可导出",
                        "data": None
                    }
                }
            }
        },
        401: {
            "description": "未认证",
            "content": {
                "application/json": {
                    "example": {
                        "code": 401,
                        "message": "未提供认证信息",
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
                        "message": "导出失败: 数据库连接错误",
                        "data": None
                    }
                }
            }
        }
    }
)
async def export_csv(
    building_id: str = Query(..., description="建筑编号，如：B001"),
    start_date: str = Query(..., description="开始日期，格式：YYYY-MM-DD，例如：2025-01-01"),
    end_date: str = Query(..., description="结束日期，格式：YYYY-MM-DD，例如：2025-01-31")
):
    """导出CSV格式报表"""
    try:
        sql = """
            SELECT * FROM energy_consumption 
            WHERE building_id = %s AND DATE(timestamp) BETWEEN %s AND %s
            ORDER BY timestamp
        """
        data = await Database.fetch_all(sql, (building_id, start_date, end_date))

        if not data:
            return {
                "code": 400,
                "message": "没有数据可导出",
                "data": None
            }

        # 转为DataFrame
        df = pd.DataFrame(data)

        # 生成CSV
        output = StringIO()
        df.to_csv(output, index=False, encoding='utf-8-sig')

        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=energy_{building_id}_{start_date}.csv"}
        )
    except Exception as e:
        return {
            "code": 500,
            "message": f"导出失败: {str(e)}",
            "data": None
        }


@router.get(
    "/excel",
    responses={
        200: {
            "description": "成功导出Excel文件",
            "content": {
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {
                    "example": "（二进制文件，此处无法展示示例）"
                }
            }
        },
        400: {
            "description": "参数错误或无数据",
            "content": {
                "application/json": {
                    "example": {
                        "code": 400,
                        "message": "没有数据可导出",
                        "data": None
                    }
                }
            }
        },
        401: {
            "description": "未认证",
            "content": {
                "application/json": {
                    "example": {
                        "code": 401,
                        "message": "未提供认证信息",
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
                        "message": "导出失败: 数据库连接错误",
                        "data": None
                    }
                }
            }
        }
    }
)
async def export_excel(
    building_id: str = Query(..., description="建筑编号，如：B001"),
    start_date: str = Query(..., description="开始日期，格式：YYYY-MM-DD，例如：2025-01-01"),
    end_date: str = Query(..., description="结束日期，格式：YYYY-MM-DD，例如：2025-01-31")
):
    """导出Excel格式报表"""
    try:
        sql = """
            SELECT * FROM energy_consumption 
            WHERE building_id = %s AND DATE(timestamp) BETWEEN %s AND %s
            ORDER BY timestamp
        """
        data = await Database.fetch_all(sql, (building_id, start_date, end_date))

        if not data:
            return {
                "code": 400,
                "message": "没有数据可导出",
                "data": None
            }

        # 转为DataFrame
        df = pd.DataFrame(data)

        # 生成Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='能耗数据')

        return Response(
            content=output.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=energy_{building_id}_{start_date}.xlsx"}
        )
    except Exception as e:
        return {
            "code": 500,
            "message": f"导出失败: {str(e)}",
            "data": None
        }


@router.get(
    "/pdf",
    responses={
        200: {
            "description": "成功导出PDF文件",
            "content": {
                "application/pdf": {
                    "example": "（二进制文件，此处无法展示示例）"
                }
            }
        },
        400: {
            "description": "参数错误或无数据",
            "content": {
                "application/json": {
                    "example": {
                        "code": 400,
                        "message": "没有数据可导出",
                        "data": None
                    }
                }
            }
        },
        401: {
            "description": "未认证",
            "content": {
                "application/json": {
                    "example": {
                        "code": 401,
                        "message": "未提供认证信息",
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
                        "message": "PDF生成失败: 字体错误",
                        "data": None
                    }
                }
            }
        }
    }
)
async def export_pdf(
    building_id: str = Query(..., description="建筑编号，如：B001"),
    start_date: str = Query(..., description="开始日期，格式：YYYY-MM-DD，例如：2025-01-01"),
    end_date: str = Query(..., description="结束日期，格式：YYYY-MM-DD，例如：2025-01-31")
):
    """导出PDF报表 - 支持中文"""
    log_file = f"pdf_debug_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    def log(msg):
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"{datetime.datetime.now()}: {msg}\n")
        print(msg, flush=True)

    log("\n" + "=" * 50)
    log("📄 PDF导出调试日志")
    log(f"参数: building_id={building_id}, start_date={start_date}, end_date={end_date}")
    log("=" * 50)

    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from io import BytesIO
        from fastapi.responses import Response
        import os

        # 查询数据
        sql = """
            SELECT 
                DATE_FORMAT(timestamp, '%%Y-%%m-%%d %%H:00') as time,
                electricity,
                water,
                ambient_temp,
                is_anomaly
            FROM energy_consumption 
            WHERE building_id = %s 
                AND DATE(timestamp) BETWEEN %s AND %s
            ORDER BY timestamp
            LIMIT 500
        """
        data = await Database.fetch_all(sql, (building_id, start_date, end_date))
        log(f"📊 查询到 {len(data)} 条数据")

        if not data:
            log("❌ 没有数据")
            return {
                "code": 400,
                "message": "没有数据可导出",
                "data": None
            }

        # 检查字体文件
        log("\n🔍 检查字体文件：")
        font_paths = [
            ("C:/Windows/Fonts/simhei.ttf", "黑体"),
            ("C:/Windows/Fonts/msyh.ttc", "微软雅黑"),
            ("C:/Windows/Fonts/simsun.ttc", "宋体"),
            ("C:/Windows/Fonts/simkai.ttf", "楷体"),
        ]

        available_fonts = []
        for font_path, font_name in font_paths:
            if os.path.exists(font_path):
                size = os.path.getsize(font_path) / 1024
                log(f"✅ {font_name}: {font_path} (大小: {size:.1f} KB)")
                available_fonts.append((font_path, font_name))
            else:
                log(f"❌ {font_name}: {font_path} 不存在")

        # 创建PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []

        # 注册字体
        font_registered = False
        font_name = 'Helvetica'

        log("\n🔤 尝试注册字体：")

        for font_path, display_name in available_fonts:
            try:
                font_key = display_name.replace('黑体', 'SimHei').replace('微软雅黑', 'MicrosoftYaHei').replace('宋体', 'SimSun').replace('楷体', 'KaiTi')
                pdfmetrics.registerFont(TTFont(font_key, font_path))
                font_name = font_key
                font_registered = True
                log(f"✅ 成功注册 {display_name} ({font_key})")
                break
            except Exception as e:
                log(f"❌ 注册 {display_name} 失败: {e}")

        if font_registered:
            log(f"\n🎉 字体注册成功！使用字体: {font_name}")
        else:
            log("\n⚠️ 所有字体注册失败，使用默认字体")

        # 创建样式
        styles = getSampleStyleSheet()

        if font_registered:
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Title'],
                fontName=font_name,
                fontSize=16,
                alignment=1,
                spaceAfter=20
            )
            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontName=font_name,
                fontSize=10,
                spaceAfter=6
            )
            log(f"✅ 创建中文样式，使用字体: {font_name}")
        else:
            title_style = styles['Title']
            normal_style = styles['Normal']
            log("⚠️ 使用默认英文字体")

        # 标题
        title_text = f"建筑 {building_id} 能耗报表 ({start_date} 至 {end_date})"
        log(f"📝 标题: {title_text}")
        elements.append(Paragraph(title_text, title_style))
        elements.append(Spacer(1, 0.2 * inch))

        # 统计信息
        total_elec = sum(d['electricity'] for d in data)
        avg_elec = total_elec / len(data) if data else 0
        max_elec = max(d['electricity'] for d in data)
        anomaly_count = sum(1 for d in data if d['is_anomaly'])

        stats_text = f"""
        总用电量: {total_elec:.2f} kWh<br/>
        平均用电量: {avg_elec:.2f} kWh<br/>
        最大用电量: {max_elec:.2f} kWh<br/>
        异常点数: {anomaly_count}<br/>
        数据条数: {len(data)}
        """
        elements.append(Paragraph(stats_text, normal_style))
        elements.append(Spacer(1, 0.2 * inch))

        # 表格数据
        table_data = [['时间', '用电量(kWh)', '用水量(m³)', '温度(℃)', '状态']]

        for row in data[:100]:
            status = "异常" if row['is_anomaly'] else "正常"
            table_data.append([
                row['time'],
                f"{row['electricity']:.2f}",
                f"{row['water']:.2f}" if row['water'] else '-',
                f"{row['ambient_temp']:.1f}" if row['ambient_temp'] else '-',
                status
            ])

        log(f"📊 表格行数: {len(table_data)}")

        # 创建表格
        table = Table(table_data, colWidths=[1.5 * inch, 1 * inch, 1 * inch, 0.8 * inch, 0.8 * inch])

        # 表格样式
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ])

        # 设置字体
        if font_registered:
            table_style.add('FONTNAME', (0, 0), (-1, 0), font_name)
            table_style.add('FONTNAME', (0, 1), (-1, -1), font_name)
            log(f"✅ 表格使用字体: {font_name}")

        # 异常行标红
        for i, row in enumerate(data[:100]):
            if row['is_anomaly']:
                table_style.add('BACKGROUND', (0, i + 1), (-1, i + 1), colors.mistyrose)
                table_style.add('TEXTCOLOR', (0, i + 1), (-1, i + 1), colors.red)

        table.setStyle(table_style)
        elements.append(table)

        # 生成PDF
        doc.build(elements)

        pdf_size = buffer.tell()
        log(f"\n✅ PDF生成成功！大小: {pdf_size} 字节")
        log("=" * 50 + "\n")

        return Response(
            content=buffer.getvalue(),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=energy_{building_id}_{start_date}.pdf"}
        )

    except Exception as e:
        log(f"\n❌ PDF导出错误: {e}")
        import traceback
        traceback.print_exc(file=open(log_file, 'a'))
        return {
            "code": 500,
            "message": f"PDF生成失败: {str(e)}",
            "data": None
        }