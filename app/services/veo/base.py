"""VEO 视频生成基类"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class VeoTaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"          # 等待中
    PROCESSING = "processing"    # 处理中
    COMPLETED = "completed"      # 已完成
    FAILED = "failed"            # 失败


@dataclass
class VeoTask:
    """VEO 任务信息"""
    task_id: str                          # 任务ID
    status: VeoTaskStatus                 # 任务状态
    prompt: str                           # 提示词
    video_url: Optional[str] = None       # 视频URL（完成后）
    file_path: Optional[str] = None       # 本地文件路径（下载后）
    error_message: Optional[str] = None   # 错误信息（失败时）
    progress: int = 0                     # 进度百分比 0-100
    created_at: Optional[str] = None      # 创建时间
    completed_at: Optional[str] = None    # 完成时间


@dataclass
class VeoResult:
    """VEO 生成结果（同步接口统一出口）"""
    success: bool
    video_url: Optional[str] = None
    file_path: Optional[str] = None       # 本地文件路径（最终输出）
    error_message: Optional[str] = None


class VeoBase(ABC):
    """VEO 视频生成基类

    每个子类对应一个渠道，必须实现 generate() 方法。
    generate() 的返回值是 VeoResult，其中 file_path 为最终落盘的本地路径。
    """

    def __init__(self, api_key: str, base_url: str = ""):
        """
        初始化

        Args:
            api_key:  API 密钥
            base_url: 可选的自定义 Base URL（部分渠道需要）
        """
        self.api_key = api_key
        self._base_url = base_url

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """渠道名称（人类可读）"""
        pass

    @property
    @abstractmethod
    def base_url(self) -> str:
        """API 基础地址"""
        pass

    @abstractmethod
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
        生成视频（同步阻塞直到完成或失败）

        Args:
            prompt:          视频描述提示词
            orientation:     方向，portrait（竖屏）/ landscape（横屏）
            duration:        视频时长（秒），通常 5 / 10
            ref_image_path:  参考图片本地路径（图生视频时使用），None 则为文生视频
            download_dir:    视频下载目录；传入后自动下载到本地并写入 file_path
            **kwargs:        渠道专有扩展参数

        Returns:
            VeoResult: 生成结果，file_path 为本地视频文件绝对路径
        """
        pass
