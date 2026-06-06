"""按作物集中管理知识访问（去掉各路由各自 build_kb 的重复）。

- bundle(crop)  → 该作物的知识路径集合（CropKnowledge）
- kb(crop)      → 该作物的 KnowledgeBase（按作物缓存，避免重复加载 jsonl）

crop 入参会经 CropRegistry.resolve 校验，非法值回退默认作物，下游无需再判空。
"""
from __future__ import annotations

from ..domain.crops import CropKnowledge, CropRegistry
from .knowledge_base import KnowledgeBase


class KnowledgeManager:
    def __init__(self, registry: CropRegistry):
        self.registry = registry
        self._kb_cache: dict[str, KnowledgeBase] = {}

    def bundle(self, crop_id: str | None) -> CropKnowledge:
        return self.registry.knowledge(crop_id)

    def kb(self, crop_id: str | None) -> KnowledgeBase:
        cid = self.registry.resolve(crop_id)
        kb = self._kb_cache.get(cid)
        if kb is None:
            b = self.registry.knowledge(cid)
            kb = KnowledgeBase(b.pests_path, b.pesticide_path)
            self._kb_cache[cid] = kb
        return kb
