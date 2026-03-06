# test_run.py
import sys

print(f"Python: {sys.version}\n")


def test_import(name, import_stmt):
    try:
        exec(f"import {import_stmt}")
        print(f"✅ {name}: 导入成功")
        return True
    except Exception as e:
        print(f"❌ {name}: {e}")
        return False


print("📦 测试核心包导入...")
test_import("huggingface-hub", "huggingface_hub")
test_import("transformers", "transformers")
test_import("sentence-transformers", "sentence_transformers")
test_import("langchain", "langchain")
test_import("faiss", "faiss")

print("\n🔧 测试关键功能...")
try:
    from langchain_community.embeddings import HuggingFaceEmbeddings

    print("✅ HuggingFaceEmbeddings 导入成功")

    # 尝试创建 embeddings（这步会下载模型，可以注释掉先）
    # embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-zh")
    # print("✅ 模型加载成功")
except Exception as e:
    print(f"❌ embeddings 导入失败: {e}")

print("\n🎉 测试完成！")