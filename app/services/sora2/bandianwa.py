"""斑点蛙 API Sora2 生成"""

import os
from typing import Optional

import requests

from ...constants import ApiUrls
from ...logger import logger
from .base import Sora2Task, Sora2TaskStatus
from .dayangyu import Sora2Dayangyu, _read_error_message


class Sora2Bandianwa(Sora2Dayangyu):
    """斑点蛙 API Sora2 生成"""

    # 斑点蛙支持的模型，按 (orientation, duration) 索引
    SUPPORTED_MODELS = {
        ("portrait", 10):  "sora-2-portrait-10s-guanzhuan",
        ("portrait", 15):  "sora-2-portrait-15s-guanzhuan",
        ("landscape", 10): "sora-2-landscape-10s-guanzhuan",
        ("landscape", 15): "sora-2-landscape-15s-guanzhuan",
    }

    @property
    def provider_name(self) -> str:
        return "斑点蛙 API"

    @property
    def base_url(self) -> str:
        return ApiUrls.BANDIANWA

    def create_task(
        self,
        prompt: str,
        orientation: str = "portrait",
        duration: int = 10,
        **kwargs,
    ) -> Sora2Task:
        """
        创建任务。

        模型由基类 resolve_model(orientation, duration) 自动选取。

        - 图生视频：按斑点蛙文档使用 multipart/form-data 提交到 POST /v1/videos
        - 文生视频：沿用与大洋芋兼容的 JSON 提交逻辑
        """
        model = self.resolve_model(orientation, duration)
        image_path: Optional[str] = kwargs.get("image_path")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }
        url = f"{self.base_url.rstrip('/')}/v1/videos"

        if image_path and os.path.isfile(image_path):
            return self._create_task_image(url, headers, prompt, model, image_path, kwargs)
        return self._create_task_text(url, headers, prompt, model)

    def _create_task_image(
        self,
        url: str,
        headers: dict,
        prompt: str,
        model: str,
        image_path: str,
        kwargs: dict,
    ) -> Sora2Task:
        """图生视频：POST multipart/form-data"""
        size = kwargs.get("size")
        seconds = kwargs.get("seconds")
        if seconds is None:
            seconds = self._infer_seconds_from_model(model)

        with open(image_path, "rb") as file_obj:
            file_name = os.path.basename(image_path)
            files = {
                "input_reference": (file_name, file_obj),
            }
            data = {
                "model": model,
                "prompt": prompt,
                "n": "1",
            }
            if seconds is not None:
                data["seconds"] = str(seconds)
            if size:
                data["size"] = str(size)

            try:
                logger.info(
                    f"[{self.provider_name}] 图生视频 | URL: {url} | "
                    f"model={model} | file={file_name}"
                )
                logger.info(f"[{self.provider_name}] 请求头: {headers}")
                logger.info(f"[{self.provider_name}] 表单数据: {data}")

                resp = requests.post(url, headers=headers, files=files, data=data, timeout=120)
                logger.info(f"[{self.provider_name}] 响应状态码: {resp.status_code}")
                logger.info(f"[{self.provider_name}] 响应体: {resp.text[:500]}")
                resp.raise_for_status()
                payload = resp.json()
                return self._parse_create_response(payload, prompt)
            except requests.exceptions.HTTPError as exc:
                error_message = _read_error_message(exc)
                logger.error(
                    f"[{self.provider_name}] 图生视频失败 | "
                    f"{exc.response.status_code} | {error_message}"
                )
                return Sora2Task(
                    task_id="",
                    status=Sora2TaskStatus.FAILED,
                    prompt=prompt,
                    error_message=error_message or str(exc),
                )
            except Exception as exc:
                logger.error(f"[{self.provider_name}] 图生视频异常 | {type(exc).__name__}: {exc}")
                return Sora2Task(
                    task_id="",
                    status=Sora2TaskStatus.FAILED,
                    prompt=prompt,
                    error_message=str(exc),
                )

    @staticmethod
    def _infer_seconds_from_model(model: str) -> Optional[int]:
        if not model:
            return None
        for token in model.split("-"):
            if token.endswith("s") and token[:-1].isdigit():
                return int(token[:-1])
        return None
