# test_env.py
import sys
print(f"Python 版本: {sys.version}")

try:
    import langchain
    print(f"✅ langchain: {langchain.__version__}")
except:
    print("❌ langchain 安装失败")

try:
    from langchain_community.embeddings import HuggingFaceEmbeddings
    print("✅ langchain-community 导入成功")
except Exception as e:
    print(f"❌ langchain-community 导入失败: {e}")

try:
    from sentence_transformers import SentenceTransformer
    print("✅ sentence-transformers 导入成功")
except Exception as e:
    print(f"❌ sentence-transformers 导入失败: {e}")

try:
    from huggingface_hub import hf_hub_download
    print("✅ huggingface-hub 导入成功")
except Exception as e:
    print(f"❌ huggingface-hub 导入失败: {e}")

print("\n🎉 环境检查完成！")

