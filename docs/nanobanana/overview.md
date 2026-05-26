# NanoBanana 图片生成总览

NanoBanana 是项目里的统一图片生成能力，支持文生图和图生图。不同 provider 代理的是相近的底层模型，但上游接口形态并不一致，所以代码层面做了统一封装。

## 差异速览

| 渠道 | provider | 接口风格 | 返回方式 | 适合关注什么 |
|------|----------|----------|----------|--------------|
| 云雾 | `yunwu` | fal-ai 队列接口 | 任务完成后拉取结果 | 任务创建、状态查询、结果下载 |
| 荷塘 | `hetang` | OpenAI 兼容 SSE | 流式返回 Markdown 图片 | 模型名拼接、SSE 内容解析 |
| 小搬手 | `xiaobanshou` | OpenAI 兼容 SSE | 流式返回 Markdown 图片 | 模型名拼接、SSE 内容解析 |

## 公共输入

调用方通常会传入这些字段：

| 字段 | 说明 |
|------|------|
| `prompt` | 图片生成提示词 |
| `aspect_ratio` | 宽高比，如 `9:16`、`16:9`、`1:1` |
| `image_size` | 清晰度档位，如 `1K`、`2K`、`4K` |
| `ref_images` | 参考图列表，用于图生图 |

具体字段名和上传细节可能随渠道变化，但语义保持一致。

## OpenAI 兼容渠道的模型命名

荷塘和小搬手使用统一的模型拼装规则：

```text
gemini-3.0-pro-image-{orientation}{size_suffix}
```

| 参数 | 可选值 | 来源 |
|------|--------|------|
| `orientation` | `portrait` / `landscape` / `square` / `four-three` / `three-four` | 由 `aspect_ratio` 映射 |
| `size_suffix` | `""` / `-2k` / `-4k` | 由 `image_size` 映射 |

宽高比映射：

| `aspect_ratio` | `orientation` |
|----------------|---------------|
| `9:16` | `portrait` |
| `16:9` | `landscape` |
| `1:1` | `square` |
| `4:3` | `four-three` |
| `3:4` | `three-four` |

清晰度映射：

| `image_size` | `size_suffix` | 示例模型 |
|--------------|---------------|----------|
| `1K` | `""` | `gemini-3.0-pro-image-portrait` |
| `2K` | `-2k` | `gemini-3.0-pro-image-portrait-2k` |
| `4K` | `-4k` | `gemini-3.0-pro-image-portrait-4k` |

## 认证

所有渠道都使用 Bearer Token：

```http
Authorization: Bearer <API_KEY>
Content-Type: application/json
```

## 返回归一化约定

无论上游返回什么风格，业务层最终都按统一语义处理：

- 成功时返回图片数据或可下载的图片地址。
- SSE 渠道通常会把图片以 Markdown 形式嵌在 `content` 里，例如 `![](data:image/png;base64,...)`。
- 队列型渠道可能返回 URL，需要在完成后再拉取资源。
- 失败时统一落到 `success: false`，并通过 `error_message` 暴露原因。

## 阅读建议

- 如果你在修云雾渠道，直接看 [yunwu.md](./yunwu.md)。
- 如果你在修荷塘或小搬手，优先关注模型名拼接和 SSE 解析逻辑，见 [hetang.md](./hetang.md) 和 [xiaobanshou.md](./xiaobanshou.md)。
