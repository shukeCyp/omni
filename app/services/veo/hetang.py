"""荷塘渠道 VEO 生成"""

import json
import re
from typing import Optional

import requests

from ...logger import logger
from .base import VeoBase, VeoResult, VeoTask, VeoTaskStatus
from .utils import download_video


class VeoHetang(VeoBase):
    """荷塘渠道 — 基于 Chat Completions SSE 流式接口"""

    # 文生视频模型，按方向索引
    _T2V_MODELS = {
        "portrait":  "veo_3_1_t2v_fast_portrait",
        "landscape": "veo_3_1_t2v_fast_landscape",
    }

    # 图生视频模型，按方向索引
    _I2V_MODELS = {
        "portrait":  "veo_3_1_i2v_s_fast_portrait_fl",
        "landscape": "veo_3_1_i2v_s_fast_fl",
    }

    @property
    def provider_name(self) -> str:
        return "荷塘"

    @property
    def base_url(self) -> str:
        return self._base_url or ""

    def generate(
        self,
        prompt: str,
        orientation: str = "portrait",
        duration: int = 10,  # 荷塘渠道不支持自定义时长，模型固定输出约 8 秒，此参数保留仅为接口兼容
        ref_image_path: Optional[str] = None,
        download_dir: Optional[str] = None,
        **kwargs,
    ) -> VeoResult:
        if not self.api_key or not self.base_url:
            return VeoResult(
                success=False,
                error_message="未配置荷塘 Base URL 或 API Key",
            )

        # 根据是否有参考图片和方向选择模型
        if ref_image_path:
            model = self._I2V_MODELS.get(orientation, self._I2V_MODELS["portrait"])
            import base64, mimetypes
            mime = mimetypes.guess_type(ref_image_path)[0] or "image/jpeg"
            with open(ref_image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode()
            content = [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{img_b64}"}},
            ]
            messages = [{"role": "user", "content": content}]
        else:
            model = self._T2V_MODELS.get(orientation, self._T2V_MODELS["portrait"])
            messages = [{"role": "user", "content": prompt}]

        url = f"{self.base_url}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {"model": model, "messages": messages, "stream": True}

        try:
            logger.info(
                f"[VEO/{self.provider_name}] 开始生成 | model={model} | "
                f"orientation={orientation} | ref={'有' if ref_image_path else '无'}"
            )
            resp = requests.post(
                url, headers=headers, json=payload, stream=True, timeout=600
            )
            resp.raise_for_status()

            video_url = ""
            error_message = ""
            for line in resp.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data: "):
                    continue
                raw = line[6:].strip()
                if raw == "[DONE]":
                    break
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                choices = data.get("choices", [])
                if not choices:
                    continue
                delta = choices[0].get("delta", {})
                content_str = delta.get("content", "")
                if content_str:
                    match = re.search(r"<video\s+src='([^']+)'", content_str)
                    if match:
                        video_url = match.group(1)

                reasoning = delta.get("reasoning_content", "")
                if reasoning and ("❌" in reasoning or "失败" in reasoning):
                    error_message = reasoning.strip()

            if not video_url:
                return VeoResult(
                    success=False,
                    error_message=error_message or "未从响应中提取到视频链接",
                )

            file_path = None
            if download_dir:
                file_path = download_video(
                    video_url, download_dir, f"veo_hetang"
                )

            logger.info(f"[VEO/{self.provider_name}] 生成成功 | video_url={video_url}")
            return VeoResult(success=True, video_url=video_url, file_path=file_path)

        except requests.Timeout:
            return VeoResult(success=False, error_message="请求超时（600秒）")
        except Exception as exc:
            logger.error(f"[VEO/{self.provider_name}] 生成异常: {exc}")
            return VeoResult(success=False, error_message=str(exc))
