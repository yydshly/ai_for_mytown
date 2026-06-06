"""pytest 公共夹具。

- project_root：仓库根
- knowledge_dir：真实知识目录（用于 crops/KB/alerts 等纯逻辑测试）
- crops / kb_peach / kb_apple：注册表与按作物知识库
- temp_db：tmp_path 下的独立 SQLite（仓储测试不碰真实数据）

异步函数用 asyncio.run 直接跑，避免引入 pytest-asyncio。
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.backend.domain.crops import CropRegistry  # noqa: E402
from src.backend.infra.db import Database  # noqa: E402
from src.backend.services.knowledge_manager import KnowledgeManager  # noqa: E402


@pytest.fixture(scope="session")
def project_root() -> Path:
    return ROOT


@pytest.fixture(scope="session")
def knowledge_dir(project_root) -> Path:
    return project_root / "data" / "knowledge"


@pytest.fixture()
def crops(knowledge_dir) -> CropRegistry:
    return CropRegistry(knowledge_dir)


@pytest.fixture()
def knowledge(crops) -> KnowledgeManager:
    return KnowledgeManager(crops)


@pytest.fixture()
def kb_peach(knowledge):
    return knowledge.kb("peach")


@pytest.fixture()
def kb_apple(knowledge):
    return knowledge.kb("apple")


@pytest.fixture()
def temp_db(tmp_path) -> Database:
    db = Database(tmp_path / "test.db")
    db.init_schema()
    return db
