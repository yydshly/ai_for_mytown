"""农事日志（D2）领域模型。

按地块记录每次农事操作（施肥/打药/修剪…），是"建议→执行→记录→复盘"闭环
与知识沉淀（L3）的数据来源，也为安全间隔期计算提供历史。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

# 农事类别（前端下拉用同一套）
CATEGORIES = ["施肥", "打药", "修剪", "疏花疏果", "套袋", "灌溉", "采收", "巡园", "其他"]


@dataclass
class ActivityLog:
    id: str
    plot_id: str
    date: str            # YYYY-MM-DD
    category: str
    title: str
    detail: str = ""
    created_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_row(row) -> "ActivityLog":
        return ActivityLog(
            id=row["id"],
            plot_id=row["plot_id"],
            date=row["date"],
            category=row["category"],
            title=row["title"],
            detail=row["detail"] or "",
            created_at=row["created_at"],
        )
