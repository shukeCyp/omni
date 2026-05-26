# 斑点蛙 VEO3 视频生成

## 基本信息

| 项目 | 值 |
|------|------|
| 渠道标识 | `bandianwa` |
| 显示名称 | BDW |
| Base URL | `https://api.hellobabygo.com` |
| 配置键 | `bandianwa_api_key` |
| 类名 | `VeoBandianwa` |

## 接口说明

斑点蛙 VEO3 使用**异步任务型**接口，需要三次调用：

1. **提交任务**：`POST /v1/videos`
2. **查询状态**：`GET /v1/videos/{task_id}`
3. **获取视频**：`GET /v1/videos/{task_id}/content`（可选，如果查询接口已返回 URL）

## 认证方式

```http
Authorization: Bearer {api_key}
Content-Type: application/json
```

## 提交任务

### 请求

```http
POST /v1/videos
```

**请求体：**

```json
{
  "model": "veo_3_1-fast-portrait",
  "prompt": "一只可爱的猫咪在草地上玩耍",
  "seconds": "10",
  "input_reference": "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
}
```

**字段说明：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `model` | string | 是 | 模型名称（见下方模型列表） |
| `prompt` | string | 是 | 视频描述提示词 |
| `seconds` | string | 否 | 视频时长（秒），如 `"5"` / `"8"` / `"10"` |
| `input_reference` | string | 否 | 参考图 data URL，传入后触发图生视频模式 |

**支持的模型：**

### 文生视频

| 方向 | 模型名称 |
|------|----------|
| 竖屏 (portrait) | `veo_3_1-fast-portrait` |
| 横屏 (landscape) | `veo_3_1-fast-landscape` |

### 图生视频（首尾帧模式）

| 方向 | 模型名称 |
|------|----------|
| 竖屏 (portrait) | `veo_3_1-fast-portrait-fl-hd` |
| 横屏 (landscape) | `veo_3_1-fast-landscape-fl-hd` |

**模型命名规则：**

- `-hd` 后缀用于首尾帧模型
- `-fl` 后缀表示首尾帧模式（图生视频）
- `portrait` / `landscape` 表示竖屏/横屏

### 响应

```json
{
  "task_id": "task_xxxxxxxx"
}
```

## 查询任务状态

### 请求

```http
GET /v1/videos/{task_id}
```

### 响应

**处理中：**

```json
{
  "status": "queued",
  "progress": 20
}
```

**已完成：**

```json
{
  "status": "completed",
  "data": [
    {
      "url": "https://example.com/video.mp4"
    }
  ]
}
```

**失败：**

```json
{
  "status": "failed",
  "error": {
    "code": "task_failed",
    "message": "错误信息"
  }
}
```

**状态值说明：**

| 状态 | 说明 |
|------|------|
| `queued` | 排队中 |
| `in_progress` | 处理中 |
| `completed` | 已完成 |
| `failed` | 失败 |

## 获取视频内容

### 请求

```http
GET /v1/videos/{task_id}/content
```

### 响应

直接返回视频二进制数据（仅任务 completed 后可用）。

## 轮询策略

- **轮询间隔**：35 秒
- **总超时时间**：10 分钟（600 秒）
- **建议**：客户端总超时设置为 5-10 分钟

## 代码实现位置

- 服务类：`app/services/veo/bandianwa.py`
- 注册器：`app/services/media_generation.py` 中的 `BandianwaVeoGenerator`

## 注意事项

1. **异步任务模式**：需要先提交任务，再轮询状态，最后获取视频。
2. **模型选择**：
   - 文生视频固定使用 `veo_3_1-fast-*`
   - 首尾帧固定使用 `veo_3_1-fast-*-fl-hd`
3. **图生视频支持**：
   - 支持单张参考图
   - `input_reference` 参数需要是 data URL 格式（`data:image/jpeg;base64,...`）
   - 使用 `-fl` 后缀的模型（首尾帧模式）
4. **视频时长**：通过 `seconds` 参数控制，支持 5/8/10 秒等。
5. **错误处理**：任务失败时会返回 `failed` 状态和错误信息，需妥善处理。
6. **视频下载**：获取到的视频 URL 会自动下载并保存到本地。
