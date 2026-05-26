"""大洋芋 API Sora2 生成（文生视频 / 图生视频 异步）"""

import os
from typing import Optional, Tuple

import requests

from ...constants import ApiUrls
from ...logger import logger
from .base import Sora2Base, Sora2Task, Sora2TaskStatus

def _map_status(api_status: str) -> Sora2TaskStatus:
    """将接口 status 映射为 Sora2TaskStatus"""
    s = (api_status or "").lower()
    if s in ("pending", "queued"):
        return Sora2TaskStatus.PENDING
    if s in ("processing", "running"):
        return Sora2TaskStatus.PROCESSING
    if s in ("success", "succeeded", "completed", "done"):
        return Sora2TaskStatus.COMPLETED
    if s in ("failed", "error", "cancelled"):
        return Sora2TaskStatus.FAILED
    return Sora2TaskStatus.PROCESSING


class Sora2Dayangyu(Sora2Base):
    """大洋芋 API Sora2 生成（文生视频 + 图生视频，异步）"""

    # 大洋芋支持的模型，按 (orientation, duration) 索引
    SUPPORTED_MODELS = {
        ("portrait", 10):  "sora2-portrait",
        ("portrait", 15):  "sora2-portrait-15s",
        ("landscape", 10): "sora2-landscape",
        ("landscape", 15): "sora2-landscape-15s",
    }

    @property
    def provider_name(self) -> str:
        return "大洋芋 API"

    @property
    def base_url(self) -> str:
        return ApiUrls.DAYANGYU

    def create_task(
        self,
        prompt: str,
        orientation: str = "portrait",
        duration: int = 10,
        **kwargs
    ) -> Sora2Task:
        """
        创建生成任务（文生视频或图生视频）。

        模型由基类 resolve_model(orientation, duration) 自动选取。

        Args:
            prompt: 视频描述 / 图生时的风格描述
            orientation: 方向，"portrait"（竖屏）或 "landscape"（横屏）
            duration: 时长（秒），支持 10 / 15
            **kwargs: image_path（图生时必填）, size, seconds
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

    def _create_task_text(self, url: str, headers: dict, prompt: str, model: str) -> Sora2Task:
        """文生视频：POST application/json"""
        headers["Content-Type"] = "application/json"
        body = {"prompt": prompt, "model": model}
        try:
            logger.info(f"[{self.provider_name}] 文生视频 | URL: {url} | model={model} | prompt={prompt[:50]}...")
            logger.info(f"[{self.provider_name}] 请求头: {headers}")
            logger.info(f"[{self.provider_name}] 请求体: {body}")
            resp = requests.post(url, json=body, headers=headers, timeout=60)
            logger.info(f"[{self.provider_name}] 响应状态码: {resp.status_code}")
            logger.info(f"[{self.provider_name}] 响应体: {resp.text[:500]}")
            resp.raise_for_status()
            data = resp.json()
            return self._parse_create_response(data, prompt)
        except requests.exceptions.HTTPError as e:
            msg = _read_error_message(e)
            logger.error(f"[{self.provider_name}] 文生视频失败 | {e.response.status_code} | {msg}")
            return Sora2Task(
                task_id="",
                status=Sora2TaskStatus.FAILED,
                prompt=prompt,
                error_message=msg or str(e),
            )
        except Exception as e:
            logger.error(f"[{self.provider_name}] 文生视频异常 | {type(e).__name__}: {e}")
            return Sora2Task(
                task_id="",
                status=Sora2TaskStatus.FAILED,
                prompt=prompt,
                error_message=str(e),
            )

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
        size = kwargs.get("size")  # 可选，如 1280x720
        seconds = kwargs.get("seconds")  # 可选，如 "4"

        with open(image_path, "rb") as f:
            file_name = os.path.basename(image_path)
            files = {"input_reference": (file_name, f)}
            data: dict = {"prompt": prompt, "model": model}
            if size is not None:
                data["size"] = str(size)
            if seconds is not None:
                data["seconds"] = str(seconds)
            try:
                logger.info(f"[{self.provider_name}] 图生视频 | URL: {url} | model={model} | file={file_name}")
                logger.info(f"[{self.provider_name}] 请求头: {headers}")
                logger.info(f"[{self.provider_name}] 表单数据: {data}")
                resp = requests.post(url, headers=headers, files=files, data=data, timeout=120)
                logger.info(f"[{self.provider_name}] 响应状态码: {resp.status_code}")
                logger.info(f"[{self.provider_name}] 响应体: {resp.text[:500]}")
                resp.raise_for_status()
                result = resp.json()
                return self._parse_create_response(result, prompt)
            except requests.exceptions.HTTPError as e:
                msg = _read_error_message(e)
                logger.error(f"[{self.provider_name}] 图生视频失败 | {e.response.status_code} | {msg}")
                return Sora2Task(
                    task_id="",
                    status=Sora2TaskStatus.FAILED,
                    prompt=prompt,
                    error_message=msg or str(e),
                )
            except Exception as e:
                logger.error(f"[{self.provider_name}] 图生视频异常 | {type(e).__name__}: {e}")
                return Sora2Task(
                    task_id="",
                    status=Sora2TaskStatus.FAILED,
                    prompt=prompt,
                    error_message=str(e),
                )

    def _parse_create_response(self, data: dict, prompt: str) -> Sora2Task:
        """解析创建任务响应"""
        task_id = data.get("id") or ""
        status = _map_status(data.get("status") or "pending")
        progress = int(data.get("progress") or 0)
        created_at = data.get("created_at")
        size = data.get("size")
        return Sora2Task(
            task_id=task_id,
            status=status,
            prompt=prompt,
            progress=progress,
            created_at=str(created_at) if created_at is not None else None,
            video_url=data.get("video_url") if status == Sora2TaskStatus.COMPLETED else None,
        )

    def query_task(self, task_id: str) -> Sora2Task:
        """查询任务状态。任务完成后会返回 video_url。"""
        if not task_id or not task_id.strip():
            return Sora2Task(
                task_id="",
                status=Sora2TaskStatus.FAILED,
                prompt="",
                error_message="任务 ID 为空",
            )
        url = f"{self.base_url.rstrip('/')}/v1/videos/{task_id.strip()}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }
        try:
            logger.info(f"[{self.provider_name}] 查询任务 | GET {url}")
            resp = requests.get(url, headers=headers, timeout=30)
            logger.info(f"[{self.provider_name}] 响应状态码: {resp.status_code}")
            logger.info(f"[{self.provider_name}] 响应体: {resp.text[:500]}")
            resp.raise_for_status()
            data = resp.json()
            return self._parse_query_response(data, task_id)
        except requests.exceptions.HTTPError as e:
            msg = _read_error_message(e)
            logger.error(f"[{self.provider_name}] 查询任务失败 | {task_id} | {e.response.status_code} | {msg}")
            return Sora2Task(
                task_id=task_id,
                status=Sora2TaskStatus.FAILED,
                prompt="",
                error_message=msg or str(e),
            )
        except Exception as e:
            if self.is_transient_query_exception(e):
                logger.warning(f"[{self.provider_name}] 查询任务网络异常，跳过本次轮询 | {task_id} | {type(e).__name__}: {e}")
                return self.build_transient_query_task(task_id, e)
            logger.error(f"[{self.provider_name}] 查询任务异常 | {task_id} | {type(e).__name__}: {e}")
            return Sora2Task(
                task_id=task_id,
                status=Sora2TaskStatus.FAILED,
                prompt="",
                error_message=str(e),
            )

    def _parse_query_response(self, data: dict, task_id: str) -> Sora2Task:
        """解析任务查询响应"""
        status = _map_status(data.get("status") or "pending")
        progress = int(data.get("progress") or 0)
        video_url = data.get("video_url") or None
        created_at = data.get("created_at")
        completed_at = data.get("completed_at")
        return Sora2Task(
            task_id=data.get("id") or task_id,
            status=status,
            prompt="",
            video_url=video_url,
            progress=progress,
            created_at=str(created_at) if created_at is not None else None,
            completed_at=str(completed_at) if completed_at is not None else None,
        )

    def get_video_content(self, task_id: str) -> Tuple[Optional[bytes], Optional[str], Optional[str]]:
        """
        查看视频内容（GET /v1/videos/{task_id}/content）。
        接口较慢，建议优先使用 query_task 返回的 video_url 拉取。

        Returns:
            (data, content_type, error_message)
            - 成功: (bytes, content_type, None)
            - 失败: (None, None, error_message)
        """
        if not task_id or not task_id.strip():
            return (None, None, "任务 ID 为空")
        url = f"{self.base_url.rstrip('/')}/v1/videos/{task_id.strip()}/content"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json, */*",
        }
        try:
            logger.info(f"[{self.provider_name}] 查看视频内容 | GET {url}")
            with requests.get(url, headers=headers, timeout=120) as resp:
                logger.info(f"[{self.provider_name}] 响应状态码: {resp.status_code} | Content-Type: {resp.headers.get('Content-Type', 'N/A')} | 大小: {len(resp.content)} bytes")
                resp.raise_for_status()
                content_type = (resp.headers.get("Content-Type") or "").split(";")[0].strip()
                return (resp.content, content_type or "application/octet-stream", None)
        except requests.exceptions.HTTPError as e:
            msg = _read_error_message(e)
            logger.error(f"[{self.provider_name}] 查看视频内容失败 | {task_id} | {e.response.status_code} | {msg}")
            return (None, None, msg or str(e))
        except Exception as e:
            logger.error(f"[{self.provider_name}] 查看视频内容异常 | {task_id} | {type(e).__name__}: {e}")
            return (None, None, str(e))


def _read_error_message(e: requests.exceptions.HTTPError) -> str:
    """从 HTTPError 响应中读取错误信息"""
    try:
        body = e.response.json()
        if isinstance(body, dict):
            error = body.get("error")
            if isinstance(error, dict):
                return error.get("message") or error.get("detail") or str(error)
            return body.get("message") or error or body.get("msg") or e.response.text[:500]
        return e.response.text[:500]
    except Exception:
        return (e.response.text or str(e))[:500]
