"""
性能监控工具 - 用于统计接口和代码块的执行耗时
"""
import time
from functools import wraps
from contextlib import contextmanager
from typing import Optional


@contextmanager
def timer(description: str = "代码块", log_level: str = "INFO"):
    """
    上下文管理器 - 用于统计代码块执行时间
    
    Args:
        description: 描述信息，如"数据库查询"、"数据处理"等
        log_level: 日志级别（暂未使用）
    
    Yields:
        float: 执行时间（秒）
    
    Example:
        with timer("数据库查询") as elapsed:
            data = await db.query()
        # 自动打印：[⏱️ 性能] [步骤] 数据库查询：0.12s
    """
    start_time = time.time()
    try:
        yield lambda: time.time() - start_time
    finally:
        elapsed = time.time() - start_time
        print(f"[⏱️ 性能] [步骤] {description}: {elapsed:.2f}s")


def timing_decorator(description: Optional[str] = None):
    """
    装饰器 - 用于统计函数/接口的总执行时间
    
    Args:
        description: 可选的描述信息，不传则使用函数名
    
    Returns:
        包装后的函数
    
    Example:
        @timing_decorator("获取对比数据")
        async def get_comparison_data(...):
            return result
        
        # 自动打印：[⏱️ 性能] [接口] 获取对比数据 - 总耗时：2.35s
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            func_name = description or func.__name__
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                elapsed = time.time() - start_time
                print(f"[⏱️ 性能] [接口] {func_name} - 总耗时：{elapsed:.2f}s")
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            func_name = description or func.__name__
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                elapsed = time.time() - start_time
                print(f"[⏱️ 性能] [接口] {func_name} - 总耗时：{elapsed:.2f}s")
        
        # 根据原函数是否为异步函数决定返回哪种包装器
        if time.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class PerformanceMonitor:
    """
    性能监控类 - 提供更灵活的手动计时功能
    
    Example:
        monitor = PerformanceMonitor("接口处理")
        monitor.start("初始化")
        # ... 代码
        monitor.end("初始化")
        
        monitor.start("数据库查询")
        # ... 代码
        monitor.end("数据库查询")
        
        monitor.summary()  # 输出所有阶段的耗时汇总
    """
    
    def __init__(self, task_name: str = "任务"):
        self.task_name = task_name
        self.start_times = {}
        self.elapsed_times = {}
        self._start_time = time.time()
    
    def start(self, stage: str):
        """开始某个阶段的计时"""
        self.start_times[stage] = time.time()
    
    def end(self, stage: str):
        """结束某个阶段的计时并记录"""
        if stage in self.start_times:
            elapsed = time.time() - self.start_times[stage]
            self.elapsed_times[stage] = elapsed
            print(f"[⏱️ 性能] [{self.task_name}] {stage}: {elapsed:.2f}s")
        else:
            print(f"[⏱️ 性能] ⚠️ 警告：阶段 '{stage}' 未开始计时")
    
    def summary(self):
        """输出所有阶段的耗时汇总"""
        total = time.time() - self._start_time
        print(f"\n{'='*60}")
        print(f"[⏱️ 性能] [{self.task_name}] 耗时汇总:")
        print(f"{'='*60}")
        
        for stage, elapsed in self.elapsed_times.items():
            percentage = (elapsed / total * 100) if total > 0 else 0
            bar_length = int(percentage / 2)
            bar = "█" * bar_length + "░" * (50 - bar_length)
            print(f"  {stage:20s} | {bar} | {elapsed:6.2f}s ({percentage:5.1f}%)")
        
        print(f"{'='*60}")
        print(f"  {'总耗时':20s} | {total:6.2f}s")
        print(f"{'='*60}\n")
        
        return total
