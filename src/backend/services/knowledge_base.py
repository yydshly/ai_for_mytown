"""桃树知识库检索（病虫害 + 农药表）。

MVP 阶段用零依赖的关键词/字符重叠检索（可离线、可即测、无 embedding 成本）。
语料增大后按 ADR-002 切换到 chromadb 向量检索——只需替换 PestKB.retrieve 的实现，
对外接口（retrieve / get_by_name / pesticide_for）保持不变。

所有返回项都带溯源元数据（见 docs/knowledge-governance.md 第 3 节）。
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

log = logging.getLogger("services.knowledge_base")


def _read_jsonl(path: Path) -> list[dict]:
    out: list[dict] = []
    if not path.exists():
        return out
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            # 跳过 _meta 说明行（无 id）
            if "_meta" in obj and "id" not in obj:
                continue
            out.append(obj)
    return out


def _char_overlap(a: str, b: str) -> int:
    """中文按字重叠计分（无需分词），简单但对短查询够用。"""
    sa = set(a)
    sb = set(b)
    return len(sa & sb)


@dataclass
class PestMatch:
    id: str
    name: str
    type: str            # disease | pest
    score: int
    symptoms: str
    identify_cues: str
    cultural_control: str
    confusable_with: str
    pesticide_ref: list[str]
    source: str
    trust_level: str
    review_status: str


@dataclass
class PesticideInfo:
    target: str
    status: str          # verified | pending | none
    items: list[dict]    # 仅 verified=true 时含真实用药；否则为空
    note: str            # 面向用户的说明（未审核时导向农技员）


class KnowledgeBase:
    def __init__(self, pests_path: Path, pesticide_path: Path):
        self.pests_path = pests_path
        self.pesticide_path = pesticide_path
        self._pests = _read_jsonl(pests_path)
        self._pesticide = _read_jsonl(pesticide_path)

    # ---- 病虫害检索 ----

    def _searchable_text(self, entry: dict) -> str:
        parts = [
            entry.get("name", ""),
            " ".join(entry.get("aliases", []) or []),
            entry.get("symptoms", ""),
            entry.get("identify_cues", ""),
        ]
        return " ".join(parts)

    def _region_ok(self, entry: dict, region: str | None) -> bool:
        if not region:
            return True
        regions = (entry.get("metadata") or {}).get("region") or []
        return (not regions) or (region in regions)

    def retrieve(
        self,
        query: str,
        *,
        region: str | None = None,
        topic: str | None = None,   # disease | pest | None
        k: int = 3,
    ) -> list[PestMatch]:
        """按查询文本检索最相关的病虫害条目。
        注：KnowledgeBase 已按作物隔离（每个实例只含一种作物的数据），故不再按 crop 过滤。"""
        scored: list[tuple[int, dict]] = []
        for e in self._pests:
            if topic and e.get("type") != topic:
                continue
            if not self._region_ok(e, region):
                continue
            score = _char_overlap(query, self._searchable_text(e))
            if score > 0:
                scored.append((score, e))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [self._to_match(s, e) for s, e in scored[:k]]

    def find_mentions(self, text: str) -> list[PestMatch]:
        """在一段文本（如 AI 识别结果）中查找出现的已知病虫名/别名，按名称命中。
        用于把 vision 的自由文本对齐到结构化知识条目。"""
        hits: list[PestMatch] = []
        for e in self._pests:
            names = [e.get("name", "")] + (e.get("aliases") or [])
            if any(n and n in text for n in names):
                hits.append(self._to_match(99, e))
        return hits

    def get_by_name(self, name: str) -> PestMatch | None:
        for e in self._pests:
            names = [e.get("name", "")] + (e.get("aliases") or [])
            if name in names:
                return self._to_match(100, e)
        return None

    def all_names(self) -> list[str]:
        """该作物所有病虫的主名，用于动态拼装 vision 提示词。"""
        return [e.get("name", "") for e in self._pests if e.get("name")]

    def list_all(self) -> list[dict]:
        """全部病虫条目（图鉴用）。返回面向展示的字段。"""
        out: list[dict] = []
        for e in self._pests:
            md = e.get("metadata") or {}
            out.append({
                "id": e.get("id", ""),
                "name": e.get("name", ""),
                "type": e.get("type", ""),
                "aliases": e.get("aliases") or [],
                "symptoms": e.get("symptoms", ""),
                "identify_cues": e.get("identify_cues", ""),
                "confusable_with": e.get("confusable_with", ""),
                "cultural_control": e.get("cultural_control", ""),
                "source": md.get("source", ""),
                "trust_level": md.get("trust_level", ""),
                "review_status": md.get("review_status", ""),
            })
        return out

    def sample_disease_name(self) -> str:
        """取第一个病害名，给无 key 时的 mock 诊断用（保证按作物正确）。"""
        for e in self._pests:
            if e.get("type") == "disease" and e.get("name"):
                return e["name"]
        return self._pests[0].get("name", "") if self._pests else ""

    def _to_match(self, score: int, e: dict) -> PestMatch:
        md = e.get("metadata") or {}
        return PestMatch(
            id=e.get("id", ""),
            name=e.get("name", ""),
            type=e.get("type", ""),
            score=score,
            symptoms=e.get("symptoms", ""),
            identify_cues=e.get("identify_cues", ""),
            cultural_control=e.get("cultural_control", ""),
            confusable_with=e.get("confusable_with", ""),
            pesticide_ref=e.get("pesticide_ref") or [],
            source=md.get("source", ""),
            trust_level=md.get("trust_level", ""),
            review_status=md.get("review_status", ""),
        )

    # ---- 农药查表（安全护栏，见 ADR-010）----

    def pesticide_for(self, target: str) -> PesticideInfo:
        """查某病虫的用药。只有 verified=true 才返回真实用药；
        否则一律导向农技员，绝不展示未审核的药名/剂量。"""
        entries = [p for p in self._pesticide if p.get("target") == target]
        verified = [p for p in entries if p.get("verified") is True]

        if verified:
            items = [
                {
                    "agent": p.get("agent", ""),
                    "dosage": p.get("dosage", ""),
                    "timing": p.get("timing", ""),
                    "phi_days": p.get("phi_days"),
                    "source": (p.get("metadata") or {}).get("source", ""),
                }
                for p in verified
            ]
            return PesticideInfo(
                target=target,
                status="verified",
                items=items,
                note="用药请严格按农药标签说明，并遵守安全间隔期。",
            )

        if entries:
            # 有草稿但未经农技审核 → 不展示药名，导向农技员
            timing_hints = [p.get("draft_timing", "") for p in entries if p.get("draft_timing")]
            note = "该病虫的化学用药建议尚未经农技审核，暂不提供具体药剂。"
            if timing_hints:
                note += "（用药关键期参考：" + "；".join(timing_hints[:2]) + "）"
            note += " 请先采取农业/物理措施，或点击咨询农技员。"
            return PesticideInfo(target=target, status="pending", items=[], note=note)

        return PesticideInfo(
            target=target,
            status="none",
            items=[],
            note="知识库暂无该病虫的用药信息，建议咨询当地农技员。",
        )
