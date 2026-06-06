"""地块数据访问层。SQL 仅在此出现，routes/services 不直接写 SQL。"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from ..domain.plot import Plot
from ..infra.db import Database

_COLUMNS = (
    "id, name, crop, variety, lat, lon, location_name, area_mu, notes, created_at, updated_at"
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class PlotRepository:
    def __init__(self, db: Database):
        self.db = db

    def list(self) -> list[Plot]:
        with self.db.connect() as conn:
            rows = conn.execute(
                f"SELECT {_COLUMNS} FROM plots ORDER BY created_at"
            ).fetchall()
        return [Plot.from_row(r) for r in rows]

    def get(self, plot_id: str) -> Plot | None:
        with self.db.connect() as conn:
            row = conn.execute(
                f"SELECT {_COLUMNS} FROM plots WHERE id = ?", (plot_id,)
            ).fetchone()
        return Plot.from_row(row) if row else None

    def create(self, data: dict) -> Plot:
        now = _now()
        plot = Plot(
            id=uuid.uuid4().hex[:12],
            name=data["name"],
            crop=data["crop"],
            variety=data.get("variety", "") or "",
            lat=data.get("lat"),
            lon=data.get("lon"),
            location_name=data.get("location_name", "") or "",
            area_mu=data.get("area_mu"),
            notes=data.get("notes", "") or "",
            created_at=now,
            updated_at=now,
        )
        with self.db.connect() as conn:
            conn.execute(
                f"INSERT INTO plots ({_COLUMNS}) VALUES "
                "(:id,:name,:crop,:variety,:lat,:lon,:location_name,:area_mu,:notes,:created_at,:updated_at)",
                plot.to_dict(),
            )
        return plot

    def update(self, plot_id: str, data: dict) -> Plot | None:
        existing = self.get(plot_id)
        if existing is None:
            return None
        # 仅更新允许字段
        fields = ("name", "crop", "variety", "lat", "lon", "location_name", "area_mu", "notes")
        merged = existing.to_dict()
        for f in fields:
            if f in data:
                merged[f] = data[f]
        merged["updated_at"] = _now()
        with self.db.connect() as conn:
            conn.execute(
                "UPDATE plots SET name=:name, crop=:crop, variety=:variety, lat=:lat, lon=:lon, "
                "location_name=:location_name, area_mu=:area_mu, notes=:notes, updated_at=:updated_at "
                "WHERE id=:id",
                merged,
            )
        return Plot(**merged)

    def delete(self, plot_id: str) -> bool:
        with self.db.connect() as conn:
            cur = conn.execute("DELETE FROM plots WHERE id = ?", (plot_id,))
            return cur.rowcount > 0
