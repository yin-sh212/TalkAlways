# app/api/export_api.py
from fastapi import APIRouter, Response, Query
import pandas as pd
from io import StringIO, BytesIO
from app.database.db import Database
from typing import Optional, AsyncGenerator
import json
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api/export", tags=["报表导出"])


@router.get("/csv")
async def export_csv(
        building_id: str = Query(..., description="建筑编号，如：Eagle_education_Cassie"),
        start_date: str = Query(..., description="开始日期，格式：YYYY-MM-DD，例如：2016-07-01"),
        end_date: str = Query(..., description="结束日期，格式：YYYY-MM-DD，例如：2016-07-31")
):
    """导出CSV格式报表 - 适配新数据"""
    try:
        # 查询新数据集的全部字段
        sql = """
            SELECT 
                building_id,
                meter_id,
                timestamp,
                electricity,
                cooling_load,
                heating_load,
                ambient_temp,
                pressure,
                is_anomaly
            FROM energy_consumption 
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

        # 重命名列为中文（可选，让导出的文件更易读）
        df = df.rename(columns={
            'building_id': '建筑编号',
            'meter_id': '设备编号',
            'timestamp': '时间戳',
            'electricity': '电力消耗(kW)',
            'cooling_load': '冷冻水冷量',
            'heating_load': '供热能耗',
            'ambient_temp': '气温(℃)',
            'pressure': '气压(hPa)',
            'is_anomaly': '是否异常'
        })

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


@router.get("/excel")
async def export_excel(
        building_id: str = Query(..., description="建筑编号，如：Eagle_education_Cassie"),
        start_date: str = Query(..., description="开始日期，格式：YYYY-MM-DD，例如：2016-07-01"),
        end_date: str = Query(..., description="结束日期，格式：YYYY-MM-DD，例如：2016-07-31")
):
    """导出Excel格式报表 - 适配新数据"""
    try:
        sql = """
            SELECT 
                building_id,
                meter_id,
                timestamp,
                electricity,
                cooling_load,
                heating_load,
                ambient_temp,
                pressure,
                is_anomaly
            FROM energy_consumption 
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

        # 重命名列为中文
        df = df.rename(columns={
            'building_id': '建筑编号',
            'meter_id': '设备编号',
            'timestamp': '时间戳',
            'electricity': '电力消耗(kW)',
            'cooling_load': '冷冻水冷量',
            'heating_load': '供热能耗',
            'ambient_temp': '气温(℃)',
            'pressure': '气压(hPa)',
            'is_anomaly': '是否异常'
        })

        # 生成Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # 写入数据表
            df.to_excel(writer, index=False, sheet_name='能耗数据')

            # 添加统计信息sheet
            stats_df = pd.DataFrame({
                '统计项': ['总记录数', '开始日期', '结束日期', '平均用电量', '最大用电量', '异常点数'],
                '数值': [
                    len(df),
                    start_date,
                    end_date,
                    f"{df['电力消耗(kW)'].mean():.2f}",
                    f"{df['电力消耗(kW)'].max():.2f}",
                    df['是否异常'].sum()
                ]
            })
            stats_df.to_excel(writer, index=False, sheet_name='统计信息')

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


@router.get("/pdf")
async def export_pdf(
        building_id: str = Query(..., description="建筑编号，如：Eagle_education_Cassie"),
        start_date: str = Query(..., description="开始日期，格式：YYYY-MM-DD，例如：2016-07-01"),
        end_date: str = Query(..., description="结束日期，格式：YYYY-MM-DD，例如：2016-07-31")
):
    """导出 PDF 报表 - 适配新数据"""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from io import BytesIO
        from fastapi.responses import Response
        import os

        # 查询数据（限制条数避免 PDF 过大）
        sql = """
            SELECT 
                DATE_FORMAT(timestamp, '%%Y-%%m-%%d %%H:00') as time,
                electricity,
                cooling_load,
                heating_load,
                ambient_temp,
                pressure,
                is_anomaly
            FROM energy_consumption 
            WHERE building_id = %s 
                AND DATE(timestamp) BETWEEN %s AND %s
            ORDER BY timestamp
            LIMIT 500
        """
        data = await Database.fetch_all(sql, (building_id, start_date, end_date))

        if not data:
            return {
                "code": 400,
                "message": "没有数据可导出",
                "data": None
            }

        # 创建 PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []

        # 注册中文字体
        font_registered = False
        font_name = 'Helvetica'

        font_path = "C:/Windows/Fonts/simhei.ttf"
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont('SimHei', font_path))
                font_name = 'SimHei'
                font_registered = True
            except:
                pass

        # 创建样式
        styles = getSampleStyleSheet()

        if font_registered:
            title_style = ParagraphStyle(
                'CustomTitle', parent=styles['Title'], fontName=font_name,
                fontSize=16, alignment=1, spaceAfter=20
            )
            normal_style = ParagraphStyle(
                'CustomNormal', parent=styles['Normal'], fontName=font_name,
                fontSize=10, spaceAfter=6
            )
        else:
            title_style = styles['Title']
            normal_style = styles['Normal']

        # 标题
        title_text = f"建筑 {building_id} 能耗报表 ({start_date} 至 {end_date})"
        elements.append(Paragraph(title_text, title_style))
        elements.append(Spacer(1, 0.2 * inch))

        # 统计信息
        total_elec = sum(d['electricity'] for d in data)
        avg_elec = total_elec / len(data) if data else 0
        max_elec = max(d['electricity'] for d in data)
        avg_cooling = sum(d['cooling_load'] for d in data if d['cooling_load']) / len(
            [d for d in data if d['cooling_load']]) if any(d['cooling_load'] for d in data) else 0
        anomaly_count = sum(1 for d in data if d['is_anomaly'])

        stats_text = f"""
        总用电量：{total_elec:.2f} kWh<br/>
        平均用电量：{avg_elec:.2f} kWh<br/>
        最大用电量：{max_elec:.2f} kWh<br/>
        平均冷冻水冷量：{avg_cooling:.2f}<br/>
        异常点数：{anomaly_count}<br/>
        数据条数：{len(data)}
        """
        elements.append(Paragraph(stats_text, normal_style))
        elements.append(Spacer(1, 0.2 * inch))

        # 表格数据
        table_data = [['时间', '用电量', '冷冻水', '供热', '气温', '气压', '状态']]

        for row in data[:100]:
            status = "异常" if row['is_anomaly'] else "正常"
            table_data.append([
                row['time'],
                f"{row['electricity']:.2f}",
                f"{row['cooling_load']:.2f}" if row['cooling_load'] else '-',
                f"{row['heating_load']:.2f}" if row['heating_load'] else '-',
                f"{row['ambient_temp']:.1f}",
                f"{row['pressure']:.1f}" if row['pressure'] else '-',
                status
            ])

        # 创建表格
        table = Table(table_data,
                      colWidths=[1.5 * inch, 0.8 * inch, 0.8 * inch, 0.8 * inch, 0.6 * inch, 0.8 * inch, 0.6 * inch])

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

        if font_registered:
            table_style.add('FONTNAME', (0, 0), (-1, 0), font_name)
            table_style.add('FONTNAME', (0, 1), (-1, -1), font_name)

        # 异常行标红
        for i, row in enumerate(data[:100]):
            if row['is_anomaly']:
                table_style.add('BACKGROUND', (0, i + 1), (-1, i + 1), colors.mistyrose)
                table_style.add('TEXTCOLOR', (0, i + 1), (-1, i + 1), colors.red)

        table.setStyle(table_style)
        elements.append(table)

        # 生成 PDF
        doc.build(elements)

        return Response(
            content=buffer.getvalue(),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=energy_{building_id}_{start_date}.pdf"}
        )

    except Exception as e:
        import traceback
        print(f"\n❌ PDF 导出错误：{e}")
        traceback.print_exc()
        # 返回 JSON 错误而不是 Response，这样前端能正确解析
        return {
            "code": 500,
            "message": f"PDF 生成失败：{str(e)}",
            "data": None
        }


async def september_data_stream_generator(
    building_id: Optional[str] = None,
    year: int = 2016,
    batch_size: int = 100
) -> AsyncGenerator[str, None]:
    """9 月数据集流式推送生成器"""
    try:
        # 发送开始消息
        yield f"data: {json.dumps({'type': 'start', 'message': '开始推送 9 月数据集'}, ensure_ascii=False)}\n\n"
        
        # 构建基础查询条件
        conditions = ["MONTH(timestamp) = 9", "YEAR(timestamp) = %s"]
        params = [year]
        
        if building_id and building_id != "ALL":
            conditions.append("building_id = %s")
            params.append(building_id)
        
        # 先获取总数
        count_sql = "SELECT COUNT(*) as total FROM energy_consumption WHERE " + " AND ".join(conditions)
        count_result = await Database.fetch_one(count_sql, tuple(params))
        total = count_result['total'] if count_result else 0
        
        yield f"data: {json.dumps({'type': 'progress', 'current': 0, 'total': total, 'message': f'共{total}条数据'}, ensure_ascii=False)}\n\n"
        
        # 分批查询和推送数据
        offset = 0
        sent_count = 0
        
        while True:
            sql = """
                SELECT 
                    id,
                    building_id,
                    meter_id,
                    timestamp,
                    electricity,
                    cooling_load,
                    heating_load,
                    ambient_temp,
                    pressure,
                    is_anomaly
                FROM energy_consumption 
                WHERE 
            """ + " AND ".join(conditions) + """
                ORDER BY timestamp ASC
                LIMIT %s OFFSET %s
            """
            
            query_params = tuple(params) + (batch_size, offset)
            data = await Database.fetch_all(sql, query_params)
            
            if not data:
                break
            
            # 转换为列表并发送
            data_list = [dict(row) for row in data]
            
            # 将 datetime 对象转换为字符串
            for row in data_list:
                if 'timestamp' in row and hasattr(row['timestamp'], 'isoformat'):
                    row['timestamp'] = row['timestamp'].isoformat()
            
            yield f"data: {json.dumps({'type': 'data', 'records': data_list}, ensure_ascii=False)}\n\n"
            
            sent_count += len(data)
            offset += batch_size
            
            # 发送进度更新
            yield f"data: {json.dumps({'type': 'progress', 'current': sent_count, 'total': total}, ensure_ascii=False)}\n\n"
            
            # 如果返回的数据少于 batch_size，说明已经是最后一批
            if len(data) < batch_size:
                break
        
        # 发送完成消息
        yield f"data: {json.dumps({'type': 'complete', 'message': '数据推送完成', 'total_sent': sent_count}, ensure_ascii=False)}\n\n"
        
    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        print(f"流式推送错误：{error_msg}")
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"


@router.get("/september/stream")
async def stream_september_data(
    building_id: Optional[str] = Query(None, description="建筑编号，如：Eagle_education_Cassie，不传则推送所有建筑"),
    year: int = Query(2016, description="年份，默认 2016"),
    batch_size: int = Query(100, ge=10, le=1000, description="每批推送的数据条数，默认 100")
):
    """
    流式推送 9 月数据集 - SSE 格式
    
    使用 Server-Sent Events 实时推送 9 月份的能耗数据，适合大数据量的场景。
    支持以下消息类型:
    - start: 推送开始
    - progress: 推送进度更新
    - data: 实际数据记录
    - complete: 推送完成
    - error: 发生错误
    """
    return StreamingResponse(
        september_data_stream_generator(building_id, year, batch_size),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*"
        }
    )


@router.get("/september/batch")
async def get_september_data_batch(
    building_id: Optional[str] = Query(None, description="建筑编号"),
    year: int = Query(2016, description="年份"),
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(100, ge=10, le=1000, description="每页大小")
):
    """
    分页获取 9 月数据集
    
    传统的分页查询接口，适合需要精确控制数据获取的场景。
    """
    try:
        # 构建查询条件
        conditions = ["MONTH(timestamp) = 9", "YEAR(timestamp) = %s"]
        params = [year]
        
        if building_id and building_id != "ALL":
            conditions.append("building_id = %s")
            params.append(building_id)
        
        # 查询总数
        count_sql = "SELECT COUNT(*) as total FROM energy_consumption WHERE " + " AND ".join(conditions)
        count_result = await Database.fetch_one(count_sql, tuple(params))
        total = count_result['total'] if count_result else 0
        
        # 分页查询
        offset = (page - 1) * page_size
        sql = """
            SELECT 
                id,
                building_id,
                meter_id,
                timestamp,
                electricity,
                cooling_load,
                heating_load,
                ambient_temp,
                pressure,
                is_anomaly
            FROM energy_consumption 
            WHERE 
        """ + " AND ".join(conditions) + """
            ORDER BY timestamp ASC
            LIMIT %s OFFSET %s
        """
        
        query_params = tuple(params) + (page_size, offset)
        data = await Database.fetch_all(sql, query_params)
        
        # 转换 datetime 为字符串
        data_list = []
        for row in data:
            row_dict = dict(row)
            if 'timestamp' in row_dict and hasattr(row_dict['timestamp'], 'isoformat'):
                row_dict['timestamp'] = row_dict['timestamp'].isoformat()
            data_list.append(row_dict)
        
        return {
            "code": 200,
            "data": {
                "records": data_list,
                "pagination": {
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": (total + page_size - 1) // page_size,
                    "has_more": offset + len(data) < total
                }
            }
        }
    except Exception as e:
        import traceback
        print(f"获取 9 月数据失败：{e}")
        traceback.print_exc()
        return {
            "code": 500,
            "message": f"查询失败：{str(e)}",
            "data": None
        }
