"""农事日志数据访问层。SQL 仅在此出现。"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from ..domain.activity_log import ActivityLog
from ..infra.db import Database

_COLUMNS = "id, plot_id, date, category, title, detail, created_at"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class ActivityLogRepository:
    def __init__(self, db: Database):
        self.db = db

    def list_by_plot(self, plot_id: str, limit: int = 200) -> list[ActivityLog]:
        with self.db.connect() as conn:
            rows = conn.execute(
                f"SELECT {_COLUMNS} FROM activity_logs WHERE plot_id = ? "
                "ORDER BY date DESC, created_at DESC LIMIT ?",
                (plot_id, limit),
            ).fetchall()
        return [ActivityLog.from_row(r) for r in rows]

    def create(self, plot_id: str, data: dict) -> ActivityLog:
        log = ActivityLog(
            id=uuid.uuid4().hex[:12],
            plot_id=plot_id,
            date=data["date"],
            category=data["category"],
            title=data["title"],
            detail=data.get("detail", "") or "",
            created_at=_now(),
        )
        with self.db.connect() as conn:
            conn.execute(
                f"INSERT INTO activity_logs ({_COLUMNS}) VALUES "
                "(:id,:plot_id,:date,:category,:title,:detail,:created_at)",
                log.to_dict(),
            )
        return log

    def delete(self, log_id: str) -> bool:
        with self.db.connect() as conn:
            cur = conn.execute("DELETE FROM activity_logs WHERE id = ?", (log_id,))
            return cur.rowcount > 0

    def latest_by_category(self, plot_id: str, category: str) -> ActivityLog | None:
        """某地块某类别最近一次记录（如最近一次打药，供安全间隔期参考）。"""
        with self.db.connect() as conn:
            row = conn.execute(
                f"SELECT {_COLUMNS} FROM activity_logs WHERE plot_id = ? AND category = ? "
                "ORDER BY date DESC, created_at DESC LIMIT 1",
                (plot_id, category),
            ).fetchone()
        return ActivityLog.from_row(row) if row else None
