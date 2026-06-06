"""作物列表路由（前端作物选择器用）。

GET /api/crops → 已启用作物 [{id, name, region}]，含默认作物。
"""
from fastapi import APIRouter


def register(app, ctx) -> None:
    r = APIRouter()

    @r.get("/api/crops")
    def crops():
        return {
            "default": ctx.crops.default_id,
            "crops": [
                {"id": c.id, "name": c.name, "region": c.region}
                for c in ctx.crops.list()
            ],
        }

    app.include_router(r)
