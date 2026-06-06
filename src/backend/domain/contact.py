"""通讯录联系人（F4）领域模型。

老人无障碍兜底：AI 答不出时，一键拨号给农技员/子女/邻居。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

ROLES = ["农技员", "子女", "邻居", "合作社", "其他"]


@dataclass
class Contact:
    id: str
    name: str
    phone: str
    role: str = "其他"
    note: str = ""
    created_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_row(row) -> "Contact":
        return Contact(
            id=row["id"],
            name=row["name"],
            phone=row["phone"],
            role=row["role"] or "其他",
            note=row["note"] or "",
            created_at=row["created_at"],
        )
