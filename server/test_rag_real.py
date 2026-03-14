# test_rag_real.py
from app.services.llm_client import llm_client
from app.services.vector_db import vector_db
from app.services.knowledge_base import knowledge_base


def test_rag():
    print("🔧 测试RAG流程...")

    # 1. 初始化知识库
    print("\n📚 加载知识库...")
    docs = knowledge_base.load_all_documents()
    print(f"加载了 {len(docs)} 个文档块")

    if docs:
        vector_db.add_documents(docs)

    # 2. 测试检索
    print("\n🔍 测试检索...")
    query = "冷水机组故障怎么处理"
    results = vector_db.search(query, k=3)
    print(f"找到 {len(results)} 个相关文档")
    for i, r in enumerate(results):
        print(f"{i + 1}. {r['content'][:100]}...")

    # 3. 测试生成
    print("\n💬 测试生成...")
    prompt = f"基于以下资料回答问题：\n\n{results[0]['content']}\n\n问题：{query}"
    answer = llm_client.generate(prompt)
    print(f"回答: {answer}")


if __name__ == "__main__":
    test_rag()