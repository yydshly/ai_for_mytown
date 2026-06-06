"""自然语言问答路由（语音/文字共用）。

POST /api/chat  body: {"question": "...", "history": [{role,content}]}  → {answer, mode}
GET  /api/chat/available  → {available: bool}

ASR（语音转文字）在前端用浏览器 Web Speech API 完成（见 ADR-006），后端只收文字。
"""
import logging

from fastapi import APIRouter, Body, HTTPException

from ..services.chat_service import ChatService
from ..services.knowledge_base import build_kb

log = logging.getLogger("routes.chat")

MAX_Q_CHARS = 500
MAX_HISTORY = 8


def register(app, ctx) -> None:
    r = APIRouter()
    svc = ChatService(ctx)
    kb = build_kb(ctx.knowledge_dir)

    @r.get("/api/chat/available")
    def available():
        return {"available": svc.available()}

    @r.post("/api/chat")
    async def chat(payload: dict = Body(...)):
        question = (payload.get("question") or "").strip()
        if not question:
            raise HTTPException(400, "question 不能为空")
        question = question[:MAX_Q_CHARS]
        history = payload.get("history") or []
        if isinstance(history, list):
            history = history[-MAX_HISTORY:]
        else:
            history = []
        return await svc.answer(kb, question, history)

    app.include_router(r)
