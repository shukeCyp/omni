# Sora2 视频生成总览

Sora2 是项目里的统一视频生成能力，支持文生视频和图生视频。和 NanoBanana 不同，Sora2 渠道基本都是异步任务模型，所以重点不在一次请求，而在“创建任务、轮询状态、下载结果”这条链路。

## 通用流程

```text
1. 创建任务   -> 获取 task_id
2. 轮询状态   -> 等待任务完成或失败
3. 下载视频   -> 使用 video_url 或二进制内容接口
```

大多数 provider 都符合这套模式，只是接口路径、字段名和状态值不完全一样。云雾是一个特殊分支，创建和查询路径与其他家不同，见 [yunwu.md](./yunwu.md)。

## 差异速览

| 渠道 | provider | 创建方式 | 图生视频上传 | 结果获取 |
|------|----------|----------|--------------|----------|
| 大洋鱼 | `dayangyu` | 标准任务接口 | `multipart/form-data` | `video_url`，且支持二进制内容接口 |
| 云雾 | `yunwu` | 自有任务接口 | 先上传图床，再传 `images[]` | `video_url` |
| 小搬手 | `xiaobanshou` | 与大洋鱼相近 | `multipart/form-data` | `video_url` |
| 斑点蛙 | `bandianwa` | 与大洋鱼相近 | `multipart/form-data` | `video_url` |

## 状态归一化

不同平台返回的状态词不统一，内部会按下面的语义归并：

| API 返回值 | 含义 | 内部枚举 |
|-----------|------|----------|
| `pending` / `queued` | 排队中 | `PENDING` |
| `processing` / `running` | 生成中 | `PROCESSING` |
| `success` / `succeeded` / `completed` / `done` | 已完成 | `COMPLETED` |
| `failed` / `error` / `cancelled` | 失败 | `FAILED` |

## 模型命名规则

| 渠道 | 文生视频模型 | 图生视频模型 |
|------|--------------|--------------|
| 大洋鱼 | `sora2-{orientation}` / `sora2-{orientation}-15s` | 同左 |
| 云雾 | `sora-2` | `sora-2-all` |
| 小搬手 | `sora-2-{orientation}-{duration}s` | 同左 |
| 斑点蛙 | `sora-2-{orientation}-{duration}s-guanzhuan` | 同左 |

公共参数：

| 参数 | 可选值 | 说明 |
|------|--------|------|
| `orientation` | `portrait` / `landscape` | 分别对应竖屏 `9:16` 和横屏 `16:9` |
| `duration` | `10` / `15` | 视频时长，部分渠道只支持固定档位 |

## 图生视频上传差异

| 渠道 | 上传方式 | 关键字段 |
|------|----------|----------|
| 大洋鱼 | `multipart/form-data` 直传 | `input_reference` |
| 云雾 | 先上传图床再引用 URL | `images[]` |
| 小搬手 | `multipart/form-data` 直传 | `input_reference` |
| 斑点蛙 | `multipart/form-data` 直传 | `input_reference` |

## 下载约定

任务完成后，通常直接拿到 `video_url` 并以 HTTP GET 流式下载。

需要额外注意：

- 大洋鱼还支持 `GET /v1/videos/{task_id}/content`，可直接拿视频二进制内容。
- 项目内的后台扫描器会持续扫描待处理任务，并在成功后写回本地路径与视频地址。

## 阅读建议

- 先看 [dayangyu.md](./dayangyu.md)，它最接近这套能力的基线协议。
- 如果你在修云雾，再单独看 [yunwu.md](./yunwu.md)，因为它的任务创建和图片上传方式差异最大。
- 如果你在修小搬手或斑点蛙，重点看它们相对大洋鱼有哪些字段级差异。
