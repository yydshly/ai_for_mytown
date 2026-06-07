"""AI 交互审计数据访问层。SQL 仅在此出现。"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from ..domain.interaction import Interaction
from ..infra.db import Database

_COLUMNS = "id, user_id, kind, crop, plot_id, summary, result_summary, feedback, created_at"
_CAP = 300  # 摘要截断长度


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class InteractionRepository:
    def __init__(self, db: Database):
        self.db = db

    def log(self, *, user_id: str, kind: str, crop: str = "", plot_id: str = "",
            summary: str = "", result_summary: str = "") -> Interaction:
        rec = Interaction(
            id=uuid.uuid4().hex[:12],
            user_id=user_id or "",
            kind=kind,
            crop=crop or "",
            plot_id=plot_id or "",
            summary=(summary or "")[:_CAP],
            result_summary=(result_summary or "")[:_CAP],
            feedback="",
            created_at=_now(),
        )
        with self.db.connect() as conn:
            conn.execute(
                f"INSERT INTO ai_interactions ({_COLUMNS}) VALUES "
                "(:id,:user_id,:kind,:crop,:plot_id,:summary,:result_summary,:feedback,:created_at)",
                rec.to_dict(),
            )
        return rec

    def set_feedback(self, interaction_id: str, value: str) -> bool:
        if value not in ("good", "bad"):
            return False
        with self.db.connect() as conn:
            cur = conn.execute(
                "UPDATE ai_interactions SET feedback = ? WHERE id = ?", (value, interaction_id)
            )
            return cur.rowcount > 0

    def list_recent(self, limit: int = 100, flagged_only: bool = False) -> list[Interaction]:
        q = f"SELECT {_COLUMNS} FROM ai_interactions"
        if flagged_only:
            q += " WHERE feedback = 'bad'"
        q += " ORDER BY created_at DESC LIMIT ?"
        with self.db.connect() as conn:
            rows = conn.execute(q, (limit,)).fetchall()
        return [Interaction.from_row(r) for r in rows]

    def stats(self) -> dict:
        with self.db.connect() as conn:
            total = conn.execute("SELECT COUNT(*) c FROM ai_interactions").fetchone()["c"]
            good = conn.execute("SELECT COUNT(*) c FROM ai_interactions WHERE feedback='good'").fetchone()["c"]
            bad = conn.execute("SELECT COUNT(*) c FROM ai_interactions WHERE feedback='bad'").fetchone()["c"]
            by_kind = {
                r["kind"]: r["c"]
                for r in conn.execute("SELECT kind, COUNT(*) c FROM ai_interactions GROUP BY kind").fetchall()
            }
        return {"total": total, "good": good, "bad": bad, "by_kind": by_kind}
