import asyncio

from src.backend.services.diagnose import diagnose


def test_diagnose_mock_aligns_and_guards(kb_peach):
    res = asyncio.run(diagnose(
        kb=kb_peach, config={}, image_bytes=b"fake", crop_name="桃树", force_mock=True,
    ))
    assert res["mode"] == "mock"
    assert res["candidates"], "mock 应命中知识库条目"
    c = res["candidates"][0]
    # 用药护栏：未审核 → pending，不给药剂
    assert c["pesticide"]["status"] in ("pending", "none")
    assert c["pesticide"]["items"] == []
    # 必带免责声明
    assert "仅供参考" in res["disclaimer"]
    # 病害条目带农业防治
    assert c["cultural_control"]


def test_diagnose_unconfigured_degrades(kb_peach):
    # 无 vision provider 且非 mock → 优雅降级，不抛异常
    res = asyncio.run(diagnose(
        kb=kb_peach, config={"ai": {}}, image_bytes=b"fake", crop_name="桃树", force_mock=False,
    ))
    assert res["mode"] in ("unconfigured", "error")
    assert res["candidates"] == []
    assert res["disclaimer"]
