"""地块（园子）REST 路由。

GET    /api/plots          列出
POST   /api/plots          新建 {name, crop, variety?, lat?, lon?, location_name?, area_mu?, notes?}
GET    /api/plots/{id}     详情
PUT    /api/plots/{id}     更新（部分字段）
DELETE /api/plots/{id}     删除

crop 必须在作物注册表内；薄校验后委托 PlotRepository。
"""
import logging

from fastapi import APIRouter, Body, HTTPException

from ..repositories.plot_repository import PlotRepository

log = logging.getLogger("routes.plot")

_ALLOWED = {"name", "crop", "variety", "lat", "lon", "location_name", "area_mu", "notes"}


def register(app, ctx) -> None:
    r = APIRouter()
    repo = PlotRepository(ctx.db)

    def _validate(data: dict, *, require_required: bool) -> dict:
        clean = {k: v for k, v in data.items() if k in _ALLOWED}
        if require_required:
            if not (clean.get("name") or "").strip():
                raise HTTPException(400, "地块名称不能为空")
            if not clean.get("crop"):
                raise HTTPException(400, "请选择作物")
        if "crop" in clean and clean["crop"] is not None:
            if ctx.crops.get(clean["crop"]) is None:
                raise HTTPException(400, f"未知作物：{clean['crop']}")
        for f in ("lat", "lon", "area_mu"):
            if clean.get(f) in ("", None):
                clean[f] = None
        return clean

    @r.get("/api/plots")
    def list_plots():
        return {"plots": [p.to_dict() for p in repo.list()]}

    @r.post("/api/plots")
    def create_plot(payload: dict = Body(...)):
        data = _validate(payload, require_required=True)
        return repo.create(data).to_dict()

    @r.get("/api/plots/{plot_id}")
    def get_plot(plot_id: str):
        p = repo.get(plot_id)
        if p is None:
            raise HTTPException(404, "地块不存在")
        return p.to_dict()

    @r.put("/api/plots/{plot_id}")
    def update_plot(plot_id: str, payload: dict = Body(...)):
        data = _validate(payload, require_required=False)
        p = repo.update(plot_id, data)
        if p is None:
            raise HTTPException(404, "地块不存在")
        return p.to_dict()

    @r.delete("/api/plots/{plot_id}")
    def delete_plot(plot_id: str):
        if not repo.delete(plot_id):
            raise HTTPException(404, "地块不存在")
        return {"ok": True}

    app.include_router(r)
