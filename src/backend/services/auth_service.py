"""认证服务（产品化多用户地基）。

口令用 pbkdf2_hmac(sha256) 加盐哈希（stdlib，无外部依赖）；会话用随机 token。
身份方式与业务解耦：日后接微信登录，只需在此新增一种 issue-token 入口，业务无需改。

注意（MVP）：pbkdf2 迭代数适中即可；上规模/高安全可换 argon2。
"""
from __future__ import annotations

import hashlib
import secrets
import uuid

from ..domain.user import User
from ..repositories.user_repository import UserRepository

_ITER = 120_000


class AuthError(Exception):
    """注册/登录失败（用户名占用、口令错误等）。"""


def _hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                               bytes.fromhex(salt), _ITER).hex()


class AuthService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    def register(self, username: str, password: str, display_name: str = "") -> tuple[User, str]:
        username = (username or "").strip()
        if len(username) < 2:
            raise AuthError("用户名至少 2 个字符")
        if len(password or "") < 4:
            raise AuthError("密码至少 4 位")
        if self.repo.get_by_username(username):
            raise AuthError("该用户名已被占用")
        salt = secrets.token_bytes(16).hex()
        from datetime import datetime, timezone
        user = User(
            id=uuid.uuid4().hex[:12],
            username=username,
            display_name=(display_name or "").strip() or username,
            pwd_hash=_hash(password, salt),
            salt=salt,
            created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )
        self.repo.insert(user)
        return user, self._issue_token(user.id)

    def login(self, username: str, password: str) -> tuple[User, str]:
        user = self.repo.get_by_username((username or "").strip())
        if user is None or _hash(password or "", user.salt) != user.pwd_hash:
            raise AuthError("用户名或密码不对")
        return user, self._issue_token(user.id)

    def _issue_token(self, user_id: str) -> str:
        token = secrets.token_urlsafe(32)
        self.repo.create_session(token, user_id)
        return token

    def user_by_token(self, token: str | None) -> User | None:
        if not token:
            return None
        uid = self.repo.user_id_by_token(token)
        return self.repo.get_by_id(uid) if uid else None

    def logout(self, token: str | None) -> None:
        if token:
            self.repo.delete_session(token)
