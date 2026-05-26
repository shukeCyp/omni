"""常量定义"""


class ApiUrls:
    """API 地址"""
    DAYANGYU = "https://api.dyuapi.com"
    YUNWU = "https://yunwu.ai"
    XIAOBANSHOU = "https://api.xintianwengai.com"
    XIAOBANSHOU_VEO = "https://xibapi.com"
    BANDIANWA = "https://api.hellobabygo.com"
    ZYG = "https://otuapi.com"
    CHAOWEN = "https://api.chaowenai.com"
    HOLO = "https://gpt.lyvideo.top"
    CATKING = "https://api.catking.top"
    HETANG = ""  # 荷塘渠道 Base URL 由用户在设置页面配置，无默认值


class ModelProviders:
    """模型提供商"""
    DAYANGYU = "dayangyu"
    YUNWU = "yunwu"
    XIAOBANSHOU = "xiaobanshou"
    BANDIANWA = "bandianwa"
    ZYG = "zyg"
    CHAOWEN = "chaowen"
    HOLO = "holo"
    CATKING = "catking"


class SettingKeys:
    """设置键名"""
    DEVICE_ID = "device_id"
    ACTIVATION_CODE = "activation_code"
    # 自定义 API
    DAYANGYU_API_KEY = "dayangyu_api_key"
    DAYANGYU_BASE_URL = "dayangyu_base_url"
    YUNWU_API_KEY = "yunwu_api_key"
    YUNWU_BASE_URL = "yunwu_base_url"
    XIAOBANSHOU_API_KEY = "xiaobanshou_api_key"
    XIAOBANSHOU_BASE_URL = "xiaobanshou_base_url"
    BANDIANWA_API_KEY = "bandianwa_api_key"
    BANDIANWA_BASE_URL = "bandianwa_base_url"
    ZYG_API_KEY = "zyg_api_key"
    CHAOWEN_VEO_API_KEY = "chaowen_veo_api_key"
    CHAOWEN_VEO_BASE_URL = "chaowen_veo_base_url"
    HOLO_VEO_API_KEY = "holo_veo_api_key"
    HOLO_VEO_BASE_URL = "holo_veo_base_url"
    CATKING_VEO_API_KEY = "catking_veo_api_key"
    CATKING_VEO_BASE_URL = "catking_veo_base_url"
    HETANG_VEO_BASE_URL = "hetang_veo_base_url"   # 荷塘渠道（VEO + NanoBanana 共用）
    HETANG_VEO_API_KEY = "hetang_veo_api_key"      # 荷塘渠道（VEO + NanoBanana 共用）
    # 别名：NanoBanana 荷塘渠道与 VEO 共用同一地址和密钥
    HETANG_NANOBANANA_BASE_URL = "hetang_veo_base_url"
    HETANG_NANOBANANA_API_KEY = "hetang_veo_api_key"
    CUSTOM_NANOBANANA_BASE_URL = "hetang_veo_base_url"
    CUSTOM_NANOBANANA_API_KEY = "hetang_veo_api_key"
    SORA2_MODEL = "sora2_model"
    OMNI_MODEL = "omni_model"
    SORA2_ORIENTATION = "sora2_orientation"
    SORA2_DURATION = "sora2_duration"
    NANOBANANA_MODEL = "nanobanana_model"
    NANOBANANA_RATIO = "nanobanana_ratio"
    NANOBANANA_QUALITY = "nanobanana_quality"
    GLIN_NANOBANANA_RATIO = "glin_nanobanana_ratio"
    GLIN_NANOBANANA_QUALITY = "glin_nanobanana_quality"
    HETANG_VEO_ORIENTATION = "hetang_veo_orientation"
    VIDEO_PRODUCT_IMAGE_PLATFORM = "video_product_image_platform"
    VIDEO_PRODUCT_IMAGE_PROVIDER = "video_product_image_provider"
    VIDEO_PRODUCT_VIDEO_PLATFORM = "video_product_video_platform"
    VIDEO_PRODUCT_VIDEO_PROVIDER = "video_product_video_provider"
    # 斑点蛙
    BANDIANWA_API_KEY = "bandianwa_api_key"
    # 下载配置
    AUTO_DOWNLOAD = "auto_download"
    DOWNLOAD_PATH = "download_path"
    # 重试配置
    AUTO_RETRY = "auto_retry"
    IMAGE_MAX_RETRY = "image_max_retry"
    VIDEO_MAX_RETRY = "video_max_retry"
    # 图片处理
    IMAGE_PROCESS_PROMPT = "image_process_prompt"
    # 视频处理提示词
    VIDEO_PROCESS_PROMPT = "video_process_prompt"
    # 起号图片提示词
    QIHAO_IMAGE_PROMPT = "qihao_image_prompt"
    # 起号视频提示词
    QIHAO_VIDEO_PROMPT = "qihao_video_prompt"
    # 线程池大小
    THREAD_POOL_SIZE = "thread_pool_size"
    # 主题
    THEME = "theme"
