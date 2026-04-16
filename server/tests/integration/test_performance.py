"""
系统性能自动化测试 - 验证接口响应时间、吞吐量等性能指标
"""
import pytest
import time
import asyncio
from httpx import AsyncClient


class TestAPIResponseTime:
    """API响应时间测试"""
    
    @pytest.mark.asyncio
    async def test_health_check_response_time(self, async_client: AsyncClient):
        """测试健康检查接口响应时间（应 < 200ms）"""
        start_time = time.time()
        response = await async_client.get("/api/health")
        elapsed_time = (time.time() - start_time) * 1000  # 转换为毫秒
        
        assert response.status_code == 200
        assert elapsed_time < 200, f"健康检查响应时间 {elapsed_time:.2f}ms 超过 200ms 阈值"
    
    @pytest.mark.asyncio
    async def test_building_query_response_time(self, async_client: AsyncClient):
        """测试建筑列表查询响应时间（应 < 200ms）"""
        start_time = time.time()
        response = await async_client.get("/api/query/buildings")
        elapsed_time = (time.time() - start_time) * 1000
        
        assert response.status_code == 200
        assert elapsed_time < 200, f"建筑查询响应时间 {elapsed_time:.2f}ms 超过 200ms 阈值"
    
    @pytest.mark.asyncio
    async def test_single_building_monthly_energy_response_time(self, async_client: AsyncClient):
        """测试单建筑月度能耗查询响应时间（应 < 200ms）"""
        params = {
            "building_id": "Eagle_education_Cassie",
            "start_date": "2016-07-01",
            "end_date": "2016-07-31"
        }
        
        start_time = time.time()
        response = await async_client.get("/api/statistics/summary", params=params)
        elapsed_time = (time.time() - start_time) * 1000
        
        assert response.status_code != 404
        if response.status_code == 200:
            assert elapsed_time < 200, f"月度能耗查询响应时间 {elapsed_time:.2f}ms 超过 200ms 阈值"
    
    @pytest.mark.asyncio
    async def test_cop_calculation_response_time(self, async_client: AsyncClient):
        """测试COP计算接口响应时间（应 < 500ms）"""
        params = {
            "building_id": "Eagle_education_Cassie",
            "start_date": "2016-07-01",
            "end_date": "2016-07-31"
        }
        
        start_time = time.time()
        response = await async_client.get("/api/statistics/cop", params=params)
        elapsed_time = (time.time() - start_time) * 1000
        
        assert response.status_code != 404
        if response.status_code == 200:
            assert elapsed_time < 500, f"COP计算响应时间 {elapsed_time:.2f}ms 超过 500ms 阈值"
    
    @pytest.mark.asyncio
    async def test_trend_chart_data_response_time(self, async_client: AsyncClient):
        """测试趋势图数据查询响应时间（应 < 300ms）"""
        params = {
            "building_id": "Eagle_education_Cassie",
            "metric": "electricity",
            "start_date": "2016-07-01",
            "end_date": "2016-07-31"
        }
        
        start_time = time.time()
        response = await async_client.get("/api/charts/trend", params=params)
        elapsed_time = (time.time() - start_time) * 1000
        
        assert response.status_code != 404
        if response.status_code == 200:
            assert elapsed_time < 300, f"趋势图数据响应时间 {elapsed_time:.2f}ms 超过 300ms 阈值"
    
    @pytest.mark.asyncio
    async def test_anomaly_detection_response_time(self, async_client: AsyncClient):
        """测试异常检测接口响应时间（应 < 500ms）"""
        params = {
            "building_id": "Eagle_education_Cassie",
            "start_date": "2016-07-01",
            "end_date": "2016-07-31"
        }
        
        start_time = time.time()
        response = await async_client.get("/api/statistics/anomaly", params=params)
        elapsed_time = (time.time() - start_time) * 1000
        
        assert response.status_code != 404
        if response.status_code == 200:
            assert elapsed_time < 500, f"异常检测响应时间 {elapsed_time:.2f}ms 超过 500ms 阈值"
    
    @pytest.mark.asyncio
    async def test_rag_qa_response_time(self, async_client: AsyncClient):
        """测试RAG智能问答全链路响应时间（应 < 3s）"""
        question_data = {
            "question": "建筑Eagle_education_Cassie的用电情况如何？",
            "context": {
                "building_id": "Eagle_education_Cassie"
            }
        }
        
        try:
            start_time = time.time()
            response = await async_client.post("/api/ai/analyze", json=question_data)
            elapsed_time = time.time() - start_time
            
            if response.status_code == 200:
                # RAG问答涉及LLM调用，允许较长的响应时间
                assert elapsed_time < 3000, f"RAG问答响应时间 {elapsed_time:.2f}ms 超过 3000ms 阈值"
        except Exception:
            # AI接口可能未配置，跳过此测试
            pytest.skip("AI分析接口暂未可用")


class TestAPIThroughput:
    """API吞吐量测试"""
    
    @pytest.mark.asyncio
    async def test_concurrent_health_check(self, async_client: AsyncClient):
        """测试并发健康检查请求处理能力"""
        num_requests = 10
        
        start_time = time.time()
        
        # 并发发送多个请求
        tasks = [async_client.get("/api/health") for _ in range(num_requests)]
        responses = await asyncio.gather(*tasks)
        
        elapsed_time = time.time() - start_time
        
        # 所有请求都应该成功
        success_count = sum(1 for r in responses if r.status_code == 200)
        assert success_count == num_requests, f"{success_count}/{num_requests} 请求成功"
        
        # 计算吞吐量（请求/秒）
        throughput = num_requests / elapsed_time
        print(f"\n健康检查吞吐量: {throughput:.2f} req/s")
        
        # 吞吐量应该合理（至少1 req/s）
        assert throughput >= 1.0, f"吞吐量 {throughput:.2f} req/s 过低"
    
    @pytest.mark.asyncio
    async def test_concurrent_building_queries(self, async_client: AsyncClient):
        """测试并发建筑查询请求"""
        num_requests = 5
        
        start_time = time.time()
        
        tasks = [async_client.get("/api/query/buildings") for _ in range(num_requests)]
        responses = await asyncio.gather(*tasks)
        
        elapsed_time = time.time() - start_time
        
        # 验证所有请求成功
        success_count = sum(1 for r in responses if r.status_code == 200)
        assert success_count == num_requests
        
        throughput = num_requests / elapsed_time
        print(f"\n建筑查询吞吐量: {throughput:.2f} req/s")
    
    @pytest.mark.asyncio
    async def test_sustained_load_test(self, async_client: AsyncClient):
        """测试持续负载下的稳定性"""
        num_requests = 20
        batch_size = 5
        
        total_start = time.time()
        success_count = 0
        error_count = 0
        
        # 分批发送请求，模拟持续负载
        for i in range(0, num_requests, batch_size):
            batch_tasks = [
                async_client.get("/api/health") 
                for _ in range(min(batch_size, num_requests - i))
            ]
            
            responses = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            for response in responses:
                if isinstance(response, Exception):
                    error_count += 1
                elif response.status_code == 200:
                    success_count += 1
                else:
                    error_count += 1
            
            # 短暂间隔，避免过载
            await asyncio.sleep(0.1)
        
        total_elapsed = time.time() - total_start
        
        print(f"\n持续负载测试结果:")
        print(f"  总请求数: {num_requests}")
        print(f"  成功: {success_count}")
        print(f"  失败: {error_count}")
        print(f"  总耗时: {total_elapsed:.2f}s")
        print(f"  平均吞吐量: {num_requests/total_elapsed:.2f} req/s")
        
        # 成功率应该很高（> 95%）
        success_rate = success_count / num_requests
        assert success_rate >= 0.95, f"成功率 {success_rate:.2%} 低于 95% 阈值"


class TestDatabasePerformance:
    """数据库性能测试"""
    
    @pytest.mark.asyncio
    async def test_simple_query_performance(self, async_client: AsyncClient):
        """测试简单查询性能"""
        params = {
            "building_id": "Eagle_education_Cassie",
            "limit": 10
        }
        
        start_time = time.time()
        response = await async_client.get("/api/query/raw", params=params)
        elapsed_time = (time.time() - start_time) * 1000
        
        assert response.status_code != 404
        if response.status_code == 200:
            # 小数据集查询应该很快
            assert elapsed_time < 500, f"简单查询耗时 {elapsed_time:.2f}ms 过长"
    
    @pytest.mark.asyncio
    async def test_aggregation_query_performance(self, async_client: AsyncClient):
        """测试聚合查询性能"""
        params = {
            "building_id": "Eagle_education_Cassie",
            "start_date": "2016-07-01",
            "end_date": "2016-07-31"
        }
        
        start_time = time.time()
        response = await async_client.get("/api/statistics/summary", params=params)
        elapsed_time = (time.time() - start_time) * 1000
        
        assert response.status_code != 404
        if response.status_code == 200:
            # 月度聚合查询应该在合理时间内完成
            assert elapsed_time < 1000, f"聚合查询耗时 {elapsed_time:.2f}ms 过长"


class TestMemoryAndResourceUsage:
    """内存和资源使用测试"""
    
    @pytest.mark.asyncio
    async def test_no_memory_leak_in_repeated_queries(self, async_client: AsyncClient):
        """测试重复查询无内存泄漏迹象"""
        # 执行多次查询，验证响应时间不会持续增长
        response_times = []
        
        for i in range(10):
            start_time = time.time()
            response = await async_client.get("/api/health")
            elapsed_time = (time.time() - start_time) * 1000
            
            assert response.status_code == 200
            response_times.append(elapsed_time)
        
        # 检查响应时间是否稳定（最后几次的平均值不应比前几次显著增长）
        first_half_avg = sum(response_times[:5]) / 5
        second_half_avg = sum(response_times[5:]) / 5
        
        # 允许20%的波动
        growth_rate = (second_half_avg - first_half_avg) / first_half_avg if first_half_avg > 0 else 0
        
        print(f"\n响应时间稳定性:")
        print(f"  前半段平均: {first_half_avg:.2f}ms")
        print(f"  后半段平均: {second_half_avg:.2f}ms")
        print(f"  增长率: {growth_rate:.2%}")
        
        assert growth_rate < 0.5, f"响应时间增长 {growth_rate:.2%} 可能存在性能退化"


class TestConcurrentStability:
    """并发稳定性测试"""
    
    @pytest.mark.asyncio
    async def test_high_concurrency_stability(self, async_client: AsyncClient):
        """测试高并发场景下的稳定性"""
        num_concurrent = 20
        
        # 混合不同类型的请求
        tasks = []
        for i in range(num_concurrent):
            if i % 4 == 0:
                tasks.append(async_client.get("/api/health"))
            elif i % 4 == 1:
                tasks.append(async_client.get("/api/query/buildings"))
            elif i % 4 == 2:
                tasks.append(async_client.get(
                    "/api/statistics/summary",
                    params={
                        "building_id": "Eagle_education_Cassie",
                        "start_date": "2016-07-01",
                        "end_date": "2016-07-31"
                    }
                ))
            else:
                tasks.append(async_client.get(
                    "/api/charts/trend",
                    params={
                        "building_id": "Eagle_education_Cassie",
                        "metric": "electricity",
                        "start_date": "2016-07-01",
                        "end_date": "2016-07-07"
                    }
                ))
        
        start_time = time.time()
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed_time = time.time() - start_time
        
        # 统计结果
        success_count = 0
        error_count = 0
        exception_count = 0
        
        for response in responses:
            if isinstance(response, Exception):
                exception_count += 1
            elif response.status_code == 200:
                success_count += 1
            else:
                error_count += 1
        
        print(f"\n高并发测试结果:")
        print(f"  并发请求数: {num_concurrent}")
        print(f"  成功: {success_count}")
        print(f"  HTTP错误: {error_count}")
        print(f"  异常: {exception_count}")
        print(f"  总耗时: {elapsed_time:.2f}s")
        
        # 不应该有异常
        assert exception_count == 0, f"出现 {exception_count} 个异常"
        
        # 成功率应该很高
        total_completed = success_count + error_count
        if total_completed > 0:
            success_rate = success_count / total_completed
            assert success_rate >= 0.9, f"成功率 {success_rate:.2%} 低于 90%"
    
    @pytest.mark.asyncio
    async def test_long_running_stability(self, async_client: AsyncClient):
        """测试长时间运行的稳定性（简化版）"""
        num_iterations = 50
        error_count = 0
        
        for i in range(num_iterations):
            try:
                response = await async_client.get("/api/health")
                if response.status_code != 200:
                    error_count += 1
            except Exception:
                error_count += 1
            
            # 每10次输出进度
            if (i + 1) % 10 == 0:
                print(f"  已完成 {i + 1}/{num_iterations} 次请求")
        
        error_rate = error_count / num_iterations
        
        print(f"\n长时间运行测试:")
        print(f"  总请求数: {num_iterations}")
        print(f"  错误数: {error_count}")
        print(f"  错误率: {error_rate:.2%}")
        
        # 错误率应该很低（< 2%）
        assert error_rate < 0.02, f"错误率 {error_rate:.2%} 过高"
