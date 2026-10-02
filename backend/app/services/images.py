"""Validate pixels locally and transmit image bytes, never campus-only URLs."""
import base64
import io
import os
from pathlib import Path
from urllib.parse import urlparse

import httpx

MAX_IMAGE=10*1024*1024


def validate_bytes(content):
    if not content or len(content)>MAX_IMAGE:
        raise ValueError("图片为空或超过 10MB")
    from PIL import Image, UnidentifiedImageError
    try:
        with Image.open(io.BytesIO(content)) as image:
            if image.width*image.height>25_000_000 or min(image.size)<32:
                raise ValueError("图片尺寸超出支持范围")
            kind=image.format
            image.verify()
    except (UnidentifiedImageError,OSError,Image.DecompressionBombError) as exc:
        raise ValueError("图片内容无效") from exc
    if kind not in {"JPEG","PNG","WEBP"}:
        raise ValueError("仅支持 JPEG、PNG、WebP")
    return {"JPEG":"image/jpeg","PNG":"image/png","WEBP":"image/webp"}[kind]


async def image_data_url(source):
    if source.startswith("data:"):
        try:
            metadata,payload=source.split(",",1)
            if ";base64" not in metadata:
                raise ValueError
            content=base64.b64decode(payload,validate=True)
        except Exception as exc:
            raise ValueError("图片编码无效") from exc
    elif source.startswith("/"):
        root=Path(os.getenv("STATIC_DIR","/app/static")).resolve()
        path=(root/source.lstrip("/")).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError("参考图片不存在或路径不合法")
        content=path.read_bytes()
    else:
        parsed=urlparse(source)
        allowed=set(filter(None,os.getenv("CAMERA_ALLOWED_HOSTS","").split(",")))
        if parsed.scheme not in {"http","https"} or parsed.hostname not in allowed or parsed.username or parsed.password:
            raise ValueError("图片地址不在管理员配置的采集主机白名单中")
        # Explicitly approved campus camera hosts can be private IPs. Redirects
        # are forbidden so authorization cannot be escaped via another host.
        content=bytearray()
        async with httpx.AsyncClient(timeout=10,follow_redirects=False,trust_env=False) as client:
            async with client.stream("GET",source) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes():
                    content.extend(chunk)
                    if len(content)>MAX_IMAGE:
                        raise ValueError("图片超过 10MB")
        content=bytes(content)
    mime=validate_bytes(content)
    return "data:"+mime+";base64,"+base64.b64encode(content).decode()
