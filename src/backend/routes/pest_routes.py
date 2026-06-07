"""病虫害图鉴路由（E3）。

GET /api/pests?crop=  → 该作物全部病虫条目（症状/识别/防治/出处），供父母主动查阅。
"""
from fastapi import APIRouter, Query

from ..repositories.image_repository import ImageRepository


def register(app, ctx) -> None:
    r = APIRouter()
    images = ImageRepository(ctx.db)

    @r.get("/api/pests")
    def pests(crop: str | None = Query(None)):
        cid = ctx.crops.resolve(crop)
        meta = ctx.crops.get(cid)
        kb = ctx.knowledge.kb(cid)
        items = kb.list_all()
        for it in items:
            it["images"] = [
                {"id": im["id"], "url": f"/api/images/{im['filename']}", "caption": im["caption"]}
                for im in images.list_by_pest(cid, it["id"])
            ]
        return {
            "crop": cid,
            "crop_name": meta.name if meta else cid,
            "items": items,
        }

    app.include_router(r)
