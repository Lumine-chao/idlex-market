"""图片上传：本地存储（开发环境替代 MinIO 预签名直传）"""
import os
import uuid
from fastapi import APIRouter, Depends, UploadFile, File
from .. import errors
from ..config import settings
from ..deps import get_current_user_async
from ..models import User

router = APIRouter(prefix="/api/v1/uploads", tags=["uploads"])

ALLOWED = {"jpg", "jpeg", "png", "webp"}
MAX_SIZE = 10 * 1024 * 1024


@router.post("/presign")
async def presign(user: User = Depends(get_current_user_async)):
    """简化实现：直接返回一个可用于上传的端点占位。实际文件走 /presign/upload。"""
    return {"code": 0, "message": "ok", "data": {"uploadUrl": "/api/v1/uploads/upload",
            "method": "POST", "field": "file"}}


@router.post("/upload")
async def upload(file: UploadFile = File(...),
                 user: User = Depends(get_current_user_async)):
    ext = (file.filename or "").rsplit(".", 1)[-1].strip().lower()
    if ext not in ALLOWED:
        raise errors.error(errors.ErrorCodes.IMAGE_FORMAT, "image.upload.format")
    data = await file.read()
    if len(data) > MAX_SIZE:
        raise errors.error(errors.ErrorCodes.IMAGE_TOO_LARGE, "image.upload.size")
    os.makedirs(settings.upload_dir, exist_ok=True)
    name = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(settings.upload_dir, name)
    with open(path, "wb") as f:
        f.write(data)
    url = f"{settings.public_base}/{name}"
    return {"code": 0, "message": "ok", "data": {"url": url}}