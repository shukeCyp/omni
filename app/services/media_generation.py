"""统一图片/视频生成入口。

上游只关心生成请求参数；渠道选择、实例化与调用由注册表和各自生成器负责。
"""

from __future__ import annotations

import base64
import os
import tempfile
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

from ..constants import SettingKeys
from ..logger import logger
from .gpt_image import GptImageBandianwa, GptImageXiaobanshou
from .nanobanana import NanoBananaGlinCustom, NanoBananaXiaobanshou, NanoBananaYunwu, NanoBananaBandianwa
from .omni import OmniCloudy
from .sora2 import (
    Sora2Bandianwa,
    Sora2Dayangyu,
    Sora2TaskStatus,
    Sora2Xiaobanshou,
)
from .veo import VeoHetang, VeoBandianwa, VeoXiaobanshou, VeoZyg, VeoChaowen, VeoHolo, VeoCatking

_IMAGE_EXT_MAP = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


@dataclass(frozen=True)
class GeneratorOption:
    """前端可见的生成器选项。"""

    platform: str
    provider: str
    platform_label: str
    provider_label: str
    configured: bool
    kind: str

    @property
    def label(self) -> str:
        return f"{self.platform_label} / {self.provider_label}"


@dataclass
class ImageGenerationRequest:
    prompt: str
    ref_images: list
    aspect_ratio: str = "9:16"
    image_size: str = "1K"
    download_dir: Optional[Path] = None


@dataclass
class ImageGenerationResult:
    success: bool
    image_data: Optional[str] = None
    mime_type: Optional[str] = None
    file_path: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class VideoGenerationRequest:
    prompt: str
    ref_images: list
    orientation: str = "portrait"
    duration: int = 10
    resolution: str = "720P"
    generation_mode: str = "components"
    input_video: Optional[str] = None
    download_dir: Optional[Path] = None


@dataclass
class VideoGenerationResult:
    success: bool
    video_url: Optional[str] = None
    file_path: Optional[str] = None
    error_message: Optional[str] = None


class BaseGenerator(ABC):
    """生成器基类。"""

    kind: str = ""
    platform: str = ""
    provider: str = ""
    platform_label: str = ""
    provider_label: str = ""
    setting_key: str = ""

    def get_api_key(self, settings: dict) -> str:
        return (settings.get(self.setting_key) or "").strip()

    def is_configured(self, settings: dict) -> bool:
        return bool(self.get_api_key(settings))

    def get_missing_key_message(self) -> str:
        return f"未配置 {self.provider_label} API Key，请前往设置页面配置"

    def to_option(self, settings: dict) -> GeneratorOption:
        return GeneratorOption(
            platform=self.platform,
            provider=self.provider,
            platform_label=self.platform_label,
            provider_label=self.provider_label,
            configured=self.is_configured(settings),
            kind=self.kind,
        )


class BaseImageGenerator(BaseGenerator, ABC):
    kind = "image"

    @abstractmethod
    def generate(self, request: ImageGenerationRequest, settings: dict) -> ImageGenerationResult:
        raise NotImplementedError


class BaseVideoGenerator(BaseGenerator, ABC):
    kind = "video"

    @abstractmethod
    def generate(self, request: VideoGenerationRequest, settings: dict) -> VideoGenerationResult:
        raise NotImplementedError


def _save_base64_image(image_data: str, mime_type: str, download_dir: Path, prefix: str) -> str:
    download_dir.mkdir(parents=True, exist_ok=True)
    ext = _IMAGE_EXT_MAP.get(mime_type or "", ".png")
    filename = f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{uuid.uuid4().hex[:6]}{ext}"
    file_path = download_dir / filename
    file_path.write_bytes(base64.b64decode(image_data))
    return str(file_path)


def _download_remote_file(url: str, download_dir: Path, prefix: str, default_ext: str = ".mp4") -> str:
    download_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}{default_ext}"
    file_path = download_dir / filename
    with requests.get(url, timeout=120, stream=True) as response:
        response.raise_for_status()
        with open(file_path, "wb") as handle:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    handle.write(chunk)
    return str(file_path)


def _write_temp_image(ref_images: list) -> Optional[str]:
    if not ref_images:
        return None
    image = ref_images[0]
    image_data = image.get("base64", "")
    if not image_data:
        return None

    ext = _IMAGE_EXT_MAP.get(image.get("mime", "image/png"), ".png")
    tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
    try:
        tmp.write(base64.b64decode(image_data))
        tmp.flush()
        return tmp.name
    finally:
        tmp.close()


def _write_temp_images(ref_images: list) -> list[str]:
    paths = []
    for image in ref_images or []:
        image_data = image.get("base64", "")
        if not image_data:
            continue
        ext = _IMAGE_EXT_MAP.get(image.get("mime", "image/png"), ".png")
        tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
        try:
            tmp.write(base64.b64decode(image_data))
            tmp.flush()
            paths.append(tmp.name)
        finally:
            tmp.close()
    return paths


def _is_invalid_bearer_token(value: str) -> bool:
    token = (value or "").strip()
    return (not token) or (not token.isascii()) or any(ch.isspace() for ch in token)


def _poll_sora_task(service, task_id: str, timeout_seconds: int = 900, interval_seconds: int = 5):
    deadline = time.time() + timeout_seconds
    last_task = None
    while time.time() < deadline:
        last_task = service.query_task(task_id)
        if last_task.status == Sora2TaskStatus.COMPLETED:
            return last_task
        if last_task.status == Sora2TaskStatus.FAILED:
            return last_task
        time.sleep(interval_seconds)
    return last_task


class NanoBananaYunwuGenerator(BaseImageGenerator):
    platform = "nanobanana"
    provider = "yunwu"
    platform_label = "香蕉生图"
    provider_label = "YW"
    setting_key = SettingKeys.YUNWU_API_KEY

    def generate(self, request: ImageGenerationRequest, settings: dict) -> ImageGenerationResult:
        api_key = self.get_api_key(settings)
        if not api_key:
            return ImageGenerationResult(success=False, error_message=self.get_missing_key_message())

        service = NanoBananaYunwu(api_key)
        kwargs = {
            "ref_images": request.ref_images or [],
            "download_dir": request.download_dir,
        }

        result = service.generate(
            prompt=request.prompt,
            aspect_ratio=request.aspect_ratio,
            image_size=request.image_size,
            **kwargs,
        )
        if not result.success:
            return ImageGenerationResult(success=False, error_message=result.error_message)

        file_path = result.file_path
        if not file_path and result.image_data and result.mime_type and request.download_dir:
            file_path = _save_base64_image(
                result.image_data,
                result.mime_type,
                request.download_dir,
                "nanobanana_yw",
            )

        return ImageGenerationResult(
            success=True,
            image_data=result.image_data,
            mime_type=result.mime_type,
            file_path=file_path,
        )


class NanoBananaXiaobanshouGenerator(BaseImageGenerator):
    platform = "nanobanana"
    provider = "xiaobanshou"
    platform_label = "香蕉生图"
    provider_label = "XBS"
    setting_key = SettingKeys.XIAOBANSHOU_API_KEY

    def generate(self, request: ImageGenerationRequest, settings: dict) -> ImageGenerationResult:
        api_key = self.get_api_key(settings)
        if not api_key:
            return ImageGenerationResult(success=False, error_message=self.get_missing_key_message())

        service = NanoBananaXiaobanshou(api_key)
        result = service.generate(
            prompt=request.prompt,
            aspect_ratio=request.aspect_ratio,
            image_size=request.image_size,
            ref_images=request.ref_images or [],
        )
        if not result.success:
            return ImageGenerationResult(success=False, error_message=result.error_message)

        file_path = result.file_path
        if not file_path and result.image_data and result.mime_type and request.download_dir:
            file_path = _save_base64_image(
                result.image_data,
                result.mime_type,
                request.download_dir,
                "nanobanana_xbs",
            )

        return ImageGenerationResult(
            success=True,
            image_data=result.image_data,
            mime_type=result.mime_type,
            file_path=file_path,
        )


class NanoBananaHetangGenerator(BaseImageGenerator):
    platform = "nanobanana"
    provider = "hetang"
    platform_label = "香蕉生图"
    provider_label = "荷塘"
    setting_key = SettingKeys.HETANG_VEO_API_KEY

    def get_base_url(self, settings: dict) -> str:
        return (settings.get(SettingKeys.HETANG_VEO_BASE_URL) or "").strip().rstrip("/")

    def is_configured(self, settings: dict) -> bool:
        return bool(self.get_api_key(settings) and self.get_base_url(settings))

    def get_missing_key_message(self) -> str:
        return "未配置荷塘 Base URL 或 API Key，请前往设置页面配置"

    def generate(self, request: ImageGenerationRequest, settings: dict) -> ImageGenerationResult:
        api_key = self.get_api_key(settings)
        base_url = self.get_base_url(settings)
        if not api_key or not base_url:
            return ImageGenerationResult(success=False, error_message=self.get_missing_key_message())

        service = NanoBananaGlinCustom(api_key, base_url)
        result = service.generate(
            prompt=request.prompt,
            aspect_ratio=request.aspect_ratio,
            image_size=request.image_size,
            ref_images=request.ref_images or [],
            download_dir=str(request.download_dir) if request.download_dir else None,
        )
        if not result.success:
            return ImageGenerationResult(success=False, error_message=result.error_message)

        file_path = result.file_path
        if not file_path and result.image_data and result.mime_type and request.download_dir:
            file_path = _save_base64_image(
                result.image_data,
                result.mime_type,
                request.download_dir,
                "nanobanana_hetang",
            )

        return ImageGenerationResult(
            success=True,
            image_data=result.image_data,
            mime_type=result.mime_type,
            file_path=file_path,
        )


class NanoBananaBandianwaGenerator(BaseImageGenerator):
    platform = "nanobanana"
    provider = "bandianwa"
    platform_label = "香蕉生图"
    provider_label = "BDW"
    setting_key = SettingKeys.BANDIANWA_API_KEY

    def generate(self, request: ImageGenerationRequest, settings: dict) -> ImageGenerationResult:
        api_key = self.get_api_key(settings)
        if not api_key:
            return ImageGenerationResult(success=False, error_message=self.get_missing_key_message())

        service = NanoBananaBandianwa(api_key)
        kwargs = {
            "ref_images": request.ref_images or [],
            "download_dir": request.download_dir,
        }

        result = service.generate(
            prompt=request.prompt,
            aspect_ratio=request.aspect_ratio,
            image_size=request.image_size,
            **kwargs,
        )
        if not result.success:
            return ImageGenerationResult(success=False, error_message=result.error_message)

        file_path = result.file_path
        if not file_path and result.image_data and result.mime_type and request.download_dir:
            file_path = _save_base64_image(
                result.image_data,
                result.mime_type,
                request.download_dir,
                "nanobanana_bdw",
            )

        return ImageGenerationResult(
            success=True,
            image_data=result.image_data,
            mime_type=result.mime_type,
            file_path=file_path,
        )


class GptImageBandianwaGenerator(BaseImageGenerator):
    platform = "gpt-image"
    provider = "bandianwa"
    platform_label = "GPT 图片"
    provider_label = "BDW"
    setting_key = SettingKeys.BANDIANWA_API_KEY

    def generate(self, request: ImageGenerationRequest, settings: dict) -> ImageGenerationResult:
        api_key = self.get_api_key(settings)
        if not api_key:
            return ImageGenerationResult(success=False, error_message=self.get_missing_key_message())

        service = GptImageBandianwa(api_key)
        result = service.generate(
            prompt=request.prompt,
            aspect_ratio=request.aspect_ratio,
            image_size=request.image_size,
            ref_images=request.ref_images or [],
            download_dir=request.download_dir,
        )
        if not result.success:
            return ImageGenerationResult(success=False, error_message=result.error_message)

        file_path = result.file_path
        if not file_path and result.image_data and result.mime_type and request.download_dir:
            file_path = _save_base64_image(
                result.image_data,
                result.mime_type,
                request.download_dir,
                "gpt_image_bdw",
            )

        return ImageGenerationResult(
            success=True,
            image_data=result.image_data,
            mime_type=result.mime_type,
            file_path=file_path,
        )


class GptImageXiaobanshouGenerator(BaseImageGenerator):
    platform = "gpt-image"
    provider = "xiaobanshou"
    platform_label = "GPT 图片"
    provider_label = "XBS"
    setting_key = SettingKeys.XIAOBANSHOU_API_KEY

    def generate(self, request: ImageGenerationRequest, settings: dict) -> ImageGenerationResult:
        api_key = self.get_api_key(settings)
        if not api_key:
            return ImageGenerationResult(success=False, error_message=self.get_missing_key_message())

        service = GptImageXiaobanshou(api_key)
        result = service.generate(
            prompt=request.prompt,
            aspect_ratio=request.aspect_ratio,
            image_size=request.image_size,
            ref_images=request.ref_images or [],
            download_dir=request.download_dir,
        )
        if not result.success:
            return ImageGenerationResult(success=False, error_message=result.error_message)

        file_path = result.file_path
        if not file_path and result.image_data and result.mime_type and request.download_dir:
            file_path = _save_base64_image(
                result.image_data,
                result.mime_type,
                request.download_dir,
                "gpt_image_xbs",
            )

        return ImageGenerationResult(
            success=True,
            image_data=result.image_data,
            mime_type=result.mime_type,
            file_path=file_path,
        )


class HetangVeo3Generator(BaseVideoGenerator):
    platform = "veo3"
    provider = "hetang"
    platform_label = "VEO3"
    provider_label = "荷塘"
    setting_key = SettingKeys.HETANG_VEO_API_KEY

    def get_base_url(self, settings: dict) -> str:
        return (settings.get(SettingKeys.HETANG_VEO_BASE_URL) or "").strip().rstrip("/")

    def is_configured(self, settings: dict) -> bool:
        return bool(self.get_api_key(settings) and self.get_base_url(settings))

    def get_missing_key_message(self) -> str:
        return "未配置荷塘 VEO 的 Base URL 或 API Key，请前往设置页面配置"

    def generate(self, request: VideoGenerationRequest, settings: dict) -> VideoGenerationResult:
        api_key = self.get_api_key(settings)
        base_url = self.get_base_url(settings)
        if not api_key or not base_url:
            return VideoGenerationResult(success=False, error_message=self.get_missing_key_message())

        image_path = _write_temp_image(request.ref_images)

        try:
            service = VeoHetang(api_key, base_url)
            result = service.generate(
                prompt=request.prompt,
                orientation=request.orientation,
                duration=request.duration,
                ref_image_path=image_path,
                download_dir=str(request.download_dir) if request.download_dir else None,
            )
            if not result.success:
                return VideoGenerationResult(success=False, error_message=result.error_message)

            return VideoGenerationResult(
                success=True,
                video_url=result.video_url,
                file_path=result.file_path,
            )
        except Exception as exc:
            logger.error(f"[{self.platform_label}/{self.provider_label}] 视频生成异常: {exc}")
            return VideoGenerationResult(success=False, error_message=str(exc))
        finally:
            if image_path and os.path.exists(image_path):
                try:
                    os.remove(image_path)
                except OSError:
                    pass


class BandianwaVeoGenerator(BaseVideoGenerator):
    platform = "veo3"
    provider = "bandianwa"
    platform_label = "VEO3"
    provider_label = "BDW"
    setting_key = SettingKeys.BANDIANWA_API_KEY

    def generate(self, request: VideoGenerationRequest, settings: dict) -> VideoGenerationResult:
        api_key = self.get_api_key(settings)
        if not api_key:
            return VideoGenerationResult(success=False, error_message=self.get_missing_key_message())

        image_path = _write_temp_image(request.ref_images)

        try:
            service = VeoBandianwa(api_key)
            result = service.generate(
                prompt=request.prompt,
                orientation=request.orientation,
                duration=request.duration,
                ref_image_path=image_path,
                download_dir=str(request.download_dir) if request.download_dir else None,
            )
            if not result.success:
                return VideoGenerationResult(success=False, error_message=result.error_message)

            return VideoGenerationResult(
                success=True,
                video_url=result.video_url,
                file_path=result.file_path,
            )
        except Exception as exc:
            logger.error(f"[{self.platform_label}/{self.provider_label}] 视频生成异常: {exc}")
            return VideoGenerationResult(success=False, error_message=str(exc))
        finally:
            if image_path and os.path.exists(image_path):
                try:
                    os.remove(image_path)
                except OSError:
                    pass


class CloudyOmniGenerator(BaseVideoGenerator):
    platform = "omni"
    provider = "cloudy"
    platform_label = "Omni"
    provider_label = "HOLO"
    setting_key = SettingKeys.HOLO_VEO_API_KEY

    def get_base_url(self, settings: dict) -> str:
        return ""

    def generate(self, request: VideoGenerationRequest, settings: dict) -> VideoGenerationResult:
        api_key = self.get_api_key(settings)
        if not api_key:
            return VideoGenerationResult(success=False, error_message=self.get_missing_key_message())
        mode = (request.generation_mode or "components").strip() or "components"
        if mode in {"components", "edit"} and len(request.ref_images or []) > 3:
            return VideoGenerationResult(success=False, error_message="Omni HOLO 最多支持 3 张参考图")
        if mode == "components" and not request.ref_images:
            return VideoGenerationResult(success=False, error_message="多参考视频至少需要 1 张参考图")
        if mode == "edit" and not (request.input_video or "").strip():
            return VideoGenerationResult(success=False, error_message="视频编辑需要填写源视频 URL")

        image_paths = _write_temp_images(request.ref_images)
        try:
            if len(image_paths) != len(request.ref_images):
                return VideoGenerationResult(success=False, error_message="参考图数据无效")
            result = OmniCloudy(api_key, self.get_base_url(settings)).generate(
                prompt=request.prompt,
                orientation=request.orientation,
                duration=request.duration,
                resolution=request.resolution,
                ref_image_paths=image_paths,
                input_video=request.input_video,
                mode=mode,
                download_dir=str(request.download_dir) if request.download_dir else None,
            )
            return VideoGenerationResult(
                success=result.success,
                video_url=result.video_url,
                file_path=result.file_path,
                error_message=result.error_message,
            )
        except Exception as exc:
            logger.error(f"[{self.platform_label}/{self.provider_label}] 视频生成异常: {exc}")
            return VideoGenerationResult(success=False, error_message=str(exc))
        finally:
            for image_path in image_paths:
                if os.path.exists(image_path):
                    try:
                        os.remove(image_path)
                    except OSError:
                        pass


class XiaobanshouVeoGenerator(BaseVideoGenerator):
    platform = "veo3"
    provider = "xiaobanshou"
    platform_label = "VEO3"
    provider_label = "XBS"
    setting_key = SettingKeys.XIAOBANSHOU_API_KEY

    def generate(self, request: VideoGenerationRequest, settings: dict) -> VideoGenerationResult:
        api_key = self.get_api_key(settings)
        if not api_key:
            return VideoGenerationResult(success=False, error_message=self.get_missing_key_message())

        image_path = _write_temp_image(request.ref_images)

        try:
            service = VeoXiaobanshou(api_key)
            result = service.generate(
                prompt=request.prompt,
                orientation=request.orientation,
                duration=request.duration,
                ref_image_path=image_path,
                download_dir=str(request.download_dir) if request.download_dir else None,
            )
            if not result.success:
                return VideoGenerationResult(success=False, error_message=result.error_message)

            return VideoGenerationResult(
                success=True,
                video_url=result.video_url,
                file_path=result.file_path,
            )
        except Exception as exc:
            logger.error(f"[{self.platform_label}/{self.provider_label}] 视频生成异常: {exc}")
            return VideoGenerationResult(success=False, error_message=str(exc))
        finally:
            if image_path and os.path.exists(image_path):
                try:
                    os.remove(image_path)
                except OSError:
                    pass


class ZygVeoGenerator(BaseVideoGenerator):
    platform = "veo3"
    provider = "zyg"
    platform_label = "VEO3"
    provider_label = "ZYG"
    setting_key = SettingKeys.ZYG_API_KEY

    def generate(self, request: VideoGenerationRequest, settings: dict) -> VideoGenerationResult:
        api_key = self.get_api_key(settings)
        if not api_key:
            return VideoGenerationResult(success=False, error_message=self.get_missing_key_message())
        if _is_invalid_bearer_token(api_key):
            return VideoGenerationResult(
                success=False,
                error_message="ZYG API Key 配置异常：当前内容包含中文或空白字符，请在设置页重新粘贴正确的 API Key",
            )

        image_path = _write_temp_image(request.ref_images)

        try:
            service = VeoZyg(api_key)
            result = service.generate(
                prompt=request.prompt,
                orientation=request.orientation,
                duration=request.duration,
                ref_image_path=image_path,
                download_dir=str(request.download_dir) if request.download_dir else None,
            )
            if not result.success:
                return VideoGenerationResult(success=False, error_message=result.error_message)

            return VideoGenerationResult(
                success=True,
                video_url=result.video_url,
                file_path=result.file_path,
            )
        except Exception as exc:
            logger.error(f"[{self.platform_label}/{self.provider_label}] 视频生成异常: {exc}")
            return VideoGenerationResult(success=False, error_message=str(exc))
        finally:
            if image_path and os.path.exists(image_path):
                try:
                    os.remove(image_path)
                except OSError:
                    pass


class ChaowenVeoGenerator(BaseVideoGenerator):
    platform = "veo3"
    provider = "chaowen"
    platform_label = "VEO3"
    provider_label = "CW"
    setting_key = SettingKeys.CHAOWEN_VEO_API_KEY

    def get_base_url(self, settings: dict) -> str:
        return (settings.get(SettingKeys.CHAOWEN_VEO_BASE_URL) or "").strip().rstrip("/")

    def generate(self, request: VideoGenerationRequest, settings: dict) -> VideoGenerationResult:
        api_key = self.get_api_key(settings)
        if not api_key:
            return VideoGenerationResult(success=False, error_message=self.get_missing_key_message())

        base_url = self.get_base_url(settings)
        image_path = _write_temp_image(request.ref_images)

        try:
            service = VeoChaowen(api_key, base_url)
            result = service.generate(
                prompt=request.prompt,
                orientation=request.orientation,
                duration=request.duration,
                ref_image_path=image_path,
                download_dir=str(request.download_dir) if request.download_dir else None,
            )
            if not result.success:
                return VideoGenerationResult(success=False, error_message=result.error_message)

            return VideoGenerationResult(
                success=True,
                video_url=result.video_url,
                file_path=result.file_path,
            )
        except Exception as exc:
            logger.error(f"[{self.platform_label}/{self.provider_label}] 视频生成异常: {exc}")
            return VideoGenerationResult(success=False, error_message=str(exc))
        finally:
            if image_path and os.path.exists(image_path):
                try:
                    os.remove(image_path)
                except OSError:
                    pass


class HoloVeoGenerator(BaseVideoGenerator):
    platform = "veo3"
    provider = "holo"
    platform_label = "VEO3"
    provider_label = "HOLO"
    setting_key = SettingKeys.HOLO_VEO_API_KEY

    def get_base_url(self, settings: dict) -> str:
        return (settings.get(SettingKeys.HOLO_VEO_BASE_URL) or "").strip().rstrip("/")

    def generate(self, request: VideoGenerationRequest, settings: dict) -> VideoGenerationResult:
        api_key = self.get_api_key(settings)
        if not api_key:
            return VideoGenerationResult(success=False, error_message=self.get_missing_key_message())

        base_url = self.get_base_url(settings)
        image_path = _write_temp_image(request.ref_images)

        try:
            service = VeoHolo(api_key, base_url)
            result = service.generate(
                prompt=request.prompt,
                orientation=request.orientation,
                duration=request.duration,
                ref_image_path=image_path,
                download_dir=str(request.download_dir) if request.download_dir else None,
            )
            if not result.success:
                return VideoGenerationResult(success=False, error_message=result.error_message)

            return VideoGenerationResult(
                success=True,
                video_url=result.video_url,
                file_path=result.file_path,
            )
        except Exception as exc:
            logger.error(f"[{self.platform_label}/{self.provider_label}] 视频生成异常: {exc}")
            return VideoGenerationResult(success=False, error_message=str(exc))
        finally:
            if image_path and os.path.exists(image_path):
                try:
                    os.remove(image_path)
                except OSError:
                    pass


class CatKingVeoGenerator(BaseVideoGenerator):
    platform = "veo3"
    provider = "catking"
    platform_label = "VEO3"
    provider_label = "CatKing"
    setting_key = SettingKeys.CATKING_VEO_API_KEY

    def get_base_url(self, settings: dict) -> str:
        return (settings.get(SettingKeys.CATKING_VEO_BASE_URL) or "").strip().rstrip("/")

    def generate(self, request: VideoGenerationRequest, settings: dict) -> VideoGenerationResult:
        api_key = self.get_api_key(settings)
        if not api_key:
            return VideoGenerationResult(success=False, error_message=self.get_missing_key_message())

        base_url = self.get_base_url(settings)
        image_path = _write_temp_image(request.ref_images)

        try:
            service = VeoCatking(api_key, base_url)
            result = service.generate(
                prompt=request.prompt,
                orientation=request.orientation,
                duration=request.duration,
                ref_image_path=image_path,
                download_dir=str(request.download_dir) if request.download_dir else None,
            )
            if not result.success:
                return VideoGenerationResult(success=False, error_message=result.error_message)

            return VideoGenerationResult(
                success=True,
                video_url=result.video_url,
                file_path=result.file_path,
            )
        except Exception as exc:
            logger.error(f"[{self.platform_label}/{self.provider_label}] 视频生成异常: {exc}")
            return VideoGenerationResult(success=False, error_message=str(exc))
        finally:
            if image_path and os.path.exists(image_path):
                try:
                    os.remove(image_path)
                except OSError:
                    pass


class BaseSora2Generator(BaseVideoGenerator, ABC):
    platform = "sora2"
    platform_label = "Sora2"

    @abstractmethod
    def create_service(self, api_key: str):
        raise NotImplementedError

    @abstractmethod
    def build_create_kwargs(self, request: VideoGenerationRequest, image_path: Optional[str]) -> dict:
        raise NotImplementedError

    def generate(self, request: VideoGenerationRequest, settings: dict) -> VideoGenerationResult:
        api_key = self.get_api_key(settings)
        if not api_key:
            return VideoGenerationResult(success=False, error_message=self.get_missing_key_message())

        image_path = _write_temp_image(request.ref_images)
        try:
            service = self.create_service(api_key)
            task = service.create_task(request.prompt, **self.build_create_kwargs(request, image_path))
            if task.status == Sora2TaskStatus.FAILED:
                return VideoGenerationResult(success=False, error_message=task.error_message or "视频任务创建失败")

            if task.video_url:
                video_url = task.video_url
            else:
                if not task.task_id:
                    return VideoGenerationResult(success=False, error_message=task.error_message or "未返回任务 ID")
                queried = _poll_sora_task(service, task.task_id)
                if queried is None:
                    return VideoGenerationResult(success=False, error_message="任务轮询失败")
                if queried.status != Sora2TaskStatus.COMPLETED or not queried.video_url:
                    return VideoGenerationResult(
                        success=False,
                        error_message=queried.error_message or "视频任务未完成",
                    )
                video_url = queried.video_url

            file_path = None
            if request.download_dir:
                file_path = _download_remote_file(video_url, request.download_dir, f"sora2_{self.provider}")

            return VideoGenerationResult(success=True, video_url=video_url, file_path=file_path)
        except Exception as exc:
            logger.error(f"[{self.platform_label}/{self.provider_label}] 视频生成异常: {exc}")
            return VideoGenerationResult(success=False, error_message=str(exc))
        finally:
            if image_path and os.path.exists(image_path):
                try:
                    os.remove(image_path)
                except OSError:
                    pass


class Sora2DayangyuGenerator(BaseSora2Generator):
    provider = "dayangyu"
    provider_label = "DYY"
    setting_key = SettingKeys.DAYANGYU_API_KEY

    def create_service(self, api_key: str):
        return Sora2Dayangyu(api_key)

    def build_create_kwargs(self, request: VideoGenerationRequest, image_path: Optional[str]) -> dict:
        # 模型由 Sora2Dayangyu.resolve_model() 根据 orientation/duration 自动选取
        kwargs = {
            "orientation": request.orientation,
            "duration": request.duration,
        }
        if image_path:
            kwargs["image_path"] = image_path
        return kwargs


class Sora2XiaobanshouGenerator(BaseSora2Generator):
    provider = "xiaobanshou"
    provider_label = "XBS"
    setting_key = SettingKeys.XIAOBANSHOU_API_KEY

    def create_service(self, api_key: str):
        return Sora2Xiaobanshou(api_key)

    def build_create_kwargs(self, request: VideoGenerationRequest, image_path: Optional[str]) -> dict:
        # 模型由 Sora2Xiaobanshou.resolve_model() 根据 orientation/duration 自动选取
        kwargs = {
            "orientation": request.orientation,
            "duration": request.duration,
        }
        if image_path:
            kwargs["image_path"] = image_path
        return kwargs


class Sora2BandianwaGenerator(BaseSora2Generator):
    provider = "bandianwa"
    provider_label = "BDW"
    setting_key = SettingKeys.BANDIANWA_API_KEY

    def create_service(self, api_key: str):
        return Sora2Bandianwa(api_key)

    def build_create_kwargs(self, request: VideoGenerationRequest, image_path: Optional[str]) -> dict:
        # 模型由 Sora2Bandianwa.resolve_model() 根据 orientation/duration 自动选取
        kwargs = {
            "orientation": request.orientation,
            "duration": request.duration,
        }
        if image_path:
            kwargs["image_path"] = image_path
        return kwargs


class MediaGenerationRegistry:
    """图片/视频生成器注册表。"""

    def __init__(self):
        self._image_generators: dict[tuple[str, str], BaseImageGenerator] = {}
        self._video_generators: dict[tuple[str, str], BaseVideoGenerator] = {}

    def register_image(self, generator: BaseImageGenerator) -> None:
        self._image_generators[(generator.platform, generator.provider)] = generator

    def register_video(self, generator: BaseVideoGenerator) -> None:
        self._video_generators[(generator.platform, generator.provider)] = generator

    def get_image_generator(self, platform: str, provider: str) -> Optional[BaseImageGenerator]:
        return self._image_generators.get((platform, provider))

    def get_video_generator(self, platform: str, provider: str) -> Optional[BaseVideoGenerator]:
        return self._video_generators.get((platform, provider))

    @staticmethod
    def _clean(value: Optional[str]) -> str:
        return (value or "").strip()

    @staticmethod
    def _pick_from_platform(generators: dict, settings: dict, platform: str, provider: str = ""):
        matches = [generator for (item_platform, _), generator in generators.items() if item_platform == platform]
        if not matches:
            return None

        provider = (provider or "").strip()
        if provider:
            exact = next((generator for generator in matches if generator.provider == provider), None)
            if exact:
                return exact

        configured = next((generator for generator in matches if generator.is_configured(settings)), None)
        return configured or matches[0]

    @staticmethod
    def _pick_first_configured(generators: dict, settings: dict):
        return next((generator for generator in generators.values() if generator.is_configured(settings)), None)

    def _resolve_generator(self, generators: dict, settings: dict, platform: str, provider: str, candidates: list[tuple[str, str]]):
        platform = self._clean(platform)
        provider = self._clean(provider)
        
        logger.info(f"[Registry] _resolve_generator 调用 | platform='{platform}', provider='{provider}'")
        logger.info(f"[Registry] candidates={candidates}")

        if platform:
            if not provider:
                for candidate_platform, candidate_provider in candidates:
                    candidate_platform = self._clean(candidate_platform)
                    candidate_provider = self._clean(candidate_provider)
                    if candidate_platform == platform and candidate_provider:
                        provider = candidate_provider
                        logger.info(f"[Registry] 从 candidates 中获取 provider='{provider}'")
                        break
            generator = self._pick_from_platform(generators, settings, platform, provider)
            if generator:
                logger.info(f"[Registry] 选择生成器 | platform={generator.platform}, provider={generator.provider}")
                return generator, generator.platform, generator.provider
            logger.warning(f"[Registry] 未找到匹配的生成器 | platform={platform}, provider={provider}")
            return None, platform, provider

        for candidate_platform, candidate_provider in candidates:
            candidate_platform = self._clean(candidate_platform)
            candidate_provider = self._clean(candidate_provider)
            if not candidate_platform:
                continue
            generator = self._pick_from_platform(generators, settings, candidate_platform, candidate_provider)
            if generator:
                return generator, generator.platform, generator.provider

        generator = self._pick_first_configured(generators, settings)
        if generator:
            return generator, generator.platform, generator.provider

        generator = next(iter(generators.values()), None)
        if generator:
            return generator, generator.platform, generator.provider

        return None, platform, provider

    def resolve_image_generator(self, settings: dict, platform: str = "", provider: str = ""):
        legacy_image_platform, legacy_image_provider = self._legacy_image_candidate(settings)
        return self._resolve_generator(
            self._image_generators,
            settings,
            platform,
            provider,
            candidates=[
                (legacy_image_platform, legacy_image_provider),
                (
                    settings.get(SettingKeys.VIDEO_PRODUCT_IMAGE_PLATFORM, "nanobanana"),
                    settings.get(SettingKeys.VIDEO_PRODUCT_IMAGE_PROVIDER, ""),
                ),
            ],
        )

    @staticmethod
    def _legacy_image_candidate(settings: dict) -> tuple[str, str]:
        value = (settings.get(SettingKeys.NANOBANANA_MODEL, "") or "").strip()
        if value == "gpt-image:bandianwa":
            return "gpt-image", "bandianwa"
        if value == "gpt-image:xiaobanshou":
            return "gpt-image", "xiaobanshou"
        return "nanobanana", value

    def resolve_video_generator(self, settings: dict, platform: str = "", provider: str = ""):
        return self._resolve_generator(
            self._video_generators,
            settings,
            platform,
            provider,
            candidates=[("omni", "cloudy")],
        )

    def list_image_options(self, settings: dict) -> list[GeneratorOption]:
        return [generator.to_option(settings) for generator in self._image_generators.values()]

    def list_video_options(self, settings: dict) -> list[GeneratorOption]:
        return [generator.to_option(settings) for generator in self._video_generators.values()]


media_generation_registry = MediaGenerationRegistry()
media_generation_registry.register_video(CloudyOmniGenerator())
