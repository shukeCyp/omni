# Omni 带货设计规格

## 目标

在现有 Glin 桌面应用中新增独立的 `omni带货` 页面。用户上传 1 至 3 张参考图并填写视频提示词后，应用直接通过 Omni 视频渠道生成视频，不经过中间图片生成步骤。

当前仅接入斑点蛙（BDW）渠道。设计需要保留后续扩展其他 Omni 渠道的入口，同时不改变现有 `VEO带货`、`VEO视频` 或 `Sora2带货` 行为。

## 已确认范围

- 新增侧边栏标签：`omni带货`。
- 页面交互风格以现有 `VEO带货` 为基线，包括任务列表、添加任务、批量操作、视频预览、下载、删除和失败重试。
- 单条 Omni 任务必须包含 1 至 3 张参考图。
- Omni 视频直接使用参考图生成，不先生成场景图。
- 两张参考图仍按普通参考图提交，不自动解释为首图和尾图。
- 不支持无图文生视频。
- 设置页新增独立的 `Omni 视频渠道` 选择，目前唯一选项为 `BDW`。
- Omni/BDW 复用已经存在的 `bandianwa_api_key`，不新增重复密钥输入。

## 不在范围内

- Omni 的首尾图模式。
- Omni 的无图片文生视频模式。
- 新增 BDW 之外的 Omni 渠道实现。
- 修改现有 VEO 带货页面的生成流程或渠道行为。
- 中间图片生成、图片提示词、生成图预览和生成图下载。

## 页面与交互

### 页面入口

`frontend/src/App.vue` 增加 `omni_product` 导航项并挂载新的 `OmniProduct` 组件。导航文案显示为 `omni带货`。

### 页面主体

新页面复用 `VEO带货` 的整体视觉语言，但数据流简化为单阶段视频任务：

- 顶部工具栏包含刷新、任务统计、批量下载、全部删除与添加任务。
- 页面列表展示序号、参考图缩略图组、视频提示词、方向、时长、状态及操作。
- 操作包括重新生成视频、播放、下载、编辑参数和删除。
- 状态覆盖待处理、视频处理中、已完成和失败；不出现“图片生成中”或“生成图完成”状态。

### 添加任务

添加任务弹窗包含：

- 参考图上传区域，支持点击选择与拖拽，限定 1 至 3 张。
- 视频提示词，必填。
- 视频方向及 BDW 支持的时长参数。
- 创建数量与是否立即开始生成；行为与现有带货页一致，同一组参考图和参数可复制创建多条任务，开启自动生成后提交即进入视频队列。

前端在提交前校验图片数。超过 3 张时不创建任务，并提示 BDW Omni 仅支持最多 3 张参考图。

### 批量拖拽

页面级批量拖拽延续现有带货页面行为：每一张拖入图片形成一条独立的单参考图任务，适用于批量商品处理。需要把多张图片合并为同一任务时，用户使用“添加任务”弹窗。

## 设置与扩展边界

设置页在渠道区域增加 `Omni 视频渠道` 卡片：

- 保存键为 `omni_model`。
- 展示单选项 `BDW`（值为 `bandianwa`）和 `HOLO`（值为 `cloudy`）。
- 默认值为 `bandianwa`。
- API Keys 区继续使用现有 BDW 输入 `bandianwa_api_key`。
- HOLO 选项复用现有 `holo_veo_api_key` 与 `holo_veo_base_url`。

`omni_model` 与现有 `veo_model`、`sora2_model` 独立。未来接入新的 Omni 渠道时，仅需新增对应 provider、设置选项和必要的认证配置，而无需调整 Omni 页面业务流程。

## 后端结构

### 注册表

在媒体生成注册体系中新增视频平台 `omni`，并注册 provider：

- 平台标识：`omni`
- 平台显示名：`Omni`
- provider 标识：`bandianwa`
- provider 显示名：`BDW`
- 配置密钥：`bandianwa_api_key`
- provider 标识：`cloudy`
- provider 显示名：`HOLO`
- 配置密钥：`holo_veo_api_key`

解析 Omni 请求时，未显式指定 provider 则读取 `omni_model`，默认回退 `bandianwa`。现有 `veo3/bandianwa` 与 `veo3/holo` 注册项维持原行为，不承担 Omni 多图语义。

### 请求数据流

`OmniProduct` 将每条任务的参考图数组、提示词、方向、时长和 `platform='omni'` 传入现有统一视频生成 API。后端 Omni generator 将参考图数组完整交给对应服务实现，不使用当前只落盘第一张图的 VEO 通用路径。

### BDW 接口映射

根据 BDW NEWAPI 文档，Omni/BDW 的创建请求规则如下：

- 接口：`POST /v1/videos`
- 认证：`Authorization: Bearer <bandianwa_api_key>`
- 请求编码：`multipart/form-data`
- 参考图字段：重复的 `input_reference[]` 文件字段，共 1 至 3 个。
- 表单字段包含 `model`、`prompt`、尺寸/时长参数。

### HOLO 接口映射

根据 HOLO 文档，Omni/HOLO 使用 Cloudy/HOLO 的 Omni Flash Components 协议：

- 接口：`POST /v1/generate`
- 查询：`GET /v1/tasks/{task_id}`
- 认证：`Authorization: Bearer <holo_veo_api_key>`
- 请求编码：`application/json`
- 模型：`omni_flash_components_{duration}s`
- 横竖屏：`aspect_ratio`，竖屏为 `9:16`，横屏为 `16:9`
- 参考图字段：`messages[0].content` 中的 1 至 3 个 `image_url`，最后追加 text prompt。
- 模型使用普通多参考图模式，不选择 `-fl` 首尾图模型。

任务状态查询使用 `GET /v1/videos/{task_id}`；成功后使用响应中的视频地址，下载逻辑延续现有视频文件下载能力。

### 错误处理

- 页面提交时拦截零张图片或超过三张图片。
- 后端 generator 再次验证参考图数量，防止绕过 UI 的非法请求。
- API Key 未配置时返回指向设置页的明确错误。
- 创建任务、任务失败和轮询超时沿用统一 `VideoGenerationResult` 失败返回，并在任务状态中显示可读消息。

## 测试与验证

后端新增聚焦测试：

- Omni/BDW 使用 `multipart/form-data` 提交重复的 `input_reference[]`。
- 1 张和 3 张参考图能够进入提交路径。
- 0 张及超过 3 张参考图被拒绝，不发起上游请求。
- Omni 注册表可从 `omni_model=bandianwa` 解析渠道，并复用 `bandianwa_api_key`。
- 状态轮询和完成视频 URL 提取遵循 BDW NEWAPI 响应约定。

前端使用构建验证新组件、导航项和设置表单均能编译。后端运行新增测试及现有测试集，确保 VEO 与 Sora2 现有 provider 未被回归影响。

## 文档

新增 Omni 渠道文档与索引，说明：

- Omni 当前仅支持 BDW。
- Omni 带货仅采用 1 至 3 张参考图直接生成视频。
- 它与现有 `veo3/bandianwa` 的职责边界不同：Omni 明确支持多参考图，且不使用首尾图模式。

## 接口资料来源

- 参数说明：https://xxp0w23uvv.apifox.cn/folder-83486592
- 无图片提交（明确不在当前页面范围）：https://xxp0w23uvv.apifox.cn/api-445857183
- 参考图提交：https://xxp0w23uvv.apifox.cn/api-445857184
- 首尾图提交（明确不在当前页面范围）：https://xxp0w23uvv.apifox.cn/api-445857185
- 任务查询：https://xxp0w23uvv.apifox.cn/api-445857186
- 视频内容：https://xxp0w23uvv.apifox.cn/api-445857182
