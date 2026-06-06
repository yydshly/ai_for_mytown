def test_retrieve_ranks_relevant_first(kb_peach):
    # “叶子卷曲发红增厚” 应命中缩叶病为首
    hits = kb_peach.retrieve("叶子卷曲发红增厚", k=3)
    assert hits, "应有检索结果"
    assert hits[0].name == "桃缩叶病"


def test_find_mentions_aligns_text(kb_peach):
    matches = kb_peach.find_mentions("最可能：桃褐腐病（可能性：高）")
    assert any(m.name == "桃褐腐病" for m in matches)


def test_all_names_and_sample(kb_peach):
    names = kb_peach.all_names()
    assert "桃缩叶病" in names and len(names) == 6
    assert kb_peach.sample_disease_name() in names


def test_pesticide_guardrail_pending(kb_peach):
    # 用药表全 verified=false → 不给药剂，导向农技员
    info = kb_peach.pesticide_for("桃褐腐病")
    assert info.status == "pending"
    assert info.items == []
    assert "农技员" in info.note


def test_pesticide_unknown_target(kb_peach):
    info = kb_peach.pesticide_for("不存在的病")
    assert info.status == "none"
    assert info.items == []


def test_apple_kb_isolated(kb_apple):
    # 苹果库只含苹果条目（按作物隔离）
    names = kb_apple.all_names()
    assert "苹果树腐烂病" in names
    assert all("桃" not in n for n in names)


def test_list_all_for_library(kb_peach):
    # 图鉴用：返回全部条目及展示字段
    items = kb_peach.list_all()
    assert len(items) == 6
    first = items[0]
    for key in ("name", "type", "symptoms", "identify_cues", "cultural_control", "source"):
        assert key in first
    assert any(i["type"] == "disease" for i in items)
    assert any(i["type"] == "pest" for i in items)
