"""鉴权依赖工厂。

各受保护路由用 Depends(make_current_user(ctx)) 拿当前用户；未登录 401。
required=False 时未登录返回 None（用于可匿名但登录后增强的接口，如诊断/问答）。
"""
from fastapi import Header, HTTPException


def _token(authorization: str | None) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


def make_current_user(ctx, *, required: bool = True):
    def dep(authorization: str | None = Header(None)):
        user = ctx.auth.user_by_token(_token(authorization))
        if user is None and required:
            raise HTTPException(401, "请先登录")
        return user

    return dep
