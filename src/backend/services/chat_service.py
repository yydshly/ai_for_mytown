"""自然语言问答服务（语音/文字共用）。

把父母的问题，结合本地知识（病虫害 RAG + 当前物候期 + 本周农事）喂给文字模型，
回出通俗简短的答案。用药相关仍遵守护栏（prompt 层 + 知识库只给已审核用药）。

对 AI 未配置/出错优雅降级（R-07）。
"""
from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

from ...ai.base import Capability, Message, ProviderConfigError
from ...ai.factory import make_provider
from ...ai.tasks import chat_with_context
from ..domain.crops import CropKnowledge
from ..infra.safeio import read_json
from .knowledge_base import KnowledgeBase
from .phenology import current_stage, load_stages

log = logging.getLogger("services.chat")


class ChatService:
    def __init__(self, ctx):
        self.ctx = ctx
        self._provider = None
        self._tried = False

    def _get_provider(self):
        if self._tried:
            return self._provider
        self._tried = True
        ai_cfg = self.ctx.config.get("ai") or {}
        name = ai_cfg.get("active")
        if not name:
            return None
        try:
            p = make_provider(name, ai_cfg)
        except ProviderConfigError as e:
            log.info("chat provider 未配置: %s", e)
            return None
        if not p.supports(Capability.TEXT):
            return None
        self._provider = p
        return p

    def available(self) -> bool:
        return self._get_provider() is not None

    def _context(self, kb: KnowledgeBase, bundle: CropKnowledge, question: str) -> tuple[str, list[str]]:
        """组装 RAG 上下文：当前物候期名 + 相关病虫条目 + 本周农事（按作物）。"""
        snippets: list[str] = []

        # 当前物候期 + 本周农事
        stage_name = ""
        cur = current_stage(load_stages(bundle.phenology_path), date.today())
        if cur:
            stage_name = cur.name
            calendar = read_json(bundle.calendar_path) or {}
            tasks = (calendar.get("tasks_by_stage") or {}).get(cur.key) or []
            if tasks:
                lines = [f"{t.get('title','')}：{t.get('detail','')}" for t in tasks[:4]]
                snippets.append("当前阶段农事：" + "；".join(lines))

        # 病虫害检索
        for m in kb.retrieve(question, k=2):
            snippets.append(
                f"【{m.name}】症状：{m.symptoms} 防治：{m.cultural_control}"
            )
        return stage_name, snippets

    async def answer(
        self, kb: KnowledgeBase, bundle: CropKnowledge,
        question: str, history: list[dict] | None = None,
    ) -> dict:
        question = (question or "").strip()
        if not question:
            return {"mode": "error", "answer": "没听清，请再说一遍。"}

        provider = self._get_provider()
        if provider is None:
            return {"mode": "unconfigured", "answer": "AI 暂未配置，问题我先记下了，建议咨询农技员。"}

        stage_name, snippets = self._context(kb, bundle, question)
        hist_msgs = [
            Message(role=h.get("role", "user"), content=h.get("content", ""))
            for h in (history or [])
            if h.get("content")
        ]

        try:
            out = ""
            async for delta in chat_with_context(
                provider, hist_msgs, question,
                stage_name=stage_name, kb_snippets=snippets, stream=True,
            ):
                out += delta
            return {"mode": "ai", "answer": out.strip() or "我不太确定，建议咨询当地农技员。", "stage": stage_name}
        except Exception as e:
            log.warning("chat 失败: %s", e)
            return {"mode": "error", "answer": "网络不太好，稍后再问我一次。"}
