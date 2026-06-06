"""推送去重数据访问。同一地块、同一灾害、同一天只推一次，防刷屏。"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from ..infra.db import Database


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class NotificationRepository:
    def __init__(self, db: Database):
        self.db = db

    def was_sent(self, plot_id: str, alert_kind: str, date: str) -> bool:
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM notifications_sent WHERE plot_id=? AND alert_kind=? AND date=?",
                (plot_id, alert_kind, date),
            ).fetchone()
        return row is not None

    def mark_sent(self, plot_id: str, alert_kind: str, date: str) -> None:
        with self.db.connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO notifications_sent (id, plot_id, alert_kind, date, created_at) "
                "VALUES (?,?,?,?,?)",
                (uuid.uuid4().hex[:12], plot_id, alert_kind, date, _now()),
            )
