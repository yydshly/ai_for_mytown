"""文档语料（资料灌入）数据访问层。

MVP 用关键词/字符重叠检索（零依赖、可离线），与 KnowledgeBase 一致；
语料增大后可换向量检索（chromadb/嵌入），retrieve 接口不变。
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from ..infra.db import Database


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _overlap(query: str, text: str) -> int:
    return len(set(query) & set(text))


class CorpusRepository:
    def __init__(self, db: Database):
        self.db = db

    def clear_crop(self, crop: str) -> None:
        with self.db.connect() as conn:
            conn.execute("DELETE FROM corpus_chunks WHERE crop = ?", (crop,))

    def add_chunk(self, crop: str, source: str, text: str) -> None:
        with self.db.connect() as conn:
            conn.execute(
                "INSERT INTO corpus_chunks (id, crop, source, text, created_at) VALUES (?,?,?,?,?)",
                (uuid.uuid4().hex[:12], crop, source, text, _now()),
            )

    def count(self, crop: str | None = None) -> int:
        with self.db.connect() as conn:
            if crop:
                return conn.execute(
                    "SELECT COUNT(*) c FROM corpus_chunks WHERE crop = ?", (crop,)
                ).fetchone()["c"]
            return conn.execute("SELECT COUNT(*) c FROM corpus_chunks").fetchone()["c"]

    def sources(self, crop: str) -> list[str]:
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT source FROM corpus_chunks WHERE crop = ?", (crop,)
            ).fetchall()
        return [r["source"] for r in rows]

    def retrieve(self, query: str, crop: str, k: int = 3) -> list[dict]:
        """按字符重叠粗排，取该作物 + 通用语料里最相关的 k 段。"""
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT source, text FROM corpus_chunks WHERE crop = ? OR crop = ''",
                (crop,),
            ).fetchall()
        scored = []
        for r in rows:
            s = _overlap(query, r["text"])
            if s > 0:
                scored.append((s, r["source"], r["text"]))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [{"source": src, "text": txt} for _, src, txt in scored[:k]]
