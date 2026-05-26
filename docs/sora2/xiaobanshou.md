# Sora2 — 小搬手渠道

## 基本信息

| 项目 | 值 |
|------|-----|
| 代码标识 | `sora2 / xiaobanshou` |
| 实现类 | `Sora2Xiaobanshou` |
| Base URL | `https://api.xintianwengai.com` |
| 配置键 | `xiaobanshou_api_key` |
| 文生视频 | ✅ `application/json` |
| 图生视频 | ✅ `multipart/form-data` |

> 接口结构与大洋鱼渠道高度一致，区别仅在于 Base URL 和模型命名格式。

---

## 1. 创建任务

### 1a. 文生视频

```http
POST https://api.xintianwengai.com/v1/videos
Authorization: Bearer <xiaobanshou_api_key>
Content-Type: application/json
```

```json
{
  "prompt": "一双白色运动鞋放在木质桌面上，自然光线",
  "model": "sora-2-portrait-10s"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `prompt` | string | ✅ | 提示词，支持 `@角色username` |
| `model` | string | ✅ | 见下方模型列表 |

### 1b. 图生视频

```http
POST https://api.xintianwengai.com/v1/videos
Authorization: Bearer <xiaobanshou_api_key>
Content-Type: multipart/form-data
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `input_reference` | file | ✅ | 参考图文件（本地图片，带文件名） |
| `prompt` | string | ✅ | 提示词 |
| `model` | string | ✅ | 模型名 |

---

## 2. 创建任务响应

```json
{
  "id": "task_xyz789",
  "status": "pending",
  "progress": 0,
  "created_at": "2025-01-01T00:00:00Z"
}
```

---

## 3. 查询任务状态

```http
GET https://api.xintianwengai.com/v1/videos/{task_id}
Authorization: Bearer <xiaobanshou_api_key>
```

### 响应（已完成）

```json
{
  "id": "task_xyz789",
  "status": "success",
  "progress": 100,
  "video_url": "https://cdn.xintianwengai.com/videos/output.mp4",
  "created_at": "2025-01-01T00:00:00Z",
  "completed_at": "2025-01-01T00:04:00Z"
}
```

---

## 模型列表

| 方向 | 时长 | 模型名 |
|------|------|--------|
| 竖屏（portrait） | 5s | `sora-2-portrait-5s` |
| 竖屏（portrait） | 10s | `sora-2-portrait-10s` |
| 竖屏（portrait） | 15s | `sora-2-portrait-15s` |
| 横屏（landscape） | 5s | `sora-2-landscape-5s` |
| 横屏（landscape） | 10s | `sora-2-landscape-10s` |
| 横屏（landscape） | 15s | `sora-2-landscape-15s` |

---

## 错误处理

| 场景 | 处理方式 |
|------|----------|
| API Key 未配置 | 返回错误提示 |
| HTTP 4xx / 5xx | 解析 `error.message` → `error.detail` → `message` → `msg` |
| 图片文件不存在 | 跳过图生视频，改为文生视频 |
| 任务 ID 为空 | 返回 FAILED 状态，错误信息 "任务 ID 为空" |

---

## 完整调用示例（Python）

```python
import requests, time

API_KEY = "your_xiaobanshou_api_key"
BASE = "https://api.xintianwengai.com"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

# 1. 创建文生视频任务
resp = requests.post(
    f"{BASE}/v1/videos",
    headers=HEADERS,
    json={"prompt": "产品展示视频，竖屏", "model": "sora-2-portrait-10s"},
    timeout=60,
)
task_id = resp.json()["id"]

# 2. 轮询状态
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
