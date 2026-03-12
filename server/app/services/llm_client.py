# app/services/llm_client.py
import os
import requests
from dotenv import load_dotenv

load_dotenv()


class LLMClient:
    def __init__(self):
        self.base_url = os.getenv("LLM_API_BASE_URL", "").rstrip('/')
        self.api_key = os.getenv("LLM_API_KEY", "")
        self.chat_id = os.getenv("RAGFLOW_CHAT_ID", "")

        # 构建正确的对话API路径
        if self.base_url and self.chat_id:
            self.api_url = f"{self.base_url}/api/v1/chats/{self.chat_id}/completions"
        else:
            self.api_url = ""

        self.available = bool(self.base_url and self.api_key and self.chat_id)

        if self.available:
            print(f"✅ 已配置RAGFlow对话API: {self.api_url}")
        else:
            print("⚠️ RAGFlow配置不完整，将使用模拟回答")

    def generate(self, prompt: str, max_tokens: int = 512) -> str:
        if not self.available:
            return self.mock_generate(prompt)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # RAGFlow 对话接口的正确格式！
        payload = {
            "question": prompt,  # 字段名是 question
            "stream": False  # 非流式返回
        }

        try:
            print(f"📡 正在请求: {self.api_url}")
            print(f"📤 发送内容: {payload}")

            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=60
            )

            print(f"📥 响应状态码: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                # RAGFlow 成功时 code 为 0
                if result.get("code") == 0:
                    answer = result.get("data", {}).get("answer", "")
                    session_id = result.get("data", {}).get("session_id", "")
                    print(f"✅ 获得回答 (session: {session_id})")
                    return answer
                else:
                    error_msg = result.get("message", "未知错误")
                    print(f"❌ RAGFlow错误: {error_msg}")
                    return f"【RAGFlow错误】{error_msg}"
            else:
                print(f"❌ HTTP错误: {response.status_code}")
                print(f"响应内容: {response.text}")
                return self.mock_generate(prompt)

        except requests.exceptions.Timeout:
            print("⚠️ 请求超时")
            return self.mock_generate(prompt)
        except Exception as e:
            print(f"⚠️ 异常: {e}")
            return self.mock_generate(prompt)

    def mock_generate(self, prompt: str) -> str:
        return f"【模拟回答】{prompt[:100]}..."


# 全局实例
llm_client = LLMClient()