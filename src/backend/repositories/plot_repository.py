"""地块数据访问层。SQL 仅在此出现，并按 owner_id 做多用户隔离。"""
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

    def list(self, owner_id: str) -> list[Plot]:
        with self.db.connect() as conn:
            rows = conn.execute(
                f"SELECT {_COLUMNS} FROM plots WHERE owner_id = ? ORDER BY created_at",
                (owner_id,),
            ).fetchall()
        return [Plot.from_row(r) for r in rows]

    def list_all(self) -> list[Plot]:
        """跨用户全部地块（仅供系统任务用，如定时预警推送）。"""
        with self.db.connect() as conn:
            rows = conn.execute(f"SELECT {_COLUMNS} FROM plots ORDER BY created_at").fetchall()
        return [Plot.from_row(r) for r in rows]

    def get(self, plot_id: str, owner_id: str | None = None) -> Plot | None:
        q = f"SELECT {_COLUMNS} FROM plots WHERE id = ?"
        params: list = [plot_id]
        if owner_id is not None:
            q += " AND owner_id = ?"
            params.append(owner_id)
        with self.db.connect() as conn:
            row = conn.execute(q, params).fetchone()
        return Plot.from_row(row) if row else None

    def create(self, data: dict, owner_id: str) -> Plot:
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
        row = plot.to_dict()
        row["owner_id"] = owner_id
        with self.db.connect() as conn:
            conn.execute(
                f"INSERT INTO plots (id, owner_id, {_COLUMNS.replace('id, ', '')}) VALUES "
                "(:id,:owner_id,:name,:crop,:variety,:lat,:lon,:location_name,:area_mu,:notes,:created_at,:updated_at)",
                row,
            )
        return plot

    def update(self, plot_id: str, data: dict, owner_id: str) -> Plot | None:
        existing = self.get(plot_id, owner_id)
        if existing is None:
            return None
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

    def delete(self, plot_id: str, owner_id: str) -> bool:
        with self.db.connect() as conn:
            cur = conn.execute(
                "DELETE FROM plots WHERE id = ? AND owner_id = ?", (plot_id, owner_id)
            )
            return cur.rowcount > 0
