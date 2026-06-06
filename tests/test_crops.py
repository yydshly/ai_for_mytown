def test_registry_lists_enabled(crops):
    ids = {c.id for c in crops.list()}
    assert {"peach", "apple"} <= ids


def test_default_crop(crops):
    assert crops.default_id == "peach"


def test_resolve_valid(crops):
    assert crops.resolve("apple") == "apple"


def test_resolve_invalid_falls_back(crops):
    # 非法/空 → 默认作物，下游永远拿到合法 crop_id
    assert crops.resolve("banana") == "peach"
    assert crops.resolve(None) == "peach"
    assert crops.resolve("") == "peach"


def test_knowledge_paths(crops):
    b = crops.knowledge("apple")
    assert b.crop_id == "apple"
    assert b.phenology_path.name == "phenology.json"
    assert b.dir.name == "apple"
    assert b.pests_path.exists()
    assert b.playbooks_path.exists()
