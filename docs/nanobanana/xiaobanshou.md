# NanoBanana — 小搬手渠道

## 基本信息

| 项目 | 值 |
|------|-----|
| 代码标识 | `nanobanana / xiaobanshou` |
| 实现类 | `NanoBananaXiaobanshou` |
| Base URL | `https://api.xintianwengai.com` |
| 接口风格 | OpenAI 兼容 Chat Completions SSE 流式 |
| 配置键 | `xiaobanshou_api_key` |
| 图生图支持 | ✅（多张，base64 内嵌） |
| 最大参考图数 | 不限 |

---

## 接口

```http
POST https://api.xintianwengai.com/v1/chat/completions
Authorization: Bearer <xiaobanshou_api_key>
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
      "content": "一双白色运动鞋放在木质桌面上"
    }
  ],
  "stream": true
}
```

### 图生图（多张参考图）

```json
{
  "model": "gemini-3.0-pro-image-portrait",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "根据参考图生成产品展示图"
        },
        {
          "type": "image_url",
          "image_url": {
            "url": "data:image/jpeg;base64,/9j/4AAQ..."
          }
        },
        {
          "type": "image_url",
          "image_url": {
            "url": "data:image/png;base64,iVBOR..."
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
| `model` | string | ✅ | 模型名，见[总览](./overview.md) |
| `messages[0].content` | string \| array | ✅ | 文生图传字符串；图生图传数组，每张图一个 `image_url` 对象 |
| `stream` | bool | ✅ | 固定 `true` |

---

## 响应格式（SSE 流式）

与荷塘渠道相同，见[荷塘渠道 — 响应格式](./hetang.md#响应格式sse-流式)。

拼接所有 `delta.content` 后，从 `![]()` Markdown 中提取图片 base64 或 URL。

---

## 模型列表

| 宽高比 | 清晰度 | 模型名 |
|--------|--------|--------|
| 9:16（竖屏） | 1K | `gemini-3.0-pro-image-portrait` |
| 9:16（竖屏） | 2K | `gemini-3.0-pro-image-portrait-2k` |
| 9:16（竖屏） | 4K | `gemini-3.0-pro-image-portrait-4k` |
| 16:9（横屏） | 1K | `gemini-3.0-pro-image-landscape` |
| 16:9（横屏） | 2K | `gemini-3.0-pro-image-landscape-2k` |
| 1:1（方形） | 1K | `gemini-3.0-pro-image-square` |
| 4:3 | 1K | `gemini-3.0-pro-image-four-three` |
| 3:4 | 1K | `gemini-3.0-pro-image-three-four` |

---

## 错误处理

| 场景 | 处理方式 |
|------|----------|
| API Key 未配置 | 返回错误："未配置 XBS API Key" |
| SSE 流中无 content | 返回错误："SSE 流中未收到 content 数据" |
| 响应中无图片标记 | 返回错误："未能从响应中提取图片" |
| HTTP 错误 | 解析 `error.message` 字段 |
| 请求超时（300s） | 返回错误："请求超时" |

---

## 完整调用示例（Python）

```python
import requests, re, json, base64

API_KEY = "your_xiaobanshou_api_key"
BASE_URL = "https://api.xintianwengai.com"

url = f"{BASE_URL}/v1/chat/completions"
headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

payload = {
    "model": "gemini-3.0-pro-image-portrait",
    "messages": [{"role": "user", "content": "产品展示图，纯白背景"}],
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
    _, b64_data = image_src.split(",", 1)
    image_bytes = base64.b64decode(b64_data)
    with open("output.png", "wb") as f:
        f.write(image_bytes)
```
