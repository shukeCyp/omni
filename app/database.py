import datetime
from typing import List, Optional

from peewee import (
    SqliteDatabase, Model, CharField, AutoField, DateTimeField
)

from .config import DB_PATH
from .logger import logger

# 数据库连接
db = SqliteDatabase(str(DB_PATH))


class BaseModel(Model):
    class Meta:
        database = db


class Settings(BaseModel):
    key = CharField(primary_key=True)
    value = CharField()


class VideoTask(BaseModel):
    """视频任务表"""
    id = AutoField()
    image_path = CharField(default='')
    prompt = CharField(default='')
    status = CharField(default='pending')  # pending / processing / completed / failed
    remote_task_id = CharField(default='')  # 远程 Sora2 任务 ID
    video_url = CharField(default='')
    video_path = CharField(default='')
    created_at = DateTimeField(default=datetime.datetime.now)


def _migrate_db() -> None:
    """数据库迁移：为旧表添加新字段"""
    cursor = db.execute_sql("PRAGMA table_info(videotask)")
    columns = [row[1] for row in cursor.fetchall()]
    if 'remote_task_id' not in columns:
        db.execute_sql("ALTER TABLE videotask ADD COLUMN remote_task_id VARCHAR(255) DEFAULT ''")
        logger.info("[DB] 迁移: 已添加 remote_task_id 字段")


def init_db() -> None:
    """初始化数据库"""
    logger.info(f"[DB] 连接数据库: {DB_PATH}")
    db.connect()
    db.create_tables([Settings, VideoTask], safe=True)
    _migrate_db()
    _init_default_settings()
    logger.info("[DB] 数据库初始化完成, 表: Settings, VideoTask")


_DEFAULT_BASE_URLS = {
    "dayangyu_base_url":    "https://api.dyuapi.com",
    "yunwu_base_url":       "https://yunwu.ai",
    "xiaobanshou_base_url": "https://api.xintianwengai.com",
    "bandianwa_base_url":   "https://api.hellobabygo.com",
    "hetang_veo_base_url":  "",  # 荷塘渠道（VEO + NanoBanana 共用）
}


def _init_default_settings() -> None:
    """写入默认 Base URL（仅当数据库中不存在时写入，不覆盖用户修改）"""
    for key, default_value in _DEFAULT_BASE_URLS.items():
        try:
            Settings.get(Settings.key == key)
        except Settings.DoesNotExist:
            Settings.replace(key=key, value=default_value).execute()
            logger.info(f"[DB] 写入默认配置: {key} = {default_value}")


def get_setting(key: str) -> Optional[str]:
    """获取配置"""
    try:
        setting = Settings.get(Settings.key == key)
        logger.debug(f"[DB] get_setting: key={key}, value={setting.value[:50] if setting.value else 'None'}")
        return setting.value
    except Settings.DoesNotExist:
        logger.debug(f"[DB] get_setting: key={key}, 不存在")
        return None


def set_setting(key: str, value: str) -> None:
    """设置配置"""
    Settings.replace(key=key, value=value).execute()
    logger.debug(f"[DB] set_setting: key={key}, value={value[:50] if value else ''}")


def get_all_settings() -> dict:
    """获取所有设置"""
    result = {}
    for setting in Settings.select():
        result[setting.key] = setting.value
    logger.debug(f"[DB] get_all_settings: 共 {len(result)} 项")
    return result


# ==================== VideoTask CRUD ====================

def create_video_task(image_path: str = '', prompt: str = '', status: str = 'pending') -> VideoTask:
    """创建视频任务"""
    task = VideoTask.create(image_path=image_path, prompt=prompt, status=status)
    logger.info(f"[DB] 创建视频任务: id={task.id}, status={status}, prompt={prompt[:50] if prompt else 'N/A'}")
    return task


def get_video_tasks() -> List[VideoTask]:
    """获取所有视频任务（按创建时间倒序）"""
    tasks = list(VideoTask.select().order_by(VideoTask.created_at.desc()))
    logger.debug(f"[DB] get_video_tasks: 共 {len(tasks)} 条")
    return tasks


def get_pending_video_tasks() -> List[VideoTask]:
    """获取待处理的视频任务"""
    tasks = list(VideoTask.select().where(VideoTask.status == 'pending'))
    if tasks:
        logger.debug(f"[DB] get_pending_video_tasks: 共 {len(tasks)} 条待处理")
    return tasks


def get_processing_video_tasks() -> List[VideoTask]:
    """获取处理中的视频任务"""
    tasks = list(VideoTask.select().where(VideoTask.status == 'processing'))
    if tasks:
        logger.debug(f"[DB] get_processing_video_tasks: 共 {len(tasks)} 条处理中")
    return tasks


def update_video_task(task_id: int, **kwargs) -> None:
    """更新视频任务"""
    VideoTask.update(**kwargs).where(VideoTask.id == task_id).execute()
    logger.debug(f"[DB] update_video_task: id={task_id}, fields={list(kwargs.keys())}")


def delete_video_task(task_id: int) -> None:
    """删除视频任务"""
    VideoTask.delete().where(VideoTask.id == task_id).execute()
    logger.info(f"[DB] 删除视频任务: id={task_id}")


def delete_all_video_tasks() -> int:
    """删除所有视频任务，返回删除数量"""
    count = VideoTask.delete().execute()
    logger.info(f"[DB] 删除所有视频任务: 共 {count} 条")
    return count
