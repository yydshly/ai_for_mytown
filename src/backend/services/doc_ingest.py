"""文档资料灌入（RAG 语料）。

把 data/corpus/<crop>/ 下的 .md/.txt 切成段落块，写入 corpus_chunks。
<crop> 取目录名（如 peach/apple）；放在 corpus 根目录(不分作物)的归为通用('')。

用户拿到真实《技术规程》《病虫情报》，丢进对应文件夹再 ingest 即可提升准确率。
PDF 暂不在此解析（可先转 txt/md）——保持零额外依赖。
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

from ..repositories.corpus_repository import CorpusRepository

log = logging.getLogger("services.doc_ingest")

_MIN_CHUNK = 30
_MAX_CHUNK = 600


def _chunk(text: str) -> list[str]:
    # 先按空行分段，过长的再按句号切
    paras = re.split(r"\n\s*\n", text)
    out: list[str] = []
    for p in paras:
        p = re.sub(r"\s+", " ", p).strip()
        if len(p) < _MIN_CHUNK:
            continue
        if len(p) <= _MAX_CHUNK:
            out.append(p)
        else:
            buf = ""
            for sent in re.split(r"(?<=[。！；])", p):
                if len(buf) + len(sent) > _MAX_CHUNK and buf:
                    out.append(buf.strip())
                    buf = ""
                buf += sent
            if buf.strip():
                out.append(buf.strip())
    return out


def ingest_dir(repo: CorpusRepository, corpus_dir: Path) -> dict:
    """重新灌入整个 corpus 目录（按作物先清后灌，幂等）。返回统计。"""
    if not corpus_dir.exists():
        return {"crops": {}, "total": 0}
    stats: dict[str, int] = {}
    # 先收集每个作物的文件
    crops: dict[str, list[Path]] = {}
    for fp in corpus_dir.rglob("*"):
        if fp.suffix.lower() not in (".md", ".txt"):
            continue
        rel = fp.relative_to(corpus_dir)
        crop = rel.parts[0] if len(rel.parts) > 1 else ""
        crops.setdefault(crop, []).append(fp)

    for crop, files in crops.items():
        repo.clear_crop(crop)
        n = 0
        for fp in files:
            try:
                text = fp.read_text(encoding="utf-8")
            except Exception as e:
                log.warning("读取失败 %s: %s", fp, e)
                continue
            for ch in _chunk(text):
                repo.add_chunk(crop, fp.stem, ch)
                n += 1
        stats[crop or "通用"] = n
    total = sum(stats.values())
    log.info("资料灌入完成：%s（共 %d 段）", stats, total)
    return {"crops": stats, "total": total}


def auto_ingest_if_empty(repo: CorpusRepository, corpus_dir: Path) -> None:
    """启动时若语料为空，自动灌入种子文档（开箱即用）。"""
    if repo.count() == 0:
        ingest_dir(repo, corpus_dir)
