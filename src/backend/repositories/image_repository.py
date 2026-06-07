"""病虫参考图数据访问层。图片文件存盘，DB 只存元数据。"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from ..infra.db import Database

_COLUMNS = "id, crop, pest_id, filename, caption, created_at"

_MIME_EXT = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ext_for_mime(mime: str) -> str:
    return _MIME_EXT.get(mime, "jpg")


class ImageRepository:
    def __init__(self, db: Database):
        self.db = db

    def add(self, crop: str, pest_id: str, filename: str, caption: str = "") -> dict:
        rid = uuid.uuid4().hex[:12]
        with self.db.connect() as conn:
            conn.execute(
                f"INSERT INTO pest_images ({_COLUMNS}) VALUES (?,?,?,?,?,?)",
                (rid, crop, pest_id, filename, caption, _now()),
            )
        return {"id": rid, "crop": crop, "pest_id": pest_id, "filename": filename, "caption": caption}

    def list_by_pest(self, crop: str, pest_id: str) -> list[dict]:
        with self.db.connect() as conn:
            rows = conn.execute(
                f"SELECT {_COLUMNS} FROM pest_images WHERE crop = ? AND pest_id = ? ORDER BY created_at",
                (crop, pest_id),
            ).fetchall()
        return [dict(r) for r in rows]

    def get(self, image_id: str) -> dict | None:
        with self.db.connect() as conn:
            row = conn.execute(
                f"SELECT {_COLUMNS} FROM pest_images WHERE id = ?", (image_id,)
            ).fetchone()
        return dict(row) if row else None

    def delete(self, image_id: str) -> dict | None:
        rec = self.get(image_id)
        if rec is None:
            return None
        with self.db.connect() as conn:
            conn.execute("DELETE FROM pest_images WHERE id = ?", (image_id,))
        return rec
