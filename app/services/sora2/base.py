"""Sora2 生成基类"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Tuple

import requests


class Sora2TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"          # 等待中
    PROCESSING = "processing"    # 处理中
    COMPLETED = "completed"      # 已完成
    FAILED = "failed"            # 失败


@dataclass
class Sora2Task:
    """Sora2 任务信息"""
    task_id: str                          # 任务ID
    status: Sora2TaskStatus               # 任务状态
    prompt: str                           # 提示词
    video_url: Optional[str] = None       # 视频URL（完成后）
    error_message: Optional[str] = None   # 错误信息（失败时）
    progress: int = 0                     # 进度百分比 0-100
    created_at: Optional[str] = None      # 创建时间
    completed_at: Optional[str] = None    # 完成时间


class Sora2Base(ABC):
    """Sora2 生成基类"""

    # 子类按需覆盖：(orientation, duration) -> model_name
    # orientation: "portrait" | "landscape"
    # duration: 秒数（int）
    SUPPORTED_MODELS: Dict[Tuple[str, int], str] = {}

    def __init__(self, api_key: str):
        """
        初始化

        Args:
            api_key: API密钥
        """
        self.api_key = api_key

    def build_transient_query_task(self, task_id: str, exc: Exception) -> Sora2Task:
        """将可重试的查询异常包装为处理中状态，交给上层继续轮询。"""
        return Sora2Task(
            task_id=task_id,
            status=Sora2TaskStatus.PROCESSING,
            prompt="",
            error_message=str(exc),
        )

    @staticmethod
    def is_transient_query_exception(exc: Exception) -> bool:
        """判断查询阶段是否属于可跳过的瞬时网络异常。"""
        return isinstance(
            exc,
            (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.ChunkedEncodingError,
            ),
        )

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """提供商名称"""
        pass

    @property
    @abstractmethod
    def base_url(self) -> str:
        """API基础地址"""
        pass

    def resolve_model(self, orientation: str = "portrait", duration: int = 10) -> str:
        """
        根据方向和时长解析模型名称。

        优先从 SUPPORTED_MODELS 查找精确匹配；若未找到则回退到
        按时长就近选择（同方向中最接近的时长），最终兜底返回第一个模型。

        Args:
            orientation: 方向，"portrait"（竖屏）或 "landscape"（横屏）
            duration: 视频时长（秒）

        Returns:
            对应的模型名称字符串
        """
        if not self.SUPPORTED_MODELS:
            raise NotImplementedError(
                f"{self.__class__.__name__} 未定义 SUPPORTED_MODELS，"
                "请覆盖该字典或重写 resolve_model()"
            )

        # 精确匹配
        exact = self.SUPPORTED_MODELS.get((orientation, duration))
        if exact:
            return exact

        # 同方向最近时长
        candidates = [
            (abs(d - duration), model)
            for (ori, d), model in self.SUPPORTED_MODELS.items()
            if ori == orientation
        ]
        if candidates:
            candidates.sort(key=lambda x: x[0])
            return candidates[0][1]

        # 兜底：返回第一个
        return next(iter(self.SUPPORTED_MODELS.values()))

    @abstractmethod
    def create_task(
        self,
        prompt: str,
        orientation: str = "portrait",
        duration: int = 10,
        **kwargs
    ) -> Sora2Task:
        """
        创建生成任务

        Args:
            prompt: 视频描述提示词
            orientation: 方向，"portrait" 或 "landscape"
            duration: 视频时长（秒），与 SUPPORTED_MODELS 匹配
            **kwargs: 其他参数（如 image_path）

        Returns:
            Sora2Task: 任务信息
        """
        pass

    @abstractmethod
    def query_task(self, task_id: str) -> Sora2Task:
        """
        查询任务状态

        Args:
            task_id: 任务ID

        Returns:
            Sora2Task: 任务信息
        """
        pass
