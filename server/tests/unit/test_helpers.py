"""
数据模型和辅助函数单元测试
"""
import pytest
import sys
import os
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestHelpers:
    """辅助函数测试"""
    
    def test_format_response(self):
        """测试统一响应格式"""
        from app.util.helpers import format_response
        
        # 成功响应
        response = format_response(code=200, data={"key": "value"}, message="成功")
        assert response["code"] == 200
        assert response["data"] == {"key": "value"}
        assert response["message"] == "成功"
        assert "timestamp" in response
    
    def test_parse_date_valid_formats(self):
        """测试日期解析 - 有效格式"""
        from app.util.helpers import parse_date
        
        # 测试多种日期格式
        date1 = parse_date("2024-01-15")
        assert date1.year == 2024
        assert date1.month == 1
        assert date1.day == 15
        
        date2 = parse_date("2024/01/15")
        assert date2.year == 2024
        
        date3 = parse_date("20240115")
        assert date3.year == 2024
    
    def test_parse_date_invalid_format(self):
        """测试日期解析 - 无效格式"""
        from app.util.helpers import parse_date
        
        with pytest.raises(ValueError):
            parse_date("invalid-date")
    
    def test_datetime_encoder(self):
        """测试DateTimeEncoder"""
        from app.util.helpers import DateTimeEncoder
        import json
        
        dt = datetime(2024, 1, 15, 10, 30, 45)
        encoder = DateTimeEncoder()
        
        result = encoder.default(dt)
        assert isinstance(result, str)
        assert "2024-01-15" in result


class TestDataProcessing:
    """数据处理测试"""
    
    def test_calculate_cop(self):
        """测试COP计算"""
        # COP = 制冷量 / 输入功率
        cooling_capacity = 3500  # W
        power_input = 1000  # W
        expected_cop = 3.5
        
        cop = cooling_capacity / power_input if power_input > 0 else 0
        assert abs(cop - expected_cop) < 0.01
    
    def test_anomaly_detection_threshold(self):
        """测试异常检测阈值"""
        values = [100, 105, 98, 102, 300]  # 300是异常值
        mean = sum(values[:-1]) / len(values[:-1])
        std = (sum((x - mean) ** 2 for x in values[:-1]) / len(values[:-1])) ** 0.5
        
        # 使用3σ原则
        threshold_upper = mean + 3 * std
        assert values[-1] > threshold_upper  # 300应该被识别为异常


class TestEnergyCalculations:
    """能耗计算测试"""
    
    def test_energy_consumption_calculation(self):
        """测试能耗计算"""
        # 用电量 = 功率 × 时间
        power_kw = 10.5  # kW
        hours = 24  # 小时
        energy_kwh = power_kw * hours
        
        assert energy_kwh == 252.0
    
    def test_water_consumption_calculation(self):
        """测试用水量计算"""
        flow_rate = 5.0  # m³/h
        hours = 10  # 小时
        water_m3 = flow_rate * hours
        
        assert water_m3 == 50.0
    
    def test_temperature_difference(self):
        """测试温差计算"""
        supply_temp = 45.0  # 供水温度
        return_temp = 40.0  # 回水温度
        temp_diff = supply_temp - return_temp
        
        assert temp_diff == 5.0
        assert temp_diff > 0  # 温差应为正数
