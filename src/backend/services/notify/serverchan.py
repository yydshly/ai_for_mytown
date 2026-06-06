"""Server酱（方糖）推送通道。

父母在微信关注「方糖」服务号后，用 SendKey 即可把消息推到他们微信。
是老人场景下最省事的推送方式（无需自建公众号/App 推送）。

接口：POST https://sctapi.ftqq.com/<sendkey>.send  body: title, desp
配置：notify.serverchan.sendkey（支持 ${SERVERCHAN_KEY}）
"""
from __future__ import annotations

import logging

import httpx

from .base import NotifyChannel

log = logging.getLogger("notify.serverchan")


class ServerChanChannel(NotifyChannel):
    name = "serverchan"

    def __init__(self, config: dict):
        self.sendkey = (config.get("sendkey") or "").strip()

    def configured(self) -> bool:
        return bool(self.sendkey) and not self.sendkey.startswith("PASTE_")

    async def send(self, title: str, body: str) -> bool:
        if not self.configured():
            log.warning("serverchan 未配置 sendkey，跳过推送")
            return False
        url = f"https://sctapi.ftqq.com/{self.sendkey}.send"
        try:
            async with httpx.AsyncClient(timeout=15) as cli:
                r = await cli.post(url, data={"title": title[:32], "desp": body[:2000]})
                ok = r.status_code == 200 and (r.json().get("code") == 0)
                if not ok:
                    log.warning("serverchan 推送失败: %s %s", r.status_code, r.text[:200])
                return ok
        except Exception as e:
            log.warning("serverchan 推送异常: %s", e)
            return False
