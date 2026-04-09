from __future__ import annotations

import json
from pathlib import Path

import aiosqlite


class SQLiteSpool:
    def __init__(self, path: str) -> None:
        self.path = Path(path)

    async def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS pending_batches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    payload TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.commit()

    async def enqueue(self, payload: dict, error: str | None = None) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT INTO pending_batches (payload, attempts, last_error) VALUES (?, ?, ?)",
                (json.dumps(payload, ensure_ascii=False), 0, error),
            )
            await db.commit()

    async def fetch_pending(self, limit: int) -> list[tuple[int, dict]]:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "SELECT id, payload FROM pending_batches ORDER BY id ASC LIMIT ?",
                (limit,),
            )
            rows = await cursor.fetchall()
        return [(row[0], json.loads(row[1])) for row in rows]

    async def delete(self, ids: list[int]) -> None:
        if not ids:
            return
        placeholders = ",".join("?" for _ in ids)
        async with aiosqlite.connect(self.path) as db:
            await db.execute(f"DELETE FROM pending_batches WHERE id IN ({placeholders})", ids)
            await db.commit()

    async def mark_failed(self, batch_id: int, error: str) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                UPDATE pending_batches
                SET attempts = attempts + 1,
                    last_error = ?
                WHERE id = ?
                """,
                (error[:500], batch_id),
            )
            await db.commit()
