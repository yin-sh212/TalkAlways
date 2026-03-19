# scripts/parse_manual.py
import re
import json
import docx
import os
import csv
from typing import List, Dict


class ManualParser:
    """手册解析器：Word文档 → 结构化JSON/CSV"""

    def __init__(self):
        # 分类规则（关键词匹配）
        self.category_rules = {
            '故障处理': ['故障', '异常', '报警', '错误', '问题', '处理', '解决', 'error', 'fault'],
            '运维规范': ['规范', '标准', '要求', '必须', '应', '定期', '检查', '维护'],
            '操作步骤': ['步骤', '流程', '操作', 'step', 'procedure', '如何', '怎样'],
            '节能指南': ['节能', '能效', '优化', '省电', '减排', '效率', 'energy']
        }

        # 常见标签
        self.common_tags = [
            '冷水机组', '空调', '水泵', '冷却塔', '风机', '传感器',
            '温度', '压力', '流量', '能耗', '异常', '维护', '故障',
            '变频器', '压缩机', '冷凝器', '蒸发器', '冷冻水', '冷却水'
        ]

    def extract_from_docx(self, file_path: str) -> List[Dict]:
        """
        从Word文档提取内容，按标题分割
        """
        print(f"📄 读取文件: {os.path.basename(file_path)}")
        doc = docx.Document(file_path)

        chapters = []
        current_chapter = {"title": "概述", "content": [], "level": 1}

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue

            # 判断是否是标题（通过样式或格式）
            is_heading = False
            if para.style.name.startswith('Heading'):
                is_heading = True
                level = int(para.style.name.replace('Heading', '') or 1)
            elif len(text) < 50 and (text.endswith('：') or text.endswith(':')):
                # 短文本且以冒号结尾，可能是标题
                is_heading = True
                level = 2
            elif text.isupper() and len(text) < 30:
                # 全大写短文本，可能是标题
                is_heading = True
                level = 2

            if is_heading and current_chapter['content']:
                # 保存上一章
                chapters.append(current_chapter)
                current_chapter = {"title": text, "content": [], "level": level}
            else:
                current_chapter['content'].append(text)

        # 保存最后一章
        if current_chapter['content']:
            chapters.append(current_chapter)

        print(f"  提取到 {len(chapters)} 个章节")
        return chapters

    def split_chunks(self, chapters: List[Dict], max_length: int = 300) -> List[Dict]:
        """
        将长章节分割成小块
        """
        chunks = []
        chunk_id = 0

        for chapter in chapters:
            title = chapter['title']
            content = '\n'.join(chapter['content'])

            # 如果内容不长，直接作为一块
            if len(content) < max_length:
                chunks.append({
                    "title": title,
                    "content": content,
                    "chunk_index": chunk_id
                })
                chunk_id += 1
                continue

            # 按句子分割
            sentences = re.split('[。！？!?]', content)
            current_chunk = ""

            for sent in sentences:
                sent = sent.strip()
                if not sent:
                    continue

                if len(current_chunk) + len(sent) < max_length:
                    current_chunk += sent + '。'
                else:
                    if current_chunk:
                        chunks.append({
                            "title": title,
                            "content": current_chunk,
                            "chunk_index": chunk_id
                        })
                        chunk_id += 1
                    current_chunk = sent + '。'

            # 最后一块
            if current_chunk:
                chunks.append({
                    "title": title,
                    "content": current_chunk,
                    "chunk_index": chunk_id
                })
                chunk_id += 1

        print(f"  分割为 {len(chunks)} 个知识块")
        return chunks

    def classify(self, text: str) -> str:
        """
        根据内容分类
        """
        text_lower = text.lower()
        for category, keywords in self.category_rules.items():
            for kw in keywords:
                if kw in text_lower or kw in text:
                    return category
        return '其他'

    def extract_tags(self, text: str) -> List[str]:
        """
        提取标签
        """
        tags = []
        for tag in self.common_tags:
            if tag in text:
                tags.append(tag)
        return tags

    def parse_file(self, file_path: str) -> List[Dict]:
        """
        解析单个Word文件
        """
        # 1. 提取章节
        chapters = self.extract_from_docx(file_path)

        # 2. 分块
        chunks = self.split_chunks(chapters)

        # 3. 分类和打标签
        result = []
        for chunk in chunks:
            category = self.classify(chunk['content'])
            tags = self.extract_tags(chunk['content'])

            result.append({
                "title": chunk['title'],
                "content": chunk['content'],
                "category": category,
                "tags": ','.join(tags),
                "source_file": os.path.basename(file_path),
                "chunk_index": chunk['chunk_index'],
                "char_count": len(chunk['content'])
            })

        return result

    def save_to_json(self, data: List[Dict], output_path: str):
        """保存为JSON"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ JSON已保存: {output_path}")

    def save_to_csv(self, data: List[Dict], output_path: str):
        """保存为CSV"""
        if not data:
            return
        with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        print(f"✅ CSV已保存: {output_path}")


if __name__ == "__main__":
    # 测试代码
    parser = ManualParser()
    test_file = "../data/knowledge/故障指南文档.docx"
    if os.path.exists(test_file):
        result = parser.parse_file(test_file)
        print(f"\n解析结果示例：")
        print(json.dumps(result[0], ensure_ascii=False, indent=2))
    else:
        print(f"请先将Word文档放到 data/knowledge/ 目录下")