"""AI 交互审计记录（安全审计 + 反馈 + 成本/用量追踪）。

不存完整图片/长文，只存截断摘要——既够审计，又控隐私与体积。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class Interaction:
    id: str
    user_id: str
    kind: str               # diagnose | chat
    crop: str
    plot_id: str
    summary: str            # 用户问题/补充
    result_summary: str     # AI 回答摘要
    feedback: str           # '' | good | bad
    created_at: str

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_row(row) -> "Interaction":
        return Interaction(
            id=row["id"],
            user_id=row["user_id"] or "",
            kind=row["kind"],
            crop=row["crop"] or "",
            plot_id=row["plot_id"] or "",
            summary=row["summary"] or "",
            result_summary=row["result_summary"] or "",
            feedback=row["feedback"] or "",
            created_at=row["created_at"],
        )
