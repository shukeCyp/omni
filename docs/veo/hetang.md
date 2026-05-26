# VEO3 — 荷塘渠道

## 基本信息

| 项目 | 值 |
|------|-----|
| 代码标识 | `veo3 / hetang` |
| 实现类 | `VeoHetang` / `HetangVeo3Generator` |
| Base URL | **用户在设置页面自定义**（无默认值） |
| 接口风格 | OpenAI 兼容 Chat Completions SSE 流式 |
| 配置键 | `hetang_veo_api_key` + `hetang_veo_base_url` |
| 文生视频 | ✅ |
| 图生视频 | ✅（base64 内嵌，支持多张） |
| 超时 | 600 秒 |
| 与 NanoBanana 共用 | ✅（同一套 Base URL 和 API Key） |

> **荷塘 VEO3 视频和 NanoBanana 图片生成共用同一套 Base URL 和 API Key，在设置页面统一配置。**

---

## 接口

```http
POST {hetang_veo_base_url}/v1/chat/completions
Authorization: Bearer <hetang_veo_api_key>
Content-Type: application/json
```

---

## 请求体

### 文生视频

```json
{
  "model": "veo_3_1_t2v_fast_portrait",
  "messages": [
    {
      "role": "user",
      "content": "一个女孩在樱花树下漫步，慢镜头，电影感"
    }
  ],
  "stream": true
}
```

### 图生视频

```json
{
  "model": "veo_3_1_i2v_s_fast_portrait_fl",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "产品展示视频，竖屏，自然光线"
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
| `model` | string | ✅ | 见下方模型列表 |
| `messages[0].content` | string \| array | ✅ | 文生视频传字符串；图生视频传含 `text` + 一或多个 `image_url` 的数组 |
| `stream` | bool | ✅ | 固定 `true` |

---

## 模型列表

| 模式 | 方向 | 模型名 |
|------|------|--------|
| 文生视频 | 竖屏（portrait） | `veo_3_1_t2v_fast_portrait` |
| 文生视频 | 横屏（landscape） | `veo_3_1_t2v_fast_landscape` |
| 图生视频 | 竖屏（portrait） | `veo_3_1_i2v_s_fast_portrait_fl` |
| 图生视频 | 横屏（landscape） | `veo_3_1_i2v_s_fast_fl` |

---

## 响应格式（SSE 流式）

响应为 Server-Sent Events 流，每行格式：

```
data: {"choices":[{"delta":{"content":"...","reasoning_content":"..."}}]}
data: [DONE]
```

- 每行以 `data: ` 开头，跳过空行
- `[DONE]` 表示流结束
- `delta.content` 中含视频链接（`<video src='...'>`）
- `delta.reasoning_content` 含模型思考过程，失败时包含 `❌` 或 `失败` 关键词

### 视频链接提取规则

```python
import re

for line in response.iter_lines(decode_unicode=True):
    if not line or not line.startswith("data: "):
        continue
    raw = line[6:].strip()
    if raw == "[DONE]":
        break
    data = json.loads(raw)
    content = data["choices"][0]["delta"].get("content", "")
    if content:
        match = re.search(r"<video\s+src='([^']+)'", content)
        if match:
            video_url = match.group(1)  # 提取到视频 URL

    # 检测失败信号
    reasoning = data["choices"][0]["delta"].get("reasoning_content", "")
    if reasoning and ("❌" in reasoning or "失败" in reasoning):
        error_message = reasoning.strip()
```

---

## 错误处理

| 场景 | 处理方式 |
|------|----------|
| Base URL 或 API Key 未配置 | 返回错误："未配置荷塘 Base URL 或 API Key" |
| SSE 流结束后无视频链接 | 返回错误："未获取到视频链接"，并附上 reasoning_content 中的错误信息 |
| 请求超时（600s） | 返回错误："请求超时（600秒）" |
| HTTP 错误 | 直接抛出异常，日志记录详情 |

---

## 完整调用示例（Python）

```python
import requests, json, re

API_KEY = "your_hetang_api_key"
BASE_URL = "https://your-custom-base-url.com"

url = f"{BASE_URL}/v1/chat/completions"
headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

# 文生视频
payload = {
    "model": "veo_3_1_t2v_fast_portrait",
    "messages": [{"role": "user", "content": "产品展示视频，竖屏，自然光线"}],
    "stream": True,
}

resp = requests.post(url, headers=headers, json=payload, stream=True, timeout=600)
resp.raise_for_status()

video_url = ""
error_message = ""
for line in resp.iter_lines(decode_unicode=True):
    if not line or not line.startswith("data: "):
        continue
    raw = line[6:].strip()
    if raw == "[DONE]":
        break
    data = json.loads(raw)
    choices = data.get("choices", [])
    if not choices:
        continue
    delta = choices[0].get("delta", {})
    content = delta.get("content", "")
    if content:
        match = re.search(r"<video\s+src='([^']+)'", content)
        if match:
            video_url = match.group(1)
    reasoning = delta.get("reasoning_content", "")
    if reasoning and ("❌" in reasoning or "失败" in reasoning):
        error_message = reasoning.strip()

if not video_url:
    raise RuntimeError(error_message or "未获取到视频链接")

print(f"视频链接：{video_url}")

# 下载视频
with requests.get(video_url, stream=True, timeout=120) as vr:
    with open("output.mp4", "wb") as f:
        for chunk in vr.iter_content(8192):
            f.write(chunk)
```
