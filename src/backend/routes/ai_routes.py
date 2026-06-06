"""AI 配置状态接口。

GET /api/ai/status —— 不泄露完整 key 的前提下，报告各 provider 是否就绪、
能力（text/vision/tts）、以及 key 的掩码预览。用于填完 config.json 后自检。
"""
import logging

from fastapi import APIRouter

from ...ai.base import expand_env
from ...ai.factory import make_provider

log = logging.getLogger("routes.ai")

# 占位串前缀（config.json 模板用）；命中即视为"未填写真实 key"
_PLACEHOLDER_PREFIX = "PASTE_"


def _mask(key: str) -> str:
    key = (key or "").strip()
    if not key:
        return "（空）"
    if key.startswith(_PLACEHOLDER_PREFIX):
        return "（未填写·占位）"
    if len(key) <= 8:
        return key[0] + "***"
    return f"{key[:4]}***{key[-4:]}（长度 {len(key)}）"


def _looks_real(key: str) -> bool:
    key = (key or "").strip()
    return bool(key) and not key.startswith(_PLACEHOLDER_PREFIX)


def register(app, ctx) -> None:
    r = APIRouter()

    @r.get("/api/ai/status")
    def status():
        ai_cfg = expand_env(ctx.config.get("ai") or {})
        providers_cfg = ai_cfg.get("providers") or {}

        roles = {
            "active": ai_cfg.get("active"),
            "vision_provider": ai_cfg.get("vision_provider"),
            "tts_provider": ai_cfg.get("tts_provider"),
        }

        report = []
        for name, pcfg in providers_cfg.items():
            key = pcfg.get("api_key", "")
            entry = {
                "name": name,
                "type": pcfg.get("type", name),
                "api_key_preview": _mask(key),
                "key_ready": _looks_real(key),
                "capabilities": [],
                "ok": False,
                "error": None,
            }
            # 仅当 key 像真的才尝试构建（构建不发网络请求，只校验配置）
            if _looks_real(key):
                try:
                    p = make_provider(name, ai_cfg)
                    entry["capabilities"] = sorted(p.capabilities)
                    entry["ok"] = True
                except Exception as e:
                    entry["error"] = str(e)
            report.append(entry)

        # 诊断能否走真实 vision：vision_provider 的 key 就绪且含 vision 能力
        vision_name = roles.get("vision_provider")
        vision_ready = any(
            e["name"] == vision_name and e["ok"] and "vision" in e["capabilities"]
            for e in report
        )

        return {
            "roles": roles,
            "providers": report,
            "vision_ready": vision_ready,
            "hint": (
                "vision 已就绪：可把前端 useMock 改为 false 走真实拍照诊断。"
                if vision_ready
                else "vision 未就绪：请在 config/config.json 填入 MiniMax key，"
                     "并确认 minimax.enable_vision=true。"
            ),
        }

    app.include_router(r)
