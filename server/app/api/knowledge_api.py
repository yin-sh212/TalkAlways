# app/api/knowledge_api.py（新建）
from fastapi import APIRouter, Query, Body
from typing import Optional, List
from app.database.db import Database
from datetime import datetime
from pydantic import BaseModel
import uuid

router = APIRouter(prefix="/api/knowledge", tags=["知识库"])


class KnowledgeCreate(BaseModel):
    title: str
    content: str
    category: str  # 故障处理/运维规范/节能建议等
    tags: List[str] = []
    related_alarm_types: List[str] = []


class KnowledgeUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    related_alarm_types: Optional[List[str]] = None


@router.post("/create")
async def create_knowledge(knowledge: KnowledgeCreate):
    """新增知识库条目"""
    knowledge_id = str(uuid.uuid4())[:8]

    sql = """
        INSERT INTO knowledge_base 
        (id, title, content, category, tags, related_alarm_types, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """

    await Database.execute(sql, (
        knowledge_id,
        knowledge.title,
        knowledge.content,
        knowledge.category,
        ','.join(knowledge.tags),
        ','.join(knowledge.related_alarm_types),
        datetime.now()
    ))

    return {
        "code": 200,
        "message": "知识条目创建成功",
        "data": {"knowledge_id": knowledge_id}
    }


@router.get("/list")
async def list_knowledge(
        category: Optional[str] = Query(None, description="分类"),
        keyword: Optional[str] = Query(None, description="关键词搜索"),
        tag: Optional[str] = Query(None, description="标签"),
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100)
):
    """知识库列表查询"""
    conditions = ["1=1"]
    params = []

    if category:
        conditions.append("category = %s")
        params.append(category)
    if keyword:
        conditions.append("(title LIKE %s OR content LIKE %s)")
        params.append(f"%{keyword}%")
        params.append(f"%{keyword}%")
    if tag:
        conditions.append("tags LIKE %s")
        params.append(f"%{tag}%")

    where_clause = " AND ".join(conditions)

    # 总数
    count_sql = f"SELECT COUNT(*) as total FROM knowledge_base WHERE {where_clause}"
    count_result = await Database.fetch_one(count_sql, tuple(params))
    total = count_result['total'] if count_result else 0

    # 分页查询
    offset = (page - 1) * page_size
    sql = f"""
        SELECT 
            id,
            title,
            content,
            category,
            tags,
            related_alarm_types,
            created_at,
            updated_at
        FROM knowledge_base
        WHERE {where_clause}
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
    """
    params.extend([page_size, offset])

    items = await Database.fetch_all(sql, tuple(params))

    # 处理 tags 和 related_alarm_types 字段
    for item in items:
        item['tags'] = item['tags'].split(',') if item['tags'] else []
        item['related_alarm_types'] = item['related_alarm_types'].split(',') if item['related_alarm_types'] else []

    return {
        "code": 200,
        "message": "成功",
        "data": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": items
        }
    }


@router.get("/{knowledge_id}")
async def get_knowledge_detail(knowledge_id: str):
    """获取知识库详情"""
    sql = """
        SELECT 
            id,
            title,
            content,
            category,
            tags,
            related_alarm_types,
            created_at,
            updated_at
        FROM knowledge_base
        WHERE id = %s
    """

    item = await Database.fetch_one(sql, (knowledge_id,))

    if not item:
        return {"code": 404, "message": "知识条目不存在", "data": None}

    item['tags'] = item['tags'].split(',') if item['tags'] else []
    item['related_alarm_types'] = item['related_alarm_types'].split(',') if item['related_alarm_types'] else []

    return {
        "code": 200,
        "message": "成功",
        "data": item
    }


@router.put("/{knowledge_id}")
async def update_knowledge(knowledge_id: str, knowledge: KnowledgeUpdate):
    """更新知识库条目"""
    updates = []
    params = []

    if knowledge.title:
        updates.append("title = %s")
        params.append(knowledge.title)
    if knowledge.content:
        updates.append("content = %s")
        params.append(knowledge.content)
    if knowledge.category:
        updates.append("category = %s")
        params.append(knowledge.category)
    if knowledge.tags is not None:
        updates.append("tags = %s")
        params.append(','.join(knowledge.tags))
    if knowledge.related_alarm_types is not None:
        updates.append("related_alarm_types = %s")
        params.append(','.join(knowledge.related_alarm_types))

    if not updates:
        return {"code": 400, "message": "没有要更新的字段", "data": None}

    updates.append("updated_at = %s")
    params.append(datetime.now())
    params.append(knowledge_id)

    sql = f"UPDATE knowledge_base SET {', '.join(updates)} WHERE id = %s"

    await Database.execute(sql, tuple(params))

    return {
        "code": 200,
        "message": "知识条目更新成功",
        "data": {"is_success": True}
    }


@router.delete("/{knowledge_id}")
async def delete_knowledge(knowledge_id: str):
    """删除知识库条目"""
    sql = "DELETE FROM knowledge_base WHERE id = %s"
    await Database.execute(sql, (knowledge_id,))

    return {
        "code": 200,
        "message": "知识条目删除成功",
        "data": {"is_success": True}
    }

