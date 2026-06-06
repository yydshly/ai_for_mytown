"""农事日志（D2）REST 路由。

GET    /api/plots/{plot_id}/logs   列出该地块日志（按日期倒序）
POST   /api/plots/{plot_id}/logs   新建 {date, category, title, detail?}
DELETE /api/logs/{log_id}          删除一条
GET    /api/log-categories         返回可选类别（前端下拉）
"""
import logging
from datetime import date as _date

from fastapi import APIRouter, Body, HTTPException

from ..domain.activity_log import CATEGORIES
from ..repositories.activity_log_repository import ActivityLogRepository
from ..repositories.plot_repository import PlotRepository

log = logging.getLogger("routes.log")


def _days_ago(date_str: str) -> int | None:
    try:
        return (_date.today() - _date.fromisoformat(date_str)).days
    except Exception:
        return None


def register(app, ctx) -> None:
    r = APIRouter()
    repo = ActivityLogRepository(ctx.db)
    plots = PlotRepository(ctx.db)

    @r.get("/api/log-categories")
    def categories():
        return {"categories": CATEGORIES}

    @r.get("/api/plots/{plot_id}/logs")
    def list_logs(plot_id: str):
        if plots.get(plot_id) is None:
            raise HTTPException(404, "地块不存在")
        return {"logs": [x.to_dict() for x in repo.list_by_plot(plot_id)]}

    @r.post("/api/plots/{plot_id}/logs")
    def create_log(plot_id: str, payload: dict = Body(...)):
        if plots.get(plot_id) is None:
            raise HTTPException(404, "地块不存在")
        title = (payload.get("title") or "").strip()
        category = (payload.get("category") or "").strip()
        if not title:
            raise HTTPException(400, "请填写做了什么")
        if category not in CATEGORIES:
            raise HTTPException(400, f"未知类别：{category}")
        data = {
            "date": (payload.get("date") or _date.today().isoformat()).strip(),
            "category": category,
            "title": title,
            "detail": (payload.get("detail") or "").strip(),
        }
        return repo.create(plot_id, data).to_dict()

    @r.delete("/api/logs/{log_id}")
    def delete_log(log_id: str):
        if not repo.delete(log_id):
            raise HTTPException(404, "记录不存在")
        return {"ok": True}

    @r.get("/api/plots/{plot_id}/summary")
    def plot_summary(plot_id: str):
        """地块速览：最近一次打药 + 距今天数（用于安全间隔期/复盘提示）。"""
        if plots.get(plot_id) is None:
            raise HTTPException(404, "地块不存在")
        last_spray = repo.latest_by_category(plot_id, "打药")
        all_logs = repo.list_by_plot(plot_id, limit=1000)
        return {
            "plot_id": plot_id,
            "log_count": len(all_logs),
            "last_spray": (
                {
                    "date": last_spray.date,
                    "title": last_spray.title,
                    "days_ago": _days_ago(last_spray.date),
                }
                if last_spray else None
            ),
        }

    app.include_router(r)
