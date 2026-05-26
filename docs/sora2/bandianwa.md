# Sora2 — 斑点蛙渠道

## 基本信息

| 项目 | 值 |
|------|-----|
| 代码标识 | `sora2 / bandianwa` |
| 实现类 | `Sora2Bandianwa` |
| Base URL | `https://api.hellobabygo.com` |
| 配置键 | `bandianwa_api_key` |
| 文生视频 | ✅ `application/json` |
| 图生视频 | ✅ `multipart/form-data` |
| 继承自 | `Sora2Dayangyu`（大洋鱼渠道） |

> 斑点蛙渠道继承大洋鱼的完整接口实现，区别在于 Base URL 不同，以及图生视频额外支持 `seconds` 参数（从模型名自动推断）。

---

## 1. 创建任务

### 1a. 文生视频

```http
POST https://api.hellobabygo.com/v1/videos
Authorization: Bearer <bandianwa_api_key>
Content-Type: application/json
```

```json
{
  "prompt": "产品带货视频，竖屏，关转版",
  "model": "sora-2-portrait-10s-guanzhuan"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `prompt` | string | ✅ | 提示词 |
| `model` | string | ✅ | 见下方模型列表，斑点蛙模型带 `-guanzhuan` 后缀 |

### 1b. 图生视频

```http
POST https://api.hellobabygo.com/v1/videos
Authorization: Bearer <bandianwa_api_key>
Content-Type: multipart/form-data
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `input_reference` | file | ✅ | 参考图文件 |
| `prompt` | string | ✅ | 提示词 |
| `model` | string | ✅ | 模型名 |
| `n` | string | 否 | 生成数量，固定传 `"1"` |
| `seconds` | string | 否 | 时长（秒），从模型名自动推断，如 `"10"` |
| `size` | string | 否 | 尺寸，如 `1280x720` |

> `seconds` 字段由系统从模型名中自动解析：模型名含 `-10s-` 则传 `"10"`，以此类推。

---

## 2. 创建任务响应

```json
{
  "id": "task_bdw001",
  "status": "pending",
  "progress": 0,
  "created_at": "2025-01-01T00:00:00Z"
}
```

---

## 3. 查询任务状态

```http
GET https://api.hellobabygo.com/v1/videos/{task_id}
Authorization: Bearer <bandianwa_api_key>
Accept: application/json
```

### 响应（已完成）

```json
{
  "id": "task_bdw001",
  "status": "success",
  "progress": 100,
  "video_url": "https://cdn.hellobabygo.com/videos/output.mp4",
  "completed_at": "2025-01-01T00:06:00Z"
}
```

---

## 模型列表

| 方向 | 时长 | 模型名 |
|------|------|--------|
| 竖屏（portrait） | 5s | `sora-2-portrait-5s-guanzhuan` |
| 竖屏（portrait） | 10s | `sora-2-portrait-10s-guanzhuan` |
| 竖屏（portrait） | 15s | `sora-2-portrait-15s-guanzhuan` |
| 横屏（landscape） | 5s | `sora-2-landscape-5s-guanzhuan` |
| 横屏（landscape） | 10s | `sora-2-landscape-10s-guanzhuan` |
| 横屏（landscape） | 15s | `sora-2-landscape-15s-guanzhuan` |

> 模型名中的 `-guanzhuan` 为斑点蛙渠道特有后缀，代表「关转」（带货转化）版本。

---

## 错误处理

与大洋鱼渠道相同，见[大洋鱼文档 — 错误处理](./dayangyu.md#错误处理)。

---

## 完整调用示例（Python）

```python
import requests, time

API_KEY = "your_bandianwa_api_key"
BASE = "https://api.hellobabygo.com"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

# 1. 创建文生视频任务
resp = requests.post(
    f"{BASE}/v1/videos",
    headers=HEADERS,
    json={"prompt": "产品带货视频，竖屏", "model": "sora-2-portrait-10s-guanzhuan"},
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
