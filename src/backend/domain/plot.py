"""地块（园子）领域模型。纯数据 + 轻校验，无 IO。"""
from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class Plot:
    id: str
    name: str
    crop: str                       # crop_id，对应 CropRegistry
    variety: str = ""               # 品种，如 富士 / 秦王
    lat: float | None = None        # 纬度（驱动真实天气）
    lon: float | None = None        # 经度
    location_name: str = ""         # 村镇名，如 洛川县某村
    area_mu: float | None = None    # 面积（亩）
    notes: str = ""
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_row(row) -> "Plot":
        return Plot(
            id=row["id"],
            name=row["name"],
            crop=row["crop"],
            variety=row["variety"] or "",
            lat=row["lat"],
            lon=row["lon"],
            location_name=row["location_name"] or "",
            area_mu=row["area_mu"],
            notes=row["notes"] or "",
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
