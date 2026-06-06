"""成本收益账本（D3）领域模型。

按地块记录投入与收入，回答果农最关心的问题：这地到底赚不赚钱。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

KINDS = ["expense", "income"]
EXPENSE_CATEGORIES = ["种苗", "化肥", "农药", "套袋", "人工", "水电", "机械", "运输", "其他"]
INCOME_CATEGORIES = ["销售", "补贴", "其他"]


@dataclass
class LedgerEntry:
    id: str
    plot_id: str
    date: str               # YYYY-MM-DD
    kind: str               # expense | income
    category: str = ""
    amount: float = 0.0     # 元
    note: str = ""
    created_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_row(row) -> "LedgerEntry":
        return LedgerEntry(
            id=row["id"],
            plot_id=row["plot_id"],
            date=row["date"],
            kind=row["kind"],
            category=row["category"] or "",
            amount=row["amount"],
            note=row["note"] or "",
            created_at=row["created_at"],
        )
