"""用户领域模型（产品化多用户地基）。

对外永远不暴露 pwd_hash/salt（to_public 用于响应）。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class User:
    id: str
    username: str
    display_name: str
    pwd_hash: str
    salt: str
    created_at: str

    def to_public(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "display_name": self.display_name or self.username,
            "created_at": self.created_at,
        }

    @staticmethod
    def from_row(row) -> "User":
        return User(
            id=row["id"],
            username=row["username"],
            display_name=row["display_name"] or "",
            pwd_hash=row["pwd_hash"],
            salt=row["salt"],
            created_at=row["created_at"],
        )
