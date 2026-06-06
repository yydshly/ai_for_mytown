"""TTS 语音合成服务（带磁盘缓存）。

老人产品里，"听"是核心交互（R-04 适老化）。每条建议/诊断都可能被反复朗读，
TTS 调用有成本（R-06），所以按文本+音色+模型做磁盘缓存，命中即秒回。

对 tts provider 未配置/出错都优雅降级（返回 None，路由据此回 503/友好提示）。
"""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from ...ai.base import Capability, ProviderConfigError
from ...ai.factory import make_provider

log = logging.getLogger("services.tts")

_EXT = {"audio/wav": "wav", "audio/mpeg": "mp3", "audio/ogg": "ogg"}


class TTSService:
    def __init__(self, config: dict, cache_dir: Path):
        self.config = config
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._provider = None
        self._tried = False

    def _get_provider(self):
        if self._tried:
            return self._provider
        self._tried = True
        ai_cfg = self.config.get("ai") or {}
        name = ai_cfg.get("tts_provider")
        if not name:
            return None
        try:
            p = make_provider(name, ai_cfg)
        except ProviderConfigError as e:
            log.info("tts provider 未配置: %s", e)
            return None
        if not p.supports(Capability.TTS):
            log.info("provider %s 不支持 tts", name)
            return None
        self._provider = p
        return p

    def available(self) -> bool:
        return self._get_provider() is not None

    def _key(self, text: str, voice: str) -> str:
        p = self._get_provider()
        model = getattr(p, "tts_model", "") if p else ""
        raw = f"{model}|{voice}|{text}".encode("utf-8")
        return hashlib.sha1(raw).hexdigest()

    def _cache_lookup(self, key: str) -> tuple[bytes, str] | None:
        for mime, ext in _EXT.items():
            fp = self.cache_dir / f"{key}.{ext}"
            if fp.exists():
                return fp.read_bytes(), mime
        return None

    async def synth(self, text: str, voice: str = "") -> tuple[bytes, str] | None:
        """返回 (audio_bytes, mime) 或 None（不可用）。"""
        text = (text or "").strip()
        if not text:
            return None
        p = self._get_provider()
        if p is None:
            return None

        key = self._key(text, voice)
        hit = self._cache_lookup(key)
        if hit:
            return hit

        try:
            audio, mime = await p.tts(text, voice=voice or None)
        except Exception as e:
            log.warning("tts 合成失败: %s", e)
            return None

        ext = _EXT.get(mime, "bin")
        try:
            (self.cache_dir / f"{key}.{ext}").write_bytes(audio)
        except Exception as e:
            log.warning("tts 缓存写入失败（不影响返回）: %s", e)
        return audio, mime
