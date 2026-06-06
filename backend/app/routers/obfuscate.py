"""
Image Obfuscation Router
图片加扰/解扰相关 API 路由
"""
import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..services.image_obfuscator import (
    obfuscate_image,
    deobfuscate_image,
    obfuscate_simple,
    deobfuscate_simple,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/obfuscate", tags=["obfuscate"])


@router.post("/encrypt")
async def encrypt_with_password(
    password: str,
    method: str = "xor",
    file: UploadFile = File(...)
):
    """加扰上传的图片"""
    if not file.filename or not password:
        raise HTTPException(status_code=400, detail="File and password required")

    suffix = Path(file.filename).suffix or ".png"
    input_tmp = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            input_tmp = Path(tmp.name)

        output_tmp = Path(tempfile.mktemp(suffix=suffix))

        success = obfuscate_image(input_tmp, output_tmp, password, method)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to obfuscate image")

        return FileResponse(output_tmp, media_type="image/png", filename=f"obfuscated_{file.filename}")

    finally:
        if input_tmp and input_tmp.exists():
            input_tmp.unlink(missing_ok=True)


@router.post("/decrypt")
async def decrypt_with_password(
    password: str,
    method: str = "xor",
    file: UploadFile = File(...)
):
    """解扰上传的图片"""
    if not file.filename or not password:
        raise HTTPException(status_code=400, detail="File and password required")

    suffix = Path(file.filename).suffix or ".png"
    input_tmp = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            input_tmp = Path(tmp.name)

        output_tmp = Path(tempfile.mktemp(suffix=suffix))

        success = deobfuscate_image(input_tmp, output_tmp, password, method)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to deobfuscate image")

        return FileResponse(output_tmp, media_type="image/png", filename=f"restored_{file.filename}")

    finally:
        if input_tmp and input_tmp.exists():
            input_tmp.unlink(missing_ok=True)
