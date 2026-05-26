# NanoBanana — 云雾渠道

## 基本信息

| 项目 | 值 |
|------|-----|
| 代码标识 | `nanobanana / yunwu` |
| 实现类 | `NanoBananaYunwu` |
| Base URL | `https://yunwu.ai` |
| 接口风格 | fal-ai 队列（提交 → 轮询 → 拉取） |
| 配置键 | `yunwu_api_key` |
| 图生图支持 | ✅（需先上传图床） |
| 最大参考图数 | 不限（每张分别上传） |

---

## 接口流程

```
1. [可选] 上传参考图到图床  →  POST https://imageproxy.zhongzhuan.chat/api/upload
2. 提交生成任务            →  POST https://yunwu.ai/fal-ai/nano-banana
3. 轮询任务状态            →  GET  {status_url}   (每 3 秒，最多 240 秒)
4. 拉取生成结果            →  GET  {response_url}
5. 下载图片               →  GET  {images[0].url}
```

---

## Step 1：上传参考图（图生图时）

### 请求

```http
POST https://imageproxy.zhongzhuan.chat/api/upload
Authorization: Bearer <yunwu_api_key>
Content-Type: multipart/form-data
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `file` | binary | 图片文件，文件名需带正确扩展名（如 `ref_1.png`） |

### 响应

```json
{
  "data": {
    "url": "https://imageproxy.zhongzhuan.chat/uploads/xxx.png"
  }
}
```

| 字段 | 说明 |
|------|------|
| `data.url` | 图床公网 URL，传入下一步 `image_urls` |

---

## Step 2：提交生成任务

### 请求

```http
POST https://yunwu.ai/fal-ai/nano-banana
Authorization: Bearer <yunwu_api_key>
Content-Type: application/json
```

```json
{
  "prompt": "一个穿着红色连衣裙的女孩站在花园里",
  "num_images": 1,
  "output_format": "png",
  "aspect_ratio": "9:16",
  "image_urls": ["https://imageproxy.zhongzhuan.chat/uploads/ref.png"]
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `prompt` | string | ✅ | 图片描述提示词 |
| `num_images` | int | ✅ | 固定传 `1` |
| `output_format` | string | ✅ | 固定传 `"png"` |
| `aspect_ratio` | string | 推荐 | 宽高比，见[总览](./overview.md)。不传则用模型默认值 |
| `image_urls` | array\<string\> | 否 | 图床 URL 列表，图生图时传入，文生图时省略或传 `[]` |

### 响应

```json
{
  "request_id": "abc123",
  "status_url": "https://queue.fal.run/fal-ai/nano-banana/requests/abc123/status",
  "response_url": "https://queue.fal.run/fal-ai/nano-banana/requests/abc123"
}
```

> **注意**：`status_url` 和 `response_url` 中的 `https://queue.fal.run` 会被自动替换为 `https://yunwu.ai`。

---

## Step 3：轮询任务状态

### 请求

```http
GET {status_url}
Authorization: Bearer <yunwu_api_key>
```

### 响应

```json
{
  "status": "COMPLETED"
}
```

| `status` 值 | 含义 |
|------------|------|
| `IN_QUEUE` / `PENDING` | 排队中 |
| `IN_PROGRESS` / `PROCESSING` | 生成中 |
| `COMPLETED` | 已完成 |
| `FAILED` / `ERROR` / `CANCELLED` | 失败 |

**轮询策略**：每 3 秒一次，最大等待 240 秒，超时则报错。

---

## Step 4：拉取生成结果

### 请求

```http
GET {response_url}
Authorization: Bearer <yunwu_api_key>
```

### 响应

```json
{
  "images": [
    {
      "url": "https://fal.media/files/xxx/output.png",
      "width": 576,
      "height": 1024
    }
  ],
  "prompt": "一个穿着红色连衣裙的女孩站在花园里"
}
```

| 字段 | 说明 |
|------|------|
| `images[0].url` | 图片下载链接，有时效，需立即下载 |

---

## Step 5：下载图片

```http
GET {images[0].url}
```

直接 HTTP GET 下载，响应体即为图片二进制，`Content-Type` 即 MIME 类型。

---

## 错误处理

| 场景 | 处理方式 |
|------|----------|
| 上传图床失败 | 抛出 RuntimeError，终止流程 |
| 提交任务返回 4xx | 解析 `error.message` 或 `message` 字段 |
| 轮询超时（240s） | 报错 "轮询任务结果超时" |
| 状态为 FAILED | 解析 `error` 字段返回错误信息 |
| 结果无图片链接 | 报错 "API 未返回图片链接" |

---

## 完整调用示例（Python）

```python
import requests, time, base64

API_KEY = "your_yunwu_api_key"
BASE_URL = "https://yunwu.ai"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

# 1. 提交任务
resp = requests.post(
    f"{BASE_URL}/fal-ai/nano-banana",
    headers=HEADERS,
    json={"prompt": "产品展示图", "num_images": 1, "output_format": "png", "aspect_ratio": "9:16"},
    timeout=60,
)
data = resp.json()
status_url = data["status_url"].replace("https://queue.fal.run", BASE_URL)
response_url = data["response_url"].replace("https://queue.fal.run", BASE_URL)

# 2. 轮询状态
for _ in range(80):
    s = requests.get(status_url, headers=HEADERS, timeout=30).json()
    if s["status"] == "COMPLETED":
        break
    if s["status"] in ("FAILED", "ERROR"):
        raise RuntimeError(s.get("error", "生成失败"))
    time.sleep(3)

# 3. 拉取结果
result = requests.get(response_url, headers=HEADERS, timeout=60).json()
image_url = result["images"][0]["url"]

# 4. 下载图片
img_bytes = requests.get(image_url, timeout=120).content
with open("output.png", "wb") as f:
    f.write(img_bytes)
```
