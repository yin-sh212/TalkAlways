"""
#10 回归：/api/chat/ask 与 /api/chat/ask/stream 必须对空/纯空白 query 返回 400。

只喂非法输入 —— 校验发生在检索之前，不会触发模型/LLM，故这些用例是廉价的。
"""
import pytest


class TestChatQueryValidation:
    """空 query 校验（06 #10）"""

    @pytest.mark.asyncio
    async def test_ask_rejects_empty_query(self, async_client):
        response = await async_client.post("/api/chat/ask", json={"query": ""})
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_ask_rejects_whitespace_query(self, async_client):
        response = await async_client.post("/api/chat/ask", json={"query": "   \t\n"})
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_ask_stream_rejects_empty_query(self, async_client):
        response = await async_client.post("/api/chat/ask/stream", json={"query": ""})
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_ask_stream_rejects_whitespace_query(self, async_client):
        response = await async_client.post("/api/chat/ask/stream", json={"query": "  "})
        assert response.status_code == 400
