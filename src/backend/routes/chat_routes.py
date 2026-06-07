"""自然语言问答路由（语音/文字共用）。

POST /api/chat  body: {"question": "...", "history": [{role,content}]}  → {answer, mode}
GET  /api/chat/available  → {available: bool}

ASR（语音转文字）在前端用浏览器 Web Speech API 完成（见 ADR-006），后端只收文字。
"""
import logging

from fastapi import APIRouter, Body, Depends, HTTPException

from ..infra.auth_dep import make_current_user
from ..services.chat_service import ChatService

log = logging.getLogger("routes.chat")

MAX_Q_CHARS = 500
MAX_HISTORY = 8


def register(app, ctx) -> None:
    r = APIRouter()
    svc = ChatService(ctx)
    optional_user = make_current_user(ctx, required=False)

    @r.get("/api/chat/available")
    def available():
        return {"available": svc.available()}

    @r.post("/api/chat")
    async def chat(payload: dict = Body(...), user=Depends(optional_user)):
        question = (payload.get("question") or "").strip()
        if not question:
            raise HTTPException(400, "question 不能为空")
        question = question[:MAX_Q_CHARS]
        history = payload.get("history") or []
        if isinstance(history, list):
            history = history[-MAX_HISTORY:]
        else:
            history = []

        cid = ctx.crops.resolve(payload.get("crop"))
        kb = ctx.knowledge.kb(cid)
        bundle = ctx.crops.knowledge(cid)
        # 仅在登录且拥有该地块时，才注入地块上下文
        plot_id = (payload.get("plot_id") or "").strip() or None
        owner_id = user.id if user else None
        return await svc.answer(kb, bundle, question, history, plot_id=plot_id, owner_id=owner_id)

    app.include_router(r)
