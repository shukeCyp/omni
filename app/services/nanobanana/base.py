"""NanoBanana 生成基类"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class NanoBananaResult:
    """NanoBanana 生成结果"""
    success: bool                         # 是否成功
    image_data: Optional[str] = None      # 图片 base64 数据
    mime_type: Optional[str] = None       # 图片 MIME 类型（如 image/png）
    text_content: Optional[str] = None    # 文本内容（模型返回的文本）
    error_message: Optional[str] = None   # 错误信息
    file_path: Optional[str] = None       # 自动下载后的本地文件路径


class NanoBananaBase(ABC):
    """NanoBanana 生成基类"""

    def __init__(self, api_key: str):
        """
        初始化
        
        Args:
            api_key: API密钥
        """
        self.api_key = api_key

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

    @abstractmethod
    def generate(
        self,
        prompt: str,
        aspect_ratio: str = "9:16",
        image_size: str = "1K",
        **kwargs
    ) -> NanoBananaResult:
        """
        生成图片
        
        Args:
            prompt: 图片描述提示词
            aspect_ratio: 宽高比，可选 9:16 / 16:9 / 1:1
            image_size: 图片清晰度，可选 1K / 2K / 4K
            **kwargs: 其他参数
            
        Returns:
            NanoBananaResult: 生成结果
        """
        pass
