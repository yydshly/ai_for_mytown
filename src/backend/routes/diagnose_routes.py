"""拍照诊断路由。

POST /api/diagnose  multipart：file=图片，可选 note=文字补充
查询参数 ?mock=1 强制走 mock（无 API key 也能联调）。

隐私（R-09 / config.diagnose.keep_uploaded_images_days）：默认不落盘，
处理完图片字节即丢弃。
"""
import logging

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile

from ..services.diagnose import diagnose

log = logging.getLogger("routes.diagnose")

MAX_IMAGE_BYTES = 12 * 1024 * 1024  # 12MB


def register(app, ctx) -> None:
    r = APIRouter()
    keep_days = ((ctx.config.get("diagnose") or {}).get("keep_uploaded_images_days")) or 0

    @r.post("/api/diagnose")
    async def post_diagnose(
        file: UploadFile = File(...),
        note: str = Form(""),
        crop: str = Form(""),
        mock: int = Query(0),
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

        # 隐私：默认不留存图片（keep_days=0 时 data 随函数结束被回收，不写盘）
        if keep_days and keep_days > 0:
            log.info("keep_uploaded_images_days=%s（当前未实现留存，留待后续）", keep_days)

        return result

    app.include_router(r)
