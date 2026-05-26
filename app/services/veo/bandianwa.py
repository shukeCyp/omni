"""斑点蛙 API VEO 视频生成（异步任务型）"""

import base64
import os
import time
from typing import Optional

import requests

from ...logger import logger
from .base import VeoBase, VeoResult, VeoTask, VeoTaskStatus
from .utils import download_video

BDW_BASE = "https://api.hellobabygo.com"

# 任务状态
_PENDING_STATUSES = {"queued", "in_progress", "processing", "running"}
_FAILED_STATUSES = {"failed", "error", "cancelled"}

# 模型映射
# 文生视频使用普通模型；首尾帧模式使用带 -hd 后缀的模型标识。
_T2V_MODELS = {
    "portrait": "veo_3_1-fast-portrait",
    "landscape": "veo_3_1-fast-landscape",
}

# 图生视频模型（首尾帧模式）
_I2V_MODELS = {
    "portrait": "veo_3_1-fast-portrait-fl-hd",
    "landscape": "veo_3_1-fast-landscape-fl-hd",
}


class VeoBandianwa(VeoBase):
    """斑点蛙 API VEO 视频生成"""

    @property
    def provider_name(self) -> str:
        return "斑点蛙 API"

    @property
    def base_url(self) -> str:
        return BDW_BASE

    def generate(
        self,
        prompt: str,
        orientation: str = "portrait",
        duration: int = 10,
        ref_image_path: Optional[str] = None,
        download_dir: Optional[str] = None,
        **kwargs,
    ) -> VeoResult:
        """
        生成视频（异步任务型）。

        Args:
            prompt:          视频描述提示词
            orientation:     方向，portrait（竖屏）/ landscape（横屏）
            duration:        视频时长（秒）
            ref_image_path:  参考图片本地路径（图生视频时使用）
            download_dir:    视频下载目录
            **kwargs:
                quality: 保留兼容；当前不参与斑点蛙模型路由
        """
        # 斑点蛙 VEO 当前文生走普通模型，首尾帧走 -fl-hd 模型。
        if ref_image_path:
            model = _I2V_MODELS.get(orientation, _I2V_MODELS["portrait"])
        else:
            model = _T2V_MODELS.get(orientation, _T2V_MODELS["portrait"])

        # 构建请求体（所有参数必须平级）
        payload = {
            "model": model,
            "prompt": prompt,
            # 斑点蛙后端当前按 string 解析 seconds，number 会触发 invalid_json。
            "seconds": str(duration),
        }

        # 如果有参考图，添加到 payload
        if ref_image_path and os.path.isfile(ref_image_path):
            mime = "image/jpeg"
            with open(ref_image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode()
            payload["input_reference"] = f"data:{mime};base64,{img_b64}"

        # 提交任务
        task_id = self._submit_task(payload)
        if not task_id:
            return VeoResult(success=False, error_message="任务提交失败")

        # 轮询任务状态
        result = self._poll_task(task_id)
        if not result or not result.success:
            return result or VeoResult(success=False, error_message="任务轮询失败")

        # 如果配置了下载目录，下载视频
        if result.success and result.video_url and download_dir:
            result.file_path = download_video(
                result.video_url, download_dir, f"veo_bdw"
            )

        return result

    def _submit_task(self, payload: dict) -> Optional[str]:
        """提交异步任务"""
        url = f"{self.base_url.rstrip('/')}/v1/videos"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        mode = "图生视频" if payload.get("input_reference") else "文生视频"
        logger.info(
            f"[{self.provider_name}] VEO 请求 | "
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
        timeout_seconds: int = 600,
        interval_seconds: int = 35,
    ) -> Optional[VeoResult]:
        """轮询任务状态"""
        url = f"{self.base_url.rstrip('/')}/v1/videos/{task_id}"
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

                # 检查是否完成
                if status == "completed":
                    logger.info(f"[{self.provider_name}] 任务完成 | task_id={task_id}")
                    return self._extract_result(data)

                # 检查是否失败
                if status in _FAILED_STATUSES:
                    error_msg = self._extract_error_from_response(data)
                    logger.error(f"[{self.provider_name}] 任务失败 | task_id={task_id} | error={error_msg}")
                    return VeoResult(success=False, error_message=str(error_msg))

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

        return VeoResult(success=False, error_message="轮询视频结果超时")

    def _extract_result(self, data: dict) -> VeoResult:
        """从响应中提取视频结果"""
        try:
            # 尝试从 data 数组中获取视频 URL
            data_array = data.get("data")
            if isinstance(data_array, list) and data_array:
                first_item = data_array[0]
                if isinstance(first_item, dict):
                    video_url = first_item.get("url") or first_item.get("video_url")
                    if video_url:
                        logger.info(f"[{self.provider_name}] 成功获取视频 URL")
                        return VeoResult(success=True, video_url=video_url)

            # 尝试从顶层获取
            video_url = data.get("video_url") or data.get("url")
            if video_url:
                logger.info(f"[{self.provider_name}] 成功获取视频 URL（顶层）")
                return VeoResult(success=True, video_url=video_url)

            return VeoResult(success=False, error_message="未找到视频数据")

        except Exception as exc:
            logger.error(f"[{self.provider_name}] 响应解析异常: {exc}")
            return VeoResult(success=False, error_message=f"响应解析失败: {exc}")

    @staticmethod
    def _extract_error_message(response) -> str:
        """从 HTTP 响应中提取错误信息"""
        try:
            body = response.json()
            error = body.get("error")
            if isinstance(error, dict):
                return error.get("message") or error.get("detail") or str(error)
            return body.get("message") or str(error) or response.text[:500]
        except Exception:
            return response.text[:500] if response.text else str(response)

    @staticmethod
    def _extract_error_from_response(data: dict) -> str:
        """从轮询响应中提取错误信息"""
        error = data.get("error")
        if isinstance(error, dict):
            return error.get("message") or error.get("detail") or str(error)
        if isinstance(error, str):
            return error
        return data.get("message") or "任务执行失败"
