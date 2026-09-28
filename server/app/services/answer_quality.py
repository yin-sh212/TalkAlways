# app/services/answer_quality.py
"""「无效回答」判定 —— 单一实现。

原先同一判据散在两处、且**不一致**：
  chat_api.py   `len(answer) > 300 and ("中建八局二建" in answer or "擎翼数字中枢" in answer)`
  llm_client.py `len(answer) > 300 and "中建八局二建" in answer`
两处标记词表不同 ⇒ 同一条回答在两条路径上判定可能相反。这里集中为一份配置
（`config.INVALID_ANSWER_MARKERS` / `INVALID_ANSWER_MIN_LEN`），改词表不用改代码。
"""
from typing import Any

from app.config import config


def is_invalid_answer(answer: Any) -> bool:
    """回答为空，或长到成段复述演示/公司介绍且命中标记词 ⇒ 无效。"""
    if answer is None:
        return True
    if len(answer) > config.INVALID_ANSWER_MIN_LEN:
        return any(marker in answer for marker in config.INVALID_ANSWER_MARKERS)
    return False
