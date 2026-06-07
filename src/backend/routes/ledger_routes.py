"""成本收益账本（D3）REST 路由。

GET    /api/plots/{id}/ledger?year=          列出（按日期倒序）
GET    /api/plots/{id}/ledger/summary?year=  汇总（总投入/总收入/净收益）
POST   /api/plots/{id}/ledger                新建 {date,kind,category?,amount,note?}
DELETE /api/ledger/{entry_id}                删除
GET    /api/ledger-categories                类别选项
"""
from datetime import date as _date

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from ..domain.ledger import EXPENSE_CATEGORIES, INCOME_CATEGORIES, KINDS
from ..infra.auth_dep import make_current_user
from ..repositories.ledger_repository import LedgerRepository
from ..repositories.plot_repository import PlotRepository


def register(app, ctx) -> None:
    r = APIRouter()
    repo = LedgerRepository(ctx.db)
    plots = PlotRepository(ctx.db)
    current_user = make_current_user(ctx)

    @r.get("/api/ledger-categories")
    def categories():
        return {"expense": EXPENSE_CATEGORIES, "income": INCOME_CATEGORIES}

    @r.get("/api/plots/{plot_id}/ledger")
    def list_ledger(plot_id: str, year: str | None = Query(None), user=Depends(current_user)):
        if plots.get(plot_id, user.id) is None:
            raise HTTPException(404, "地块不存在")
        return {"entries": [e.to_dict() for e in repo.list_by_plot(plot_id, year)]}

    @r.get("/api/plots/{plot_id}/ledger/summary")
    def ledger_summary(plot_id: str, year: str | None = Query(None), user=Depends(current_user)):
        if plots.get(plot_id, user.id) is None:
            raise HTTPException(404, "地块不存在")
        return repo.summary(plot_id, year)

    @r.post("/api/plots/{plot_id}/ledger")
    def create_ledger(plot_id: str, payload: dict = Body(...), user=Depends(current_user)):
        if plots.get(plot_id, user.id) is None:
            raise HTTPException(404, "地块不存在")
        kind = (payload.get("kind") or "").strip()
        if kind not in KINDS:
            raise HTTPException(400, "kind 必须是 income 或 expense")
        try:
            amount = float(payload.get("amount"))
        except (TypeError, ValueError):
            raise HTTPException(400, "金额不正确")
        if amount < 0:
            raise HTTPException(400, "金额不能为负")
        data = {
            "date": (payload.get("date") or _date.today().isoformat()).strip(),
            "kind": kind,
            "category": (payload.get("category") or "").strip(),
            "amount": amount,
            "note": (payload.get("note") or "").strip(),
        }
        return repo.create(plot_id, data).to_dict()

    @r.delete("/api/ledger/{entry_id}")
    def delete_ledger(entry_id: str, user=Depends(current_user)):
        if not repo.delete(entry_id, user.id):
            raise HTTPException(404, "记录不存在")
        return {"ok": True}

    app.include_router(r)
