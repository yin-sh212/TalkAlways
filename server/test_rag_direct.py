# test_rag_direct.py
from app.services.rag_service import rag_service


def test_rag():
    print("🔧 测试RAG服务...")

    # 初始化
    rag_service.init_knowledge_base()

    # 测试搜索
    results = rag_service.search("冷水机组故障", k=2)
    print(f"搜索结果: {len(results)} 条")
    for r in results:
        print(f"- {r['content'][:100]}...")

    # 测试问答
    answer = rag_service.answer("冷水机组故障怎么处理？")
    print(f"\n问答结果:\n{answer['answer']}")


if __name__ == "__main__":
    test_rag()