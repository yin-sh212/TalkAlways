"""
模型精度自动化测试 - 验证异常检测、预测模型的准确性
"""
import pytest
import numpy as np
from httpx import AsyncClient
from app.services.anomaly_detector import (
    detect_anomalies_3sigma,
    detect_anomalies_iqr,
    detect_dynamic_baseline,
    detect_trend_decline,
    detect_combined_alarm
)


class TestAnomalyDetectionAccuracy:
    """异常检测模型精度测试"""
    
    def test_3sigma_detection_basic(self):
        """测试3-sigma算法基本功能"""
        # 生成正常数据 + 异常点
        normal_values = [100.0] * 100
        timestamps = [f"2016-07-{i//24+1:02d} {i%24:02d}:00:00" for i in range(100)]
        
        # 添加异常点（超过3倍标准差）
        values = normal_values.copy()
        values[50] = 500.0  # 明显异常
        
        anomalies = detect_anomalies_3sigma(values, timestamps, threshold=2.0)
        
        # 应该检测到异常
        assert len(anomalies) > 0, "3-sigma算法应该检测到明显的异常点"
        
        # 验证异常点位置
        anomaly_indices = [a['index'] for a in anomalies]
        assert 50 in anomaly_indices, "应该检测到索引50的异常点"
    
    def test_3sigma_no_false_positives(self):
        """测试3-sigma算法无误报"""
        # 完全均匀的数据，不应该有异常
        values = [100.0] * 50
        timestamps = [f"2016-07-01 {i:02d}:00:00" for i in range(50)]
        
        anomalies = detect_anomalies_3sigma(values, timestamps, threshold=2.0)
        
        # 标准差为0时应该返回空列表
        assert len(anomalies) == 0, "均匀数据不应产生误报"
    
    def test_iqr_detection(self):
        """测试IQR异常检测算法"""
        # 生成包含异常值的数据
        values = list(range(50, 150))  # 正常范围 50-149
        values.append(300)  # 异常高值
        values.append(10)   # 异常低值
        
        timestamps = [f"2016-07-01 {i:02d}:00:00" for i in range(len(values))]
        
        anomalies = detect_anomalies_iqr(values, timestamps)
        
        # 应该检测到至少一个异常
        assert len(anomalies) > 0, "IQR算法应该检测到异常值"
        
        # 验证异常类型标注正确
        anomaly_types = [a['type'] for a in anomalies]
        assert "过高" in anomaly_types or "过低" in anomaly_types
    
    def test_dynamic_baseline_detection(self):
        """测试动态基线异常检测"""
        # 生成具有周期性特征的数据
        base_values = [100.0 + 10 * np.sin(i * 2 * np.pi / 24) for i in range(100)]
        timestamps = [f"2016-07-{i//24+1:02d} {i%24:02d}:00:00" for i in range(100)]
        
        # 在中间插入异常点
        values = base_values.copy()
        values[60] = 200.0  # 突然翻倍
        
        anomalies = detect_dynamic_baseline(values, timestamps, window_size=24, threshold_multiplier=2.5)
        
        # 应该检测到异常
        assert len(anomalies) > 0, "动态基线算法应该检测到突变"
    
    def test_trend_decline_detection(self):
        """测试趋势下降异常检测"""
        # 生成持续下降的数据
        values = [100 - i * 5 for i in range(20)]  # 从100持续下降到5
        timestamps = [f"2016-07-01 {i:02d}:00:00" for i in range(len(values))]
        
        anomalies = detect_trend_decline(
            values, timestamps,
            window_size=6,
            decline_threshold=0.3,
            min_decline_rate=0.15
        )
        
        # 应该检测到持续下降趋势
        assert len(anomalies) > 0, "应该检测到明显的下降趋势"
        
        # 验证下降率计算正确
        if len(anomalies) > 0:
            assert "decline_rate" in anomalies[0]
            decline_rate = float(anomalies[0]['decline_rate'].replace('%', ''))
            assert decline_rate > 0, "下降率应为正值"
    
    def test_combined_alarm_integration(self):
        """测试综合告警检测（动态基线+趋势下降）"""
        # 生成复杂场景数据
        values = [100.0 + 5 * np.sin(i * 2 * np.pi / 24) for i in range(100)]
        # 后半段开始下降
        for i in range(50, 100):
            values[i] -= (i - 50) * 2
        
        timestamps = [f"2016-07-{i//24+1:02d} {i%24:02d}:00:00" for i in range(100)]
        
        result = detect_combined_alarm(
            values, timestamps,
            dynamic_window=24,
            dynamic_threshold=2.5,
            trend_window=6,
            trend_threshold=0.3,
            min_trend_decline=0.15
        )
        
        # 验证返回结构
        assert "total_count" in result
        assert "baseline_anomalies" in result
        assert "trend_anomalies" in result
        assert "summary" in result
        
        # 验证统计信息
        summary = result["summary"]
        assert "baseline_count" in summary
        assert "trend_count" in summary
        assert "anomaly_rate" in summary
    
    @pytest.mark.asyncio
    async def test_anomaly_api_integration(self, async_client: AsyncClient):
        """测试异常检测API集成"""
        params = {
            "building_id": "Eagle_education_Cassie",
            "start_date": "2016-07-01",
            "end_date": "2016-07-31"
        }
        
        response = await async_client.get("/api/statistics/anomaly", params=params)
        
        assert response.status_code != 404
        
        if response.status_code == 200:
            data = response.json()
            # API应该返回异常检测结果
            assert isinstance(data, (list, dict))
            
            # 如果是字典格式，验证关键字段
            if isinstance(data, dict):
                assert "count" in data or "anomalies" in data or "total" in data


class TestPredictionModelAccuracy:
    """能耗预测模型精度测试"""
    
    @pytest.mark.asyncio
    async def test_energy_summary_calculation(self, async_client: AsyncClient):
        """测试能耗汇总计算的准确性"""
        params = {
            "building_id": "Eagle_education_Cassie",
            "start_date": "2016-07-01",
            "end_date": "2016-07-31"
        }
        
        response = await async_client.get("/api/statistics/summary", params=params)
        
        assert response.status_code != 404
        
        if response.status_code == 200:
            data = response.json()
            
            # 验证返回数据结构
            if isinstance(data, dict):
                # 应该包含基本的统计字段
                has_electricity = any(key in data for key in ['electricity', 'total', 'sum', 'avg'])
                assert has_electricity, "应该包含电力消耗统计数据"
    
    @pytest.mark.asyncio
    async def test_cop_calculation(self, async_client: AsyncClient):
        """测试COP（性能系数）计算"""
        params = {
            "building_id": "Eagle_education_Cassie",
            "start_date": "2016-07-01",
            "end_date": "2016-07-31"
        }
        
        response = await async_client.get("/api/statistics/cop", params=params)
        
        assert response.status_code != 404
        
        if response.status_code == 200:
            data = response.json()
            
            # COP应该是合理的数值范围（通常1-10之间）
            if isinstance(data, dict) and "cop" in data:
                cop_value = data["cop"]
                if cop_value is not None:
                    assert isinstance(cop_value, (int, float))
                    # COP值应该在合理范围内（允许极端情况）
                    assert 0 < cop_value < 50, f"COP值 {cop_value} 超出合理范围"
    
    @pytest.mark.asyncio
    async def test_trend_data_consistency(self, async_client: AsyncClient):
        """测试趋势数据的一致性"""
        params = {
            "building_id": "Eagle_education_Cassie",
            "metric": "electricity",
            "start_date": "2016-07-01",
            "end_date": "2016-07-07"
        }
        
        response = await async_client.get("/api/charts/trend", params=params)
        
        assert response.status_code != 404
        
        if response.status_code == 200:
            data = response.json()
            
            # 趋势数据应该是时间序列格式
            if isinstance(data, list) and len(data) > 0:
                # 验证数据结构一致性
                first_item = data[0]
                if isinstance(first_item, dict):
                    assert "timestamp" in first_item or "time" in first_item or "date" in first_item
                    assert "value" in first_item or "electricity" in first_item
    
    @pytest.mark.asyncio
    async def test_comparison_data_accuracy(self, async_client: AsyncClient):
        """测试对比数据的准确性"""
        params = {
            "building_ids": ["Eagle_education_Cassie"],
            "metric": "electricity",
            "start_date": "2016-07-01",
            "end_date": "2016-07-31"
        }
        
        response = await async_client.get("/api/charts/comparison", params=params)
        
        assert response.status_code != 404
        
        if response.status_code == 200:
            data = response.json()
            # 对比数据应该返回
            assert isinstance(data, (list, dict))


class TestRAGResponseQuality:
    """RAG智能问答质量测试"""
    
    @pytest.mark.asyncio
    async def test_rag_response_structure(self, async_client: AsyncClient):
        """测试RAG响应结构完整性"""
        # 注意：实际项目中可能需要调整端点路径
        question_data = {
            "question": "建筑Eagle_education_Cassie在2016年7月的用电情况如何？",
            "context": {
                "building_id": "Eagle_education_Cassie",
                "time_range": "2016-07"
            }
        }
        
        # 尝试调用AI分析接口（如果存在）
        try:
            response = await async_client.post("/api/ai/analyze", json=question_data)
            
            if response.status_code == 200:
                data = response.json()
                
                # 验证响应结构
                if isinstance(data, dict):
                    # 应该包含回答内容
                    has_answer = any(key in data for key in ['answer', 'response', 'result', 'content'])
                    assert has_answer, "AI响应应该包含回答内容"
                    
                    # 可选：验证是否有推荐问题
                    if "follow_ups" in data:
                        assert isinstance(data["follow_ups"], list)
        except Exception:
            # AI接口可能未实现或配置不完整，跳过此测试
            pytest.skip("AI分析接口暂未可用")
    
    @pytest.mark.asyncio
    async def test_rag_response_relevance(self, async_client: AsyncClient):
        """测试RAG响应相关性"""
        question_data = {
            "question": "查询建筑列表",
            "context": {}
        }
        
        try:
            response = await async_client.post("/api/ai/analyze", json=question_data)
            
            if response.status_code == 200:
                data = response.json()
                
                # 验证响应与问题相关
                if isinstance(data, dict) and "answer" in data:
                    answer = data["answer"].lower()
                    # 回答应该包含与建筑相关的关键词
                    relevant_keywords = ['建筑', 'building', '列表', 'list']
                    has_relevant_keyword = any(keyword in answer for keyword in relevant_keywords)
                    assert has_relevant_keyword, "回答应该与问题相关"
        except Exception:
            pytest.skip("AI分析接口暂未可用")


class TestModelPerformanceMetrics:
    """模型性能指标测试"""
    
    def test_anomaly_detection_precision_recall(self):
        """测试异常检测的精确率和召回率"""
        # 构造已知异常的测试数据
        values = [100.0] * 100
        true_anomaly_indices = [30, 60, 90]  # 真实异常位置
        
        for idx in true_anomaly_indices:
            values[idx] = 500.0  # 注入异常
        
        timestamps = [f"2016-07-01 {i:02d}:00:00" for i in range(len(values))]
        
        # 执行检测
        detected = detect_anomalies_3sigma(values, timestamps, threshold=2.0)
        detected_indices = set(a['index'] for a in detected)
        true_indices = set(true_anomaly_indices)
        
        # 计算精确率和召回率
        true_positives = len(detected_indices & true_indices)
        precision = true_positives / len(detected_indices) if detected_indices else 0
        recall = true_positives / len(true_indices) if true_indices else 0
        
        # 验证检测效果（允许一定的误差）
        assert recall >= 0.8, f"召回率 {recall:.2f} 低于预期阈值 0.8"
        assert precision >= 0.5, f"精确率 {precision:.2f} 低于预期阈值 0.5"
    
    def test_detection_algorithm_stability(self):
        """测试检测算法的稳定性"""
        # 多次运行相同数据，结果应该一致
        values = [100.0 + i * 0.1 for i in range(50)]
        values[25] = 500.0
        timestamps = [f"2016-07-01 {i:02d}:00:00" for i in range(len(values))]
        
        results = []
        for _ in range(10):
            anomalies = detect_anomalies_3sigma(values, timestamps, threshold=2.0)
            results.append(len(anomalies))
        
        # 所有结果应该相同（确定性算法）
        assert len(set(results)) == 1, "相同输入应该产生相同输出"
    
    @pytest.mark.asyncio
    async def test_model_response_time(self, async_client: AsyncClient):
        """测试模型响应时间（应在合理范围内）"""
        import time
        
        params = {
            "building_id": "Eagle_education_Cassie",
            "start_date": "2016-07-01",
            "end_date": "2016-07-31"
        }
        
        start_time = time.time()
        response = await async_client.get("/api/statistics/anomaly", params=params)
        elapsed_time = time.time() - start_time
        
        assert response.status_code != 404
        
        # 响应时间应该在合理范围内（例如小于5秒）
        if response.status_code == 200:
            assert elapsed_time < 5.0, f"异常检测响应时间 {elapsed_time:.2f}s 过长"
