# app/services/realtime_collector.py
"""
实时数据采集模拟器
按照时间顺序不断上报数据到数据库，实现准实时采集效果
"""
import asyncio
import math
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from app.database.db import Database
import random


class RealTimeDataSimulator:
    """实时数据模拟器"""
    
    def __init__(self):
        self.is_running = False
        self.devices: List[Dict] = []
    
    async def initialize_devices(self, building_id: Optional[str] = None):
        """初始化设备列表"""
        try:
            # 查询建筑列表
            if building_id:
                buildings = await Database.fetch_all(
                    "SELECT id, name, type FROM buildings WHERE id = %s",
                    (building_id,)
                )
            else:
                buildings = await Database.fetch_all(
                    "SELECT id, name, type FROM buildings"
                )
            
            # 为每个建筑查询监测点
            self.devices = []
            for building in buildings:
                meters = await Database.fetch_all(
                    "SELECT id FROM meters WHERE building_id = %s",
                    (building['id'],)
                )
                for meter in meters:
                    self.devices.append({
                        'device_id': meter['id'],
                        'building_id': building['id'],
                        'building_name': building['name'],
                        'building_type': building['type']
                    })
            
            print(f"✅ 初始化 {len(self.devices)} 个监测点")
            
        except Exception as e:
            print(f"❌ 初始化设备失败：{e}")
    
    def generate_device_data(self, device_id: str, timestamp: datetime) -> Dict:
        """生成单个设备的实时数据 - 基于真实物理模型"""
        # 基础负荷：根据时间段确定（不使用随机数）
        hour = timestamp.hour
        
        # 工作日模式（假设 2016-09-03 是星期六）
        if timestamp.weekday() >= 5:  # 周末
            if 8 <= hour <= 18:
                base_power = 80.0  # 周末白天基础负荷
            else:
                base_power = 30.0  # 夜间基础负荷
        else:  # 工作日
            if 9 <= hour <= 17:
                base_power = 120.0  # 工作时间高峰
            elif 7 <= hour <= 9 or 17 <= hour <= 20:
                base_power = 90.0  # 早晚过渡时段
            else:
                base_power = 40.0  # 夜间低谷
        
        # 确定电力值（去掉随机波动）
        power = base_power
        
        # 温度数据（基于小时的正弦曲线模拟真实温度变化）
        # 凌晨最低（20℃），下午最高（35℃）
        ambient_temp = 27.5 + 7.5 * math.sin((hour - 6) * math.pi / 12)
        
        # 冷冻水供水/回水温度（固定值，符合实际）
        supply_temp = 7.0
        return_temp = 12.0
        
        # 负荷数据（与电力成固定比例）
        cooling_load = power * 0.4
        heating_load = power * 0.3
        
        # 环境参数（固定值）
        humidity = 55.0
        pressure = 101.3
        
        # 不设置异常标记 - 异常应该由算法检测，而不是预先标记
        is_anomaly = False
        
        return {
            'device_id': device_id,
            'timestamp': timestamp,
            'electricity': round(power, 2),
            'cooling_load': round(cooling_load, 2),
            'heating_load': round(heating_load, 2),
            'ambient_temp': round(ambient_temp, 1),
            'supply_temp': supply_temp,
            'return_temp': return_temp,
            'humidity': humidity,
            'pressure': pressure,
            'is_anomaly': is_anomaly
        }
    
    async def push_to_database(self, data: Dict):
        """将数据推送到数据库"""
        try:
            await Database.execute("""
                INSERT INTO energy_consumption 
                (building_id, meter_id, timestamp, electricity, cooling_load, 
                 heating_load, ambient_temp, pressure, is_anomaly)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                data['device_id'].split('_')[0],  # 提取建筑 ID
                data['device_id'],
                data['timestamp'],
                data['electricity'],
                data['cooling_load'],
                data['heating_load'],
                data['ambient_temp'],
                data['pressure'],
                data['is_anomaly']
            ))
            return True
        except Exception as e:
            print(f"❌ 数据推送失败：{e}")
            return False
    
    async def start_simulation(self, 
                               start_time: datetime,
                               end_time: datetime,
                               speed: int = 1,
                               building_id: Optional[str] = None):
        """
        启动模拟采集
        
        Args:
            start_time: 开始时间（如 2016-09-01 00:00:00）
            end_time: 结束时间（如 2016-09-30 23:59:59）
            speed: 加速倍数（1= realtime, 10=10 倍速，即现实 1 秒= 模拟 10 秒）
            building_id: 建筑 ID 过滤
        """
        if self.is_running:
            print("⚠️  模拟器已在运行中")
            return
        
        self.is_running = True
        await self.initialize_devices(building_id)
        
        current_time = start_time
        real_seconds_passed = 0
        
        print(f"🚀 开始模拟采集:")
        print(f"   时间范围：{start_time} ~ {end_time}")
        print(f"   加速倍数：{speed}x")
        print(f"   设备数量：{len(self.devices)}")
        
        while self.is_running and current_time <= end_time:
            # 为每个设备生成并推送数据
            tasks = []
            for device in self.devices:
                data = await self.generate_device_data(device['device_id'], current_time)
                tasks.append(self.push_to_database(data))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            success_count = sum(1 for r in results if r is True)
            
            print(f"📊 [{current_time}] 推送 {success_count}/{len(self.devices)} 条数据成功")
            
            # 时间前进
            time_step = timedelta(seconds=1) * speed
            current_time += time_step
            
            # 真实世界的延迟（控制推送频率）
            delay = max(0.1, 1.0 / speed)  # 速度越快，延迟越短
            await asyncio.sleep(delay)
            
            real_seconds_passed += delay
            
            # 每 1000 次输出统计
            if int(real_seconds_passed) % 100 == 0:
                print(f"ℹ️  已运行 {int(real_seconds_passed)} 秒，模拟到 {current_time}")
        
        self.is_running = False
        print(f"✅ 模拟采集完成，最终时间：{current_time}")
    
    def stop(self):
        """停止模拟"""
        self.is_running = False
        print("⏹️  模拟器已停止")


# ==================== 使用示例 ====================

async def demo_quick_start():
    """快速演示 - 模拟 1 小时的数据"""
    simulator = RealTimeDataSimulator()
    
    # 模拟 9 月份某 1 小时的数据，10 倍速
    start = datetime(2016, 9, 15, 10, 0, 0)
    end = datetime(2016, 9, 15, 11, 0, 0)
    
    await simulator.start_simulation(
        start_time=start,
        end_time=end,
        speed=10,  # 10 倍速
        building_id=None  # 所有建筑
    )


if __name__ == "__main__":
    # 运行演示
    asyncio.run(demo_quick_start())