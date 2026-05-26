# Sora2 — 大洋鱼渠道

## 基本信息

| 项目 | 值 |
|------|-----|
| 代码标识 | `sora2 / dayangyu` |
| 实现类 | `Sora2Dayangyu` |
| Base URL | `https://api.dyuapi.com` |
| 配置键 | `dayangyu_api_key` |
| 文生视频 | ✅ `application/json` |
| 图生视频 | ✅ `multipart/form-data` |
| 额外接口 | `GET /v1/videos/{id}/content`（视频二进制） |

---

## 1. 创建任务

### 1a. 文生视频

```http
POST https://api.dyuapi.com/v1/videos
Authorization: Bearer <dayangyu_api_key>
Content-Type: application/json
```

```json
{
  "prompt": "一个女孩在樱花树下漫步，慢镜头，电影感",
  "model": "sora2-portrait"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `prompt` | string | ✅ | 视频描述提示词 |
| `model` | string | ✅ | 见下方模型列表 |

### 1b. 图生视频

```http
POST https://api.dyuapi.com/v1/videos
Authorization: Bearer <dayangyu_api_key>
Content-Type: multipart/form-data
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `input_reference` | file | ✅ | 参考图文件（本地图片，带文件名） |
| `prompt` | string | ✅ | 提示词 |
| `model` | string | ✅ | 模型名 |
| `size` | string | 否 | 尺寸，如 `1280x720` |
| `seconds` | string | 否 | 时长（秒），如 `"10"` |

---

## 2. 创建任务响应

```json
{
  "id": "task_abc123",
  "status": "pending",
  "progress": 0,
  "created_at": "2025-01-01T00:00:00Z"
}
```

| 字段 | 说明 |
|------|------|
| `id` | 任务 ID，用于后续查询 |
| `status` | 初始状态，通常为 `pending` |
| `progress` | 进度 0–100 |
| `created_at` | 创建时间 ISO 8601 |

---

## 3. 查询任务状态

```http
GET https://api.dyuapi.com/v1/videos/{task_id}
Authorization: Bearer <dayangyu_api_key>
Accept: application/json
```

### 响应（进行中）

```json
{
  "id": "task_abc123",
  "status": "processing",
  "progress": 45
}
```

### 响应（已完成）

```json
{
  "id": "task_abc123",
  "status": "success",
  "progress": 100,
  "video_url": "https://cdn.dyuapi.com/videos/output.mp4",
  "created_at": "2025-01-01T00:00:00Z",
  "completed_at": "2025-01-01T00:05:30Z"
}
```

| 字段 | 说明 |
|------|------|
| `status` | 见[状态枚举](./overview.md#任务状态枚举) |
| `video_url` | 视频下载链接（完成后出现） |
| `completed_at` | 完成时间 |

---

## 4. 下载视频内容（可选）

当 `video_url` 存在时效限制时，可通过此接口直接拉取视频二进制：

```http
GET https://api.dyuapi.com/v1/videos/{task_id}/content
Authorization: Bearer <dayangyu_api_key>
Accept: application/json, */*
```

**响应**：视频文件二进制流，`Content-Type` 为 `video/mp4` 等。

> 此接口响应较慢，优先使用 `video_url` 直接下载。

---

## 模型列表

| 方向 | 时长 | 模型名 |
|------|------|--------|
| 竖屏（portrait） | 10s | `sora2-portrait` |
| 竖屏（portrait） | 15s | `sora2-portrait-15s` |
| 横屏（landscape） | 10s | `sora2-landscape` |
| 横屏（landscape） | 15s | `sora2-landscape-15s` |

**Pro 模型（生成时间更长，质量更高）**：
| 方向 | 时长 | 模型名 |
|------|------|--------|
| 竖屏 | 25s | `sora2-pro-portrait-25s` |
| 横屏 | 25s | `sora2-pro-landscape-25s` |
| 竖屏高清 | 15s | `sora2-pro-portrait-hd-15s` |
| 横屏高清 | 15s | `sora2-pro-landscape-hd-15s` |

---

## 错误处理

| 场景 | 处理方式 |
|------|----------|
| API Key 未配置 | 返回错误提示 |
| HTTP 4xx / 5xx | 解析 `error.message` → `error.detail` → `message` → `msg` → 响应体文本 |
| 图片文件不存在 | 跳过图生视频，改为文生视频 |
| 任务 ID 为空 | 返回 FAILED 状态 |

---

## 完整调用示例（Python）

```python
import requests, time

API_KEY = "your_dayangyu_api_key"
BASE = "https://api.dyuapi.com"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

# 1. 创建文生视频任务
resp = requests.post(
    f"{BASE}/v1/videos",
    headers=HEADERS,
    json={"prompt": "产品展示视频，竖屏", "model": "sora2-portrait"},
    timeout=60,
)
task_id = resp.json()["id"]

# 2. 轮询状态（每 5 秒，最多 15 分钟）
for _ in range(180):
    r = requests.get(
        f"{BASE}/v1/videos/{task_id}",
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=30,
    ).json()
    if r["status"] in ("success", "completed", "done"):
        video_url = r["video_url"]
        break
    if r["status"] in ("failed", "error", "cancelled"):
        raise RuntimeError("视频生成失败")
    time.sleep(5)

# 3. 下载视频
with requests.get(video_url, stream=True, timeout=120) as vr:
    with open("output.mp4", "wb") as f:
        for chunk in vr.iter_content(8192):
            f.write(chunk)
```
