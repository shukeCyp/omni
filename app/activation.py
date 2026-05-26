import hashlib
import platform
import uuid

from .config import ACTIVATION_SECRET
from .constants import SettingKeys
from .database import get_setting, set_setting
from .logger import logger


def get_device_id() -> str:
    """获取设备唯一标识（首次生成后存入数据库，保证稳定）"""
    stored_id = get_setting(SettingKeys.DEVICE_ID)
    if stored_id:
        logger.debug(f"[Activation] 读取已有设备ID: {stored_id}")
        return stored_id

    # 首次运行，生成设备ID
    node = uuid.getnode()
    system = platform.system()
    machine = platform.machine()
    random_part = uuid.uuid4().hex[:8]
    raw = f"{node}-{system}-{machine}-{random_part}"
    device_id = hashlib.md5(raw.encode()).hexdigest()[:16].upper()

    set_setting(SettingKeys.DEVICE_ID, device_id)
    logger.info(f"[Activation] 生成新设备ID: {device_id} (node={node}, system={system}, machine={machine})")

    return device_id


def generate_activation_code(device_id: str) -> str:
    """根据设备ID和密钥生成激活码"""
    raw = f"{ACTIVATION_SECRET}:{device_id}"
    code = hashlib.sha256(raw.encode()).hexdigest()[:12].upper()
    logger.debug(f"[Activation] 生成激活码: device_id={device_id}, code={code}")
    return code


def verify_activation(device_id: str, code: str) -> bool:
    """验证激活码"""
    expected = generate_activation_code(device_id)
    result = code.strip().upper() == expected
    if result:
        logger.info(f"[Activation] 激活码验证通过: device_id={device_id}")
    else:
        logger.warning(f"[Activation] 激活码验证失败: device_id={device_id}, 输入={code}, 期望={expected}")
    return result
