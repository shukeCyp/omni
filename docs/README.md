# 荷塘 Omni 文档

这个项目只接入 HOLO Omni，不包含其他渠道选择。

## 当前能力

| 左侧入口 | 上游模型 | 输入 |
|----------|----------|------|
| 文生视频 | `omni_flash_*` | 提示词 |
| 多参考视频 | `omni_flash_components_*` | 1 至 3 张参考图 + 提示词 |

## 固定配置

| 项目 | 值 |
|------|----|
| provider | `omni/cloudy` |
| Base URL | `https://gpt.lyvideo.top` |
| API Key 设置键 | `holo_veo_api_key` |
| 创建接口 | `POST /v1/generate` |
| 查询接口 | `GET /v1/tasks/{task_id}` |

详细协议见 [omni/cloudy.md](./omni/cloudy.md)。
