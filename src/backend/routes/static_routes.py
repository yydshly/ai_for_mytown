"""托管前端静态资源。

MVP 阶段前端是自包含的 frontend/index.html（Vue3 CDN + 手写适老化）。
生产版迁移到 Vite 构建产物后，把 frontend 指向 dist 即可。
"""
from fastapi import HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles


def register(app, ctx) -> None:
    frontend_dir = ctx.project_root / "frontend"

    @app.get("/")
    def index():
        idx = frontend_dir / "index.html"
        if idx.exists():
            return FileResponse(str(idx))
        return HTMLResponse("<h1>前端未就绪：缺少 frontend/index.html</h1>", status_code=500)

    # PWA：manifest 与 service worker 必须在根作用域（sw 的 scope 决定能否控制 "/"）
    @app.get("/manifest.webmanifest")
    def manifest():
        fp = frontend_dir / "manifest.webmanifest"
        if not fp.exists():
            raise HTTPException(404)
        return FileResponse(str(fp), media_type="application/manifest+json")

    @app.get("/sw.js")
    def service_worker():
        fp = frontend_dir / "sw.js"
        if not fp.exists():
            raise HTTPException(404)
        # 不缓存 SW 本体，确保更新能生效
        return FileResponse(
            str(fp),
            media_type="application/javascript",
            headers={"Cache-Control": "no-cache"},
        )

    # 图标 + 预留静态资源
    icons_dir = frontend_dir / "icons"
    if icons_dir.exists():
        app.mount("/icons", StaticFiles(directory=str(icons_dir)), name="icons")
    if frontend_dir.exists():
        app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")
