import asyncio

from src.backend.services.alerts import evaluate_alerts
from src.backend.services.weather import WeatherClient


def _weather(scenario):
    return asyncio.run(WeatherClient({}).get(scenario))


def _playbooks(crops, crop="peach"):
    return crops.knowledge(crop).playbooks_path


def test_none_scenario_no_alerts(crops):
    al = evaluate_alerts(_weather("none"), "fruit_expansion", _playbooks(crops))
    assert al == []


def test_frost_severe_in_flowering(crops):
    # 花期霜冻 = severe
    al = evaluate_alerts(_weather("frost"), "flowering", _playbooks(crops))
    assert al and al[0]["kind"] == "frost" and al[0]["severity"] == "severe"


def test_frost_info_in_fruit_expansion(crops):
    # 膨大期非霜冻敏感期 → 降级 info
    al = evaluate_alerts(_weather("frost"), "fruit_expansion", _playbooks(crops))
    assert al and al[0]["kind"] == "frost" and al[0]["severity"] == "info"


def test_hail_always_severe(crops):
    al = evaluate_alerts(_weather("hail"), "fruit_expansion", _playbooks(crops))
    assert any(a["kind"] == "hail" and a["severity"] == "severe" for a in al)


def test_alert_carries_measures(crops):
    al = evaluate_alerts(_weather("hail"), "fruit_expansion", _playbooks(crops))
    hail = next(a for a in al if a["kind"] == "hail")
    assert hail["measures"]["before"], "应带应对措施"
    assert hail["threat"]


def test_weather_mock_scenarios():
    assert _weather("frost").night_min_temp <= 2
    assert _weather("heat").max_temp >= 35
    assert "冰雹" in _weather("hail").hazards
