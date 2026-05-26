# Frontend

这里不是通用的 Vue 模板，而是 Glin 桌面应用的前端部分。它运行在 `pywebview` 容器里，负责页面导航、参数输入、任务展示、设置管理，以及通过 `window.pywebview.api` 调用 Python 后端。

## 技术栈

- Vue 3
- Vite
- 原生 CSS
- pywebview JS Bridge

## 常用命令

```bash
npm install
npm run dev
npm run build
npm run preview
```

脚本说明：

- `npm run dev`：启动 Vite 开发服务器，只适合纯前端样式和交互调试。
- `npm run build`：构建到项目根目录的 `../static`，供桌面壳直接加载。
- `npm run preview`：本地预览构建产物。

## 目录重点

```text
frontend/
├── src/
│   ├── App.vue           应用壳层、激活态切换、侧边栏导航
│   ├── main.js           Vue 启动入口
│   ├── style.css         全局样式和主题变量
│   └── components/       各业务页面与通用组件
├── index.html
└── vite.config.js
```

当前主要页面组件包括：

- `NanoBanana.vue`
- `GlinVeo.vue`
- `Sora2Generation.vue`
- `VeoGeneration.vue`
- `VideoProduct.vue`
- `VeoProduct.vue`
- `VeoQihao.vue`
- `Settings.vue`
- `Debug.vue`

## 和后端的协作方式

前端不直接请求第三方渠道，统一通过 pywebview 暴露的 API 调用 Python：

```js
await window.pywebview.api.get_all_settings()
await window.pywebview.api.generate_image(payload)
await window.pywebview.api.generate_video(payload)
```

这意味着你改前端时要注意两件事：

- JS 方法名和参数结构必须与 `app/api.py` 保持一致。
- 仅运行 `npm run dev` 时，很多依赖 pywebview 的功能并不会完整工作。

## 构建约定

[`vite.config.js`](/Users/chaiyapeng/Documents/Glin/frontend/vite.config.js) 已配置：

- `base: './'`，保证静态资源能被本地文件协议正确加载。
- `outDir: '../static'`，构建结果直接覆盖桌面应用使用的资源目录。

如果你改了前端代码，但桌面应用里看不到变化，先确认是否重新执行过：

```bash
npm run build
```

## 开发建议

- 改导航和页面入口时，先看 [`src/App.vue`](/Users/chaiyapeng/Documents/Glin/frontend/src/App.vue)。
- 改设置项时，同时核对前端字段名、`window.pywebview.api` 调用和后端 `Settings` key。
- 改调试页面时，记得它只在 `GLIN_DEV_UI=1` 时显示。
