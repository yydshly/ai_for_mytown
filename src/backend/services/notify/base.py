"""推送通道抽象。所有通道实现 send()，返回是否成功。

新增通道：实现 NotifyChannel 子类 + 在 factory._REGISTRY 注册。
"""
from __future__ import annotations

import re


class NotifyChannel:
    name = "base"

    async def send(self, title: str, body: str) -> bool:  # pragma: no cover
        raise NotImplementedError

    def configured(self) -> bool:
        return True


_ENV_RE = re.compile(r"\$\{([A-Z_][A-Z0-9_]*)\}")


def expand_env(value):
    """与 ai.base.expand_env 一致：展开 ${VAR}，让 config 不写死密钥。"""
    import os

    if isinstance(value, str):
        return _ENV_RE.sub(lambda m: os.environ.get(m.group(1), ""), value)
    if isinstance(value, dict):
        return {k: expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [expand_env(v) for v in value]
    return value
