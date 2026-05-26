import os
import shutil
import time
from pathlib import Path

from .config import BASE_DIR
from .constants import SettingKeys
from .database import get_setting, set_setting, get_all_settings
from .logger import logger
from .services.media_generation import (
    ImageGenerationRequest,
    VideoGenerationRequest,
    media_generation_registry,
)
from .services.nanobanana import NanoBananaYunwu, NanoBananaGlinCustom, NanoBananaXiaobanshou
from .services.sora2 import Sora2Dayangyu, Sora2Xiaobanshou, Sora2Bandianwa


def get_default_download_dir() -> Path:
    """~/Downloads/HetangOmni"""
    return Path.home() / "Downloads" / "HetangOmni"


def get_download_root_dir() -> Path:
    custom_path = get_setting(SettingKeys.DOWNLOAD_PATH)
    root_dir = Path(custom_path) if custom_path and custom_path.strip() else get_default_download_dir()
    root_dir.mkdir(parents=True, exist_ok=True)
    return root_dir


def get_media_download_dir(kind: str) -> Path:
    folder_name = "videos" if kind == "video" else "images"
    download_dir = get_download_root_dir() / folder_name
    download_dir.mkdir(parents=True, exist_ok=True)
    return download_dir


def _is_winerror_32(exc: Exception) -> bool:
    if getattr(exc, "winerror", None) == 32:
        return True
    return "WinError 32" in str(exc)


def _copy_file_with_retries(src: Path, dst: Path, retries: int = 5, delay_seconds: float = 1.0) -> None:
    last_error = None
    for attempt in range(retries):
        try:
            with open(src, "rb") as src_handle:
                with open(dst, "wb") as dst_handle:
                    shutil.copyfileobj(src_handle, dst_handle, length=1024 * 1024)
            return
        except Exception as exc:
            last_error = exc
            if not _is_winerror_32(exc) or attempt == retries - 1:
                raise
            logger.warning(
                f"[API] batch_export_files -> 文件占用，等待重试 "
                f"{attempt + 1}/{retries}: {src.name} | {exc}"
            )
            time.sleep(delay_seconds)

    if last_error:
        raise last_error

class Api:
    """pywebview JS API"""

    @staticmethod
    def _resolve_download_dir(kind: str) -> Path:
        return get_media_download_dir(kind)

    @staticmethod
    def _folder_dialog_type(webview_module):
        file_dialog = getattr(webview_module, "FileDialog", None)
        if file_dialog and hasattr(file_dialog, "FOLDER"):
            return file_dialog.FOLDER
        return webview_module.FOLDER_DIALOG

    def _generate_image_via_registry(
        self,
        prompt: str,
        ref_images: list = None,
        aspect_ratio: str = "9:16",
        image_size: str = "1K",
        platform: str = "",
        provider: str = "",
        download: bool = True,
    ) -> dict:
        settings = get_all_settings()
        generator, resolved_platform, resolved_provider = media_generation_registry.resolve_image_generator(
            settings,
            platform,
            provider,
        )
        response_meta = {
            "platform": resolved_platform,
            "provider": resolved_provider,
        }
        if not generator:
            suffix = f": {resolved_platform}/{resolved_provider}" if resolved_platform or resolved_provider else ""
            return {"ok": False, "msg": f"未找到图片生成器{suffix}", **response_meta}

        request = ImageGenerationRequest(
            prompt=prompt,
            ref_images=ref_images or [],
            aspect_ratio=aspect_ratio,
            image_size=image_size,
            download_dir=self._resolve_download_dir("image") if download else None,
        )
        result = generator.generate(request, settings)
        if not result.success:
            return {"ok": False, "msg": result.error_message or "图片生成失败", **response_meta}

        response = {
            "ok": True,
            "image_data": result.image_data,
            "mime_type": result.mime_type,
            **response_meta,
        }
        if result.file_path:
            response["file_path"] = result.file_path
        return response

    def _generate_video_via_registry(
        self,
        prompt: str,
        ref_images: list = None,
        orientation: str = "portrait",
        duration: int = 10,
        resolution: str = "720P",
        generation_mode: str = "components",
        input_video: str = "",
        platform: str = "",
        provider: str = "",
        download: bool = True,
    ) -> dict:
        settings = get_all_settings()
        generator, resolved_platform, resolved_provider = media_generation_registry.resolve_video_generator(
            settings,
            platform,
            provider,
        )
        response_meta = {
            "platform": resolved_platform,
            "provider": resolved_provider,
        }
        if not generator:
            suffix = f": {resolved_platform}/{resolved_provider}" if resolved_platform or resolved_provider else ""
            return {"ok": False, "msg": f"未找到视频生成器{suffix}", **response_meta}

        request = VideoGenerationRequest(
            prompt=prompt,
            ref_images=ref_images or [],
            orientation=orientation,
            duration=int(duration or settings.get(SettingKeys.SORA2_DURATION, "10") or 10),
            resolution=resolution,
            generation_mode=generation_mode,
            input_video=input_video,
            download_dir=self._resolve_download_dir("video") if download else None,
        )
        result = generator.generate(request, settings)
        if not result.success:
            return {"ok": False, "msg": result.error_message or "视频生成失败", **response_meta}

        response = {
            "ok": True,
            "video_url": result.video_url,
            **response_meta,
        }
        if result.file_path:
            response["file_path"] = result.file_path
        return response

    def get_status(self) -> dict:
        """无激活验证，直接进入主界面。"""
        logger.debug("[API] get_status 调用 -> activated")
        return {"state": "activated"}

    def activate(self, code: str) -> dict:
        """兼容旧前端调用；当前版本不再验证激活码。"""
        logger.debug("[API] activate 调用 -> ok")
        return {"ok": True}

    def save_settings(self, settings: dict) -> dict:
        """保存设置"""
        logger.info(f"[API] save_settings 调用, keys={list(settings.keys())}")
        for key, value in settings.items():
            normalized_value = str(value).strip()
            log_value = "***" if "api_key" in key else normalized_value
            logger.info(f"[API] save_settings: {key} = {log_value}")
            set_setting(key, normalized_value)
        logger.info(f"[API] save_settings -> 保存成功, 共 {len(settings)} 项")
        return {"ok": True}

    def get_all_settings(self) -> dict:
        """获取所有设置"""
        import os
        logger.debug("[API] get_all_settings 调用")
        result = get_all_settings()
        # 调试模式标志，供前端判断是否显示调试标签
        result["__dev_mode__"] = "1" if os.environ.get("GLIN_DEV_UI") else "0"
        return result

    # ==================== 文件夹选择 ====================

    def select_folder(self) -> dict:
        """打开文件夹选择对话框"""
        logger.debug("[API] select_folder 调用")
        import webview
        window = webview.windows[0] if webview.windows else None
        if not window:
            logger.warning("[API] select_folder -> 无法获取窗口实例")
            return {"ok": False, "msg": "无法获取窗口实例"}
        result = window.create_file_dialog(self._folder_dialog_type(webview))
        if result and len(result) > 0:
            folder = result[0]
            logger.info(f"[API] select_folder -> 已选择: {folder}")
            return {"ok": True, "path": folder}
        logger.debug("[API] select_folder -> 用户取消选择")
        return {"ok": False, "msg": "未选择文件夹"}

    # ==================== 图片处理 ====================

    _DEFAULT_IMAGE_PROMPT = "请根据图片中的产品，为其绘制一个真实、自然的展示场景。场景需要与产品类型相匹配，突出产品本身，背景环境要逼真有质感。注意：画面中不要出现任何文字、标签或水印。"

    def get_image_process_prompt(self) -> dict:
        """获取图片处理提示词"""
        logger.debug("[API] get_image_process_prompt 调用")
        prompt = get_setting(SettingKeys.IMAGE_PROCESS_PROMPT) or self._DEFAULT_IMAGE_PROMPT
        return {"ok": True, "prompt": prompt}

    def set_image_process_prompt(self, prompt: str) -> dict:
        """保存图片处理提示词"""
        logger.info(f"[API] set_image_process_prompt 调用, prompt={prompt[:50]}...")
        set_setting(SettingKeys.IMAGE_PROCESS_PROMPT, prompt.strip())
        logger.info("[API] set_image_process_prompt -> 保存成功")
        return {"ok": True}

    # ==================== 调试接口 ====================

    def debug_dayangyu_sora2_create(self, prompt: str, image_base64: str = "", mime_type: str = "") -> dict:
        """调试 大洋芋 Sora2 - 创建任务（文生视频 / 图生视频）"""
        import base64
        import os
        import tempfile

        settings = get_all_settings()
        api_key = settings.get(SettingKeys.DAYANGYU_API_KEY, "")
        if not api_key:
            return {"ok": False, "msg": "未配置大洋芋 API Key，请前往设置页面配置"}
        orientation = settings.get(SettingKeys.SORA2_ORIENTATION, "portrait")
        duration = settings.get(SettingKeys.SORA2_DURATION, "10")
        model_name = f"sora2-pro-{orientation}-hd-{duration}s"
        image_path = None
        try:
            service = Sora2Dayangyu(api_key)
            if image_base64:
                ext_map = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp", "image/gif": ".gif"}
                ext = ext_map.get(mime_type or "", ".png")
                image_data = base64.b64decode(image_base64)
                tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
                tmp.write(image_data)
                tmp.close()
                image_path = tmp.name
                task = service.create_task(prompt, model=model_name, image_path=image_path)
            else:
                task = service.create_task(prompt, model=model_name)
            if image_path and os.path.exists(image_path):
                os.remove(image_path)
            return {
                "ok": True,
                "task_id": task.task_id,
                "status": task.status.value,
                "prompt": task.prompt,
                "mode": "图生视频" if image_base64 else "文生视频",
            }
        except Exception as e:
            if image_path and os.path.exists(image_path):
                try:
                    os.remove(image_path)
                except Exception:
                    pass
            logger.error(f"调试 大洋芋 Sora2 异常: {e}")
            return {"ok": False, "msg": str(e)}

    def debug_dayangyu_sora2_query(self, task_id: str) -> dict:
        """调试 大洋芋 Sora2 - 查询任务状态"""
        settings = get_all_settings()
        api_key = settings.get(SettingKeys.DAYANGYU_API_KEY, "")
        if not api_key:
            return {"ok": False, "msg": "未配置大洋芋 API Key"}
        try:
            service = Sora2Dayangyu(api_key)
            task = service.query_task(task_id)
            result = {
                "ok": True,
                "task_id": task.task_id,
                "status": task.status.value,
                "progress": task.progress,
            }
            if task.video_url:
                result["video_url"] = task.video_url
            if task.error_message:
                result["error_message"] = task.error_message
            return result
        except Exception as e:
            logger.error(f"调试 大洋芋 Sora2 查询异常: {e}")
            return {"ok": False, "msg": str(e)}

    def debug_dayangyu_sora2_content(self, task_id: str) -> dict:
        """调试 大洋芋 Sora2 - 查看视频内容（接口较慢，建议优先用查询结果中的 video_url）"""
        import base64

        settings = get_all_settings()
        api_key = settings.get(SettingKeys.DAYANGYU_API_KEY, "")
        if not api_key:
            return {"ok": False, "msg": "未配置大洋芋 API Key"}
        try:
            service = Sora2Dayangyu(api_key)
            data, content_type, err = service.get_video_content(task_id)
            if err:
                return {"ok": False, "msg": err}
            if not data:
                return {"ok": False, "msg": "未获取到视频数据"}
            return {
                "ok": True,
                "content_type": content_type or "video/mp4",
                "data": base64.b64encode(data).decode("ascii"),
            }
        except Exception as e:
            logger.error(f"调试 大洋芋 Sora2 查看视频异常: {e}")
            return {"ok": False, "msg": str(e)}

    def debug_xiaobanshou_sora2_create(self, prompt: str, image_base64: str = "", mime_type: str = "") -> dict:
        """调试 小扳手 Sora2 - 创建任务（文生视频 / 图生视频）"""
        import base64
        import os
        import tempfile

        settings = get_all_settings()
        api_key = settings.get(SettingKeys.XIAOBANSHOU_API_KEY, "")
        if not api_key:
            return {"ok": False, "msg": "未配置小扳手 API Key，请前往设置页面配置"}
        orientation = settings.get(SettingKeys.SORA2_ORIENTATION, "portrait")
        duration = settings.get(SettingKeys.SORA2_DURATION, "10")
        model_name = f"sora-2-{orientation}-{duration}s"
        image_path = None
        try:
            service = Sora2Xiaobanshou(api_key)
            if image_base64:
                ext_map = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp", "image/gif": ".gif"}
                ext = ext_map.get(mime_type or "", ".png")
                image_data = base64.b64decode(image_base64)
                tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
                tmp.write(image_data)
                tmp.close()
                image_path = tmp.name
                task = service.create_task(prompt, model=model_name, image_path=image_path)
            else:
                task = service.create_task(prompt, model=model_name)
            if image_path and os.path.exists(image_path):
                os.remove(image_path)
            return {
                "ok": True,
                "task_id": task.task_id,
                "status": task.status.value,
                "prompt": task.prompt,
                "mode": "图生视频" if image_base64 else "文生视频",
            }
        except Exception as e:
            if image_path and os.path.exists(image_path):
                try:
                    os.remove(image_path)
                except Exception:
                    pass
            logger.error(f"调试 小扳手 Sora2 异常: {e}")
            return {"ok": False, "msg": str(e)}

    def debug_xiaobanshou_sora2_query(self, task_id: str) -> dict:
        """调试 小扳手 Sora2 - 查询任务状态"""
        settings = get_all_settings()
        api_key = settings.get(SettingKeys.XIAOBANSHOU_API_KEY, "")
        if not api_key:
            return {"ok": False, "msg": "未配置小扳手 API Key"}
        try:
            service = Sora2Xiaobanshou(api_key)
            task = service.query_task(task_id)
            result = {
                "ok": True,
                "task_id": task.task_id,
                "status": task.status.value,
                "progress": task.progress,
            }
            if task.video_url:
                result["video_url"] = task.video_url
            if task.error_message:
                result["error_message"] = task.error_message
            return result
        except Exception as e:
            logger.error(f"调试 小扳手 Sora2 查询异常: {e}")
            return {"ok": False, "msg": str(e)}

    def debug_bandianwa_sora2_create(self, prompt: str, image_base64: str = "", mime_type: str = "") -> dict:
        """调试 斑点蛙 Sora2 - 创建任务（文生视频 / 图生视频）"""
        import base64
        import os
        import tempfile

        settings = get_all_settings()
        api_key = settings.get(SettingKeys.BANDIANWA_API_KEY, "")
        if not api_key:
            return {"ok": False, "msg": "未配置斑点蛙 API Key，请前往设置页面配置"}
        orientation = settings.get(SettingKeys.SORA2_ORIENTATION, "portrait")
        duration = settings.get(SettingKeys.SORA2_DURATION, "10")
        model_name = f"sora-2-{orientation}-{duration}s-guanzhuan"
        image_path = None
        try:
            service = Sora2Bandianwa(api_key)
            if image_base64:
                ext_map = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp", "image/gif": ".gif"}
                ext = ext_map.get(mime_type or "", ".png")
                image_data = base64.b64decode(image_base64)
                tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
                tmp.write(image_data)
                tmp.close()
                image_path = tmp.name
                task = service.create_task(prompt, model=model_name, image_path=image_path)
            else:
                task = service.create_task(prompt, model=model_name)
            if image_path and os.path.exists(image_path):
                os.remove(image_path)
            return {
                "ok": True,
                "task_id": task.task_id,
                "status": task.status.value,
                "prompt": task.prompt,
                "mode": "图生视频" if image_base64 else "文生视频",
            }
        except Exception as e:
            if image_path and os.path.exists(image_path):
                try:
                    os.remove(image_path)
                except Exception:
                    pass
            logger.error(f"调试 斑点蛙 Sora2 异常: {e}")
            return {"ok": False, "msg": str(e)}

    def debug_bandianwa_sora2_query(self, task_id: str) -> dict:
        """调试 斑点蛙 Sora2 - 查询任务状态"""
        settings = get_all_settings()
        api_key = settings.get(SettingKeys.BANDIANWA_API_KEY, "")
        if not api_key:
            return {"ok": False, "msg": "未配置斑点蛙 API Key"}
        try:
            service = Sora2Bandianwa(api_key)
            task = service.query_task(task_id)
            result = {
                "ok": True,
                "task_id": task.task_id,
                "status": task.status.value,
                "progress": task.progress,
            }
            if task.video_url:
                result["video_url"] = task.video_url
            if task.error_message:
                result["error_message"] = task.error_message
            return result
        except Exception as e:
            logger.error(f"调试 斑点蛙 Sora2 查询异常: {e}")
            return {"ok": False, "msg": str(e)}

    def debug_nanobanana(self, prompt: str, ref_images: list = None, aspect_ratio: str = None, image_size: str = None) -> dict:
        """NanoBanana 生成图片（支持文生图和多图生图）

        Args:
            ref_images: [{base64: str, mime: str}, ...]  或空列表/None 表示文生图
        """
        settings = get_all_settings()
        nanobanana_model = settings.get(SettingKeys.NANOBANANA_MODEL, "hetang")

        if nanobanana_model == "xiaobanshou":
            api_key = settings.get(SettingKeys.XIAOBANSHOU_API_KEY, "")
            if not api_key:
                return {"ok": False, "msg": "未配置小扳手 API Key，请前往设置页面配置"}
            service = NanoBananaXiaobanshou(api_key)
            provider_label = "小扳手"
        elif nanobanana_model == "hetang":
            api_key = settings.get(SettingKeys.HETANG_VEO_API_KEY, "")
            base_url = (settings.get(SettingKeys.HETANG_VEO_BASE_URL) or "").strip()
            if not api_key or not base_url:
                return {"ok": False, "msg": "未配置荷塘的 Base URL 或 API Key，请前往设置页面配置"}
            service = NanoBananaGlinCustom(api_key, base_url)
            provider_label = "荷塘渠道"
        else:
            api_key = settings.get(SettingKeys.YUNWU_API_KEY, "")
            if not api_key:
                return {"ok": False, "msg": "未配置云雾 API Key，请前往设置页面配置"}
            service = NanoBananaYunwu(api_key)
            provider_label = "云雾"

        aspect_ratio = aspect_ratio or settings.get(SettingKeys.NANOBANANA_RATIO, "9:16")
        image_size = image_size or settings.get(SettingKeys.NANOBANANA_QUALITY, "1K")

        try:
            kwargs = {}
            imgs = ref_images or []
            if imgs:
                kwargs["ref_images"] = imgs
                logger.info(f"NanoBanana 调试 ({provider_label}): 图生图模式, {len(imgs)} 张图片")
            else:
                logger.info(f"NanoBanana 调试 ({provider_label}): 文生图模式")

            dl_dir = get_media_download_dir("image")
            kwargs["download_dir"] = str(dl_dir)

            result = service.generate(
                prompt=prompt,
                aspect_ratio=aspect_ratio,
                image_size=image_size,
                **kwargs,
            )

            if result.success:
                resp = {
                    "ok": True,
                    "image_data": result.image_data,
                    "mime_type": result.mime_type,
                    "text_content": result.text_content,
                }
                if result.file_path:
                    resp["file_path"] = result.file_path
                return resp
            else:
                return {"ok": False, "msg": result.error_message}
        except Exception as e:
            logger.error(f"调试 NanoBanana ({provider_label}) 异常: {e}")
            return {"ok": False, "msg": str(e)}

    # ==================== 可插拔生成架构 ====================

    def get_media_generator_options(self) -> dict:
        """返回可用的图片/视频生成器选项以及当前默认值。"""
        settings = get_all_settings()
        image_platform = settings.get(SettingKeys.VIDEO_PRODUCT_IMAGE_PLATFORM, "nanobanana") or "nanobanana"
        image_provider = settings.get(SettingKeys.VIDEO_PRODUCT_IMAGE_PROVIDER, "yunwu") or "yunwu"
        global_image_model = (settings.get(SettingKeys.NANOBANANA_MODEL, "") or "").strip()
        if global_image_model == "gpt-image:bandianwa":
            image_platform = "gpt-image"
            image_provider = "bandianwa"
        elif global_image_model == "gpt-image:xiaobanshou":
            image_platform = "gpt-image"
            image_provider = "xiaobanshou"
        elif global_image_model:
            image_platform = "nanobanana"
            image_provider = global_image_model

        image_options = [
            {
                "platform": option.platform,
                "provider": option.provider,
                "platform_label": option.platform_label,
                "provider_label": option.provider_label,
                "label": option.label,
                "configured": option.configured,
            }
            for option in media_generation_registry.list_image_options(settings)
        ]
        video_options = [
            {
                "platform": option.platform,
                "provider": option.provider,
                "platform_label": option.platform_label,
                "provider_label": option.provider_label,
                "label": option.label,
                "configured": option.configured,
            }
            for option in media_generation_registry.list_video_options(settings)
        ]

        return {
            "ok": True,
            "image_options": image_options,
            "video_options": video_options,
            "defaults": {
                "image_platform": image_platform,
                "image_provider": image_provider,
                "video_platform": settings.get(SettingKeys.VIDEO_PRODUCT_VIDEO_PLATFORM, "veo3") or "veo3",
                "video_provider": settings.get(SettingKeys.VIDEO_PRODUCT_VIDEO_PROVIDER, "hetang") or "hetang",
            },
        }

    def generate_media_image(
        self,
        prompt: str,
        ref_images: list = None,
        aspect_ratio: str = "9:16",
        image_size: str = "1K",
        platform: str = "",
        provider: str = "",
    ) -> dict:
        """通过注册表调用指定图片生成器。"""
        try:
            return self._generate_image_via_registry(
                prompt=prompt,
                ref_images=ref_images or [],
                aspect_ratio=aspect_ratio,
                image_size=image_size,
                platform=platform,
                provider=provider,
                download=True,
            )
        except Exception as e:
            logger.error(f"[API] generate_media_image -> 异常: {e}")
            return {"ok": False, "msg": str(e)}

    def generate_media_video(
        self,
        prompt: str,
        ref_images: list = None,
        orientation: str = "portrait",
        duration: int = 10,
        platform: str = "",
        provider: str = "",
        resolution: str = "720P",
        generation_mode: str = "components",
        input_video: str = "",
    ) -> dict:
        """通过注册表调用指定视频生成器。"""
        try:
            return self._generate_video_via_registry(
                prompt=prompt,
                ref_images=ref_images or [],
                orientation=orientation,
                duration=duration,
                resolution=resolution,
                generation_mode=generation_mode,
                input_video=input_video,
                platform=platform,
                provider=provider,
                download=True,
            )
        except Exception as e:
            logger.error(f"[API] generate_media_video -> 异常: {e}")
            return {"ok": False, "msg": str(e)}

    # ==================== VEO 视频生成 ====================

    def veo_text_to_video(self, prompt: str, orientation: str = "landscape") -> dict:
        """VEO 文生视频兼容入口，内部走统一视频生成器。"""
        logger.info(f"[API] veo_text_to_video 调用, orientation={orientation}, prompt={prompt[:50]}...")
        try:
            # 从设置中读取 VEO provider
            settings = get_all_settings()
            veo_provider = settings.get("veo_model", "hetang")
            return self._generate_video_via_registry(
                prompt=prompt,
                ref_images=[],
                orientation=orientation,
                duration=10,
                platform="veo3",
                provider=veo_provider,
                download=False,
            )
        except Exception as e:
            logger.error(f"[API] veo_text_to_video -> 异常: {e}")
            return {"ok": False, "msg": str(e)}

    def veo_image_to_video(self, prompt: str, image_base64: str, mime_type: str, orientation: str = "landscape") -> dict:
        """VEO 图生视频兼容入口，内部走统一视频生成器。"""
        logger.info(f"[API] veo_image_to_video 调用, orientation={orientation}, prompt={prompt[:50]}...")
        try:
            # 从设置中读取 VEO provider
            settings = get_all_settings()
            veo_provider = settings.get("veo_model", "hetang")
            return self._generate_video_via_registry(
                prompt=prompt,
                ref_images=[{"base64": image_base64, "mime": mime_type}],
                orientation=orientation,
                duration=10,
                platform="veo3",
                provider=veo_provider,
                download=False,
            )
        except Exception as e:
            logger.error(f"[API] veo_image_to_video -> 异常: {e}")
            return {"ok": False, "msg": str(e)}

    def hetang_veo_generate(self, prompt: str, ref_images: list = None, orientation: str = "landscape") -> dict:
        """荷塘 VEO 兼容入口，内部走统一视频生成器。"""
        logger.info(f"[API] hetang_veo_generate 调用, orientation={orientation}, 模式={'图生视频' if ref_images else '文生视频'}")
        try:
            # 从设置中读取 VEO provider
            settings = get_all_settings()
            veo_provider = settings.get("veo_model", "hetang")
            return self._generate_video_via_registry(
                prompt=prompt,
                ref_images=ref_images or [],
                orientation=orientation,
                duration=10,
                platform="veo3",
                provider=veo_provider,
                download=True,
            )
        except Exception as e:
            logger.error(f"[API] hetang_veo_generate -> 异常: {e}")
            return {"ok": False, "msg": str(e)}

    def sora2_text_to_video(self, prompt: str, orientation: str = "landscape", duration: int = 10) -> dict:
        """Sora2 文生视频兼容入口，内部走统一视频生成器。"""
        logger.info(f"[API] sora2_text_to_video 调用, orientation={orientation}, duration={duration}, prompt={prompt[:50]}...")
        try:
            settings = get_all_settings()
            provider = settings.get(SettingKeys.SORA2_MODEL, "dayangyu") or "dayangyu"
            return self._generate_video_via_registry(
                prompt=prompt,
                ref_images=[],
                orientation=orientation,
                duration=duration,
                platform="sora2",
                provider=provider,
                download=False,
            )
        except Exception as e:
            logger.error(f"[API] sora2_text_to_video -> 异常: {e}")
            return {"ok": False, "msg": str(e)}

    def download_veo_video(self, video_url: str) -> dict:
        """下载 VEO 视频（优先用设置的下载路径，否则用默认 Glin 文件夹）"""
        import requests
        from datetime import datetime
        from urllib.parse import urlparse

        logger.info(f"[API] download_veo_video 调用, url={video_url[:80]}...")

        try:
            download_dir = get_media_download_dir("video")
        except Exception as e:
            return {"ok": False, "msg": f"下载目录无法创建: {e}"}

        last_err = None
        for attempt in range(3):
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                filename = f"omni_{timestamp}.mp4"
                filepath = download_dir / filename
                headers = {}
                parsed_url = urlparse(video_url)
                if (
                    parsed_url.netloc in {"api.dealonhorizon.us", "gpt.lyvideo.top"}
                    and parsed_url.path.startswith("/v1/tasks/")
                    and parsed_url.path.endswith("/file")
                ):
                    api_key = (get_setting(SettingKeys.HOLO_VEO_API_KEY) or "").strip()
                    if api_key:
                        headers["Authorization"] = f"Bearer {api_key}"

                with requests.get(video_url, headers=headers, timeout=120, stream=True) as resp:
                    resp.raise_for_status()
                    with open(str(filepath), "wb") as f:
                        for chunk in resp.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)

                logger.info(f"[API] download_veo_video -> 保存成功: {filepath}")
                return {"ok": True, "path": str(filepath)}
            except Exception as e:
                last_err = e
                logger.warning(f"[API] download_veo_video -> 下载失败(第{attempt+1}次): {e}")
                import time
                if attempt < 2:
                    time.sleep(2)
        logger.error(f"[API] download_veo_video -> 3次重试均失败: {last_err}")
        return {"ok": False, "msg": str(last_err)}

    def download_omni_video(self, video_url: str) -> dict:
        """下载 Omni 视频。"""
        return self.download_veo_video(video_url)

    # ==================== 视频任务 ====================

    _DEFAULT_VIDEO_PROMPT = "根据图片内容生成一段自然流畅的展示视频"

    def get_video_process_prompt(self) -> dict:
        """获取视频处理提示词"""
        logger.debug("[API] get_video_process_prompt 调用")
        prompt = get_setting(SettingKeys.VIDEO_PROCESS_PROMPT) or self._DEFAULT_VIDEO_PROMPT
        return {"ok": True, "prompt": prompt}

    def set_video_process_prompt(self, prompt: str) -> dict:
        """保存视频处理提示词"""
        logger.info(f"[API] set_video_process_prompt 调用, prompt={prompt[:50]}...")
        set_setting(SettingKeys.VIDEO_PROCESS_PROMPT, prompt.strip())
        logger.info("[API] set_video_process_prompt -> 保存成功")
        return {"ok": True}

    _DEFAULT_QIHAO_IMAGE_PROMPT = "请根据参考图片，为其绘制一个自然、真实的起号展示场景，突出人物或产品，背景环境要逼真有质感。注意：画面中不要出现任何文字、标签或水印。"
    _DEFAULT_QIHAO_VIDEO_PROMPT = "根据图片内容生成一段自然流畅的起号展示视频"

    def get_qihao_image_prompt(self) -> dict:
        """获取起号图片提示词"""
        logger.debug("[API] get_qihao_image_prompt 调用")
        prompt = get_setting(SettingKeys.QIHAO_IMAGE_PROMPT) or self._DEFAULT_QIHAO_IMAGE_PROMPT
        return {"ok": True, "prompt": prompt}

    def set_qihao_image_prompt(self, prompt: str) -> dict:
        """保存起号图片提示词"""
        logger.info(f"[API] set_qihao_image_prompt 调用, prompt={prompt[:50]}...")
        set_setting(SettingKeys.QIHAO_IMAGE_PROMPT, prompt.strip())
        logger.info("[API] set_qihao_image_prompt -> 保存成功")
        return {"ok": True}

    def get_qihao_video_prompt(self) -> dict:
        """获取起号视频提示词"""
        logger.debug("[API] get_qihao_video_prompt 调用")
        prompt = get_setting(SettingKeys.QIHAO_VIDEO_PROMPT) or self._DEFAULT_QIHAO_VIDEO_PROMPT
        return {"ok": True, "prompt": prompt}

    def set_qihao_video_prompt(self, prompt: str) -> dict:
        """保存起号视频提示词"""
        logger.info(f"[API] set_qihao_video_prompt 调用, prompt={prompt[:50]}...")
        set_setting(SettingKeys.QIHAO_VIDEO_PROMPT, prompt.strip())
        logger.info("[API] set_qihao_video_prompt -> 保存成功")
        return {"ok": True}

    def get_video_tasks(self) -> dict:
        """获取所有视频任务"""
        logger.debug("[API] get_video_tasks 调用")
        from .database import get_video_tasks
        try:
            tasks = get_video_tasks()
            logger.debug(f"[API] get_video_tasks -> 返回 {len(tasks)} 条任务")
            return {
                "ok": True,
                "tasks": [
                    {
                        "id": t.id,
                        "image_path": t.image_path,
                        "prompt": t.prompt,
                        "status": t.status,
                        "remote_task_id": t.remote_task_id,
                        "video_url": t.video_url,
                        "video_path": t.video_path,
                        "created_at": str(t.created_at),
                    }
                    for t in tasks
                ],
            }
        except Exception as e:
            logger.error(f"[API] get_video_tasks -> 异常: {e}")
            return {"ok": False, "msg": str(e)}

    def create_video_task(self, image_base64: str, mime_type: str, prompt: str) -> dict:
        """手动创建视频任务"""
        logger.info(f"[API] create_video_task 调用, mime={mime_type}, prompt={prompt[:50]}...")
        import base64
        import os
        import uuid
        from .config import DATA_DIR

        try:
            images_dir = DATA_DIR / "images"
            images_dir.mkdir(exist_ok=True)
            ext_map = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp", "image/gif": ".gif"}
            ext = ext_map.get(mime_type or "", ".png")
            filename = f"{uuid.uuid4().hex}{ext}"
            filepath = images_dir / filename
            image_data = base64.b64decode(image_base64)
            filepath.write_bytes(image_data)
            logger.debug(f"[API] create_video_task -> 图片已保存: {filepath}")

            from .database import create_video_task as db_create
            task = db_create(image_path=str(filepath), prompt=prompt)
            logger.info(f"[API] create_video_task -> 成功, id={task.id}, image={filename}")
            return {"ok": True, "task_id": task.id}
        except Exception as e:
            logger.error(f"[API] create_video_task -> 异常: {e}")
            return {"ok": False, "msg": str(e)}

    def auto_create_video_task(self, image_base64: str, mime_type: str) -> dict:
        """图片生成完毕后自动创建视频任务"""
        logger.info(f"[API] auto_create_video_task 调用, mime={mime_type}")
        import base64
        import os
        import uuid
        from .config import DATA_DIR

        try:
            prompt = get_setting(SettingKeys.VIDEO_PROCESS_PROMPT) or self._DEFAULT_VIDEO_PROMPT
            images_dir = DATA_DIR / "images"
            images_dir.mkdir(exist_ok=True)
            ext_map = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp", "image/gif": ".gif"}
            ext = ext_map.get(mime_type or "", ".png")
            filename = f"{uuid.uuid4().hex}{ext}"
            filepath = images_dir / filename
            image_data = base64.b64decode(image_base64)
            filepath.write_bytes(image_data)
            logger.debug(f"[API] auto_create_video_task -> 图片已保存: {filepath}")

            from .database import create_video_task as db_create
            task = db_create(image_path=str(filepath), prompt=prompt)
            logger.info(f"[API] auto_create_video_task -> 成功, id={task.id}, image={filename}")
            return {"ok": True, "task_id": task.id}
        except Exception as e:
            logger.error(f"[API] auto_create_video_task -> 异常: {e}")
            return {"ok": False, "msg": str(e)}

    def delete_video_task(self, task_id: int) -> dict:
        """删除视频任务"""
        logger.info(f"[API] delete_video_task 调用, task_id={task_id}")
        from .database import delete_video_task as db_delete
        try:
            db_delete(task_id)
            logger.info(f"[API] delete_video_task -> 成功, id={task_id}")
            return {"ok": True}
        except Exception as e:
            logger.error(f"[API] delete_video_task -> 异常: {e}")
            return {"ok": False, "msg": str(e)}

    def download_video_task(self, task_id: int) -> dict:
        """下载视频（优先用设置的下载路径，否则用默认 Glin 文件夹）"""
        import requests
        from datetime import datetime

        logger.info(f"[API] download_video_task 调用, task_id={task_id}")

        try:
            download_dir = get_media_download_dir("video")
        except Exception as e:
            logger.error(f"[API] download_video_task -> 创建下载目录失败: {e}")
            return {"ok": False, "msg": f"下载目录无法创建: {e}"}

        from .database import get_video_tasks, update_video_task
        try:
            tasks = get_video_tasks()
            task = None
            for t in tasks:
                if t.id == task_id:
                    task = t
                    break
            if not task:
                return {"ok": False, "msg": "任务不存在"}
            if not task.video_url:
                return {"ok": False, "msg": "该任务暂无视频链接"}

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            remote_id = task.remote_task_id or ""

            settings = get_all_settings()
            use_api_download = False

            provider = settings.get(SettingKeys.SORA2_MODEL, "dayangyu")
            if remote_id and provider in {"dayangyu", "xiaobanshou"}:
                use_api_download = True

            if use_api_download:
                logger.info(f"[API] download_video_task -> 使用 API 下载, remote_id={remote_id}")
                if provider == "xiaobanshou":
                    api_key = settings.get(SettingKeys.XIAOBANSHOU_API_KEY, "")
                    service = Sora2Xiaobanshou(api_key)
                else:
                    api_key = settings.get(SettingKeys.DAYANGYU_API_KEY, "")
                    service = Sora2Dayangyu(api_key)

                data, content_type, err = service.get_video_content(remote_id)
                if err or not data:
                    logger.warning(f"[API] download_video_task -> API 下载失败: {err}，回退到 URL 下载")
                    use_api_download = False
                else:
                    ext = ".mp4"
                    if content_type and "webm" in content_type:
                        ext = ".webm"
                    elif content_type and "mov" in content_type:
                        ext = ".mov"
                    filename = f"video_{task_id}_{timestamp}{ext}"
                    filepath = download_dir / filename
                    filepath.write_bytes(data)
                    logger.info(f"[API] download_video_task -> API 下载完成: {filepath}")
                    update_video_task(task_id, video_path=str(filepath))
                    return {"ok": True, "path": str(filepath)}

            video_url = task.video_url
            ext = ".mp4"
            if ".webm" in video_url:
                ext = ".webm"
            elif ".mov" in video_url:
                ext = ".mov"
            filename = f"video_{task_id}_{timestamp}{ext}"
            filepath = download_dir / filename

            logger.info(f"[API] download_video_task -> 使用 URL 下载: {video_url}")
            with requests.get(video_url, timeout=120, stream=True) as resp:
                resp.raise_for_status()
                with open(str(filepath), "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            logger.info(f"[API] download_video_task -> URL 下载完成: {filepath}")

            update_video_task(task_id, video_path=str(filepath))
            return {"ok": True, "path": str(filepath)}
        except Exception as e:
            logger.error(f"[API] download_video_task -> 异常: {e}")
            return {"ok": False, "msg": str(e)}

    def delete_all_video_tasks(self) -> dict:
        """删除所有视频任务"""
        logger.info("[API] delete_all_video_tasks 调用")
        from .database import delete_all_video_tasks as db_delete_all
        try:
            count = db_delete_all()
            logger.info(f"[API] delete_all_video_tasks -> 成功, 共删除 {count} 条")
            return {"ok": True, "count": count}
        except Exception as e:
            logger.error(f"[API] delete_all_video_tasks -> 异常: {e}")
            return {"ok": False, "msg": str(e)}

    def retry_video_task(self, task_id: int) -> dict:
        """重试失败的视频任务（重置状态为 pending）"""
        logger.info(f"[API] retry_video_task 调用, task_id={task_id}")
        from .database import update_video_task
        try:
            update_video_task(task_id, status='pending', video_url='', video_path='')
            logger.info(f"[API] retry_video_task -> 成功, id={task_id}")
            return {"ok": True}
        except Exception as e:
            logger.error(f"[API] retry_video_task -> 异常: {e}")
            return {"ok": False, "msg": str(e)}

    # ==================== 图片下载 ====================

    def download_image(self, image_base64: str, mime_type: str, filename_prefix: str = "image") -> dict:
        """将 base64 图片保存（优先用设置的下载路径，否则用默认 Glin 文件夹）"""
        import base64
        from datetime import datetime

        logger.info(f"[API] download_image 调用, prefix={filename_prefix}")

        try:
            download_dir = get_media_download_dir("image")
        except Exception as e:
            return {"ok": False, "msg": f"下载目录无法创建: {e}"}

        try:
            ext_map = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp", "image/gif": ".gif"}
            ext = ext_map.get(mime_type or "", ".png")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"{filename_prefix}_{timestamp}{ext}"
            filepath = download_dir / filename

            image_data = base64.b64decode(image_base64)
            filepath.write_bytes(image_data)
            logger.info(f"[API] download_image -> 保存成功: {filepath}")
            return {"ok": True, "path": str(filepath)}
        except Exception as e:
            logger.error(f"[API] download_image -> 异常: {e}")
            return {"ok": False, "msg": str(e)}

    # ==================== 数据文件状态 ====================

    def get_data_status(self) -> dict:
        """获取数据库和日志文件的状态信息"""
        import os
        from .config import BASE_DIR, DB_PATH, LOGS_DIR

        logger.debug("[API] get_data_status 调用")
        try:
            db_size = 0
            db_exists = DB_PATH.exists()
            if db_exists:
                db_size = DB_PATH.stat().st_size

            log_files = 0
            log_total_size = 0
            if LOGS_DIR.exists():
                for f in LOGS_DIR.iterdir():
                    if f.is_file():
                        log_files += 1
                        log_total_size += f.stat().st_size

            return {
                "ok": True,
                "base_dir": str(BASE_DIR),
                "db_path": str(DB_PATH),
                "db_exists": db_exists,
                "db_size": db_size,
                "logs_dir": str(LOGS_DIR),
                "log_files": log_files,
                "log_total_size": log_total_size,
            }
        except Exception as e:
            logger.error(f"[API] get_data_status -> 异常: {e}")
            return {"ok": False, "msg": str(e)}

    def clean_logs(self) -> dict:
        """清理历史日志文件（保留当前运行的日志）"""
        import os
        from .config import LOGS_DIR
        from .logger import log_filename as current_log_filename

        logger.info("[API] clean_logs 调用")
        try:
            if not LOGS_DIR.exists():
                return {"ok": True, "count": 0}

            deleted = 0
            for f in LOGS_DIR.iterdir():
                if f.is_file() and f.name != current_log_filename:
                    try:
                        f.unlink()
                        deleted += 1
                    except Exception as e:
                        logger.warning(f"[API] clean_logs -> 删除文件失败 {f.name}: {e}")

            logger.info(f"[API] clean_logs -> 已删除 {deleted} 个日志文件")
            return {"ok": True, "count": deleted}
        except Exception as e:
            logger.error(f"[API] clean_logs -> 异常: {e}")
            return {"ok": False, "msg": str(e)}

    def open_root_directory(self) -> dict:
        """在文件管理器中打开应用根目录"""
        import os
        import platform
        import subprocess
        from .config import BASE_DIR

        logger.info(f"[API] open_root_directory 调用, path={BASE_DIR}")
        try:
            system = platform.system()
            if system == "Windows":
                os.startfile(str(BASE_DIR))
            elif system == "Darwin":
                subprocess.Popen(["open", str(BASE_DIR)])
            else:
                subprocess.Popen(["xdg-open", str(BASE_DIR)])
            return {"ok": True}
        except Exception as e:
            logger.error(f"[API] open_root_directory -> 异常: {e}")
            return {"ok": False, "msg": str(e)}

    def batch_export_files(self, file_paths: list) -> dict:
        """让用户选择目标文件夹，将文件从 Glin 下载目录复制过去"""
        import webview

        if not file_paths:
            return {"ok": False, "msg": "没有可导出的文件"}

        window = webview.windows[0] if webview.windows else None
        if not window:
            return {"ok": False, "msg": "无法获取窗口实例"}

        result = window.create_file_dialog(self._folder_dialog_type(webview))
        if not result or len(result) == 0:
            return {"ok": False, "msg": "未选择文件夹"}

        dest_dir = Path(result[0])
        dest_dir.mkdir(parents=True, exist_ok=True)

        copied = 0
        errors = []
        for fp in file_paths:
            src = Path(fp)
            if not src.exists():
                errors.append(f"文件不存在: {src.name}")
                continue
            try:
                _copy_file_with_retries(src, dest_dir / src.name)
                copied += 1
            except Exception as e:
                errors.append(f"{src.name}: {e}")

        if copied == 0:
            detail = "；".join(errors[:3]) if errors else "没有可导出的本地文件"
            logger.warning(f"[API] batch_export_files -> 导出失败 0/{len(file_paths)} 到 {dest_dir} | {detail}")
            return {
                "ok": False,
                "msg": f"导出失败：0/{len(file_paths)} 成功。{detail}",
                "copied": copied,
                "total": len(file_paths),
                "errors": errors,
            }

        logger.info(f"[API] batch_export_files -> 导出 {copied}/{len(file_paths)} 到 {dest_dir}")
        msg = f"已导出 {copied} 个文件到 {dest_dir}"
        if errors:
            msg += f"，{len(errors)} 个失败"
        return {"ok": True, "msg": msg, "copied": copied, "total": len(file_paths), "errors": errors}

    def get_download_status(self) -> dict:
        """获取默认下载文件夹（~/Downloads/Glin）的状态"""
        dl_dir = get_download_root_dir()
        try:
            image_dir = dl_dir / "images"
            video_dir = dl_dir / "videos"
            image_count = 0
            image_size = 0
            video_count = 0
            video_size = 0

            if image_dir.exists():
                for f in image_dir.rglob("*"):
                    if f.is_file():
                        image_count += 1
                        image_size += f.stat().st_size

            if video_dir.exists():
                for f in video_dir.rglob("*"):
                    if f.is_file():
                        video_count += 1
                        video_size += f.stat().st_size

            return {
                "ok": True,
                "path": str(dl_dir),
                "file_count": image_count + video_count,
                "total_size": image_size + video_size,
                "image_count": image_count,
                "image_total_size": image_size,
                "video_count": video_count,
                "video_total_size": video_size,
            }
        except Exception as e:
            logger.error(f"[API] get_download_status -> 异常: {e}")
            return {"ok": False, "msg": str(e)}

    def clean_downloads(self) -> dict:
        """清理默认下载文件夹（~/Downloads/Glin）中的所有文件"""
        dl_dir = get_download_root_dir()
        try:
            count = 0
            for subdir_name in ("images", "videos"):
                subdir = dl_dir / subdir_name
                if not subdir.exists():
                    continue
                for f in subdir.rglob("*"):
                    if f.is_file():
                        f.unlink()
                        count += 1
            logger.info(f"[API] clean_downloads -> 已清理 {count} 个文件")
            return {"ok": True, "count": count}
        except Exception as e:
            logger.error(f"[API] clean_downloads -> 异常: {e}")
            return {"ok": False, "msg": str(e)}

    def open_download_directory(self) -> dict:
        """在文件管理器中打开下载文件夹"""
        import platform
        import subprocess

        dl_dir = get_download_root_dir()
        get_media_download_dir("image")
        get_media_download_dir("video")
        try:
            system = platform.system()
            if system == "Windows":
                import os
                os.startfile(str(dl_dir))
            elif system == "Darwin":
                subprocess.Popen(["open", str(dl_dir)])
            else:
                subprocess.Popen(["xdg-open", str(dl_dir)])
            return {"ok": True}
        except Exception as e:
            logger.error(f"[API] open_download_directory -> 异常: {e}")
            return {"ok": False, "msg": str(e)}

    # ==================== 提示词生成 ====================

    def import_prompt_images(self, folder_path: str = "") -> dict:
        """导入图片：递归扫描文件夹，为每张图片创建 tmp 子文件夹并复制图片"""
        try:
            if not folder_path:
                return self.select_folder()
            from .services.prompt_generation import import_images
            return import_images(folder_path)
        except Exception as e:
            logger.error(f"[API] import_prompt_images 异常: {e}")
            return {"ok": False, "msg": str(e)}

    def get_prompt_items(self) -> dict:
        """获取所有提示词项目"""
        try:
            from .services.prompt_generation import get_items
            return get_items()
        except Exception as e:
            logger.error(f"[API] get_prompt_items 异常: {e}")
            return {"ok": False, "msg": str(e), "items": []}

    def generate_prompt(self, item_id: str) -> dict:
        """为单个项目生成提示词"""
        try:
            from .services.prompt_generation import generate_prompt
            return generate_prompt(item_id)
        except Exception as e:
            logger.error(f"[API] generate_prompt 异常: {e}")
            return {"ok": False, "msg": str(e)}

    def read_prompt_text(self, item_id: str) -> dict:
        """读取项目的 prompt.txt 内容"""
        try:
            from .services.prompt_generation import read_prompt
            return read_prompt(item_id)
        except Exception as e:
            logger.error(f"[API] read_prompt_text 异常: {e}")
            return {"ok": False, "msg": str(e)}

    def delete_prompt_item(self, item_id: str) -> dict:
        """删除提示词项目"""
        try:
            from .services.prompt_generation import delete_item
            return delete_item(item_id)
        except Exception as e:
            logger.error(f"[API] delete_prompt_item 异常: {e}")
            return {"ok": False, "msg": str(e)}

    def open_prompt_folder(self, item_id: str) -> dict:
        """打开项目的 tmp 文件夹"""
        try:
            from .services.prompt_generation import open_item_folder
            return open_item_folder(item_id)
        except Exception as e:
            logger.error(f"[API] open_prompt_folder 异常: {e}")
            return {"ok": False, "msg": str(e)}

    def get_prompt_image(self, item_id: str) -> dict:
        """获取项目的图片 base64（用于预览）"""
        try:
            from .services.prompt_generation import get_image_base64
            return get_image_base64(item_id)
        except Exception as e:
            logger.error(f"[API] get_prompt_image 异常: {e}")
            return {"ok": False, "msg": str(e)}

    def select_folder_for_prompt(self) -> dict:
        """选择文件夹并直接导入图片（合并选择+导入）"""
        try:
            import webview
            window = webview.windows[0] if webview.windows else None
            if not window:
                return {"ok": False, "msg": "无法打开文件夹选择对话框"}
            result = window.create_file_dialog(self._folder_dialog_type(webview))
            if result and len(result) > 0:
                folder_path = result[0]
                from .services.prompt_generation import import_images
                return import_images(folder_path)
            return {"ok": False, "msg": "未选择文件夹"}
        except Exception as e:
            logger.error(f"[API] select_folder_for_prompt 异常: {e}")
            return {"ok": False, "msg": str(e)}

    # ==================== 调试接口 (GLIN_DEV_UI=1 时使用) ====================

    def debug_get_channels(self) -> dict:
        """返回所有调试渠道列表及配置状态"""
        import os
        if not os.environ.get("GLIN_DEV_UI"):
            return {"ok": False, "msg": "调试模式未开启"}
        try:
            from .constants import SettingKeys
            from .services.nanobanana import NanoBananaYunwu, NanoBananaGlinCustom, NanoBananaXiaobanshou
            from .services.veo import VeoHetang, VeoXiaobanshou, VeoZyg, VeoChaowen, VeoHolo, VeoCatking
            from .services.sora2 import Sora2Dayangyu, Sora2Xiaobanshou, Sora2Bandianwa

            settings = get_all_settings()

            def _key(s, k): return (s.get(k) or "").strip()

            channels = [
                {"key": "nb_yunwu",        "label": "云雾 (YW)",      "tab": "nanobanana", "configured": bool(_key(settings, SettingKeys.YUNWU_API_KEY))},
                {"key": "nb_hetang",        "label": "荷塘 (HT)",      "tab": "nanobanana", "configured": bool(_key(settings, SettingKeys.HETANG_VEO_API_KEY) and _key(settings, SettingKeys.HETANG_VEO_BASE_URL))},
                {"key": "veo_hetang",       "label": "荷塘 (HT)",      "tab": "veo",        "configured": bool(_key(settings, SettingKeys.HETANG_VEO_API_KEY) and _key(settings, SettingKeys.HETANG_VEO_BASE_URL))},
                {"key": "veo_xiaobanshou",  "label": "小扳手 (XBS)",   "tab": "veo",        "configured": bool(_key(settings, SettingKeys.XIAOBANSHOU_API_KEY))},
                {"key": "veo_zyg",          "label": "ZYG",           "tab": "veo",        "configured": bool(_key(settings, SettingKeys.ZYG_API_KEY))},
                {"key": "veo_chaowen",      "label": "超稳 (CW)",      "tab": "veo",        "configured": bool(_key(settings, SettingKeys.CHAOWEN_VEO_API_KEY))},
                {"key": "veo_holo",         "label": "HOLO",          "tab": "veo",        "configured": bool(_key(settings, SettingKeys.HOLO_VEO_API_KEY))},
                {"key": "veo_catking",      "label": "CatKing",          "tab": "veo",        "configured": bool(_key(settings, SettingKeys.CATKING_VEO_API_KEY))},
                {"key": "sora2_dayangyu",   "label": "大洋芋 (DYY)",   "tab": "sora2",      "configured": bool(_key(settings, SettingKeys.DAYANGYU_API_KEY))},
                {"key": "sora2_xiaobanshou","label": "小扳手 (XBS)",   "tab": "sora2",      "configured": bool(_key(settings, SettingKeys.XIAOBANSHOU_API_KEY))},
                {"key": "sora2_bandianwa",  "label": "斑点蛙 (BDW)",   "tab": "sora2",      "configured": bool(_key(settings, SettingKeys.BANDIANWA_API_KEY))},
            ]
            return {"ok": True, "channels": channels}
        except Exception as e:
            logger.error(f"[API] debug_get_channels 异常: {e}")
            return {"ok": False, "msg": str(e)}

    def debug_generate(self, channel_key: str, params: dict) -> dict:
        """在调试标签中执行生成任务，返回结果（含预览 base64 / 文件路径）"""
        import os
        import base64
        import tempfile
        import time
        from datetime import datetime
        from pathlib import Path

        if not os.environ.get("GLIN_DEV_UI"):
            return {"ok": False, "msg": "调试模式未开启"}

        try:
            from .constants import SettingKeys
            from .services.nanobanana import NanoBananaYunwu, NanoBananaGlinCustom, NanoBananaXiaobanshou
            from .services.veo import VeoHetang, VeoXiaobanshou, VeoZyg, VeoChaowen, VeoHolo, VeoCatking
            from .services.sora2 import Sora2Dayangyu, Sora2Xiaobanshou, Sora2Bandianwa, Sora2TaskStatus
            from .services.veo.utils import download_video

            settings = get_all_settings()
            def _key(k): return (settings.get(k) or "").strip()

            # ── 将 ref_base64 落盘为临时文件，获得 ref_image_path ──
            _tmp_path = None
            params = dict(params)
            ref_b64 = params.pop("ref_base64", "")
            ref_mime = params.pop("ref_mime", "image/jpeg")
            if ref_b64:
                ext_map = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp", "image/gif": ".gif"}
                ext = ext_map.get(ref_mime, ".jpg")
                tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
                tmp.write(base64.b64decode(ref_b64))
                tmp.close()
                _tmp_path = tmp.name
                params["ref_image_path"] = _tmp_path

            output_dir = Path.home() / "Downloads" / "Glin" / "debug" / channel_key / datetime.now().strftime("%Y%m%d")
            output_dir.mkdir(parents=True, exist_ok=True)

            try:
                # ── NanoBanana ──
                if channel_key == "nb_yunwu":
                    runner = NanoBananaYunwu(_key(SettingKeys.YUNWU_API_KEY))
                elif channel_key == "nb_hetang":
                    runner = NanoBananaGlinCustom(_key(SettingKeys.HETANG_VEO_API_KEY), _key(SettingKeys.HETANG_VEO_BASE_URL))
                elif channel_key == "nb_xiaobanshou":
                    runner = NanoBananaXiaobanshou(_key(SettingKeys.XIAOBANSHOU_API_KEY))
                else:
                    runner = None

                if runner is not None:
                    result = runner.generate(
                        prompt=params.get("prompt", ""),
                        aspect_ratio=params.get("aspect_ratio", "9:16"),
                        image_size=params.get("image_size", "1K"),
                        ref_image_path=params.get("ref_image_path"),
                        download_dir=str(output_dir),
                    )
                    if not result.success:
                        return {"ok": False, "msg": result.error_message}
                    return {
                        "ok": True,
                        "file_path": result.file_path,
                        "preview_b64": result.image_data,
                        "mime_type": result.mime_type,
                    }

                # ── VEO ──
                if channel_key == "veo_hetang":
                    veo = VeoHetang(_key(SettingKeys.HETANG_VEO_API_KEY), _key(SettingKeys.HETANG_VEO_BASE_URL))
                    result = veo.generate(
                        prompt=params.get("prompt", ""),
                        orientation=params.get("orientation", "portrait"),
                        duration=int(params.get("duration", 10)),
                        ref_image_path=params.get("ref_image_path"),
                        download_dir=str(output_dir),
                    )
                    if not result.success:
                        return {"ok": False, "msg": result.error_message}
                    return {"ok": True, "file_path": result.file_path, "video_url": result.video_url}

                if channel_key == "veo_xiaobanshou":
                    veo = VeoXiaobanshou(_key(SettingKeys.XIAOBANSHOU_API_KEY))
                    result = veo.generate(
                        prompt=params.get("prompt", ""),
                        orientation=params.get("orientation", "portrait"),
                        duration=int(params.get("duration", 10)),
                        ref_image_path=params.get("ref_image_path"),
                        download_dir=str(output_dir),
                    )
                    if not result.success:
                        return {"ok": False, "msg": result.error_message}
                    return {"ok": True, "file_path": result.file_path, "video_url": result.video_url}

                if channel_key == "veo_zyg":
                    veo = VeoZyg(_key(SettingKeys.ZYG_API_KEY))
                    result = veo.generate(
                        prompt=params.get("prompt", ""),
                        orientation=params.get("orientation", "portrait"),
                        duration=int(params.get("duration", 10)),
                        ref_image_path=params.get("ref_image_path"),
                        download_dir=str(output_dir),
                    )
                    if not result.success:
                        return {"ok": False, "msg": result.error_message}
                    return {"ok": True, "file_path": result.file_path, "video_url": result.video_url}

                if channel_key == "veo_chaowen":
                    veo = VeoChaowen(_key(SettingKeys.CHAOWEN_VEO_API_KEY), _key(SettingKeys.CHAOWEN_VEO_BASE_URL))
                    result = veo.generate(
                        prompt=params.get("prompt", ""),
                        orientation=params.get("orientation", "portrait"),
                        duration=int(params.get("duration", 10)),
                        ref_image_path=params.get("ref_image_path"),
                        download_dir=str(output_dir),
                    )
                    if not result.success:
                        return {"ok": False, "msg": result.error_message}
                    return {"ok": True, "file_path": result.file_path, "video_url": result.video_url}

                if channel_key == "veo_holo":
                    veo = VeoHolo(_key(SettingKeys.HOLO_VEO_API_KEY), _key(SettingKeys.HOLO_VEO_BASE_URL))
                    result = veo.generate(
                        prompt=params.get("prompt", ""),
                        orientation=params.get("orientation", "portrait"),
                        duration=int(params.get("duration", 10)),
                        ref_image_path=params.get("ref_image_path"),
                        download_dir=str(output_dir),
                    )
                    if not result.success:
                        return {"ok": False, "msg": result.error_message}
                    return {"ok": True, "file_path": result.file_path, "video_url": result.video_url}

                if channel_key == "veo_catking":
                    veo = VeoCatking(_key(SettingKeys.CATKING_VEO_API_KEY), _key(SettingKeys.CATKING_VEO_BASE_URL))
                    result = veo.generate(
                        prompt=params.get("prompt", ""),
                        orientation=params.get("orientation", "portrait"),
                        duration=int(params.get("duration", 10)),
                        ref_image_path=params.get("ref_image_path"),
                        download_dir=str(output_dir),
                    )
                    if not result.success:
                        return {"ok": False, "msg": result.error_message}
                    return {"ok": True, "file_path": result.file_path, "video_url": result.video_url}

                # ── Sora2 ──
                sora2_map = {
                    "sora2_dayangyu":    (Sora2Dayangyu,    SettingKeys.DAYANGYU_API_KEY),
                    "sora2_xiaobanshou": (Sora2Xiaobanshou, SettingKeys.XIAOBANSHOU_API_KEY),
                    "sora2_bandianwa":   (Sora2Bandianwa,   SettingKeys.BANDIANWA_API_KEY),
                }
                if channel_key in sora2_map:
                    cls, key = sora2_map[channel_key]
                    sora = cls(_key(key))
                    create_kwargs = {
                        "duration": int(params.get("duration", 10)),
                        "orientation": params.get("orientation", "portrait"),
                    }
                    if params.get("ref_image_path") and os.path.isfile(params["ref_image_path"]):
                        create_kwargs["image_path"] = params["ref_image_path"]
                    task = sora.create_task(params.get("prompt", ""), **create_kwargs)
                    if task.status == Sora2TaskStatus.FAILED:
                        return {"ok": False, "msg": task.error_message or "任务创建失败"}
                    video_url = task.video_url
                    if not video_url:
                        if not task.task_id:
                            return {"ok": False, "msg": "未返回任务 ID"}
                        deadline = time.time() + 900
                        while time.time() < deadline:
                            task = sora.query_task(task.task_id)
                            if task.status in (Sora2TaskStatus.COMPLETED, Sora2TaskStatus.FAILED):
                                break
                            time.sleep(5)
                        if task.status != Sora2TaskStatus.COMPLETED or not task.video_url:
                            return {"ok": False, "msg": task.error_message or "任务未完成"}
                        video_url = task.video_url
                    file_path = download_video(video_url, str(output_dir), "sora2")
                    return {"ok": True, "file_path": file_path, "video_url": video_url}

                return {"ok": False, "msg": f"未知渠道: {channel_key}"}

            finally:
                if _tmp_path:
                    try:
                        os.remove(_tmp_path)
                    except OSError:
                        pass
        except Exception as e:
            logger.error(f"[API] debug_generate 异常: {e}")
            return {"ok": False, "msg": str(e)}
