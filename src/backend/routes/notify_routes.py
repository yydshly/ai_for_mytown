"""主动推送路由（F1）。

GET  /api/notify/status      推送通道状态
POST /api/notify/check-now   立即巡检并推送（测试用，可带 ?scenario= 与 ?force=1）
"""
from fastapi import APIRouter, Query

from ..services.alert_scheduler import run_alert_check
from ..services.notify.factory import build_channel


def register(app, ctx) -> None:
    r = APIRouter()

    @r.get("/api/notify/status")
    def status():
        ch = build_channel(ctx.config)
        configured_name = (ctx.config.get("notify") or {}).get("channel") or "log"
        return {
            "active_channel": ch.name,
            "configured_channel": configured_name,
            "fallback_to_log": ch.name == "log" and configured_name != "log",
            "schedule_hours": (ctx.config.get("notify") or {}).get("schedule_hours") or [6, 12, 18],
        }

    @r.post("/api/notify/check-now")
    async def check_now(scenario: str | None = Query(None), force: int = Query(0)):
        return await run_alert_check(ctx, scenario=scenario, force=bool(force))

    app.include_router(r)
