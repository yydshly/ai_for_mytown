"""推送通道工厂。按 config.notify.channel 选择；未知/未配置回退 log 通道。"""
from __future__ import annotations

import logging

from .base import NotifyChannel, expand_env
from .log_channel import LogChannel
from .serverchan import ServerChanChannel

log = logging.getLogger("notify.factory")

_REGISTRY = {
    "log": LogChannel,
    "serverchan": ServerChanChannel,
}


def build_channel(config: dict) -> NotifyChannel:
    notify_cfg = expand_env(config.get("notify") or {})
    name = notify_cfg.get("channel") or "log"
    cls = _REGISTRY.get(name)
    if cls is None:
        log.warning("未知推送通道 '%s'，回退 log", name)
        return LogChannel()
    sub_cfg = notify_cfg.get(name) or {}
    channel = cls(sub_cfg)
    # 选了真实通道但没配好 → 回退 log，保证不报错（仍会在日志留痕）
    if not channel.configured():
        log.warning("推送通道 '%s' 未配置完整，回退 log 通道", name)
        return LogChannel()
    return channel
