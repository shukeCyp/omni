"""云雾 Gemini 文本生成服务 - 提示词生成"""

import base64
import json
import os
import shutil
import threading
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional

import requests

from ..config import BASE_DIR
from ..constants import SettingKeys
from ..database import get_setting
from ..logger import logger

TMP_DIR = BASE_DIR / "data" / "tmp"
STATE_FILE = TMP_DIR / "prompt_state.json"

_state_lock = threading.Lock()

SYSTEM_PROMPT = """你是TikTok墨西哥区专业短视频策略专家，精通拉美年轻用户偏好、TikTok算法、即梦Seedance视频生成规则。

核心能力：

1. 快速识别产品：目标人群、痛点、差异化卖点；

2. 内容结构严格遵守：【提问制造需求 → 揭秘锁定真相 → 产品核心吸引力 → 造梦放大下单欲】；

3. 严格15秒竖屏9:16，分镜按0‑3s强钩子、3‑10s塑品、10‑15s促单；

4. 判断镜头节奏：快切镜/长镜头，UGC原生手持拍摄，去AI滤镜、瑕疵真实质感、去稳定化、轻微镜头抖动；

5. 细节完整：场景、光线、摆设、人物、表情、动作、镜头角度、产品无畸变；

6. 输出2部分：【即梦Seedance可直接复制中文提示词】+【墨西哥本土化西班牙语口播文案】；

7. 严格合规：规避敏感词、夸大词、极限词，适配即梦生成规则，无违规内容。

8.最终将即梦Seedance可直接复制中文提示词和墨西哥本土化西班牙语口播文案合为一体，可直接复制给Seedance使用。口播文案不要中文提示词

9.我要生成通用提示词，请你不要描述产品的细节及图案，根据产品图和需求进行生成。

10.保持口播嘴型的一致性。

提示词禁忌：

一、基础技术硬禁忌（所有视频必加）

镜头切换，转场特效，剪辑痕迹，画面跳转，跳帧卡顿，画面断层，硬切，分镜，多镜头，蒙太奇，推拉摇移过度，画面抖动剧烈，画面模糊，画质低，像素差，颗粒感重，过曝，暗角，硬阴影，反光严重，穿帮镜头，穿模，贴图错误，模型崩坏，肢体畸形，手指畸形，面部扭曲，表情僵硬，动作不自然

二、人物与语言禁忌（所有视频必加）

亚洲人，中国人，白人，黑人，非拉丁裔，欧美面孔，东亚面孔，英语，中文，法语，德语，日语，韩语，非西班牙语，机械配音，机器人声音，口型不同步，声音与动作脱节，男性博主 (女装 / 美妆类专用), 老年博主，儿童博主，身材肥胖，身材过瘦，妆容夸张，浓妆艳抹，纹身，穿孔

三、画面元素禁忌（所有视频必加）

文字，字幕，水印，贴纸，特效，动画，边框，滤镜，美颜过度，磨皮过度，瘦脸过度，手机，相机，三脚架，拍摄设备，遥控器，电线，插座，垃圾桶，杂物，垃圾，凌乱，杂乱，多余人物，路人，观众，动物，植物 (非场景指定), 家具 (非场景指定)

四、产品展示禁忌（所有视频必加）

产品变形，产品破损，产品污渍，产品划痕，产品掉色，产品开胶，产品断裂，功能失效，操作失败，漏水，漏油，撒漏，糊锅，变质，发霉，异味，飞粉，结块，卡粉，脱妆，起球，起皱，缩水，掉色，开线，拉链损坏，纽扣脱落

五、墨西哥市场专属禁忌

美国国旗，美国元素，西班牙国旗，西班牙元素，殖民历史相关，政治相关，宗教相关，骷髅头 (亡灵节除外), 黑色猫咪，数字 13, 黄色花朵 (葬礼用), 紫色 (与死亡相关), 左手递东西，竖中指，交叉手臂，摸头

六、特殊品类专属禁忌

女装类

露脸 (不露脸视频专用), 上半身 (仅展示下装专用), 下半身 (仅展示上装专用), 内衣，泳装，透视装，暴露服装，性感姿势，挑逗动作

美妆类

皮肤过敏，红肿，痘痘，瑕疵，卸妆，化妆失败，口红沾杯，眼影飞粉，粉底卡粉，睫毛膏晕染

数码类

屏幕碎裂，机身变形，进水，死机，卡顿，连接失败，充电失败，续航短，发热严重

美食类

生肉，生鱼，生鸡蛋，变质食物，过期食物，垃圾食品，高热量食物，油炸食品 (非产品本身)

家居类

灰尘，污垢，污渍，破损家具，杂乱房间，卫生间，卧室 (非场景指定)

使用说明

通用版：直接复制「基础技术硬禁忌 + 人物与语言禁忌 + 画面元素禁忌 + 产品展示禁忌 + 墨西哥市场专属禁忌」到 Seedance 负面提示词框

品类版：在通用版基础上，添加对应「特殊品类专属禁忌」

场景版：根据具体场景添加额外禁忌（如试衣间场景添加 "其他顾客"" 试衣间门打开 ""衣架过多"）

更新提示：每次生成新视频前，检查是否有新增禁忌词，及时补充到库中

以纯文本的形式给我，我要直接点击复制使用。"""

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff", ".tif"}


def _load_state() -> dict:
    """加载状态文件（调用方需持有 _state_lock）"""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"items": []}


def _save_state(state: dict) -> None:
    """保存状态文件（调用方需持有 _state_lock）"""
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _find_item_by_id(item_id: str) -> Optional[dict]:
    """根据 ID 查找项目"""
    with _state_lock:
        state = _load_state()
        for item in state.get("items", []):
            if item["id"] == item_id:
                return dict(item)
    return None


def _update_item(item_id: str, updates: dict) -> Optional[dict]:
    """更新项目字段（原子操作：加锁 → 读取 → 修改 → 写入）"""
    with _state_lock:
        state = _load_state()
        for item in state.get("items", []):
            if item["id"] == item_id:
                item.update(updates)
                _save_state(state)
                return dict(item)
    return None


def import_images(source_folder: str) -> dict:
    """递归扫描文件夹中的图片，创建 tmp 子文件夹并复制图片"""
    folder_path = Path(source_folder)
    if not folder_path.is_dir():
        return {"ok": False, "msg": "所选路径不是有效文件夹"}

    # 递归查找图片
    image_files = []
    for root, dirs, files in os.walk(folder_path):
        # 跳过隐藏文件夹
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for f in files:
            if Path(f).suffix.lower() in IMAGE_EXTENSIONS and not f.startswith("."):
                image_files.append(Path(root) / f)

    if not image_files:
        return {"ok": False, "msg": "所选文件夹中未找到图片文件"}

    with _state_lock:
        state = _load_state()
        items = state.get("items", [])
        new_items = []

        for img_path in image_files:
            item_id = uuid.uuid4().hex[:12]
            item_tmp_dir = TMP_DIR / item_id
            item_tmp_dir.mkdir(parents=True, exist_ok=True)

            # 复制图片到 tmp 子文件夹
            ext = img_path.suffix.lower()
            dest_name = f"image{ext}"
            dest_path = item_tmp_dir / dest_name
            shutil.copy2(img_path, dest_path)

            # 取图片的直接父文件夹名作为分类
            folder_name = img_path.parent.name
            item = {
                "id": item_id,
                "folder_name": folder_name,
                "image_name": img_path.name,
                "status": "pending",
                "error": None,
            }
            items.append(item)
            new_items.append(dict(item))

        _save_state(state)
    logger.info(f"[提示词生成] 导入 {len(new_items)} 张图片，来源: {source_folder}")
    return {"ok": True, "items": new_items, "total": len(new_items)}


def get_items() -> dict:
    """获取所有项目列表"""
    with _state_lock:
        state = _load_state()
        items = state.get("items", [])
        changed = False
        for item in items:
            prompt_file = TMP_DIR / item["id"] / "prompt.txt"
            if prompt_file.exists() and item.get("status") not in ("processing",):
                if item.get("status") != "completed":
                    item["status"] = "completed"
                    changed = True
            tmp_dir = TMP_DIR / item["id"]
            if not tmp_dir.exists():
                item["status"] = "failed"
                item["error"] = "临时文件夹已被删除"
                changed = True
        if changed:
            _save_state(state)
        result = []
        for it in items:
            d = dict(it)
            d["thumb"] = get_thumbnail(d["id"])
            result.append(d)
        return {"ok": True, "items": result}


def generate_prompt(item_id: str) -> dict:
    """调用 yunwu gemini-3.1-pro-preview 生成提示词（支持自动重试）"""
    item = _find_item_by_id(item_id)
    if not item:
        return {"ok": False, "msg": "项目不存在"}

    _update_item(item_id, {"status": "processing", "error": None})

    # 读取 settings
    api_key = get_setting(SettingKeys.YUNWU_API_KEY)
    base_url = get_setting(SettingKeys.YUNWU_BASE_URL) or "https://yunwu.ai"

    if not api_key:
        _update_item(item_id, {"status": "failed", "error": "未配置云雾 API Key"})
        return {"ok": False, "msg": "未配置云雾 API Key，请在设置页面配置"}

    # 读取重试配置
    auto_retry = get_setting(SettingKeys.AUTO_RETRY) or "false"
    max_retry_str = get_setting(SettingKeys.IMAGE_MAX_RETRY) or "0"
    try:
        max_retry = int(max_retry_str)
    except (ValueError, TypeError):
        max_retry = 0

    # 读取图片
    tmp_dir = TMP_DIR / item_id
    image_files = list(tmp_dir.glob("image.*"))
    if not image_files:
        _update_item(item_id, {"status": "failed", "error": "图片文件不存在"})
        return {"ok": False, "msg": "图片文件不存在"}

    image_path = image_files[0]
    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode("ascii")

    # 判断 MIME 类型
    ext_to_mime = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
    }
    mime_type = ext_to_mime.get(image_path.suffix.lower(), "image/jpeg")

    # 构建请求
    model = "gemini-3.1-pro-preview"
    url = f"{base_url.rstrip('/')}/v1beta/models/{model}:generateContent?key={api_key}"

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": SYSTEM_PROMPT},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": image_b64,
                        }
                    },
                ],
            }
        ],
        "generationConfig": {
            "responseModalities": ["TEXT"],
        },
    }

    headers = {"Content-Type": "application/json"}

    total_attempts = max_retry + 1 if auto_retry == "true" else 1
    last_error = None

    for attempt in range(1, total_attempts + 1):
        logger.info(
            f"[提示词生成] 请求 gemini-3.1-pro-preview | "
            f"item={item_id} | 第{attempt}/{total_attempts}次尝试"
        )

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=300)
            resp.raise_for_status()
            data = resp.json()

            # 提取文本
            candidates = data.get("candidates") or []
            if not candidates:
                error = data.get("error", {})
                msg = error.get("message") if isinstance(error, dict) else str(error)
                raise Exception(msg or "响应中无 candidates")

            parts = candidates[0].get("content", {}).get("parts", [])
            text_parts = [p.get("text", "") for p in parts if p.get("text")]
            result_text = "".join(text_parts)

            if not result_text:
                raise Exception("响应中未找到文本内容")

            # 保存到 prompt.txt
            prompt_file = tmp_dir / "prompt.txt"
            with open(prompt_file, "w", encoding="utf-8") as f:
                f.write(result_text)

            _update_item(item_id, {"status": "completed", "error": None})
            logger.info(
                f"[提示词生成] 生成成功 | item={item_id} | "
                f"尝试次数={attempt} | 文本长度={len(result_text)}"
            )
            return {"ok": True, "text": result_text}

        except requests.exceptions.Timeout:
            last_error = "请求超时"
            logger.warning(
                f"[提示词生成] 超时 | item={item_id} | "
                f"第{attempt}/{total_attempts}次尝试"
            )
        except Exception as exc:
            last_error = str(exc)
            logger.warning(
                f"[提示词生成] 失败 | item={item_id} | "
                f"第{attempt}/{total_attempts}次尝试 | {last_error}"
            )

        if attempt < total_attempts:
            import time
            time.sleep(2)

    _update_item(item_id, {"status": "failed", "error": last_error})
    logger.error(f"[提示词生成] 全部重试失败 | item={item_id} | {last_error}")
    return {"ok": False, "msg": last_error or "生成失败"}


def _get_image_path(item_id: str) -> Optional[Path]:
    """获取项目图片路径"""
    tmp_dir = TMP_DIR / item_id
    if not tmp_dir.is_dir():
        return None
    for ext in IMAGE_EXTENSIONS:
        p = tmp_dir / f"image{ext}"
        if p.exists():
            return p
    return None


def get_image_base64(item_id: str) -> dict:
    """读取图片并返回 base64（用于预览）"""
    img_path = _get_image_path(item_id)
    if not img_path:
        return {"ok": False, "msg": "图片文件不存在"}

    ext_to_mime = {
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".webp": "image/webp", ".gif": "image/gif", ".bmp": "image/bmp",
    }
    mime = ext_to_mime.get(img_path.suffix.lower(), "image/jpeg")

    try:
        with open(img_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        return {"ok": True, "base64": b64, "mime": mime}
    except Exception as exc:
        return {"ok": False, "msg": f"读取失败: {exc}"}


def get_thumbnail(item_id: str) -> str:
    """获取缩略图 base64（小尺寸，嵌入列表 JSON）"""
    img_path = _get_image_path(item_id)
    if not img_path:
        return ""
    try:
        from PIL import Image
        import io
        with Image.open(img_path) as img:
            img.thumbnail((176, 176))
            buf = io.BytesIO()
            img.convert("RGB").save(buf, "JPEG", quality=60)
            return base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        pass
    # 回退：直接读原始文件的前若干字节
    try:
        with open(img_path, "rb") as f:
            return base64.b64encode(f.read()).decode("ascii")
    except Exception:
        return ""


def read_prompt(item_id: str) -> dict:
    """读取 prompt.txt 内容"""
    prompt_file = TMP_DIR / item_id / "prompt.txt"
    if not prompt_file.exists():
        return {"ok": False, "msg": "提示词文件不存在，请先生成"}
    try:
        with open(prompt_file, "r", encoding="utf-8") as f:
            text = f.read()
        return {"ok": True, "text": text}
    except Exception as exc:
        return {"ok": False, "msg": f"读取失败: {exc}"}


def delete_item(item_id: str) -> dict:
    """删除项目的 tmp 子文件夹"""
    tmp_dir = TMP_DIR / item_id
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)

    with _state_lock:
        state = _load_state()
        items = state.get("items", [])
        state["items"] = [it for it in items if it["id"] != item_id]
        _save_state(state)

    logger.info(f"[提示词生成] 删除项目 | item={item_id}")
    return {"ok": True}


def open_item_folder(item_id: str) -> dict:
    """在文件管理器中打开 tmp 子文件夹"""
    tmp_dir = TMP_DIR / item_id
    if not tmp_dir.exists():
        return {"ok": False, "msg": "文件夹不存在"}

    import platform
    import subprocess

    path = str(tmp_dir)
    try:
        system = platform.system()
        if system == "Darwin":
            subprocess.run(["open", path], check=True)
        elif system == "Windows":
            os.startfile(path)
        else:
            subprocess.run(["xdg-open", path], check=True)
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "msg": f"打开失败: {exc}"}
