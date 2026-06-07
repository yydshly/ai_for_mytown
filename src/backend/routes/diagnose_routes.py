"""拍照诊断路由。

POST /api/diagnose  multipart：file=图片，可选 note=文字补充
查询参数 ?mock=1 强制走 mock（无 API key 也能联调）。

隐私（R-09 / config.diagnose.keep_uploaded_images_days）：默认不落盘，
处理完图片字节即丢弃。
"""
import logging
from datetime import date as _date

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile

from ..infra.auth_dep import make_current_user
from ..repositories.activity_log_repository import ActivityLogRepository
from ..repositories.interaction_repository import InteractionRepository
from ..repositories.plot_repository import PlotRepository
from ..services.diagnose import diagnose

log = logging.getLogger("routes.diagnose")

MAX_IMAGE_BYTES = 12 * 1024 * 1024  # 12MB


def _days_ago(date_str: str) -> int | None:
    try:
        return (_date.today() - _date.fromisoformat(date_str)).days
    except Exception:
        return None


def register(app, ctx) -> None:
    r = APIRouter()
    keep_days = ((ctx.config.get("diagnose") or {}).get("keep_uploaded_images_days")) or 0
    plots = PlotRepository(ctx.db)
    logs = ActivityLogRepository(ctx.db)
    interactions = InteractionRepository(ctx.db)
    optional_user = make_current_user(ctx, required=False)

    @r.post("/api/diagnose")
    async def post_diagnose(
        file: UploadFile = File(...),
        note: str = Form(""),
        crop: str = Form(""),
        plot_id: str = Form(""),
        mock: int = Query(0),
        user=Depends(optional_user),
    ):
        data = await file.read()
        if not data:
            raise HTTPException(400, "未收到图片")
        if len(data) > MAX_IMAGE_BYTES:
            raise HTTPException(413, "图片过大，请压缩后重试")

        cid = ctx.crops.resolve(crop or None)
        meta = ctx.crops.get(cid)
        kb = ctx.knowledge.kb(cid)

        mime = file.content_type or "image/jpeg"
        result = await diagnose(
            kb=kb,
            config=ctx.config,
            image_bytes=data,
            image_mime=mime,
            user_note=note.strip(),
            crop_name=(meta.name if meta else "果树"),
            force_mock=bool(mock),
        )

        # 安全上下文：当前地块距上次打药天数（防重复/超量用药）。仅当登录且拥有该地块。
        if plot_id and user and plots.get(plot_id, user.id) is not None:
            last = logs.latest_by_category(plot_id, "打药")
            if last:
                result["plot_context"] = {
                    "last_spray_date": last.date,
                    "last_spray_title": last.title,
                    "days_ago": _days_ago(last.date),
                }

        # 审计：记一条 AI 交互（仅截断摘要，不存图片）
        rec = interactions.log(
            user_id=(user.id if user else ""), kind="diagnose", crop=cid,
            plot_id=(plot_id or ""), summary=(note.strip() or "拍照诊断"),
            result_summary=result.get("identification_raw") or result.get("confidence_note", ""),
        )
        result["interaction_id"] = rec.id

        # 隐私：默认不留存图片（keep_days=0 时 data 随函数结束被回收，不写盘）
        if keep_days and keep_days > 0:
            log.info("keep_uploaded_images_days=%s（当前未实现留存，留待后续）", keep_days)

        return result

    app.include_router(r)
