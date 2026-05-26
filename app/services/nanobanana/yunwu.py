"""云雾 API NanoBanana 图片生成（Gemini 原生 generateContent 接口）"""

import base64
import os
import re
import uuid
from datetime import datetime
from typing import Optional

import requests

from ...logger import logger
from .base import NanoBananaBase, NanoBananaResult

YUNWU_BASE = "https://yunwu.ai"

_MIME_TO_EXT = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


class NanoBananaYunwu(NanoBananaBase):
    """云雾 API NanoBanana 图片生成（Gemini 原生 generateContent 接口）"""

    _MODEL = "gemini-3-pro-image-preview"

    # 支持的清晰度（imageSize）
    _VALID_SIZES = {"1K", "2K", "4K"}

    @property
    def provider_name(self) -> str:
        return "云雾 API"

    @property
    def base_url(self) -> str:
        return YUNWU_BASE

    def generate(
        self,
        prompt: str,
        aspect_ratio: str = "9:16",
        image_size: str = "1K",
        **kwargs,
    ) -> NanoBananaResult:
        """
        生成图片（Gemini 原生 generateContent 接口）。

        Args:
            prompt:       图片描述提示词
            aspect_ratio: 宽高比，支持 9:16 / 16:9 / 1:1 / 4:3 / 3:4 等
            image_size:   清晰度，1K / 2K / 4K
            **kwargs:
                ref_images:    [{base64, mime}, ...] 参考图列表
                ref_image:     单张图片 base64（兼容旧调用）
                ref_mime_type: 单张图片 MIME（兼容旧调用）
                download_dir:  生成后自动保存到本地的目录
        """
        # 支持 ref_image_path：从磁盘读取图片并转为 base64
        ref_image_path = kwargs.get("ref_image_path")
        if ref_image_path and os.path.isfile(ref_image_path):
            import mimetypes
            mime = mimetypes.guess_type(ref_image_path)[0] or "image/jpeg"
            with open(ref_image_path, "rb") as _f:
                _b64 = base64.b64encode(_f.read()).decode("ascii")
            existing = list(kwargs.get("ref_images") or [])
            existing.insert(0, {"base64": _b64, "mime": mime})
            kwargs = {**kwargs, "ref_images": existing}

        ref_images = self._collect_ref_images(kwargs)
        download_dir = kwargs.get("download_dir")
        image_size = image_size if image_size in self._VALID_SIZES else "1K"

        # 构建 parts：先放文本，再放参考图
        parts: list[dict] = [{"text": prompt}]
        for img in ref_images:
            b64 = img.get("base64", "")
            mime = img.get("mime", "image/jpeg")
            if b64:
                parts.append({
                    "inline_data": {
                        "mime_type": mime,
                        "data": b64,
                    }
                })

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": parts,
                }
            ],
            "generationConfig": {
                "responseModalities": ["IMAGE"],
                "imageConfig": {
                    "aspectRatio": aspect_ratio,
                    "imageSize": image_size,
                },
            },
        }

        url = (
            f"{self.base_url.rstrip('/')}"
            f"/v1beta/models/{self._MODEL}:generateContent"
            f"?key={self.api_key}"
        )
        headers = {"Content-Type": "application/json"}

        mode = f"图生图({len(ref_images)}张)" if ref_images else "文生图"
        logger.info(
            f"[{self.provider_name}] NanoBanana 请求 | "
            f"model={self._MODEL} | 模式={mode} | "
            f"比例={aspect_ratio} | 清晰度={image_size}"
        )

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=300)
            logger.info(f"[{self.provider_name}] 响应状态码: {resp.status_code}")
            logger.info(f"[{self.provider_name}] 响应体（前500字符）: {resp.text[:500]}")
            resp.raise_for_status()
            data = resp.json()

            result = self._extract_image(data)

            if result.success and result.image_data and download_dir:
                result.file_path = self._save_to_dir(
                    result.image_data, result.mime_type or "image/png", str(download_dir)
                )

            return result

        except requests.exceptions.Timeout:
            logger.error(f"[{self.provider_name}] NanoBanana 请求超时")
            return NanoBananaResult(success=False, error_message="请求超时，请稍后重试")
        except requests.exceptions.HTTPError as exc:
            error_message = f"HTTP 错误: {exc.response.status_code}"
            try:
                body = exc.response.json()
                error_message = (
                    body.get("error", {}).get("message")
                    or body.get("message")
                    or error_message
                )
            except Exception:
                pass
            logger.error(f"[{self.provider_name}] NanoBanana HTTP 异常: {error_message}")
            return NanoBananaResult(success=False, error_message=error_message)
        except Exception as exc:
            logger.error(f"[{self.provider_name}] NanoBanana 生成异常: {exc}")
            return NanoBananaResult(success=False, error_message=f"生成失败: {exc}")

    def _collect_ref_images(self, kwargs: dict) -> list[dict]:
        ref_images = list(kwargs.get("ref_images") or [])
        legacy = kwargs.get("ref_image")
        if legacy:
            ref_images.append(
                {"base64": legacy, "mime": kwargs.get("ref_mime_type", "image/jpeg")}
            )
        return [img for img in ref_images if img.get("base64")]

    def _extract_image(self, data: dict) -> NanoBananaResult:
        """
        从 Gemini generateContent 响应中提取图片。

        响应结构：
        {
          "candidates": [{
            "content": {
              "parts": [
                {"text": "..."},
                {"inlineData": {"mimeType": "image/png", "data": "base64..."}}
              ]
            }
          }]
        }
        """
        try:
            candidates = data.get("candidates") or []
            if not candidates:
                error = data.get("error", {})
                msg = error.get("message") if isinstance(error, dict) else str(error)
                return NanoBananaResult(
                    success=False,
                    error_message=msg or "响应中无 candidates",
                )

            parts = candidates[0].get("content", {}).get("parts", [])
            for part in parts:
                inline = part.get("inlineData") or part.get("inline_data")
                if inline:
                    mime_type = inline.get("mimeType") or inline.get("mime_type") or "image/png"
                    image_data = inline.get("data", "")
                    # 清理可能的换行
                    image_data = image_data.replace("\n", "").replace(" ", "").replace("\r", "")
                    if image_data:
                        logger.info(
                            f"[{self.provider_name}] 提取到 base64 图片 | "
                            f"mime={mime_type} | 长度={len(image_data)}"
                        )
                        return NanoBananaResult(
                            success=True,
                            image_data=image_data,
                            mime_type=mime_type,
                        )

            # 兜底：parts 里只有 text，没有图片
            texts = [p.get("text", "") for p in parts if p.get("text")]
            return NanoBananaResult(
                success=False,
                error_message="响应中未找到图片数据" + (f"，模型文本：{texts[0][:200]}" if texts else ""),
            )
        except Exception as exc:
            logger.error(f"[{self.provider_name}] 响应解析异常: {exc}")
            return NanoBananaResult(success=False, error_message=f"响应解析失败: {exc}")

    @staticmethod
    def _save_to_dir(image_data: str, mime_type: str, download_dir: str) -> str:
        os.makedirs(download_dir, exist_ok=True)
        ext = _MIME_TO_EXT.get(mime_type, ".png")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"nanobanana_yw_{ts}_{uuid.uuid4().hex[:6]}{ext}"
        file_path = os.path.join(download_dir, filename)
        raw = base64.b64decode(image_data)
        with open(file_path, "wb") as f:
            f.write(raw)
        logger.info(f"[云雾 API] 图片已保存: {file_path} ({len(raw)} bytes)")
        return file_path
