import numpy as np
from typing import List, Dict, Any, Tuple


def detect_anomalies_3sigma(
        values: List[float],
        timestamps: List[str],
        threshold: float = 2.0
) -> List[Dict[str, Any]]:
    """
    基于 3-sigma 法则的异常检测
    threshold: 标准差倍数，超过该值判定为异常
    """
    if len(values) < 3:
        return []

    mean = np.mean(values)
    std = np.std(values)

    if std == 0:
        return []

    anomalies = []
    for i, (value, ts) in enumerate(zip(values, timestamps)):
        z_score = abs(value - mean) / std
        if z_score > threshold:
            anomalies.append({
                "index": i,
                "timestamp": ts,
                "value": float(value),
                "mean": float(mean),
                "std": float(std),
                "z_score": float(z_score),
                "deviation": f"{((value - mean) / mean * 100):.1f}%"
            })

    return anomalies


def detect_anomalies_iqr(values: List[float], timestamps: List[str]):
    """
    基于四分位距 (IQR) 的异常检测
    """
    if len(values) < 4:
        return []

    q1 = np.percentile(values, 25)
    q3 = np.percentile(values, 75)
    iqr = q3 - q1

    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr

    anomalies = []
    for i, (value, ts) in enumerate(zip(values, timestamps)):
        if value < lower_bound or value > upper_bound:
            anomalies.append({
                "index": i,
                "timestamp": ts,
                "value": float(value),
                "lower_bound": float(lower_bound),
                "upper_bound": float(upper_bound),
                "type": "过低" if value < lower_bound else "过高"
            })

    return anomalies


def detect_dynamic_baseline(
        values: List[float],
        timestamps: List[str],
        window_size: int = 24,
        threshold_multiplier: float = 2.5
) -> List[Dict[str, Any]]:
    """
    动态基线异常检测算法
    
    原理：
    1. 使用滑动窗口计算局部统计量（均值和标准差）
    2. 根据时间序列的周期性特征建立动态基线
    3. 超过动态阈值则判定为异常
    
    Args:
        values: 数据值列表
        timestamps: 时间戳列表
        window_size: 滑动窗口大小（小时），默认 24 小时
        threshold_multiplier: 阈值倍数，默认 2.5 倍标准差
    
    Returns:
        异常检测结果列表
    """
    if len(values) < window_size:
        return []

    anomalies = []
    
    for i in range(window_size, len(values)):
        # 获取前一个窗口的数据
        window_values = values[i - window_size:i]
        
        # 计算窗口的统计量
        mean = np.mean(window_values)
        std = np.std(window_values)
        
        # 动态阈值
        upper_bound = mean + threshold_multiplier * std
        lower_bound = mean - threshold_multiplier * std
        
        current_value = values[i]
        
        # 判断是否异常
        if current_value > upper_bound or current_value < lower_bound:
            deviation = ((current_value - mean) / mean * 100) if mean > 0 else 0
            anomalies.append({
                "index": i,
                "timestamp": timestamps[i],
                "value": float(current_value),
                "baseline_mean": float(mean),
                "baseline_std": float(std),
                "upper_bound": float(upper_bound),
                "lower_bound": float(lower_bound),
                "deviation": f"{deviation:.1f}%",
                "type": "过高" if current_value > upper_bound else "过低",
                "severity": _calculate_severity(current_value, mean, std, threshold_multiplier)
            })
    
    return anomalies


def detect_trend_decline(
        values: List[float],
        timestamps: List[str],
        window_size: int = 6,
        decline_threshold: float = 0.3,
        min_decline_rate: float = 0.15
) -> List[Dict[str, Any]]:
    """
    趋势下降异常检测算法
    
    原理：
    1. 检测连续多个时间点的持续下降趋势
    2. 计算下降斜率和累计下降幅度
    3. 当下降速率和幅度都超过阈值时判定为异常
    
    Args:
        values: 数据值列表
        timestamps: 时间戳列表
        window_size: 检测窗口大小（连续下降点数），默认 6 个点
        decline_threshold: 下降阈值（斜率），默认 0.3
        min_decline_rate: 最小下降率，默认 15%
    
    Returns:
        趋势下降异常检测结果列表
    """
    if len(values) < window_size:
        return []

    anomalies = []
    
    for i in range(window_size - 1, len(values)):
        # 获取当前窗口的数据
        window_values = values[i - window_size + 1:i + 1]
        window_timestamps = timestamps[i - window_size + 1:i + 1]
        
        # 检查是否持续下降
        is_declining = all(window_values[j] > window_values[j + 1] for j in range(len(window_values) - 1))
        
        if not is_declining:
            continue
        
        # 计算累计下降幅度
        start_value = window_values[0]
        end_value = window_values[-1]
        decline_amount = start_value - end_value
        decline_rate = decline_amount / start_value if start_value > 0 else 0
        
        # 计算平均下降斜率
        avg_decline_slope = decline_amount / (window_size - 1)
        
        # 判断是否达到异常阈值
        if decline_rate >= min_decline_rate:
            anomalies.append({
                "index": i,
                "timestamp": timestamps[i],
                "start_timestamp": window_timestamps[0],
                "end_timestamp": window_timestamps[-1],
                "start_value": float(start_value),
                "end_value": float(end_value),
                "decline_amount": float(decline_amount),
                "decline_rate": f"{decline_rate * 100:.1f}%",
                "avg_decline_slope": float(avg_decline_slope),
                "continuous_points": window_size,
                "severity": _calculate_trend_severity(decline_rate, window_size)
            })
    
    return anomalies


def detect_combined_alarm(
        values: List[float],
        timestamps: List[str],
        dynamic_window: int = 24,
        dynamic_threshold: float = 2.5,
        trend_window: int = 6,
        trend_threshold: float = 0.3,
        min_trend_decline: float = 0.15
) -> Dict[str, Any]:
    """
    综合告警检测：结合动态基线和趋势下降两种算法
    
    Args:
        values: 数据值列表
        timestamps: 时间戳列表
        dynamic_window: 动态基线窗口大小
        dynamic_threshold: 动态基线阈值倍数
        trend_window: 趋势检测窗口大小
        trend_threshold: 趋势下降阈值
        min_trend_decline: 最小下降率
    
    Returns:
        综合检测结果
    """
    # 分别执行两种算法
    baseline_anomalies = detect_dynamic_baseline(
        values, timestamps, 
        window_size=dynamic_window,
        threshold_multiplier=dynamic_threshold
    )
    
    trend_anomalies = detect_trend_decline(
        values, timestamps,
        window_size=trend_window,
        decline_threshold=trend_threshold,
        min_decline_rate=min_trend_decline
    )
    
    # 合并结果
    total_anomalies = len(baseline_anomalies) + len(trend_anomalies)
    
    return {
        "total_count": total_anomalies,
        "baseline_anomalies": baseline_anomalies,
        "trend_anomalies": trend_anomalies,
        "summary": {
            "baseline_count": len(baseline_anomalies),
            "trend_count": len(trend_anomalies),
            "data_points": len(values),
            "anomaly_rate": f"{(total_anomalies / len(values) * 100) if values else 0:.2f}%"
        }
    }


def _calculate_severity(value: float, mean: float, std: float, threshold: float) -> str:
    """计算异常严重程度"""
    if std == 0:
        return "unknown"
    
    z_score = abs(value - mean) / std
    
    if z_score > threshold * 1.5:
        return "critical"  # 严重
    elif z_score > threshold * 1.2:
        return "high"  # 高
    elif z_score > threshold:
        return "medium"  # 中等
    else:
        return "low"  # 低


def _calculate_trend_severity(decline_rate: float, continuous_points: int) -> str:
    """计算趋势下降的严重程度"""
    severity_score = decline_rate * continuous_points
    
    if severity_score > 1.5:
        return "critical"  # 严重
    elif severity_score > 1.0:
        return "high"  # 高
    elif severity_score > 0.5:
        return "medium"  # 中等
    else:
        return "low"  # 低
