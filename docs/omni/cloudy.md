# Omni - HOLO 渠道

## 基本信息

| 项目 | 值 |
|------|----|
| 代码标识 | `omni / cloudy` |
| 显示名称 | `HOLO` |
| Base URL | `https://gpt.lyvideo.top`（固定，不开放配置） |
| 配置键 | `omni_model=cloudy` + `holo_veo_api_key` |
| 创建接口 | `POST /v1/generate` |
| 查询接口 | `GET /v1/tasks/{task_id}` |
| 模型 | `omni_flash_*` |

## 页面范围

左侧抽屉提供两个 Omni 入口，全部固定使用 HOLO：

- 文生视频：`omni_flash_{duration}s{resolution_suffix}`，无需图片。
- 多参考视频：`omni_flash_components_{duration}s{resolution_suffix}`，包含 1 至 3 张参考图。
- 横竖屏通过 `aspect_ratio` 控制，不写入模型名。
- 时长支持 4、6、8、10 秒；分辨率支持 720P（无后缀）、1080P（`_1080p`）和 4K（`_4k`）。

## 创建任务

```http
POST /v1/generate
Authorization: Bearer <holo_veo_api_key>
Content-Type: application/json
```

多参考视频竖屏示例：

```json
{
  "model": "omni_flash_components_10s",
  "aspect_ratio": "9:16",
  "messages": [
    {
      "role": "user",
      "content": [
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}},
        {"type": "text", "text": "展示产品卖点，镜头缓慢推进"}
      ]
    }
  ]
}
```

字段映射：

| 应用参数 | Cloudy 字段 |
|----------|-------------|
| `orientation=portrait` | `aspect_ratio="9:16"` |
| `orientation=landscape` | `aspect_ratio="16:9"` |
| `duration=10` | `model="omni_flash_components_10s"` |
| `resolution=1080P` | 模型名追加 `_1080p` |
| `resolution=4K` | 模型名追加 `_4k` |
| 参考图数组 | 多个 `messages[0].content[].image_url.url` |
| 视频提示词 | `messages[0].content[-1].text` |

## 查询与下载

任务创建后使用 `GET /v1/tasks/{task_id}` 轮询。完成后优先读取 `result.url` 或 `result.video_url`；如果响应只返回 `result.file_url`，则拼接 Base URL 得到下载地址。

下载文件时继续携带 `Authorization: Bearer <holo_veo_api_key>`。

## 参考文档

- HOLO API 文档：https://api.dealonhorizon.us/docs
