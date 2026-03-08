import numpy as np
from typing import List, Dict, Any


def detect_anomalies_3sigma(
        values: List[float],
        timestamps: List[str],
        threshold: float = 2.0
) -> List[Dict[str, Any]]:
    """
    基于3-sigma法则的异常检测
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
    基于四分位距(IQR)的异常检测
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