# app/services/llm_client.py
import os
import requests
from dotenv import load_dotenv
from urllib3.exceptions import InsecureRequestWarning

# 禁用 SSL 警告（仅开发环境）
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

load_dotenv()


class LLMClient:
    def __init__(self):
        self.base_url = os.getenv("LLM_API_BASE_URL", "").rstrip('/')
        self.api_key = os.getenv("LLM_API_KEY", "")
        self.model = os.getenv("LLM_MODEL", "gemma3:4b")
        
        # 支持多个 chat_id
        self.chat_id_main = os.getenv("RAGFLOW_CHAT_ID_MAIN", "")
        self.chat_id_alt = os.getenv("RAGFLOW_CHAT_ID_ALT", "")

        # 构建正确的对话 API 路径
        self.api_url_main = f"{self.base_url}/api/v1/chats/{self.chat_id_main}/completions" if self.chat_id_main else ""
        self.api_url_alt = f"{self.base_url}/api/v1/chats/{self.chat_id_alt}/completions" if self.chat_id_alt else ""

        self.available = bool(self.base_url and self.api_key and self.chat_id_main)

        # DeepSeek 配置
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY", "")
        
        if self.deepseek_api_key:
            print("✅ 已配置 DeepSeek API")
        
        if self.available:
            print(f"✅ 已配置 RAGFlow 对话 API (主): {self.api_url_main}")
            if self.chat_id_alt:
                print(f"✅ 已配置 RAGFlow 对话 API (备用): {self.api_url_alt}")
        elif not self.deepseek_api_key:
            print("⚠️ RAGFlow 与 DeepSeek 均未配置完整，将使用模拟回答")

    def generate(self, prompt: str, max_tokens: int = 512, use_alt: bool = False) -> str:
        """
        生成回答 - 优先使用 DeepSeek，失败时降级到 RAGFlow
        
        Args:
            prompt: 提示词
            max_tokens: 最大 token 数 (部分模型暂不使用此参数，保留兼容性)
            use_alt: 是否使用备用助手 (仅对 RAGFlow 生效)
            
        Returns:
            生成的回答
        """
        # 优先使用 DeepSeek（真实 AI）
        if self.deepseek_api_key:
            try:
                return self._call_deepseek(prompt)
            except Exception as e:
                print(f"⚠️ DeepSeek 失败：{e}，降级到 RAGFlow...")
        
        # 降级到 RAGFlow
        if not self.available:
            return self.mock_generate(prompt)
            
        return self._call_ragflow(prompt, use_alt)

    def _call_deepseek(self, prompt: str) -> str:
        """调用 DeepSeek API"""
        url = "https://api.deepseek.com/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.deepseek_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "system",
                    "content": "你是一位专业的建筑能源管理和设备运维专家。请针对用户的具体问题给出专业、简洁的回答。直接回答问题本身，不要重复自我介绍，不要输出欢迎语模板。"
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 1000
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        if result.get("choices") and len(result["choices"]) > 0:
            answer = result["choices"][0]["message"]["content"]
            print(f"✅ DeepSeek 回答成功，长度：{len(answer)} 字符")
            return answer
        else:
            raise Exception(f"DeepSeek 错误：{result}")

    def _call_dashscope(self, prompt: str) -> str:
        """调用通义千问 API（已禁用）"""
        raise NotImplementedError("通义千问 API 已禁用")

    def _call_ragflow(self, prompt: str, use_alt: bool = False) -> str:
        """调用 RAGFlow API - 备用方案"""
        assistant_name = "主助手" if not use_alt else "备用助手"
        api_url = self.api_url_alt if use_alt else self.api_url_main
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "query": prompt,
            "stream": False
        }
        
        response = requests.post(api_url, headers=headers, json=payload, timeout=60, verify=False)
        response.raise_for_status()
        
        result = response.json()
        answer = result.get("data", {}).get("answer", "")
        
        if len(answer) > 300 and "中建八局二建" in answer:
            print(f"⚠️ {assistant_name}返回标准欢迎语，长度：{len(answer)} 字符")
            if not use_alt and self.chat_id_alt:
                print("🔄 尝试使用备用助手...")
                return self._call_ragflow(prompt, use_alt=True)
            return None
        else:
            print(f"✅ {assistant_name}回答成功，长度：{len(answer)} 字符")
            return answer

    def mock_generate(self, prompt: str) -> str:
        """模拟回答（仅用于演示）"""
        from datetime import datetime
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"【模拟回答】当前时间：{current_time}\n\n用户问题：{prompt}\n\n提示：配置有效的 LLM API 后可获得真实 AI 回答。"


# 创建全局实例
llm_client = LLMClient()
