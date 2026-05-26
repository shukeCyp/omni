# NanoBanana — 荷塘渠道

## 基本信息

| 项目 | 值 |
|------|-----|
| 代码标识 | `nanobanana / hetang` |
| 实现类 | `NanoBananaGlinCustom` |
| Base URL | **用户在设置页面自定义**（无默认值） |
| 接口风格 | OpenAI 兼容 Chat Completions SSE 流式 |
| 配置键 | `hetang_veo_api_key` + `hetang_veo_base_url` |
| 图生图支持 | ✅（单张，base64 内嵌） |
| 最大参考图数 | 1 张 |
| 与 VEO3 共用 | ✅（同一套 Base URL 和 API Key） |

> **荷塘渠道的 NanoBanana 生图与 VEO3 视频使用完全相同的 Base URL 和 API Key，在设置页面统一填写。**

---

## 接口

```http
POST {hetang_veo_base_url}/v1/chat/completions
Authorization: Bearer <hetang_veo_api_key>
Content-Type: application/json
```

---

## 请求体

### 文生图

```json
{
  "model": "gemini-3.0-pro-image-portrait",
  "messages": [
    {
      "role": "user",
      "content": "一个穿着红色连衣裙的女孩站在花园里"
    }
  ],
  "stream": true
}
```

### 图生图

```json
{
  "model": "gemini-3.0-pro-image-portrait",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "将这张产品图放到自然场景中"
        },
        {
          "type": "image_url",
          "image_url": {
            "url": "data:image/jpeg;base64,/9j/4AAQ..."
          }
        }
      ]
    }
  ],
  "stream": true
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `model` | string | ✅ | 模型名，见[总览](./overview.md)的命名规则 |
| `messages` | array | ✅ | 固定一条 user 消息 |
| `messages[0].content` | string \| array | ✅ | 文生图传字符串；图生图传含 `text` + `image_url` 的数组 |
| `stream` | bool | ✅ | 固定传 `true` |

---

## 响应格式（SSE 流式）

```
data: {"choices":[{"delta":{"content":"![](data:image/png;base64,iVBOR...)"}}]}
data: {"choices":[{"delta":{"content":""}}]}
data: [DONE]
```

- 每行以 `data: ` 开头，跳过空行
- `[DONE]` 表示流结束
- 拼接所有 `delta.content`，再从 Markdown `![]()` 中提取图片

### 图片提取规则

```python
import re

# 正则匹配 Markdown 图片
match = re.search(r'!\[.*?\]\((.*?)\)', full_content, re.DOTALL)
image_src = match.group(1).strip()

if image_src.startswith("data:"):
    # base64 内嵌，直接解析 mime 和数据
    # 格式：data:image/png;base64,<base64_data>
    mime, b64 = image_src.split(",", 1)
    mime_type = mime.split(":")[1].split(";")[0]
elif image_src.startswith("http"):
    # URL 形式，需再次 GET 下载
    img_resp = requests.get(image_src, timeout=60)
    mime_type = img_resp.headers.get("Content-Type", "image/png")
    image_bytes = img_resp.content
```

---

## 模型列表

| 宽高比 | 清晰度 | 模型名 |
|--------|--------|--------|
| 9:16（竖屏） | 1K | `gemini-3.0-pro-image-portrait` |
| 9:16（竖屏） | 2K | `gemini-3.0-pro-image-portrait-2k` |
| 9:16（竖屏） | 4K | `gemini-3.0-pro-image-portrait-4k` |
| 16:9（横屏） | 1K | `gemini-3.0-pro-image-landscape` |
| 16:9（横屏） | 2K | `gemini-3.0-pro-image-landscape-2k` |
| 16:9（横屏） | 4K | `gemini-3.0-pro-image-landscape-4k` |
| 1:1（方形） | 1K | `gemini-3.0-pro-image-square` |
| 4:3 | 1K | `gemini-3.0-pro-image-four-three` |
| 3:4 | 1K | `gemini-3.0-pro-image-three-four` |

---

## 错误处理

| 场景 | 处理方式 |
|------|----------|
| Base URL 或 API Key 未配置 | 返回错误："未配置荷塘的 Base URL 或 API Key" |
| 传入多于 1 张参考图 | 返回错误："当前图片渠道仅支持单张参考图" |
| SSE 流中无 content | 返回错误："SSE 流中未收到 content 数据" |
| 响应中无图片标记 | 返回错误："未能从响应中提取图片" |
| HTTP 错误 | 解析 `error.message` 字段，返回具体错误 |
| 请求超时（300s） | 返回错误："请求超时" |

---

## 完整调用示例（Python）

```python
import requests, re, json

API_KEY = "your_hetang_api_key"
BASE_URL = "https://your-custom-base-url.com"  # 荷塘自定义地址

url = f"{BASE_URL}/v1/chat/completions"
headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

payload = {
    "model": "gemini-3.0-pro-image-portrait",
    "messages": [{"role": "user", "content": "产品展示图，白色背景，高清"}],
    "stream": True,
}

resp = requests.post(url, headers=headers, json=payload, stream=True, timeout=300)
resp.raise_for_status()

full_content = ""
for line in resp.iter_lines(decode_unicode=True):
    if not line or not line.startswith("data: "):
        continue
    raw = line[6:].strip()
    if raw == "[DONE]":
        break
    chunk = json.loads(raw)
    delta = chunk.get("choices", [{}])[0].get("delta", {})
    full_content += delta.get("content", "")

match = re.search(r'!\[.*?\]\((.*?)\)', full_content, re.DOTALL)
image_src = match.group(1).strip()

if image_src.startswith("data:"):
    mime_type, b64_data = image_src.split(",", 1)
    image_bytes = __import__('base64').b64decode(b64_data)
    with open("output.png", "wb") as f:
        f.write(image_bytes)
```
