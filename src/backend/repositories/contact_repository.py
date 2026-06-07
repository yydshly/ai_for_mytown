"""通讯录数据访问层。SQL 仅在此出现，并按 owner_id 做多用户隔离。"""
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

    def list(self, owner_id: str) -> list[Contact]:
        with self.db.connect() as conn:
            rows = conn.execute(
                f"SELECT {_COLUMNS} FROM contacts WHERE owner_id = ? ORDER BY created_at",
                (owner_id,),
            ).fetchall()
        return [Contact.from_row(r) for r in rows]

    def get(self, contact_id: str, owner_id: str | None = None) -> Contact | None:
        q = f"SELECT {_COLUMNS} FROM contacts WHERE id = ?"
        params: list = [contact_id]
        if owner_id is not None:
            q += " AND owner_id = ?"
            params.append(owner_id)
        with self.db.connect() as conn:
            row = conn.execute(q, params).fetchone()
        return Contact.from_row(row) if row else None

    def create(self, data: dict, owner_id: str) -> Contact:
        c = Contact(
            id=uuid.uuid4().hex[:12],
            name=data["name"],
            phone=data["phone"],
            role=data.get("role", "其他") or "其他",
            note=data.get("note", "") or "",
            created_at=_now(),
        )
        row = c.to_dict()
        row["owner_id"] = owner_id
        with self.db.connect() as conn:
            conn.execute(
                f"INSERT INTO contacts (id, owner_id, {_COLUMNS.replace('id, ', '')}) VALUES "
                "(:id,:owner_id,:name,:role,:phone,:note,:created_at)",
                row,
            )
        return c

    def update(self, contact_id: str, data: dict, owner_id: str) -> Contact | None:
        existing = self.get(contact_id, owner_id)
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

    def delete(self, contact_id: str, owner_id: str) -> bool:
        with self.db.connect() as conn:
            cur = conn.execute(
                "DELETE FROM contacts WHERE id = ? AND owner_id = ?", (contact_id, owner_id)
            )
            return cur.rowcount > 0
