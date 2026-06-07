from src.backend.repositories.corpus_repository import CorpusRepository
from src.backend.services.doc_ingest import _chunk, ingest_dir


def test_chunking_splits_paragraphs():
    text = (
        "萌芽前应喷一次石硫合剂封园，压低桃缩叶病、红蜘蛛、介壳虫的越冬基数，这是早春清园的关键一步。"
        "\n\n"
        "花期最怕晚霜冻，夜间最低气温接近零度时应提前准备熏烟、喷防霜剂或地面灌水保温，避免花器受冻减产。"
    )
    chunks = _chunk(text)
    assert len(chunks) == 2
    assert all(len(c) >= 30 for c in chunks)


def test_ingest_and_retrieve(temp_db, project_root):
    repo = CorpusRepository(temp_db)
    stats = ingest_dir(repo, project_root / "data" / "corpus")
    assert stats["total"] > 0
    assert repo.count("peach") > 0
    assert repo.count("apple") > 0

    # 按作物隔离 + 相关检索
    hits = repo.retrieve("缩叶病 萌芽 石硫合剂", "peach", k=3)
    assert hits, "应检索到相关资料段"
    assert any("缩叶" in h["text"] or "石硫合剂" in h["text"] for h in hits)


def test_reingest_is_idempotent(temp_db, project_root):
    repo = CorpusRepository(temp_db)
    ingest_dir(repo, project_root / "data" / "corpus")
    n1 = repo.count("peach")
    ingest_dir(repo, project_root / "data" / "corpus")   # 再灌一次
    assert repo.count("peach") == n1   # 先清后灌，不重复累积
