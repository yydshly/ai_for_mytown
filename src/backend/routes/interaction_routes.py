"""AI 交互反馈 + 管理员审计后台（Phase 19）。

POST /api/interactions/{id}/feedback {value: good|bad}   用户标"有用/不对"（开放）
GET  /api/admin/interactions?flagged=1                   管理员看记录（仅 admin）
GET  /api/admin/stats                                    管理员看统计（仅 admin）

安全模型：不实时人审每条；控知识源头 + 护栏（已做）+ 此处事后审计与反馈。
"""
from fastapi import APIRouter, Body, Depends, HTTPException, Query

from ..infra.auth_dep import make_current_user
from ..repositories.interaction_repository import InteractionRepository


def register(app, ctx) -> None:
    r = APIRouter()
    repo = InteractionRepository(ctx.db)
    require_user = make_current_user(ctx)

    def require_admin(user=Depends(require_user)):
        if not getattr(user, "is_admin", False):
            raise HTTPException(403, "需要管理员权限")
        return user

    @r.post("/api/interactions/{interaction_id}/feedback")
    def feedback(interaction_id: str, payload: dict = Body(...)):
        value = (payload.get("value") or "").strip()
        if value not in ("good", "bad"):
            raise HTTPException(400, "value 必须是 good 或 bad")
        if not repo.set_feedback(interaction_id, value):
            raise HTTPException(404, "记录不存在")
        return {"ok": True}

    @r.get("/api/admin/interactions")
    def admin_list(flagged: int = Query(0), limit: int = Query(100), user=Depends(require_admin)):
        items = repo.list_recent(limit=min(limit, 500), flagged_only=bool(flagged))
        return {"interactions": [x.to_dict() for x in items]}

    @r.get("/api/admin/stats")
    def admin_stats(user=Depends(require_admin)):
        return repo.stats()

    app.include_router(r)
