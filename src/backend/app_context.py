"""AppContext 装配：集中持有路径、配置和（未来的）AI provider 句柄。

路由通过 ctx.xxx 访问运行期资源，避免把全局散落到各模块。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .domain.crops import CropRegistry
from .infra.db import Database
from .infra.safeio import read_json
from .repositories.user_repository import UserRepository
from .services.auth_service import AuthService
from .services.knowledge_manager import KnowledgeManager


@dataclass
class AppContext:
    project_root: Path
    config: dict[str, Any] = field(default_factory=dict)

    # 路径
    data_dir: Path = field(init=False)
    knowledge_dir: Path = field(init=False)
    log_dir: Path = field(init=False)

    # 多作物：注册表 + 按作物知识管理（路由通过 ?crop= 解析）
    crops: CropRegistry = field(init=False)
    knowledge: KnowledgeManager = field(init=False)

    # 持久化（地块、农事日志等）
    db: Database = field(init=False)
    # 认证（多用户地基）
    auth: AuthService = field(init=False)

    def __post_init__(self):
        self.data_dir = self.project_root / "data"
        self.knowledge_dir = self.data_dir / "knowledge"
        self.log_dir = self.project_root / "logs"
        self.crops = CropRegistry(self.knowledge_dir)
        self.knowledge = KnowledgeManager(self.crops)
        self.db = Database(self.data_dir / "app.db")
        self.db.init_schema()
        self.auth = AuthService(UserRepository(self.db))


def build_context(project_root: Path) -> AppContext:
    config_path = project_root / "config" / "config.json"
    example_path = project_root / "config" / "config.example.json"

    if config_path.exists():
        cfg = read_json(config_path) or {}
    else:
        # 开发期：config.json 缺失时回退到 example，方便冒烟（不含真实 key）
        cfg = read_json(example_path) or {}

    return AppContext(project_root=project_root, config=cfg)
