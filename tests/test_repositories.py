import pytest

from src.backend.repositories.activity_log_repository import ActivityLogRepository
from src.backend.repositories.contact_repository import ContactRepository
from src.backend.repositories.ledger_repository import LedgerRepository
from src.backend.repositories.notification_repository import NotificationRepository
from src.backend.repositories.plot_repository import PlotRepository


# ---- 地块 ----

def test_plot_crud(temp_db):
    repo = PlotRepository(temp_db)
    p = repo.create({"name": "测试园", "crop": "apple", "lat": 35.7, "lon": 109.4, "area_mu": 3.5})
    assert p.id and p.crop == "apple"

    assert len(repo.list()) == 1
    assert repo.get(p.id).name == "测试园"

    updated = repo.update(p.id, {"name": "测试园(改)", "area_mu": 4.2})
    assert updated.name == "测试园(改)" and updated.area_mu == 4.2
    assert updated.created_at == p.created_at        # 创建时间保留
    assert updated.updated_at >= p.updated_at        # 更新时间不回退（秒级，可能相等）

    assert repo.delete(p.id) is True
    assert repo.get(p.id) is None
    assert repo.delete("nope") is False


# ---- 农事日志 + 级联 ----

def test_activity_log_order_and_cascade(temp_db):
    plots = PlotRepository(temp_db)
    logs = ActivityLogRepository(temp_db)
    p = plots.create({"name": "园", "crop": "peach"})

    logs.create(p.id, {"date": "2026-06-05", "category": "打药", "title": "防褐腐"})
    logs.create(p.id, {"date": "2026-06-06", "category": "疏花疏果", "title": "疏果"})
    rows = logs.list_by_plot(p.id)
    assert [r.date for r in rows] == ["2026-06-06", "2026-06-05"]  # 倒序

    assert logs.latest_by_category(p.id, "打药").title == "防褐腐"

    # 删除地块 → 日志级联删除（FK ON DELETE CASCADE）
    plots.delete(p.id)
    assert logs.list_by_plot(p.id) == []


# ---- 推送去重 ----

def test_notification_dedup(temp_db):
    repo = NotificationRepository(temp_db)
    assert repo.was_sent("plot1", "frost", "2026-06-06") is False
    repo.mark_sent("plot1", "frost", "2026-06-06")
    assert repo.was_sent("plot1", "frost", "2026-06-06") is True
    # 不同天/不同灾害互不影响
    assert repo.was_sent("plot1", "frost", "2026-06-07") is False
    assert repo.was_sent("plot1", "hail", "2026-06-06") is False
    # 重复 mark 不报错
    repo.mark_sent("plot1", "frost", "2026-06-06")


# ---- 通讯录 ----

def test_contact_crud(temp_db):
    repo = ContactRepository(temp_db)
    c = repo.create({"name": "张技术员", "phone": "13800001111", "role": "农技员", "note": "管苹果"})
    assert c.id and c.role == "农技员"
    assert len(repo.list()) == 1
    updated = repo.update(c.id, {"phone": "13900002222"})
    assert updated.phone == "13900002222" and updated.name == "张技术员"
    assert repo.delete(c.id) is True
    assert repo.get(c.id) is None


# ---- 账本 ----

def test_ledger_summary_and_cascade(temp_db):
    plots = PlotRepository(temp_db)
    ledger = LedgerRepository(temp_db)
    p = plots.create({"name": "园", "crop": "apple"})

    ledger.create(p.id, {"date": "2026-03-01", "kind": "expense", "category": "化肥", "amount": 800})
    ledger.create(p.id, {"date": "2026-06-01", "kind": "expense", "category": "农药", "amount": 200})
    ledger.create(p.id, {"date": "2026-10-01", "kind": "income", "category": "销售", "amount": 5000})

    s = ledger.summary(p.id)
    assert s["total_expense"] == 1000.0
    assert s["total_income"] == 5000.0
    assert s["net"] == 4000.0

    assert len(ledger.list_by_plot(p.id)) == 3
    # 删除地块 → 账本级联删除
    plots.delete(p.id)
    assert ledger.list_by_plot(p.id) == []
