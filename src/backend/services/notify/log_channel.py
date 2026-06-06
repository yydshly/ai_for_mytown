"""日志通道：把推送内容写日志。默认/兜底通道，无需任何密钥，永远可用。
用于本地联调和"未配置真实通道时也不报错"。"""
from __future__ import annotations

import logging

from .base import NotifyChannel

log = logging.getLogger("notify.log")


class LogChannel(NotifyChannel):
    name = "log"

    def __init__(self, config: dict | None = None):
        self.config = config or {}

    async def send(self, title: str, body: str) -> bool:
        log.info("[模拟推送] %s | %s", title, body)
        return True
