"""AI 助农 Web 服务入口。

职责仅限：路径初始化、AppContext 装配、路由注册、生命周期协调。
具体业务接口在 src/backend/routes/。
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.backend.app_context import build_context  # noqa: E402
from src.backend.infra.logging_setup import setup_logging  # noqa: E402
from src.backend.routes import (  # noqa: E402
    ai_routes,
    alert_routes,
    calendar_routes,
    chat_routes,
    crop_routes,
    diagnose_routes,
    plot_routes,
    runtime_routes,
    static_routes,
    tts_routes,
)

log = logging.getLogger("server")


def create_app() -> tuple[FastAPI, "object"]:
    ctx = build_context(PROJECT_ROOT)
    setup_logging(ctx.log_dir)
    log.info("AppContext ready; project_root=%s", PROJECT_ROOT)

    app = FastAPI(title="AI 助农（桃树 MVP）")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 内网/本机使用；上线前收紧
        allow_methods=["*"],
        allow_headers=["*"],
    )

    runtime_routes.register(app, ctx)
    crop_routes.register(app, ctx)
    plot_routes.register(app, ctx)
    calendar_routes.register(app, ctx)
    diagnose_routes.register(app, ctx)
    alert_routes.register(app, ctx)
    chat_routes.register(app, ctx)
    ai_routes.register(app, ctx)
    tts_routes.register(app, ctx)
    static_routes.register(app, ctx)
    return app, ctx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    app, ctx = create_app()
    host = args.host or (ctx.config.get("server") or {}).get("host") or "127.0.0.1"
    port = args.port or (ctx.config.get("server") or {}).get("port") or 8770

    _print_urls(host, port)
    uvicorn.run(app, host=host, port=port, reload=args.reload)


def _print_urls(host: str, port: int) -> None:
    """打印可访问地址，方便手机/内网穿透联调。"""
    import socket

    print("\n" + "=" * 52)
    print(" AI 助农 · 桃树  已启动")
    print("=" * 52)
    print(f"  本机:    http://127.0.0.1:{port}/")
    if host in ("0.0.0.0", "::"):
        try:
            lan_ip = socket.gethostbyname(socket.gethostname())
            print(f"  局域网:  http://{lan_ip}:{port}/   (同一 WiFi 的手机可访问)")
        except Exception:
            pass
    print(f"  接口文档: http://127.0.0.1:{port}/docs")
    print("-" * 52)
    print(" 手机访问提示：语音输入(ASR)与'添加到主屏幕'需 HTTPS，")
    print(" 建议用带 https 的内网穿透（cpolar 等）。详见 docs/deploy-mobile.md")
    print("=" * 52 + "\n")


if __name__ == "__main__":
    main()
