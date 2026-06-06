"""SQLite 持久化基础设施（ADR-002）。

设计取向（家庭级小并发）：
- 每次操作开一个独立连接（with 自动关闭），彻底避开多线程共享连接的坑。
- schema 通过 _MIGRATIONS 顺序声明；启动时幂等执行（IF NOT EXISTS）。
- Row 工厂返回类字典行，便于映射到 domain。

repositories/ 层基于本模块做数据访问；routes/services 不直接写 SQL。
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

# 顺序声明的建表/迁移语句，幂等。新增表/列时在末尾追加。
_MIGRATIONS: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS plots (
        id            TEXT PRIMARY KEY,
        name          TEXT NOT NULL,
        crop          TEXT NOT NULL,
        variety       TEXT DEFAULT '',
        lat           REAL,
        lon           REAL,
        location_name TEXT DEFAULT '',
        area_mu       REAL,
        notes         TEXT DEFAULT '',
        created_at    TEXT NOT NULL,
        updated_at    TEXT NOT NULL
    )
    """,
]


class Database:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(str(self.path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_schema(self) -> None:
        with self.connect() as conn:
            for stmt in _MIGRATIONS:
                conn.executescript(stmt)
