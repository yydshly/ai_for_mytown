"""病虫害图鉴路由（E3）。

GET /api/pests?crop=  → 该作物全部病虫条目（症状/识别/防治/出处），供父母主动查阅。
"""
from fastapi import APIRouter, Query


def register(app, ctx) -> None:
    r = APIRouter()

    @r.get("/api/pests")
    def pests(crop: str | None = Query(None)):
        cid = ctx.crops.resolve(crop)
        meta = ctx.crops.get(cid)
        kb = ctx.knowledge.kb(cid)
        return {
            "crop": cid,
            "crop_name": meta.name if meta else cid,
            "items": kb.list_all(),
        }

    app.include_router(r)
