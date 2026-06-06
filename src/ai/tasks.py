"""农业领域高层 AI 任务函数。

这些函数是框架无关的（不依赖 FastAPI）：接收 provider + 上下文 → 产出文本/流式文本。
HTTP 层（routes/）负责解析 provider、装载 RAG 上下文、组装响应。

四个核心任务对应 MVP 的四块能力：
- diagnose_disease     拍照诊断（vision + RAG）
- advise_calendar      物候期建议
- explain_alert        天气/灾害预警解读
- chat_with_context    自然语言问答
"""
from __future__ import annotations

import logging
from typing import AsyncIterator

from .base import LLMProvider, Message

log = logging.getLogger("ai.tasks")


SYSTEM_DIAGNOSE = (
    "你是一名陕西本地的果树农技顾问，专攻桃树。"
    "请根据用户提供的叶片/果实/枝干照片以及参考知识，判断最可能的病虫害。"
    "回答必须**结构化**：\n"
    "1) 最可能诊断（1 条）+ 可能性高/中/低\n"
    "2) 备选诊断（最多 2 条）\n"
    "3) 处置建议（用药名称、稀释倍数、施药时机、安全间隔期；优先低毒/低残留方案）\n"
    "4) 短期注意事项（48 小时内观察重点、是否暂停采收等）\n"
    "5) 若图片信息不足以判断，明确说明需要补拍哪个部位、哪个角度。\n"
    "不要编造未在参考知识中出现的农药名；如知识库无对应方案，提示用户线下咨询农技员。"
)

SYSTEM_CALENDAR = (
    "你是桃树农事顾问。基于当前物候期与最近天气，输出未来 7 天内"
    "**3-5 条**具体行动建议。每条包含：动作、时间窗口、操作要点。"
    "口吻直白，面向年长的果农，避免专业术语堆砌。"
)

SYSTEM_ALERT = (
    "你是桃树灾害应对顾问。根据气象预警事实，结合当前物候期，给出："
    "1) 这次灾害对桃树的具体威胁（1-2 句）\n"
    "2) **现在到灾害到来前**需要做的应对措施（按优先级排序）\n"
    "3) 灾害过后的补救动作。\n"
    "措施要可操作，避免『做好防护』这类空话。"
)

SYSTEM_CHAT = (
    "你是陕西本地的桃树种植助手，回答父母（年长果农）关于种植的问题。"
    "用通俗、简短、肯定的中文。如有参考知识请引用关键事实；"
    "若无法确定，直说『我不确定，建议请教当地农技员』，不要瞎猜用药。"
)


def _kb_block(kb_snippets: list[str] | None) -> str:
    if not kb_snippets:
        return ""
    body = "\n---\n".join(s.strip() for s in kb_snippets if s.strip())
    return f"<<<参考知识开始>>>\n{body}\n<<<参考知识结束>>>\n"


async def diagnose_disease(
    provider: LLMProvider,
    image_bytes: bytes,
    *,
    image_mime: str = "image/jpeg",
    kb_snippets: list[str] | None = None,
    user_note: str = "",
) -> str:
    """病虫害拍照诊断。需要 provider 支持 vision；返回一次性的结构化文本。"""
    prompt_parts = [SYSTEM_DIAGNOSE]
    kb = _kb_block(kb_snippets)
    if kb:
        prompt_parts.append(kb)
    if user_note:
        prompt_parts.append(f"用户补充说明：{user_note}")
    prompt_parts.append("请基于上面照片给出诊断与处置建议。")
    prompt = "\n\n".join(prompt_parts)
    return await provider.vision(image_bytes, prompt, mime=image_mime)


async def advise_calendar(
    provider: LLMProvider,
    *,
    stage_name: str,
    stage_summary: str,
    upcoming_tasks: list[dict],
    recent_weather_note: str = "",
    kb_snippets: list[str] | None = None,
    stream: bool = True,
) -> AsyncIterator[str]:
    """基于当前物候期+天气产出未来 7 天行动建议（流式）。"""
    tasks_text = "\n".join(
        f"- [{t.get('category','')}] {t.get('title','')}：{t.get('detail','')}"
        for t in (upcoming_tasks or [])
    ) or "（无）"

    user_block = (
        f"当前物候期：{stage_name}\n"
        f"阶段概述：{stage_summary}\n"
        f"基础农事条目：\n{tasks_text}\n"
    )
    if recent_weather_note:
        user_block += f"\n最近天气：{recent_weather_note}\n"
    kb = _kb_block(kb_snippets)
    if kb:
        user_block += "\n" + kb

    messages = [
        Message(role="system", content=SYSTEM_CALENDAR),
        Message(role="user", content=user_block),
        Message(role="user", content="请给我未来 7 天的 3-5 条具体建议。"),
    ]
    async for delta in provider.chat(messages, stream=stream, max_tokens=900, temperature=0.4):
        yield delta


async def explain_alert(
    provider: LLMProvider,
    *,
    alert_kind: str,
    alert_detail: str,
    stage_name: str,
    kb_snippets: list[str] | None = None,
    stream: bool = True,
) -> AsyncIterator[str]:
    """解读一条天气/灾害预警，给桃树果农可操作的应对方案。"""
    user_block = (
        f"灾害类型：{alert_kind}\n"
        f"预警详情：{alert_detail}\n"
        f"当前桃树物候期：{stage_name}\n"
    )
    kb = _kb_block(kb_snippets)
    if kb:
        user_block += "\n" + kb
    messages = [
        Message(role="system", content=SYSTEM_ALERT),
        Message(role="user", content=user_block),
    ]
    async for delta in provider.chat(messages, stream=stream, max_tokens=900, temperature=0.3):
        yield delta


async def chat_with_context(
    provider: LLMProvider,
    history: list[Message],
    user_question: str,
    *,
    stage_name: str = "",
    kb_snippets: list[str] | None = None,
    stream: bool = True,
) -> AsyncIterator[str]:
    """自然语言问答（语音/文字共用）。带物候期 + RAG 上下文。"""
    messages: list[Message] = [Message(role="system", content=SYSTEM_CHAT)]
    ctx_lines: list[str] = []
    if stage_name:
        ctx_lines.append(f"当前桃树物候期：{stage_name}")
    kb = _kb_block(kb_snippets)
    if kb:
        ctx_lines.append(kb)
    if ctx_lines:
        messages.append(Message(role="user", content="\n".join(ctx_lines)))
    for h in history:
        messages.append(h)
    messages.append(Message(role="user", content=user_question))
    async for delta in provider.chat(messages, stream=stream, max_tokens=1200, temperature=0.5):
        yield delta
