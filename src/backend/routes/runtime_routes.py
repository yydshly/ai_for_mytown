from fastapi import APIRouter

from ..domain.app_metadata import APP_NAME, APP_VERSION, RELEASE_BASELINE


def register(app, ctx) -> None:
    r = APIRouter()

    @r.get("/api/health")
    def health():
        return {"ok": True, "app": APP_NAME, "version": APP_VERSION, "baseline": RELEASE_BASELINE}

    app.include_router(r)
