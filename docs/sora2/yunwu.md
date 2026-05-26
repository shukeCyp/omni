# Sora2 — 云雾渠道

## 基本信息

| 项目 | 值 |
|------|-----|
| 代码标识 | `sora2 / yunwu` |
| 实现类 | `Sora2Yunwu` |
| Base URL | `https://yunwu.ai` |
| 配置键 | `yunwu_api_key` |
| 文生视频 | ✅ |
| 图生视频 | ✅（需先上传图床获取 URL） |
| 接口风格 | 独立创建/查询路径（非标准 `/v1/videos`） |

> 云雾渠道的创建接口为 `/v1/video/create`，查询接口为 `/v1/video/query?id=`，与其他渠道**不同**。

---

## Step 1（图生视频）：上传图片到图床

```http
POST https://imageproxy.zhongzhuan.chat/api/upload
Authorization: Bearer <yunwu_api_key>
Content-Type: multipart/form-data
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `file` | binary | 图片文件，文件名需带扩展名（如 `.jpg`、`.png`） |

### 响应

```json
{
  "data": {
    "url": "https://imageproxy.zhongzhuan.chat/uploads/ref.png"
  }
}
```

将 `data.url` 传入下一步的 `images` 数组。

---

## Step 2：创建任务

```http
POST https://yunwu.ai/v1/video/create
Authorization: Bearer <yunwu_api_key>
Content-Type: application/json
```

```json
{
  "images": [],
  "model": "sora-2",
  "orientation": "portrait",
  "prompt": "产品展示视频，竖屏，自然光线",
  "size": "large",
  "duration": 10,
  "watermark": false,
  "private": true
}
```

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `images` | array\<string\> | ✅ | `[]` | 图床 URL 列表；文生视频传 `[]`，图生视频传图床 URL |
| `model` | string | ✅ | — | 文生视频 `"sora-2"`；图生视频 `"sora-2-all"` |
| `orientation` | string | ✅ | — | `"portrait"`（竖屏）/ `"landscape"`（横屏） |
| `prompt` | string | ✅ | — | 提示词 |
| `size` | string | 否 | `"large"` | `"large"` / `"small"` |
| `duration` | int | 否 | `10` | 视频时长（秒） |
| `watermark` | bool | 否 | `false` | 是否加水印 |
| `private` | bool | 否 | `true` | 是否私密 |

### 响应

```json
{
  "id": "task_abc123",
  "status": "pending"
}
```

| 字段 | 说明 |
|------|------|
| `id` | 任务 ID，用于后续查询 |
| `status` | 初始状态 |

---

## Step 3：查询任务状态

```http
GET https://yunwu.ai/v1/video/query?id={task_id}
Authorization: Bearer <yunwu_api_key>
Content-Type: application/json
```

> 注意：查询使用 **Query String** 传参（`?id=`），非路径参数。

### 响应（进行中）

```json
{
  "id": "task_abc123",
  "status": "processing"
}
```

### 响应（已完成）

```json
{
  "id": "task_abc123",
  "status": "completed",
  "video_url": "https://cdn.yunwu.ai/videos/output.mp4",
  "enhanced_prompt": "产品展示视频，竖屏，自然光线，高清"
}
```

| 字段 | 说明 |
|------|------|
| `status` | 见[状态枚举](./overview.md#任务状态枚举) |
| `video_url` | 视频下载链接（完成后出现） |
| `enhanced_prompt` | 模型优化后的提示词（可选） |

---

## 状态映射

| API 返回值 | 内部状态 |
|-----------|----------|
| `pending` | `PENDING` |
| `processing` | `PROCESSING` |
| `completed` | `COMPLETED` |
| `failed` | `FAILED` |

---

## 错误处理

| 场景 | 处理方式 |
|------|----------|
| API Key 未配置 | 返回错误提示 |
| 图片文件不存在 | 抛出 `FileNotFoundError` |
| 图床上传失败 | 抛出 `RuntimeError: 图片上传图床失败` |
| HTTP 4xx / 5xx | 直接抛出异常，日志记录响应体 |

---

## 完整调用示例（Python）

```python
import requests, time

API_KEY = "your_yunwu_api_key"
BASE = "https://yunwu.ai"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

# 1. 创建文生视频任务
resp = requests.post(
    f"{BASE}/v1/video/create",
    headers=HEADERS,
    json={
        "images": [],
        "model": "sora-2",
        "orientation": "portrait",
        "prompt": "产品展示视频，竖屏",
        "size": "large",
        "duration": 10,
        "watermark": False,
        "private": True,
    },
    timeout=60,
)
task_id = resp.json()["id"]

# 2. 轮询状态（每 5 秒，最多 15 分钟）
for _ in range(180):
    r = requests.get(
        f"{BASE}/v1/video/query",
        headers=HEADERS,
        params={"id": task_id},
        timeout=30,
    ).json()
    if r["status"] == "completed":
        video_url = r["video_url"]
        break
    if r["status"] == "failed":
        raise RuntimeError("视频生成失败")
    time.sleep(5)

# 3. 下载视频
with requests.get(video_url, stream=True, timeout=120) as vr:
    with open("output.mp4", "wb") as f:
        for chunk in vr.iter_content(8192):
            f.write(chunk)
```
