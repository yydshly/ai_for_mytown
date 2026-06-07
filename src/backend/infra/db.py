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
        owner_id      TEXT DEFAULT '',
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
    """
    CREATE TABLE IF NOT EXISTS activity_logs (
        id         TEXT PRIMARY KEY,
        plot_id    TEXT NOT NULL REFERENCES plots(id) ON DELETE CASCADE,
        date       TEXT NOT NULL,
        category   TEXT NOT NULL,
        title      TEXT NOT NULL,
        detail     TEXT DEFAULT '',
        created_at TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_logs_plot ON activity_logs(plot_id, date)",
    """
    CREATE TABLE IF NOT EXISTS notifications_sent (
        id         TEXT PRIMARY KEY,
        plot_id    TEXT NOT NULL,
        alert_kind TEXT NOT NULL,
        date       TEXT NOT NULL,
        created_at TEXT NOT NULL,
        UNIQUE(plot_id, alert_kind, date)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS contacts (
        id         TEXT PRIMARY KEY,
        owner_id   TEXT DEFAULT '',
        name       TEXT NOT NULL,
        role       TEXT DEFAULT '其他',
        phone      TEXT NOT NULL,
        note       TEXT DEFAULT '',
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ledger_entries (
        id         TEXT PRIMARY KEY,
        plot_id    TEXT NOT NULL REFERENCES plots(id) ON DELETE CASCADE,
        date       TEXT NOT NULL,
        kind       TEXT NOT NULL,            -- income | expense
        category   TEXT DEFAULT '',
        amount     REAL NOT NULL,            -- 元
        note       TEXT DEFAULT '',
        created_at TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_ledger_plot ON ledger_entries(plot_id, date)",
    """
    CREATE TABLE IF NOT EXISTS users (
        id           TEXT PRIMARY KEY,
        username     TEXT NOT NULL UNIQUE,
        display_name TEXT DEFAULT '',
        pwd_hash     TEXT NOT NULL,
        salt         TEXT NOT NULL,
        is_admin     INTEGER DEFAULT 0,
        created_at   TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sessions (
        token      TEXT PRIMARY KEY,
        user_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ai_interactions (
        id             TEXT PRIMARY KEY,
        user_id        TEXT DEFAULT '',
        kind           TEXT NOT NULL,            -- diagnose | chat
        crop           TEXT DEFAULT '',
        plot_id        TEXT DEFAULT '',
        summary        TEXT DEFAULT '',          -- 用户问题/补充（截断）
        result_summary TEXT DEFAULT '',          -- AI 回答（截断）
        feedback       TEXT DEFAULT '',          -- '' | good | bad
        created_at     TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_ai_fb ON ai_interactions(feedback, created_at)",
    """
    CREATE TABLE IF NOT EXISTS corpus_chunks (
        id         TEXT PRIMARY KEY,
        crop       TEXT DEFAULT '',
        source     TEXT DEFAULT '',
        text       TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_corpus_crop ON corpus_chunks(crop)",
    """
    CREATE TABLE IF NOT EXISTS pest_images (
        id         TEXT PRIMARY KEY,
        crop       TEXT DEFAULT '',
        pest_id    TEXT NOT NULL,
        filename   TEXT NOT NULL,
        caption    TEXT DEFAULT '',
        created_at TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_pestimg ON pest_images(crop, pest_id)",
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
            # 向后兼容：已存在的旧库补列（新库 CREATE 已含，ALTER 重复→忽略）
            for table in ("plots", "contacts"):
                try:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN owner_id TEXT DEFAULT ''")
                except Exception:
                    pass
            try:
                conn.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
            except Exception:
                pass
