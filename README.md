# 荷塘 Omni
 
基于 `pywebview + Vue 3` 的桌面应用，只接入 HOLO Omni 视频生成。

## 功能

左侧抽屉提供两个入口：

| 入口 | 输入 | 上游模型 |
|------|------|----------|
| 文生视频 | 提示词 | `omni_flash_*` |
| 多参考视频 | 1 至 3 张参考图 + 提示词 | `omni_flash_components_*` |

Base URL 固定为：

```text
https://gpt.lyvideo.top
```

设置页只需要填写 HOLO API Key、下载路径、重试和并发配置。

## 运行

```bash
cd frontend
npm install
npm run build
cd ..
source .venv/bin/activate
python main.py
```

也可以使用：

```bash
./run.sh
```

## 关键文件

| 文件 | 作用 |
|------|------|
| `frontend/src/App.vue` | 左侧抽屉入口 |
| `frontend/src/components/OmniProduct.vue` | 三类 Omni 任务页面 |
| `frontend/src/components/Settings.vue` | HOLO API Key 与本地配置 |
| `app/services/omni/cloudy.py` | HOLO Omni 请求、轮询与下载 |
| `docs/omni/cloudy.md` | 接口字段映射 |
