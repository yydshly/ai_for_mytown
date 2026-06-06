from datetime import date

from src.backend.services.phenology import current_stage, load_stages, neighbors


def _stages(crops):
    return load_stages(crops.knowledge("peach").phenology_path)


def test_load_stages_nonempty(crops):
    stages = _stages(crops)
    assert len(stages) == 8
    assert {s.key for s in stages} >= {"flowering", "fruit_expansion", "dormancy"}


def test_current_stage_midyear(crops):
    # 6 月初桃为果实膨大期
    cur = current_stage(_stages(crops), date(2026, 6, 6))
    assert cur is not None and cur.key == "fruit_expansion"


def test_current_stage_cross_year_dormancy(crops):
    # 休眠期跨年 12-01 ~ 02-15：1 月与 12 月都应命中
    stages = _stages(crops)
    assert current_stage(stages, date(2026, 1, 10)).key == "dormancy"
    assert current_stage(stages, date(2026, 12, 20)).key == "dormancy"


def test_neighbors_wrap(crops):
    stages = _stages(crops)
    cur = current_stage(stages, date(2026, 6, 6))  # fruit_expansion
    prev_s, next_s = neighbors(stages, cur)
    assert prev_s.key == "young_fruit"
    assert next_s.key == "harvest"


def test_apple_differs_from_peach(crops):
    # 同一天，苹果应为幼果期（与桃的膨大期不同）—— 多作物隔离验证
    apple = current_stage(load_stages(crops.knowledge("apple").phenology_path), date(2026, 6, 6))
    assert apple.key == "young_fruit"
