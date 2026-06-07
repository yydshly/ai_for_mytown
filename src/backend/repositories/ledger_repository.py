"""账本数据访问层。SQL 仅在此出现。"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from ..domain.ledger import LedgerEntry
from ..infra.db import Database

_COLUMNS = "id, plot_id, date, kind, category, amount, note, created_at"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class LedgerRepository:
    def __init__(self, db: Database):
        self.db = db

    def list_by_plot(self, plot_id: str, year: str | None = None) -> list[LedgerEntry]:
        q = f"SELECT {_COLUMNS} FROM ledger_entries WHERE plot_id = ?"
        params: list = [plot_id]
        if year:
            q += " AND substr(date,1,4) = ?"
            params.append(year)
        q += " ORDER BY date DESC, created_at DESC"
        with self.db.connect() as conn:
            rows = conn.execute(q, params).fetchall()
        return [LedgerEntry.from_row(r) for r in rows]

    def create(self, plot_id: str, data: dict) -> LedgerEntry:
        e = LedgerEntry(
            id=uuid.uuid4().hex[:12],
            plot_id=plot_id,
            date=data["date"],
            kind=data["kind"],
            category=data.get("category", "") or "",
            amount=float(data["amount"]),
            note=data.get("note", "") or "",
            created_at=_now(),
        )
        with self.db.connect() as conn:
            conn.execute(
                f"INSERT INTO ledger_entries ({_COLUMNS}) VALUES "
                "(:id,:plot_id,:date,:kind,:category,:amount,:note,:created_at)",
                e.to_dict(),
            )
        return e

    def delete(self, entry_id: str, owner_id: str | None = None) -> bool:
        with self.db.connect() as conn:
            if owner_id is None:
                cur = conn.execute("DELETE FROM ledger_entries WHERE id = ?", (entry_id,))
            else:
                cur = conn.execute(
                    "DELETE FROM ledger_entries WHERE id = ? AND plot_id IN "
                    "(SELECT id FROM plots WHERE owner_id = ?)",
                    (entry_id, owner_id),
                )
            return cur.rowcount > 0

    def summary(self, plot_id: str, year: str | None = None) -> dict:
        q = (
            "SELECT kind, COALESCE(SUM(amount),0) AS total FROM ledger_entries "
            "WHERE plot_id = ?"
        )
        params: list = [plot_id]
        if year:
            q += " AND substr(date,1,4) = ?"
            params.append(year)
        q += " GROUP BY kind"
        income = expense = 0.0
        with self.db.connect() as conn:
            for row in conn.execute(q, params).fetchall():
                if row["kind"] == "income":
                    income = float(row["total"])
                elif row["kind"] == "expense":
                    expense = float(row["total"])
        return {
            "total_income": round(income, 2),
            "total_expense": round(expense, 2),
            "net": round(income - expense, 2),
        }
