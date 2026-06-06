"""通讯录数据访问层。SQL 仅在此出现。"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from ..domain.contact import Contact
from ..infra.db import Database

_COLUMNS = "id, name, role, phone, note, created_at"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class ContactRepository:
    def __init__(self, db: Database):
        self.db = db

    def list(self) -> list[Contact]:
        with self.db.connect() as conn:
            rows = conn.execute(
                f"SELECT {_COLUMNS} FROM contacts ORDER BY created_at"
            ).fetchall()
        return [Contact.from_row(r) for r in rows]

    def get(self, contact_id: str) -> Contact | None:
        with self.db.connect() as conn:
            row = conn.execute(
                f"SELECT {_COLUMNS} FROM contacts WHERE id = ?", (contact_id,)
            ).fetchone()
        return Contact.from_row(row) if row else None

    def create(self, data: dict) -> Contact:
        c = Contact(
            id=uuid.uuid4().hex[:12],
            name=data["name"],
            phone=data["phone"],
            role=data.get("role", "其他") or "其他",
            note=data.get("note", "") or "",
            created_at=_now(),
        )
        with self.db.connect() as conn:
            conn.execute(
                f"INSERT INTO contacts ({_COLUMNS}) VALUES "
                "(:id,:name,:role,:phone,:note,:created_at)",
                c.to_dict(),
            )
        return c

    def update(self, contact_id: str, data: dict) -> Contact | None:
        existing = self.get(contact_id)
        if existing is None:
            return None
        merged = existing.to_dict()
        for f in ("name", "phone", "role", "note"):
            if f in data:
                merged[f] = data[f]
        with self.db.connect() as conn:
            conn.execute(
                "UPDATE contacts SET name=:name, role=:role, phone=:phone, note=:note WHERE id=:id",
                merged,
            )
        return Contact(**merged)

    def delete(self, contact_id: str) -> bool:
        with self.db.connect() as conn:
            cur = conn.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
            return cur.rowcount > 0
