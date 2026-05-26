"""斑点蛙 API NanoBanana 图片生成（异步任务型）"""

import base64
import os
import re
import time
from typing import Optional

import requests

from ...logger import logger
from .base import NanoBananaBase, NanoBananaResult

BDW_BASE = "https://api.hellobabygo.com"

# 任务状态
_PENDING_STATUSES = {"queued", "in_progress", "processing", "running"}
_FAILED_STATUSES = {"failed", "error", "cancelled"}

# 模型映射：清晰度-方向 -> 完整模型名
_SIZE_TO_MODEL = {
    "1K-landscape": "nano_banana_pro-1K-landscape",
    "1K-portrait": "nano_banana_pro-1K-portrait",
    "1K-square": "nano_banana_pro-1K-square",
    "2K-landscape": "nano_banana_pro-2K-landscape",
    "2K-portrait": "nano_banana_pro-2K-portrait",
    "2K-square": "nano_banana_pro-2K-square",
    "4K-landscape": "nano_banana_pro-4K-landscape",
    "4K-portrait": "nano_banana_pro-4K-portrait",
    "4K-square": "nano_banana_pro-4K-square",
}

# 宽高比映射
_RATIO_TO_ORIENTATION = {
    "16:9": "landscape",
    "9:16": "portrait",
    "1:1": "square",
    "4:3": "landscape",
    "3:4": "portrait",
}


class NanoBananaBandianwa(NanoBananaBase):
    """斑点蛙 API NanoBanana 图片生成"""

    @property
    def provider_name(self) -> str:
        return "斑点蛙 API"

    @property
    def base_url(self) -> str:
        return BDW_BASE

    def generate(
        self,
        prompt: str,
        aspect_ratio: str = "9:16",
        image_size: str = "1K",
        **kwargs,
    ) -> NanoBananaResult:
        """
        生成图片（异步任务型）。

        Args:
            prompt:       图片描述提示词
            aspect_ratio: 宽高比，支持 9:16 / 16:9 / 1:1 / 4:3 / 3:4 等
            image_size:   清晰度，1K / 2K / 4K
            **kwargs:
                ref_images:    [{base64, mime}, ...] 参考图列表
                ref_image_path: 单张图片路径
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

        # 解析模型名称
        orientation = self._ratio_to_orientation(aspect_ratio)
        model_name = self._resolve_model(image_size, orientation)

        # 构建请求体（所有参数必须平级，不要嵌套）
        # 注意：model 已包含清晰度和方向，不需要再传 size 和 aspectRatio
        payload = {
            "model": model_name,
            "prompt": prompt,
            "response_format": "url",
        }

        # 如果有参考图，添加到 payload（图生图只取第一张）
        if ref_images:
            # 斑点蛙的 image 参数需要是 URL 或 base64 data URL
            first_image = ref_images[0]
            image_data_url = self._to_data_url(first_image)
            payload["image"] = image_data_url

        # 提交任务
        task_id = self._submit_task(payload)
        if not task_id:
            return NanoBananaResult(success=False, error_message="任务提交失败")

        # 轮询任务状态
        result = self._poll_task(task_id)
        if not result or not result.success:
            return result or NanoBananaResult(success=False, error_message="任务轮询失败")

        # 如果配置了下载目录，保存图片
        if result.success and result.image_data and download_dir:
            result.file_path = self._save_to_dir(
                result.image_data, result.mime_type or "image/png", str(download_dir)
            )

        return result

    def _submit_task(self, payload: dict) -> Optional[str]:
        """提交异步任务"""
        url = f"{self.base_url.rstrip('/')}/v1/images/generations?async=true"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        mode = f"图生图({len(payload.get('images', []))}张)" if payload.get("images") else "文生图"
        logger.info(
            f"[{self.provider_name}] NanoBanana 请求 | "
            f"model={payload.get('model')} | 模式={mode} | "
            f"POST {url}"
        )

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            logger.info(f"[{self.provider_name}] 响应状态码: {resp.status_code}")
            logger.info(f"[{self.provider_name}] 响应体: {resp.text[:500]}")
            resp.raise_for_status()

            data = resp.json()
            task_id = data.get("task_id") or data.get("id")
            if not task_id:
                logger.error(f"[{self.provider_name}] 响应中未找到 task_id")
                return None

            logger.info(f"[{self.provider_name}] 任务已提交 | task_id={task_id}")
            return task_id

        except requests.exceptions.Timeout:
            logger.error(f"[{self.provider_name}] 任务提交超时")
            return None
        except requests.exceptions.HTTPError as exc:
            error_message = self._extract_error_message(exc.response)
            logger.error(f"[{self.provider_name}] 任务提交 HTTP 异常: {error_message}")
            return None
        except Exception as exc:
            logger.error(f"[{self.provider_name}] 任务提交异常: {exc}")
            return None

    def _poll_task(
        self,
        task_id: str,
        timeout_seconds: int = 300,
        interval_seconds: int = 15,
    ) -> Optional[NanoBananaResult]:
        """轮询任务状态"""
        url = f"{self.base_url.rstrip('/')}/v1/images/{task_id}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }
        deadline = time.time() + timeout_seconds

        while time.time() < deadline:
            try:
                resp = requests.get(url, headers=headers, timeout=30)
                logger.info(f"[{self.provider_name}] 轮询状态码: {resp.status_code}")
                logger.info(f"[{self.provider_name}] 轮询响应: {resp.text[:500]}")
                resp.raise_for_status()

                data = resp.json()
                status = str(data.get("status") or "").lower()

                # 检查是否完成：status=completed 或 data 数组中有 url
                if status == "completed" or self._has_image_url(data):
                    logger.info(f"[{self.provider_name}] 任务完成 | task_id={task_id}")
                    return self._extract_result(data)

                # 检查是否失败
                if status in _FAILED_STATUSES:
                    error_msg = data.get("error") or data.get("message") or "任务执行失败"
                    logger.error(f"[{self.provider_name}] 任务失败 | task_id={task_id} | error={error_msg}")
                    return NanoBananaResult(success=False, error_message=str(error_msg))

                # 继续轮询
                if status not in _PENDING_STATUSES and status != "":
                    logger.warning(f"[{self.provider_name}] 未识别状态: {status}")

                time.sleep(interval_seconds)

            except requests.exceptions.Timeout:
                logger.warning(f"[{self.provider_name}] 轮询请求超时，继续重试")
                time.sleep(interval_seconds)
            except Exception as exc:
                logger.error(f"[{self.provider_name}] 轮询异常: {exc}")
                time.sleep(interval_seconds)

        return NanoBananaResult(success=False, error_message="轮询图片结果超时")

    def _has_image_url(self, data: dict) -> bool:
        """检查响应中是否包含图片 URL"""
        data_array = data.get("data")
        if not isinstance(data_array, list) or not data_array:
            return False
        # 检查 data[0] 中是否有 url
        first_item = data_array[0]
        if isinstance(first_item, dict) and first_item.get("url"):
            return True
        return False

    def _extract_result(self, data: dict) -> NanoBananaResult:
        """从响应中提取图片结果"""
        try:
            data_array = data.get("data")
            if not isinstance(data_array, list) or not data_array:
                return NanoBananaResult(success=False, error_message="响应中无数据")

            first_item = data_array[0]
            if not isinstance(first_item, dict):
                return NanoBananaResult(success=False, error_message="数据格式错误")

            image_url = first_item.get("url")
            if not image_url:
                return NanoBananaResult(success=False, error_message="未找到图片数据")

            # 如果是 URL，下载图片
            if image_url.startswith("http"):
                logger.info(f"[{self.provider_name}] 下载图片 | url={image_url[:100]}")
                resp = requests.get(image_url, timeout=60)
                resp.raise_for_status()

                mime_type = resp.headers.get("Content-Type", "image/jpeg").split(";")[0].strip()
                image_data = base64.b64encode(resp.content).decode("ascii")

                logger.info(
                    f"[{self.provider_name}] 成功下载图片 | "
                    f"mime={mime_type} | 大小={len(resp.content)} bytes"
                )

                return NanoBananaResult(
                    success=True,
                    image_data=image_data,
                    mime_type=mime_type,
                )

            # 如果是 data URL 格式
            if image_url.startswith("data:"):
                match = re.match(r"data:(image/[^;]+);base64,(.*)", image_url, re.DOTALL)
                if not match:
                    return NanoBananaResult(success=False, error_message="无法解析 data URL")
                mime_type = match.group(1)
                image_data = match.group(2).replace("\n", "").replace(" ", "").replace("\r", "")

                logger.info(
                    f"[{self.provider_name}] 成功解析 data URL | "
                    f"mime={mime_type} | 长度={len(image_data)}"
                )

                return NanoBananaResult(
                    success=True,
                    image_data=image_data,
                    mime_type=mime_type,
                )

            return NanoBananaResult(success=False, error_message=f"不支持的图片格式: {image_url[:50]}")

        except requests.exceptions.Timeout:
            logger.error(f"[{self.provider_name}] 下载图片超时")
            return NanoBananaResult(success=False, error_message="下载图片超时")
        except requests.exceptions.HTTPError as exc:
            error_message = self._extract_error_message(exc.response)
            logger.error(f"[{self.provider_name}] 下载图片 HTTP 异常: {error_message}")
            return NanoBananaResult(success=False, error_message=f"下载图片失败: {error_message}")
        except Exception as exc:
            logger.error(f"[{self.provider_name}] 响应解析异常: {exc}")
            return NanoBananaResult(success=False, error_message=f"响应解析失败: {exc}")

    def _fetch_image(self, task_id: str) -> NanoBananaResult:
        """获取图片内容"""
        url = f"{self.base_url.rstrip('/')}/v1/images/{task_id}/content"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }

        try:
            resp = requests.get(url, headers=headers, timeout=60)
            logger.info(f"[{self.provider_name}] 获取图片状态码: {resp.status_code}")
            resp.raise_for_status()

            # 获取 MIME 类型
            mime_type = resp.headers.get("Content-Type", "image/png").split(";")[0].strip()
            image_data = base64.b64encode(resp.content).decode("ascii")

            logger.info(
                f"[{self.provider_name}] 成功获取图片 | "
                f"mime={mime_type} | 大小={len(resp.content)} bytes"
            )

            return NanoBananaResult(
                success=True,
                image_data=image_data,
                mime_type=mime_type,
            )

        except requests.exceptions.Timeout:
            logger.error(f"[{self.provider_name}] 获取图片超时")
            return NanoBananaResult(success=False, error_message="获取图片超时")
        except requests.exceptions.HTTPError as exc:
            error_message = self._extract_error_message(exc.response)
            logger.error(f"[{self.provider_name}] 获取图片 HTTP 异常: {error_message}")
            return NanoBananaResult(success=False, error_message=f"获取图片失败: {error_message}")
        except Exception as exc:
            logger.error(f"[{self.provider_name}] 获取图片异常: {exc}")
            return NanoBananaResult(success=False, error_message=f"获取图片异常: {exc}")

    def _collect_ref_images(self, kwargs: dict) -> list[dict]:
        """收集参考图"""
        ref_images = list(kwargs.get("ref_images") or [])
        legacy = kwargs.get("ref_image")
        if legacy:
            ref_images.append(
                {"base64": legacy, "mime": kwargs.get("ref_mime_type", "image/jpeg")}
            )
        return [img for img in ref_images if img.get("base64")]

    @staticmethod
    def _to_data_url(image: dict) -> str:
        """将 base64 图片转换为 data URL"""
        mime_type = image.get("mime", "image/jpeg")
        return f"data:{mime_type};base64,{image.get('base64', '')}"

    def _resolve_model(self, image_size: str, orientation: str) -> str:
        """解析模型名称"""
        key = f"{image_size}-{orientation}"
        model = _SIZE_TO_MODEL.get(key)
        if model:
            return model

        # 兜底：使用默认模型
        logger.warning(f"[{self.provider_name}] 未找到匹配的模型 {key}，使用默认 nano_banana_pro-1K-square")
        return "nano_banana_pro-1K-square"

    @staticmethod
    def _ratio_to_orientation(aspect_ratio: str) -> str:
        """将宽高比映射到方向"""
        return _RATIO_TO_ORIENTATION.get(aspect_ratio, "portrait")

    @staticmethod
    def _extract_error_message(response) -> str:
        """提取错误信息"""
        try:
            body = response.json()
            error = body.get("error")
            if isinstance(error, dict):
                return error.get("message") or error.get("detail") or str(error)
            return body.get("message") or str(error) or response.text[:500]
        except Exception:
            return response.text[:500] if response.text else str(response)

    @staticmethod
    def _save_to_dir(image_data: str, mime_type: str, download_dir: str) -> str:
        """保存图片到本地"""
        os.makedirs(download_dir, exist_ok=True)
        ext_map = {
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "image/webp": ".webp",
            "image/gif": ".gif",
        }
        ext = ext_map.get(mime_type, ".png")

        from datetime import datetime
        import uuid

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"nanobanana_bdw_{ts}_{uuid.uuid4().hex[:6]}{ext}"
        file_path = os.path.join(download_dir, filename)

        raw = base64.b64decode(image_data)
        with open(file_path, "wb") as f:
            f.write(raw)

        logger.info(f"[{NanoBananaBandianwa(None).provider_name}] 图片已保存: {file_path} ({len(raw)} bytes)")
        return file_path
