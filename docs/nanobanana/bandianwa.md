# 斑点蛙 NanoBanana 图片生成

## 基本信息

| 项目 | 值 |
|------|------|
| 渠道标识 | `bandianwa` |
| 显示名称 | BDW |
| Base URL | `https://api.hellobabygo.com` |
| 配置键 | `bandianwa_api_key` |
| 类名 | `NanoBananaBandianwa` |

## 接口说明

斑点蛙 NanoBanana 使用**异步任务型**接口，需要三次调用：

1. **提交任务**：`POST /v1/images/generations?async=true`
2. **查询状态**：`GET /v1/images/{task_id}`
3. **获取图片**：`GET /v1/images/{task_id}/content`（可选，如果查询接口已返回 URL）

### ⚠️ 重要注意事项

- **所有参数必须为顶层平级结构**，禁止使用 `metadata` 嵌套
- `response_format` 建议固定传 `"url"`
- 图生图时，`image` 参数为 **data URL 字符串**（`data:image/jpeg;base64,...`）

## 认证方式

```http
Authorization: Bearer {api_key}
Content-Type: application/json
```

## 提交任务

### 请求

```http
POST /v1/images/generations?async=true
```

**请求体：**

```json
{
  "model": "nano_banana_pro-2K-landscape",
  "prompt": "一张美丽的风景图片",
  "response_format": "url",
  "aspectRatio": "16:9",
  "size": "2K",
  "image": "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
}
```

**字段说明：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `model` | string | 是 | 模型名称，格式为 `{基础模型}-{清晰度}-{方向}` |
| `prompt` | string | 是 | 图片描述提示词 |
| `response_format` | string | 建议 | 响应格式，固定传 `"url"` |
| `aspectRatio` | string | 否 | 图片宽高比（如 `"16:9"`） |
| `size` | string | 否 | 图片尺寸档位（如 `"2K"`） |
| `image` | string | 否 | 参考图 data URL，传入后触发图生图模式（只取第一张） |

**支持的模型：**

| 清晰度 | 方向 | 模型名称 |
|--------|------|----------|
| 1K | 横图 (landscape) | `nano_banana_pro-1K-landscape` |
| 1K | 竖图 (portrait) | `nano_banana_pro-1K-portrait` |
| 1K | 方图 (square) | `nano_banana_pro-1K-square` |
| 2K | 横图 (landscape) | `nano_banana_pro-2K-landscape` |
| 2K | 竖图 (portrait) | `nano_banana_pro-2K-portrait` |
| 2K | 方图 (square) | `nano_banana_pro-2K-square` |
| 4K | 横图 (landscape) | `nano_banana_pro-4K-landscape` |
| 4K | 竖图 (portrait) | `nano_banana_pro-4K-portrait` |
| 4K | 方图 (square) | `nano_banana_pro-4K-square` |

**方向与宽高比映射：**

| 宽高比 | 方向 |
|--------|------|
| 16:9, 4:3 | landscape |
| 9:16, 3:4 | portrait |
| 1:1 | square |

### 响应

```json
{
  "task_id": "task_xxxxxxxx"
}
```

## 查询任务状态

### 请求

```http
GET /v1/images/{task_id}
```

### 响应

**处理中：**

```json
{
  "status": "in_progress"
}
```

**已完成：**

```json
{
  "status": "completed",
  "data": [
    {
      "url": "https://example.com/image.jpg"
    }
  ]
}
```

**失败：**

```json
{
  "status": "failed",
  "error": "错误信息"
}
```

**状态值说明：**

| 状态 | 说明 |
|------|------|
| `queued` | 排队中 |
| `in_progress` | 处理中 |
| `completed` | 已完成 |
| `failed` | 失败 |
| `error` | 错误 |
| `cancelled` | 已取消 |

## 获取图片内容

### 请求

```http
GET /v1/images/{task_id}/content
```

### 响应

直接返回图片二进制数据，Content-Type 为图片 MIME 类型。

## 轮询策略

- **轮询间隔**：15 秒
- **总超时时间**：5 分钟（300 秒）
- **建议**：客户端总超时设置为 5-10 分钟

## 代码实现位置

- 服务类：`app/services/nanobanana/bandianwa.py`
- 注册器：`app/services/media_generation.py` 中的 `NanoBananaBandianwaGenerator`

## 注意事项

1. **异步任务模式**：与云雾的同步返回不同，斑点蛙需要先提交任务，再轮询状态，最后获取图片。
2. **参数平级结构**：所有请求参数必须平级放置，禁止使用 `metadata` 嵌套。
3. **模型选择**：根据用户选择的清晰度（1K/2K/4K）和宽高比自动映射到完整模型名称。
4. **图生图支持**：
   - 只支持单张参考图（取 `ref_images` 的第一张）
   - `image` 参数需要是 data URL 格式（`data:image/jpeg;base64,...`）
5. **响应格式**：
   - 提交时建议传 `response_format: "url"`
   - 完成时图片 URL 在 `data[0].url`
   - 代码会自动下载 URL 图片并转为 base64
6. **错误处理**：任务失败时会返回 `failed` 状态和错误信息，需妥善处理。
7. **图片下载**：获取到的图片 URL 会自动下载并转为 base64 后保存。
