"""AI 配置自检脚本。

用法（在项目根目录）：
  python scripts/check_ai.py                # 只看配置状态（不发网络请求）
  python scripts/check_ai.py --text         # 真实调一次文字对话
  python scripts/check_ai.py --tts          # 真实合成一句语音，存 D:/tmp 或 ./
  python scripts/check_ai.py --vision 图片路径   # 真实拍照诊断识别

不会打印完整 key（自动掩码）。
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.ai.base import Capability, Message, expand_env  # noqa: E402
from src.ai.factory import make_provider  # noqa: E402
from src.backend.app_context import build_context  # noqa: E402


def mask(key: str) -> str:
    key = (key or "").strip()
    if not key:
        return "（空）"
    if key.startswith("PASTE_"):
        return "（未填写·占位）"
    return f"{key[:4]}***{key[-4:]}" if len(key) > 8 else key[0] + "***"


def show_status(ai_cfg: dict) -> None:
    print("=== AI 配置状态 ===")
    print("active        :", ai_cfg.get("active"))
    print("vision_provider:", ai_cfg.get("vision_provider"))
    print("tts_provider  :", ai_cfg.get("tts_provider"))
    print("- providers -")
    for name, pcfg in (ai_cfg.get("providers") or {}).items():
        key = pcfg.get("api_key", "")
        ready = bool(key) and not key.startswith("PASTE_")
        line = f"  {name:18s} key={mask(key):20s}"
        if ready:
            try:
                p = make_provider(name, ai_cfg)
                line += f" caps={sorted(p.capabilities)}"
            except Exception as e:
                line += f" 构建失败: {e}"
        else:
            line += " （未就绪）"
        print(line)


async def run_text(ai_cfg: dict) -> None:
    name = ai_cfg.get("active")
    print(f"\n=== 文字对话测试（{name}）===")
    p = make_provider(name, ai_cfg)
    msgs = [Message(role="user", content="用一句话说说桃树果实膨大期最该注意什么。")]
    out = ""
    async for d in p.chat(msgs, stream=True, max_tokens=200):
        out += d
        print(d, end="", flush=True)
    print("\n[完成]" if out else "\n[空响应]")


async def run_tts(ai_cfg: dict) -> None:
    name = ai_cfg.get("tts_provider")
    print(f"\n=== TTS 测试（{name}）===")
    p = make_provider(name, ai_cfg)
    audio, mime = await p.tts("桃树进入果实膨大期，记得套袋和防褐腐病。")
    out_dir = Path("D:/tmp") if Path("D:/tmp").exists() else ROOT
    ext = "mp3" if "mpeg" in mime else "wav"
    fp = out_dir / f"tts_test.{ext}"
    fp.write_bytes(audio)
    print(f"已合成 {len(audio)} 字节 -> {fp}（mime={mime}）")


async def run_vision(ai_cfg: dict, img_path: str) -> None:
    name = ai_cfg.get("vision_provider")
    print(f"\n=== 拍照诊断测试（{name}）===")
    p = make_provider(name, ai_cfg)
    if not p.supports(Capability.VISION):
        print("该 provider 未启用 vision（检查 enable_vision 与 models.vision）")
        return
    data = Path(img_path).read_bytes()
    prompt = "你是桃树农技顾问，看这张照片，判断最可能的病虫害并简述依据。"
    res = await p.vision(data, prompt)
    print(res)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", action="store_true")
    ap.add_argument("--tts", action="store_true")
    ap.add_argument("--vision", metavar="IMG", default=None)
    args = ap.parse_args()

    ctx = build_context(ROOT)
    ai_cfg = expand_env(ctx.config.get("ai") or {})
    show_status(ai_cfg)

    try:
        if args.text:
            asyncio.run(run_text(ai_cfg))
        if args.tts:
            asyncio.run(run_tts(ai_cfg))
        if args.vision:
            asyncio.run(run_vision(ai_cfg, args.vision))
    except Exception as e:
        print(f"\n[调用失败] {type(e).__name__}: {e}")
        print("常见原因：key 错误/未激活、模型无权限、网络问题。")


if __name__ == "__main__":
    main()
