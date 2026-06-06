from datetime import date

from fastapi import APIRouter, HTTPException

from ..infra.safeio import read_json
from ..services.phenology import current_stage, load_stages, neighbors


def register(app, ctx) -> None:
    r = APIRouter()

    @r.get("/api/calendar/today")
    def today():
        stages = load_stages(ctx.phenology_path)
        if not stages:
            raise HTTPException(500, "物候期数据未加载")
        today_date = date.today()
        cur = current_stage(stages, today_date)
        if cur is None:
            raise HTTPException(500, f"未匹配到当前物候期：{today_date}")
        prev_s, next_s = neighbors(stages, cur)

        calendar = read_json(ctx.calendar_path) or {}
        tasks = (calendar.get("tasks_by_stage") or {}).get(cur.key) or []

        return {
            "date": today_date.isoformat(),
            "crop": "peach",
            "region": "陕西关中",
            "stage": {
                "key": cur.key,
                "name": cur.name,
                "summary": cur.summary,
                "window": f"{cur.start[0]:02d}-{cur.start[1]:02d} ~ {cur.end[0]:02d}-{cur.end[1]:02d}",
            },
            "prev_stage": {"key": prev_s.key, "name": prev_s.name} if prev_s else None,
            "next_stage": {"key": next_s.key, "name": next_s.name} if next_s else None,
            "tasks": tasks,
        }

    @r.get("/api/calendar/all")
    def all_stages():
        stages = load_stages(ctx.phenology_path)
        calendar = read_json(ctx.calendar_path) or {}
        tasks_map = calendar.get("tasks_by_stage") or {}
        return {
            "crop": "peach",
            "region": "陕西关中",
            "stages": [
                {
                    "key": s.key,
                    "name": s.name,
                    "summary": s.summary,
                    "window": f"{s.start[0]:02d}-{s.start[1]:02d} ~ {s.end[0]:02d}-{s.end[1]:02d}",
                    "tasks": tasks_map.get(s.key) or [],
                }
                for s in stages
            ],
        }

    app.include_router(r)
