"""语音合成路由。

POST /api/tts  body: {"text": "...", "voice": "可选"}  → 音频字节（带缓存）。
GET  /api/tts/available  → {available: bool}  供前端决定是否显示"听"按钮。
"""
import logging

from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import Response

from ..services.tts_service import TTSService

log = logging.getLogger("routes.tts")

MAX_TTS_CHARS = 800  # 单次朗读上限，过长截断（老人场景一般是短段落）


def register(app, ctx) -> None:
    r = APIRouter()
    svc = TTSService(ctx.config, ctx.project_root / "cache" / "tts")

    @r.get("/api/tts/available")
    def available():
        return {"available": svc.available()}

    @r.post("/api/tts")
    async def tts(payload: dict = Body(...)):
        text = (payload.get("text") or "").strip()
        voice = (payload.get("voice") or "").strip()
        if not text:
            raise HTTPException(400, "text 不能为空")
        text = text[:MAX_TTS_CHARS]

        result = await svc.synth(text, voice)
        if result is None:
            raise HTTPException(503, "语音功能暂不可用")
        audio, mime = result
        return Response(content=audio, media_type=mime)

    app.include_router(r)
