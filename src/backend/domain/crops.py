"""作物注册表与按作物的知识路径解析（纯领域层，不依赖 FastAPI）。

扩展新作物只需两步：
1. 在 data/knowledge/crops.json 登记 {id, name, region, enabled}
2. 建 data/knowledge/<id>/ 目录，放 phenology/calendar/pests/pesticide/playbooks

所有作物共用同一套物候期 key（见 crops.json 说明），只是日期/内容不同，
因此 alerts/calendar 等逻辑无需为每个作物改代码。
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..infra.safeio import read_json


@dataclass(frozen=True)
class CropMeta:
    id: str
    name: str
    region: str
    enabled: bool = True


@dataclass(frozen=True)
class CropKnowledge:
    """某作物的知识文件路径集合。"""
    crop_id: str
    dir: Path

    @property
    def phenology_path(self) -> Path:
        return self.dir / "phenology.json"

    @property
    def calendar_path(self) -> Path:
        return self.dir / "calendar.json"

    @property
    def pests_path(self) -> Path:
        return self.dir / "pests.jsonl"

    @property
    def pesticide_path(self) -> Path:
        return self.dir / "pesticide.jsonl"

    @property
    def playbooks_path(self) -> Path:
        return self.dir / "playbooks.json"


class CropRegistry:
    def __init__(self, knowledge_dir: Path):
        self.knowledge_dir = knowledge_dir
        data = read_json(knowledge_dir / "crops.json") or {}
        self._crops: dict[str, CropMeta] = {}
        for c in data.get("crops") or []:
            if not c.get("id"):
                continue
            self._crops[c["id"]] = CropMeta(
                id=c["id"],
                name=c.get("name", c["id"]),
                region=c.get("region", ""),
                enabled=bool(c.get("enabled", True)),
            )
        self.default_id = data.get("default") or next(iter(self._crops), "peach")

    def list(self) -> list[CropMeta]:
        return [c for c in self._crops.values() if c.enabled]

    def get(self, crop_id: str | None) -> CropMeta | None:
        return self._crops.get(crop_id or "")

    def resolve(self, crop_id: str | None) -> str:
        """校验并回退到默认作物，保证下游永远拿到合法 crop_id。"""
        meta = self._crops.get(crop_id or "")
        if meta and meta.enabled:
            return meta.id
        return self.default_id

    def knowledge(self, crop_id: str | None) -> CropKnowledge:
        cid = self.resolve(crop_id)
        return CropKnowledge(cid, self.knowledge_dir / cid)
