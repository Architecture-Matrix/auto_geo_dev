# -*- coding: utf-8 -*-
"""
文件上传API
用这个来处理图片上传！
"""

import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from loguru import logger

from backend.config import BASE_DIR


router = APIRouter(prefix="/api/upload", tags=["文件上传"])

# 上传目录
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# 图片子目录
IMAGES_DIR = UPLOAD_DIR / "images"
IMAGES_DIR.mkdir(exist_ok=True)

# 允许的图片格式
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
# 最大文件大小 (5MB)
MAX_FILE_SIZE = 5 * 1024 * 1024


@router.post("/image", response_model=dict)
async def upload_image(file: UploadFile = File(...)):
    """
    上传图片

    支持格式：jpg, jpeg, png, gif, webp
    最大大小：5MB
    """
    # 验证文件扩展名
    file_ext = Path(file.filename).suffix.lower() if file.filename else ""
    if file_ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式。支持的格式：{', '.join(ALLOWED_IMAGE_EXTENSIONS)}"
        )

    # 读取文件内容
    content = await file.read()

    # 验证文件大小
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件大小超过限制（最大 {MAX_FILE_SIZE // 1024 // 1024}MB）"
        )

    # 生成唯一文件名
    timestamp = datetime.now().strftime("%Y%m%d")
    unique_id = uuid.uuid4().hex[:8]
    filename = f"{timestamp}_{unique_id}{file_ext}"
    file_path = IMAGES_DIR / filename

    # 保存文件
    try:
        with open(file_path, "wb") as f:
            f.write(content)
        logger.info(f"图片已保存: {filename}")
    except Exception as e:
        logger.error(f"保存图片失败: {e}")
        raise HTTPException(status_code=500, detail="保存图片失败")

    # 返回访问URL
    return {
        "success": True,
        "message": "上传成功",
        "data": {
            "url": f"/api/upload/images/{filename}",
            "filename": filename,
            "size": len(content),
            "original_name": file.filename
        }
    }


@router.post("/images", response_model=dict)
async def upload_images(files: List[UploadFile] = File(...)):
    """
    批量上传图片

    支持同时上传多张图片
    """
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="最多同时上传10张图片")

    results = []
    for file in files:
        try:
            result = await upload_image(file)
            results.append(result["data"])
        except HTTPException as e:
            results.append({
                "success": False,
                "error": e.detail,
                "original_name": file.filename
            })

    return {
        "success": True,
        "message": f"成功上传 {sum(1 for r in results if r.get('success'))}/{len(files)} 张图片",
        "data": results
    }


@router.get("/images/{filename}", response_class=FileResponse)
async def get_image(filename: str):
    """
    获取上传的图片

    通过这个接口访问已上传的图片
    """
    file_path = IMAGES_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="图片不存在")

    return FileResponse(file_path)


@router.delete("/images/{filename}", response_model=dict)
async def delete_image(filename: str):
    """
    删除上传的图片
    """
    file_path = IMAGES_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="图片不存在")

    try:
        os.remove(file_path)
        logger.info(f"图片已删除: {filename}")
        return {"success": True, "message": "图片已删除"}
    except Exception as e:
        logger.error(f"删除图片失败: {e}")
        raise HTTPException(status_code=500, detail="删除图片失败")
