"""万米霖渠道 NanoBanana 图片生成（gemini-3.0-pro-image 系列 + 自动下载）"""

import base64
import json
import os
import re
import uuid
from datetime import datetime

import requests

from ...constants import ApiUrls
from ...logger import logger
from .base import NanoBananaBase, NanoBananaResult

_RATIO_TO_ORIENTATION = {
    "16:9": "landscape",
    "9:16": "portrait",
    "1:1": "square",
    "4:3": "four-three",
    "3:4": "three-four",
}

_SIZE_TO_SUFFIX = {
    "1K": "",
    "2K": "-2k",
    "4K": "-4k",
}

_MIME_TO_EXT = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


class NanoBananaGlin(NanoBananaBase):
    """万米霖渠道 NanoBanana 图片生成"""

    @property
    def provider_name(self) -> str:
        return "万米霖 API"

    @property
    def base_url(self) -> str:
        return ApiUrls.GLIN

    def generate(
        self,
        prompt: str,
        aspect_ratio: str = "9:16",
        image_size: str = "1K",
        **kwargs,
    ) -> NanoBananaResult:
        download_dir = kwargs.pop("download_dir", None)

        orientation = _RATIO_TO_ORIENTATION.get(aspect_ratio, "portrait")
        suffix = _SIZE_TO_SUFFIX.get(image_size, "")
        model = f"gemini-3.0-pro-image-{orientation}{suffix}"

        url = f"{self.base_url.rstrip('/')}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

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

        ref_images = kwargs.get("ref_images") or []

        if ref_images:
            content = [{"type": "text", "text": prompt}]
            for img in ref_images:
                b64 = img.get("base64", "")
                mime = img.get("mime", "image/jpeg")
                if b64:
                    content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})
        else:
            content = prompt

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": content}],
            "stream": True,
        }

        try:
            mode = f"图生图({len(ref_images)}张)" if ref_images else "文生图"
            logger.info(
                f"[{self.provider_name}] 生成请求 | model={model} | "
                f"比例={aspect_ratio} 清晰度={image_size} 模式={mode} | base_url={self.base_url}"
            )

            resp = requests.post(url, headers=headers, json=payload, timeout=300, stream=True)
            logger.info(f"[{self.provider_name}] 响应状态码: {resp.status_code}")
            resp.raise_for_status()

            full_content = ""
            for line in resp.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    choices = chunk.get("choices", [])
                    if choices:
                        delta = choices[0].get("delta", {})
                        c = delta.get("content")
                        if c:
                            full_content += c
                except json.JSONDecodeError:
                    continue

            if not full_content:
                return NanoBananaResult(success=False, error_message="SSE 流中未收到 content 数据")

            logger.info(f"[{self.provider_name}] SSE 完成, content 长度: {len(full_content)}")

            result = self._extract_image(full_content)

            if result.success and result.image_data and download_dir:
                result.file_path = self._save_to_dir(result.image_data, result.mime_type, download_dir)

            return result

        except requests.exceptions.Timeout:
            logger.error(f"[{self.provider_name}] 请求超时")
            return NanoBananaResult(success=False, error_message="请求超时，请稍后重试")
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP 错误: {e.response.status_code}"
            resp_text = ""
            try:
                resp_text = e.response.text[:1000] if e.response.text else ""
                error_detail = e.response.json()
                error_msg = error_detail.get("error", {}).get("message", error_msg)
            except Exception:
                if resp_text:
                    error_msg = f"{error_msg} | {resp_text}"
            logger.error(f"[{self.provider_name}] {error_msg}")
            return NanoBananaResult(success=False, error_message=error_msg)
        except Exception as e:
            logger.error(f"[{self.provider_name}] 生成异常: {e}")
            return NanoBananaResult(success=False, error_message=f"生成失败: {str(e)}")

    def _extract_image(self, content: str) -> NanoBananaResult:
        """从 markdown content 中提取图片（base64 或 URL）"""
        match = re.search(r'!\[.*?\]\((.*?)\)', content, re.DOTALL)
        if not match:
            return NanoBananaResult(success=False, error_message="未能从响应中提取图片")

        image_src = match.group(1).strip()

        if image_src.startswith("data:"):
            data_match = re.match(r'data:(image/[^;]+);base64,(.*)', image_src, re.DOTALL)
            if not data_match:
                return NanoBananaResult(success=False, error_message="无法解析 base64 data URL")
            mime_type = data_match.group(1)
            image_data = data_match.group(2).replace("\n", "").replace(" ", "").replace("\r", "")
            logger.info(f"[{self.provider_name}] 提取到 base64 图片 | mime={mime_type}")
            return NanoBananaResult(success=True, image_data=image_data, mime_type=mime_type)

        if image_src.startswith("http"):
            logger.info(f"[{self.provider_name}] 提取到图片 URL，下载中: {image_src[:80]}")
            try:
                img_resp = requests.get(image_src, timeout=60)
                img_resp.raise_for_status()
                ct = (img_resp.headers.get("Content-Type") or "image/jpeg").split(";")[0].strip()
                image_data = base64.b64encode(img_resp.content).decode("ascii")
                logger.info(f"[{self.provider_name}] 图片下载成功 | mime={ct}, size={len(img_resp.content)} bytes")
                return NanoBananaResult(success=True, image_data=image_data, mime_type=ct)
            except Exception as e:
                logger.error(f"[{self.provider_name}] 图片下载失败: {e}")
                return NanoBananaResult(success=False, error_message=f"图片下载失败: {str(e)}")

        return NanoBananaResult(success=False, error_message=f"未知的图片格式: {image_src[:100]}")

    @staticmethod
    def _save_to_dir(image_data: str, mime_type: str, download_dir: str) -> str:
        """将 base64 图片保存到指定目录，返回文件路径"""
        os.makedirs(download_dir, exist_ok=True)
        ext = _MIME_TO_EXT.get(mime_type, ".png")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"nanobanana_{ts}_{uuid.uuid4().hex[:6]}{ext}"
        filepath = os.path.join(download_dir, filename)
        raw = base64.b64decode(image_data)
        with open(filepath, "wb") as f:
            f.write(raw)
        logger.info(f"[万米霖 API] 图片已保存: {filepath} ({len(raw)} bytes)")
        return filepath


class NanoBananaGlinCustom(NanoBananaGlin):
    """荷塘渠道 NanoBanana 图片生成（万米霖同协议，自定义 Base URL）"""

    def __init__(self, api_key: str, custom_base_url: str):
        super().__init__(api_key)
        self._custom_base_url = custom_base_url.rstrip("/")

    @property
    def provider_name(self) -> str:
        return "荷塘渠道"

    @property
    def base_url(self) -> str:
        return self._custom_base_url
