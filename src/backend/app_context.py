"""AppContext 装配：集中持有路径、配置和（未来的）AI provider 句柄。

路由通过 ctx.xxx 访问运行期资源，避免把全局散落到各模块。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .infra.safeio import read_json


@dataclass
class AppContext:
    project_root: Path
    config: dict[str, Any] = field(default_factory=dict)

    # 路径
    data_dir: Path = field(init=False)
    knowledge_dir: Path = field(init=False)
    phenology_path: Path = field(init=False)
    calendar_path: Path = field(init=False)
    log_dir: Path = field(init=False)

    # 占位 — Phase 2+ 才装配
    ai_text_provider: Any = None
    ai_vision_provider: Any = None
    ai_tts_provider: Any = None

    def __post_init__(self):
        self.data_dir = self.project_root / "data"
        self.knowledge_dir = self.data_dir / "knowledge"
        self.phenology_path = self.knowledge_dir / "peach_phenology.json"
        self.calendar_path = self.knowledge_dir / "peach_calendar.json"
        self.log_dir = self.project_root / "logs"


def build_context(project_root: Path) -> AppContext:
    config_path = project_root / "config" / "config.json"
    example_path = project_root / "config" / "config.example.json"

    if config_path.exists():
        cfg = read_json(config_path) or {}
    else:
        # 开发期：config.json 缺失时回退到 example，方便冒烟（不含真实 key）
        cfg = read_json(example_path) or {}

    return AppContext(project_root=project_root, config=cfg)
