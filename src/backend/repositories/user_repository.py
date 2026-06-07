"""用户 + 会话数据访问层。SQL 仅在此出现。"""
from __future__ import annotations

from datetime import datetime, timezone

from ..domain.user import User
from ..infra.db import Database

_COLUMNS = "id, username, display_name, pwd_hash, salt, is_admin, created_at"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class UserRepository:
    def __init__(self, db: Database):
        self.db = db

    # ---- users ----

    def get_by_username(self, username: str) -> User | None:
        with self.db.connect() as conn:
            row = conn.execute(
                f"SELECT {_COLUMNS} FROM users WHERE username = ?", (username,)
            ).fetchone()
        return User.from_row(row) if row else None

    def get_by_id(self, user_id: str) -> User | None:
        with self.db.connect() as conn:
            row = conn.execute(
                f"SELECT {_COLUMNS} FROM users WHERE id = ?", (user_id,)
            ).fetchone()
        return User.from_row(row) if row else None

    def insert(self, user: User) -> None:
        row = dict(user.__dict__)
        row["is_admin"] = 1 if user.is_admin else 0
        with self.db.connect() as conn:
            conn.execute(
                f"INSERT INTO users ({_COLUMNS}) VALUES "
                "(:id,:username,:display_name,:pwd_hash,:salt,:is_admin,:created_at)",
                row,
            )

    def count(self) -> int:
        with self.db.connect() as conn:
            return conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]

    # ---- sessions ----

    def create_session(self, token: str, user_id: str) -> None:
        with self.db.connect() as conn:
            conn.execute(
                "INSERT INTO sessions (token, user_id, created_at) VALUES (?,?,?)",
                (token, user_id, _now()),
            )

    def user_id_by_token(self, token: str) -> str | None:
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT user_id FROM sessions WHERE token = ?", (token,)
            ).fetchone()
        return row["user_id"] if row else None

    def delete_session(self, token: str) -> None:
        with self.db.connect() as conn:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
