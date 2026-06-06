"""通讯录（F4）REST 路由。

GET    /api/contacts        列出
POST   /api/contacts        新建 {name, phone, role?, note?}
PUT    /api/contacts/{id}   更新
DELETE /api/contacts/{id}   删除
GET    /api/contact-roles   角色选项
"""
from fastapi import APIRouter, Body, HTTPException

from ..domain.contact import ROLES
from ..repositories.contact_repository import ContactRepository

_ALLOWED = {"name", "phone", "role", "note"}


def register(app, ctx) -> None:
    r = APIRouter()
    repo = ContactRepository(ctx.db)

    def _clean(data: dict, *, require: bool) -> dict:
        c = {k: v for k, v in data.items() if k in _ALLOWED}
        if require:
            if not (c.get("name") or "").strip():
                raise HTTPException(400, "请填联系人姓名")
            if not (c.get("phone") or "").strip():
                raise HTTPException(400, "请填电话号码")
        if "role" in c and c["role"] and c["role"] not in ROLES:
            c["role"] = "其他"
        return c

    @r.get("/api/contact-roles")
    def roles():
        return {"roles": ROLES}

    @r.get("/api/contacts")
    def list_contacts():
        return {"contacts": [c.to_dict() for c in repo.list()]}

    @r.post("/api/contacts")
    def create_contact(payload: dict = Body(...)):
        return repo.create(_clean(payload, require=True)).to_dict()

    @r.put("/api/contacts/{contact_id}")
    def update_contact(contact_id: str, payload: dict = Body(...)):
        c = repo.update(contact_id, _clean(payload, require=False))
        if c is None:
            raise HTTPException(404, "联系人不存在")
        return c.to_dict()

    @r.delete("/api/contacts/{contact_id}")
    def delete_contact(contact_id: str):
        if not repo.delete(contact_id):
            raise HTTPException(404, "联系人不存在")
        return {"ok": True}

    app.include_router(r)
