import json
from datetime import datetime
from typing import Any, Dict, List

from app.database.db import Database
from app.services.rag_pipeline import rag_pipeline
from app.services.vector_db import vector_db


def _normalize_tags(tags: List[str] | None) -> List[str]:
    if not tags:
        return []
    seen = set()
    normalized: List[str] = []
    for tag in tags:
        value = str(tag).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    return normalized


def _normalize_notes(notes: List[str] | None) -> List[str]:
    if not notes:
        return []
    return [str(note).strip() for note in notes if str(note).strip()]


def build_knowledge_text(document: Dict[str, Any]) -> str:
    tags = _normalize_tags(document.get("tags"))
    notes = _normalize_notes(document.get("notes"))

    sections = [
        f"标题：{document.get('title', '').strip()}",
        f"分类：{document.get('category', '').strip()}",
    ]

    if tags:
        sections.append(f"标签：{', '.join(tags)}")
    if document.get("summary"):
        sections.append(f"摘要：{str(document['summary']).strip()}")
    if document.get("description"):
        sections.append(f"问题描述：{str(document['description']).strip()}")
    if document.get("solution"):
        sections.append(f"解决方案：{str(document['solution']).strip()}")
    if notes:
        sections.append("注意事项：")
        sections.extend(f"- {note}" for note in notes)

    return "\n".join(section for section in sections if section.strip())


def sync_document_to_rag(document: Dict[str, Any]) -> bool:
    try:
        content = build_knowledge_text(document)
        if not content.strip():
            return False

        vector_db.add_documents([
            {
                "content": content,
                "metadata": {
                    "source": f"knowledge_document_{document.get('id') or document.get('title', 'unknown')}",
                    "title": document.get("title", ""),
                    "category": document.get("category", ""),
                    "tags": _normalize_tags(document.get("tags")),
                }
            }
        ])
        rag_pipeline.initialized = rag_pipeline.initialized or bool(getattr(vector_db, "documents", []))
        return True
    except Exception as exc:
        print(f"⚠️ 同步知识条目到 RAG 失败：{exc}")
        return False


async def save_knowledge_document(document: Dict[str, Any], *, sync_to_rag: bool = True) -> Dict[str, Any]:
    title = str(document.get("title", "")).strip()
    category = str(document.get("category", "case")).strip() or "case"
    summary = str(document.get("summary", "")).strip()
    description = str(document.get("description", "")).strip()
    solution = str(document.get("solution", "")).strip()
    tags = _normalize_tags(document.get("tags"))
    notes = _normalize_notes(document.get("notes"))

    if not title:
        raise ValueError("知识条目标题不能为空")

    existing = await Database.fetch_one(
        "SELECT id FROM knowledge_documents WHERE title = %s ORDER BY id DESC LIMIT 1",
        (title,)
    )

    now = datetime.now()
    document_id = None
    synced_to_rag = False

    if existing:
        document_id = existing["id"]
        await Database.execute(
            """
            UPDATE knowledge_documents
            SET category = %s,
                tags = %s,
                summary = %s,
                description = %s,
                solution = %s,
                notes = %s,
                updated_at = %s
            WHERE id = %s
            """,
            (
                category,
                ",".join(tags),
                summary,
                description,
                solution,
                json.dumps(notes, ensure_ascii=False),
                now,
                document_id,
            ),
        )
    else:
        await Database.execute(
            """
            INSERT INTO knowledge_documents
            (title, category, tags, summary, description, solution, notes, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                title,
                category,
                ",".join(tags),
                summary,
                description,
                solution,
                json.dumps(notes, ensure_ascii=False),
                now,
                now,
            ),
        )
        inserted = await Database.fetch_one(
            "SELECT id FROM knowledge_documents WHERE title = %s ORDER BY id DESC LIMIT 1",
            (title,)
        )
        document_id = inserted["id"] if inserted else None

        if sync_to_rag:
            synced_to_rag = sync_document_to_rag({
                "id": document_id,
                "title": title,
                "category": category,
                "tags": tags,
                "summary": summary,
                "description": description,
                "solution": solution,
                "notes": notes,
            })

    return {
        "id": document_id,
        "is_success": True,
        "is_new": existing is None,
        "synced_to_rag": synced_to_rag,
    }


async def search_knowledge_documents(keywords: List[str], limit: int = 5) -> List[Dict[str, Any]]:
    terms = [term.strip() for term in keywords if str(term).strip()]
    if not terms:
        return []

    conditions: List[str] = []
    params: List[Any] = []

    for term in terms[:5]:
        like_value = f"%{term}%"
        conditions.append(
            "(title LIKE %s OR summary LIKE %s OR description LIKE %s OR solution LIKE %s OR tags LIKE %s)"
        )
        params.extend([like_value, like_value, like_value, like_value, like_value])

    sql = f"""
        SELECT id, title, category, summary, created_at
        FROM knowledge_documents
        WHERE {" OR ".join(conditions)}
        ORDER BY updated_at DESC, views DESC, created_at DESC
        LIMIT %s
    """
    params.append(limit)

    items = await Database.fetch_all(sql, tuple(params))

    return [
        {
            "id": item["id"],
            "title": item["title"],
            "category": item.get("category"),
            "summary": item.get("summary"),
            "url": f"/workspace?tab=knowledge&docId={item['id']}",
        }
        for item in items
    ]
