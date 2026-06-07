"""资料灌入 CLI。

把 data/corpus/<crop>/ 下的 .md/.txt 灌入 RAG 语料库（重新灌入，幂等）。
用户拿到真实《技术规程》《病虫情报》后，丢进对应作物文件夹，跑一次本脚本即可。

用法（项目根目录）：
    python scripts/ingest_docs.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.backend.app_context import build_context  # noqa: E402
from src.backend.repositories.corpus_repository import CorpusRepository  # noqa: E402
from src.backend.services.doc_ingest import ingest_dir  # noqa: E402


def main():
    ctx = build_context(ROOT)
    repo = CorpusRepository(ctx.db)
    corpus_dir = ROOT / "data" / "corpus"
    print(f"灌入目录：{corpus_dir}")
    stats = ingest_dir(repo, corpus_dir)
    print(f"完成：{stats['crops']}（共 {stats['total']} 段）")
    for crop in ("peach", "apple"):
        print(f"  {crop}: {repo.count(crop)} 段，来源 {repo.sources(crop)}")


if __name__ == "__main__":
    main()
