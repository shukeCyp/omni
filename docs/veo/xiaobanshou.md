# 小扳手 VEO3 视频生成

## 基本信息

| 项目 | 值 |
|------|------|
| 代码标识 | `veo3 / xiaobanshou` |
| 渠道标识 | `xiaobanshou` |
| 显示名称 | XBS |
| Base URL | `https://xibapi.com` |
| 配置键 | `xiaobanshou_api_key` |
| 类名 | `VeoXiaobanshou` |

## 接口说明

小扳手 VEO3 使用异步任务接口：

1. `POST /v1/videos` 提交任务
2. `GET /v1/videos/{task_id}` 查询状态

## 认证方式

```http
Authorization: Bearer {api_key}
```

## 提交任务

### 请求

```http
POST /v1/videos
Content-Type: multipart/form-data
```

### 表单字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `model` | string | 是 | 文生视频使用 `veo_3_1-fast`；首尾帧模式使用 `veo_3_1-fast-fl` |
| `prompt` | string | 是 | 视频提示词 |
| `size` | string | 是 | 视频尺寸，格式 `widthxheight` |
| `input_reference[]` | repeatable | 否 | 参考图字段，字段名必须带 `[]` |

### 当前实现约定

- 文生视频：`model=veo_3_1-fast`
- 图生视频：当前 Glin VEO 流程仅上传 1 张参考图，因此映射为首尾帧模式 `veo_3_1-fast-fl`
- 竖屏默认尺寸：`720x1280`
- 横屏默认尺寸：`1280x720`

## 查询任务

### 请求

```http
GET /v1/videos/{task_id}
```

### 完成响应

```json
{
  "id": "task_xxxxxxxxxxxxx",
  "object": "video",
  "model": "veo_3_1-fast",
  "status": "completed",
  "progress": 100,
  "created_at": 1709876543,
  "completed_at": 1709876600,
  "url": "https://example.com/videos/xxx.mp4"
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `status` | string | `queued` / `processing` / `completed` / `failed` |
| `url` | string | 完成后返回的视频下载地址 |
| `error` | string | 失败时的错误信息 |

## 代码实现位置

- 服务类：`app/services/veo/xiaobanshou.py`
- 注册器：`app/services/media_generation.py` 中的 `XiaobanshouVeoGenerator`

## 注意事项

1. 创建任务必须使用 `multipart/form-data`，不要提交 JSON。
2. 参考图字段名必须是 `input_reference[]`。
3. 当前统一视频入口只会传 1 张参考图，因此暂未暴露 2 张首尾帧或 3 张参考图的多图能力。
