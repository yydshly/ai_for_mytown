"""认证路由（产品化多用户地基）。

POST /api/auth/register {username, password, display_name?}  → {user, token}
POST /api/auth/login    {username, password}                 → {user, token}
GET  /api/auth/me        (Authorization: Bearer <token>)      → {user} 或 401
POST /api/auth/logout    (Authorization: Bearer <token>)

前端拿到 token 后，后续请求带 Authorization 头。当前为加法式接入，
不破坏既有接口；Phase 17 再给各实体加 owner 做数据隔离。
"""
from fastapi import APIRouter, Body, Header, HTTPException

from ..services.auth_service import AuthError


def _token(authorization: str | None) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


def register(app, ctx) -> None:
    r = APIRouter()
    auth = ctx.auth

    @r.post("/api/auth/register")
    def do_register(payload: dict = Body(...)):
        try:
            user, token = auth.register(
                payload.get("username", ""), payload.get("password", ""),
                payload.get("display_name", ""),
            )
        except AuthError as e:
            raise HTTPException(400, str(e))
        return {"user": user.to_public(), "token": token}

    @r.post("/api/auth/login")
    def do_login(payload: dict = Body(...)):
        try:
            user, token = auth.login(payload.get("username", ""), payload.get("password", ""))
        except AuthError as e:
            raise HTTPException(401, str(e))
        return {"user": user.to_public(), "token": token}

    @r.get("/api/auth/me")
    def me(authorization: str | None = Header(None)):
        user = auth.user_by_token(_token(authorization))
        if user is None:
            raise HTTPException(401, "未登录")
        return {"user": user.to_public()}

    @r.post("/api/auth/logout")
    def logout(authorization: str | None = Header(None)):
        auth.logout(_token(authorization))
        return {"ok": True}

    app.include_router(r)
