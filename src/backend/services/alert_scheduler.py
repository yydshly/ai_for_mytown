"""灾害预警的主动巡检与推送（F1）。

run_alert_check：遍历所有地块 → 按地块作物/位置评估灾害 → 对新出现的
severe/warning 预警，经去重后推送给父母（通道见 services/notify）。

AlertScheduler：用 APScheduler 在配置的时间点（默认 6/12/18 时）定时跑 run_alert_check，
随应用生命周期启停。漏报=绝收，故走硬规则（见 alerts.py），不依赖 LLM。
"""
from __future__ import annotations

import logging
from datetime import date

from ..repositories.notification_repository import NotificationRepository
from ..repositories.plot_repository import PlotRepository
from .alerts import evaluate_alerts
from .notify.factory import build_channel
from .phenology import current_stage, load_stages
from .weather import WeatherClient

log = logging.getLogger("services.alert_scheduler")

# 只推送达到此严重度的预警（info 不打扰父母）
_PUSH_SEVERITIES = {"severe", "warning"}


async def run_alert_check(ctx, *, scenario: str | None = None, force: bool = False) -> dict:
    """巡检所有地块并推送新预警。返回本次动作明细（供手动触发/调试查看）。
    force=True 时忽略去重（用于测试）。"""
    weather = WeatherClient(ctx.config)
    channel = build_channel(ctx.config)
    plots_repo = PlotRepository(ctx.db)
    notif_repo = NotificationRepository(ctx.db)
    today = date.today().isoformat()

    plots = plots_repo.list_all()
    results: list[dict] = []

    for plot in plots:
        wv = await weather.get(scenario, lat=plot.lat, lon=plot.lon)
        stages = load_stages(ctx.crops.knowledge(plot.crop).phenology_path)
        cur = current_stage(stages, date.today())
        stage_key = cur.key if cur else ""
        alerts = evaluate_alerts(wv, stage_key, ctx.crops.knowledge(plot.crop).playbooks_path)

        for a in alerts:
            if a["severity"] not in _PUSH_SEVERITIES:
                continue
            if not force and notif_repo.was_sent(plot.id, a["kind"], today):
                results.append({"plot": plot.name, "kind": a["kind"], "action": "skip-deduped"})
                continue
            title = f"【{plot.name}】{a['name']}预警"
            before = "；".join(a["measures"].get("before") or [])
            body = f"{a['reason']}。{a['threat']}\n应对：{before}"
            ok = await channel.send(title, body)
            if ok:
                notif_repo.mark_sent(plot.id, a["kind"], today)
            results.append({
                "plot": plot.name, "kind": a["kind"], "severity": a["severity"],
                "action": "sent" if ok else "send-failed", "channel": channel.name,
            })

    return {"checked_plots": len(plots), "channel": channel.name, "results": results}


class AlertScheduler:
    def __init__(self, ctx):
        self.ctx = ctx
        self._scheduler = None

    def start(self) -> None:
        hours = (self.ctx.config.get("notify") or {}).get("schedule_hours") or [6, 12, 18]
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.cron import CronTrigger
        except Exception as e:
            log.warning("APScheduler 不可用，定时推送未启用: %s", e)
            return

        import asyncio

        def _job():
            try:
                asyncio.run(run_alert_check(self.ctx))
            except Exception as e:
                log.warning("定时预警巡检失败: %s", e)

        sched = BackgroundScheduler(timezone="Asia/Shanghai")
        for h in hours:
            sched.add_job(_job, CronTrigger(hour=int(h), minute=0), id=f"alert_check_{h}")
        sched.start()
        self._scheduler = sched
        log.info("预警定时推送已启用，时间点: %s 时", hours)

    def stop(self) -> None:
        if self._scheduler is not None:
            self._scheduler.shutdown(wait=False)
            self._scheduler = None
