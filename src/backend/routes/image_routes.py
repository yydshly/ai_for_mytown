"""病虫参考图：上传(管理员) / 浏览 / 删除。

POST   /api/pests/{pest_id}/images?crop=&caption=   管理员上传参考图
GET    /api/images/{name}                            浏览图片（开放，文件名经净化）
DELETE /api/pest-images/{image_id}                   管理员删除

图片存盘 data/images/，DB(pest_images) 存元数据。图鉴(GET /api/pests)返回每条的图。
"""
import logging
import os
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..infra.auth_dep import make_current_user
from ..repositories.image_repository import ImageRepository, ext_for_mime

log = logging.getLogger("routes.image")

MAX_IMG = 8 * 1024 * 1024
_MIME = {"image/jpeg", "image/png", "image/webp"}


def register(app, ctx) -> None:
    r = APIRouter()
    repo = ImageRepository(ctx.db)
    images_dir = ctx.data_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    require_user = make_current_user(ctx)

    def require_admin(user=Depends(require_user)):
        if not getattr(user, "is_admin", False):
            raise HTTPException(403, "需要管理员权限")
        return user

    @r.post("/api/pests/{pest_id}/images")
    async def upload(pest_id: str, file: UploadFile = File(...), crop: str = Form(""),
                     caption: str = Form(""), user=Depends(require_admin)):
        mime = file.content_type or "image/jpeg"
        if mime not in _MIME:
            raise HTTPException(400, "只支持 jpg/png/webp 图片")
        data = await file.read()
        if not data:
            raise HTTPException(400, "未收到图片")
        if len(data) > MAX_IMG:
            raise HTTPException(413, "图片过大（上限 8MB）")
        cid = ctx.crops.resolve(crop or None)
        filename = f"{uuid.uuid4().hex}.{ext_for_mime(mime)}"
        (images_dir / filename).write_bytes(data)
        rec = repo.add(cid, pest_id, filename, caption.strip())
        rec["url"] = f"/api/images/{filename}"
        return rec

    @r.get("/api/images/{name}")
    def serve(name: str):
        # 净化：只取 basename，防路径穿越
        safe = os.path.basename(name)
        fp = images_dir / safe
        if not fp.exists() or not fp.is_file():
            raise HTTPException(404, "图片不存在")
        return FileResponse(str(fp))

    @r.delete("/api/pest-images/{image_id}")
    def delete(image_id: str, user=Depends(require_admin)):
        rec = repo.delete(image_id)
        if rec is None:
            raise HTTPException(404, "图片不存在")
        # 删文件（失败不影响 DB 删除）
        try:
            (images_dir / rec["filename"]).unlink(missing_ok=True)
        except Exception:
            pass
        return {"ok": True}

    app.include_router(r)
