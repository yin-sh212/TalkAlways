# app/api/realtime_api.py
"""
实时数据回放接口
按照时间顺序"回放"历史数据集，模拟准实时采集过程
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
import asyncio
import json
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, AsyncGenerator, Dict, Any, List
from app.database.db import Database
from app.services.anomaly_detector import detect_anomalies_3sigma

router = APIRouter(prefix="/api/realtime", tags=["实时数据回放"])


async def detect_anomalies_for_batch(data: List[Dict]) -> List[Dict[str, Any]]:
    """
    对一批数据进行实时异常检测
    
    使用 3-sigma 算法检测电力消耗异常，并将异常插入到 alarms 表
    """
    if not data or len(data) < 3:
        return []
    
    # 提取电力值和时间戳
    electricity_values = []
    timestamps = []
    
    for row in data:
        if row.get('electricity') is not None:
            electricity_values.append(row['electricity'])
            timestamps.append(row['timestamp'])
    
    if len(electricity_values) < 3:
        return []
    
    # 调用 3-sigma 异常检测算法
    anomalies = detect_anomalies_3sigma(
        values=electricity_values,
        timestamps=timestamps,
        threshold=2.5  # 2.5 倍标准差
    )
    
    # 将检测结果插入到 alarms 表
    if anomalies:
        pool = await Database.get_pool()
        conn = await pool.acquire()
        try:
            async with conn.cursor() as cursor:
                for anomaly in anomalies:
                    # 从数据中找到对应的记录，获取 building_id
                    matching_records = [r for r in data if r['timestamp'] == anomaly['timestamp']]
                    if matching_records:
                        record = matching_records[0]
                        building_id = record.get('building_id', 'unknown')
                        meter_id = record.get('meter_id', f'{building_id}_meter')
                        electricity_value = record.get('electricity', anomaly['value'])
                        
                        # 插入告警记录
                        insert_sql = """
                            INSERT INTO alarms 
                            (building_id, meter_id, alarm_type, alarm_level, description, 
                             start_time, value, threshold, status)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """
                        
                        description = f"能耗异常（3-sigma 检测），值为{electricity_value:.2f} kWh (Z-score: {anomaly['z_score']:.2f})"
                        
                        try:
                            await cursor.execute(insert_sql, (
                                building_id,
                                meter_id,
                                'energy',  # 告警类型
                                2,  # 告警级别（警告）
                                description,
                                anomaly['timestamp'],
                                electricity_value,
                                anomaly['upper_bound'],  # 阈值
                                'pending'  # 状态
                            ))
                        except Exception as e:
                            print(f"❌ 插入告警失败：{e}")
                            await conn.rollback()
                        else:
                            await conn.commit()
        finally:
            await conn.release()
    
    return anomalies


async def historical_data_stream(
    start_time: datetime,
    end_time: datetime,
    speed: int = 1,
    building_id: Optional[str] = None,
    batch_seconds: int = 3600  # 每次推送多少秒的数据（默认 1 小时）
) -> AsyncGenerator[str, None]:
    """
    历史数据流式回放生成器
    
    Args:
        start_time: 开始时间（如 2016-09-01 00:00:00）
        end_time: 结束时间（如 2016-09-30 23:59:59）
        speed: 加速倍数（1= 现实 1 秒= 模拟 1 秒，10= 现实 1 秒= 模拟 10 秒）
        building_id: 建筑 ID 过滤
        batch_seconds: 每批推送的时间跨度（秒），默认 3600（1 小时）
    """
    try:
        # 发送开始消息
        start_msg = {
            'type': 'start',
            'message': f'开始回放历史数据：{start_time.strftime("%Y-%m-%d %H:%M:%S")} ~ {end_time.strftime("%Y-%m-%d %H:%M:%S")}',
            'speed': speed,
            'batch_seconds': batch_seconds
        }
        yield f"data: {json.dumps(start_msg, ensure_ascii=False)}\n\n"
        
        current_time = start_time
        total_batches = int((end_time - start_time).total_seconds() / batch_seconds) + 1
        batch_count = 0
        total_anomalies_detected = 0
        
        while current_time < end_time:
            # 计算本批次的时间范围
            batch_end = min(current_time + timedelta(seconds=batch_seconds), end_time)
            
            # 构建查询条件
            conditions = ["timestamp >= %s", "timestamp < %s"]
            params = [current_time, batch_end]
            
            if building_id and building_id != "ALL":
                conditions.append("building_id = %s")
                params.append(building_id)
            
            # 查询该时间段的所有数据
            sql = """
                SELECT 
                    id, building_id, meter_id, timestamp, electricity, 
                    cooling_load, heating_load, ambient_temp, pressure, is_anomaly
                FROM energy_consumption 
                WHERE """ + " AND ".join(conditions) + """
                ORDER BY timestamp ASC
            """
            
            data = await Database.fetch_all(sql, tuple(params))
            
            # 转换为列表并处理时间格式
            data_list = []
            for row in data:
                row_dict = dict(row)
                if hasattr(row_dict['timestamp'], 'isoformat'):
                    row_dict['timestamp'] = row_dict['timestamp'].isoformat()
                data_list.append(row_dict)
            
            # 🔥 实时异常检测：对这批数据运行 3-sigma 算法
            detected_anomalies = await detect_anomalies_for_batch(data_list)
            
            if detected_anomalies:
                print(f"⚠️  检测到 {len(detected_anomalies)} 个异常点（{current_time} ~ {batch_end}）")
                total_anomalies_detected += len(detected_anomalies)
                
                # 将检测结果标记到数据中（仅用于前端展示，不写入数据库）
                anomaly_timestamps = {a['timestamp'] for a in detected_anomalies}
                for row in data_list:
                    if row['timestamp'] in anomaly_timestamps:
                        row['is_anomaly'] = True
                        row['anomaly_info'] = next(
                            (a for a in detected_anomalies if a['timestamp'] == row['timestamp']), 
                            None
                        )
            
            # 推送本批次数据（包含实时检测的异常标记）
            data_msg = {
                'type': 'data',
                'records': data_list,
                'batch_start': current_time.isoformat(),
                'batch_end': batch_end.isoformat(),
                'record_count': len(data_list),
                'anomaly_count': len(detected_anomalies)
            }
            yield f"data: {json.dumps(data_msg, ensure_ascii=False)}\n\n"
            
            batch_count += 1
            
            # 发送进度更新
            progress = (batch_count / total_batches) * 100
            progress_msg = {
                'type': 'progress',
                'current_batch': batch_count,
                'total_batches': total_batches,
                'progress_percent': round(progress, 2),
                'current_time': current_time.isoformat(),
                'anomalies_detected_so_far': total_anomalies_detected
            }
            yield f"data: {json.dumps(progress_msg, ensure_ascii=False)}\n\n"
            
            # 移动到下一批次
            current_time = batch_end
            
            # 根据速度计算延迟 - 真正等待现实时间过去
            # speed=1: 每批次间隔 = batch_hours * 3600 秒（真实等待）
            # speed=10: 每批次间隔 = (batch_hours * 3600) / 10 秒（10 倍速）
            # 例如：batch_hours=1 时，speed=1 需要真实等待 3600 秒（1 小时）
            base_delay_seconds = batch_seconds  # 基础延迟 = 批次的小时数（秒）
            delay = base_delay_seconds / speed
            print(f"⏰ 等待 {delay:.1f} 秒后推送下一批数据（模拟时间跨度：{batch_seconds}秒，速度：{speed}x）")
            await asyncio.sleep(delay)
        
        # 发送完成消息
        complete_msg = {
            'type': 'complete',
            'message': '数据回放完成',
            'total_batches': batch_count,
            'total_anomalies_detected': total_anomalies_detected
        }
        yield f"data: {json.dumps(complete_msg, ensure_ascii=False)}\n\n"
        
    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        print(f"流式推送错误：{error_msg}")
        error_response = {'type': 'error', 'message': str(e)}
        yield f"data: {json.dumps(error_response, ensure_ascii=False)}\n\n"


@router.get("/stream")
async def stream_historical_data(
    start_date: str = Query(..., description="开始日期，格式：YYYY-MM-DD HH:MM:SS，如：2016-09-01 00:00:00"),
    end_date: str = Query(..., description="结束日期，格式：YYYY-MM-DD HH:MM:SS，如：2016-09-30 23:59:59"),
    speed: int = Query(10, ge=1, le=1000, description="加速倍数（1= 现实 1 秒推送 1 秒数据，10= 现实 1 秒推送 10 秒数据）"),
    building_id: Optional[str] = Query(None, description="建筑 ID 过滤，不传则推送所有建筑"),
    batch_hours: int = Query(1, ge=1, le=24, description="每批推送的小时数，默认 1 小时")
):
    """
    流式回放历史数据集 - SSE 格式
    
    从数据库中按时间顺序读取历史数据，模拟准实时采集过程。
    
    **使用场景：**
    - 假装现在是 2016-09-01，从头开始"采集"9 月份数据
    - 可以控制播放速度（如 10 倍速、100 倍速快进）
    - 适合数据大屏展示、实时监控演示
    
    **参数说明：**
    - start_date: 回放起始时间（如 2016-09-01 00:00:00）
    - end_date: 回放结束时间（如 2016-09-30 23:59:59）
    - speed: 加速倍数
      - 1 = 现实 1 秒 = 模拟 1 秒（真实时间）
      - 10 = 现实 1 秒 = 模拟 10 秒（10 倍速）
      - 100 = 现实 1 分钟 = 模拟 100 分钟（超快进）
    - batch_hours: 每批推送的数据量
      - 1 = 每次推送 1 小时的数据
      - 6 = 每次推送 6 小时的数据
      
    **返回消息类型：**
    - start: 回放开始
    - data: 实际数据记录
    - progress: 进度更新
    - complete: 回放完成
    - error: 发生错误
    """
    try:
        start_time = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
        end_time = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")
        
        if start_time >= end_time:
            raise HTTPException(status_code=400, detail="开始时间必须早于结束时间")
        
        # 验证时间范围是否在数据集范围内
        if start_time.year != 2016 or end_time.year != 2016:
            raise HTTPException(status_code=400, detail="目前仅支持 2016 年的数据集")
        
        if start_time.month not in [7, 8, 9] or end_time.month not in [7, 8, 9]:
            raise HTTPException(status_code=400, detail="目前仅支持 7-9 月的数据集")
        
        batch_seconds = batch_hours * 3600
        
        return StreamingResponse(
            historical_data_stream(start_time, end_time, speed, building_id, batch_seconds),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "Access-Control-Allow-Origin": "*"
            }
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"日期格式错误：{str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动失败：{str(e)}")


@router.get("/check-data")
async def check_available_data(
    year: int = Query(2016, description="年份"),
    month: int = Query(9, ge=1, le=12, description="月份")
):
    """
    检查指定月份有多少可用的历史数据
    
    用于确认数据集中有哪些时间段的数据
    """
    try:
        # 统计该月份的总数据量
        count_sql = """
            SELECT COUNT(*) as total, 
                   MIN(timestamp) as earliest,
                   MAX(timestamp) as latest
            FROM energy_consumption 
            WHERE YEAR(timestamp) = %s AND MONTH(timestamp) = %s
        """
        
        result = await Database.fetch_one(count_sql, (year, month))
        
        if result:
            return {
                "code": 200,
                "data": {
                    "year": year,
                    "month": month,
                    "total_records": result['total'],
                    "earliest_time": result['earliest'].isoformat() if result['earliest'] else None,
                    "latest_time": result['latest'].isoformat() if result['latest'] else None,
                    "available_buildings": await get_building_list(year, month)
                }
            }
        else:
            return {
                "code": 200,
                "data": {
                    "year": year,
                    "month": month,
                    "total_records": 0,
                    "earliest_time": None,
                    "latest_time": None,
                    "available_buildings": []
                }
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败：{str(e)}")


async def get_building_list(year: int, month: int) -> list:
    """获取指定月份有数据的建筑列表"""
    sql = """
        SELECT DISTINCT building_id 
        FROM energy_consumption 
        WHERE YEAR(timestamp) = %s AND MONTH(timestamp) = %s
        ORDER BY building_id
    """
    
    rows = await Database.fetch_all(sql, (year, month))
    return [row['building_id'] for row in rows]
