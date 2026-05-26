# Omni 带货 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增仅通过 1 至 3 张参考图直接生成视频的 `omni带货` 页面，并接入 BDW Omni 视频渠道。

**Architecture:** 在现有统一媒体 API 上增加独立 `omni/bandianwa` 视频平台注册和服务实现，使多参考图协议不会改变已有 `veo3/bandianwa` 的单图/首尾图行为。前端新增单阶段视频任务组件，沿用 VEO 带货的页面语言，但只管理参考图和视频结果；设置通过独立 `omni_model` 保存未来可扩展的渠道选择。

**Tech Stack:** Python 3、`requests`、`unittest`、Vue 3 `<script setup>`、Vite、pywebview Settings bridge

---

## File Map

- Create: `app/services/omni/__init__.py` - 导出 Omni 服务实现。
- Create: `app/services/omni/bandianwa.py` - 将 1 至 3 张本地参考图转为 BDW NEWAPI multipart 视频任务，并轮询结果。
- Create: `tests/test_bandianwa_omni.py` - 覆盖多图 multipart、数量校验、轮询结果和注册表解析。
- Modify: `app/constants.py` - 声明 `OMNI_MODEL` 设置键。
- Modify: `app/services/media_generation.py` - 新增 Omni generator，保存多张临时图片并注册 `omni/bandianwa`。
- Create: `frontend/src/components/OmniProduct.vue` - 单阶段参考图直出视频页面。
- Modify: `frontend/src/App.vue` - 添加 `omni带货` 导航和页面实例。
- Modify: `frontend/src/components/Settings.vue` - 添加独立 Omni 渠道设置，并读写 `omni_model`。
- Create: `docs/omni/bandianwa.md` - 记录 Omni/BDW 的多参考图协议和范围。
- Modify: `docs/README.md` - 索引 Omni 能力、provider 与配置。
- Modify: `README.md` - 展示新增业务入口和支持渠道。

### Task 1: Lock The BDW Omni Protocol With Failing Tests

**Files:**
- Create: `tests/test_bandianwa_omni.py`

- [ ] **Step 1: Write tests for multipart reference uploads and image-count validation**

```python
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from app.services.omni.bandianwa import OmniBandianwa


class OmniBandianwaTests(unittest.TestCase):
    def setUp(self):
        self.service = OmniBandianwa("test-key")

    @patch("app.services.omni.bandianwa.OmniBandianwa._poll_task")
    @patch("app.services.omni.bandianwa.requests.post")
    def test_generate_submits_three_reference_images_as_repeated_file_fields(self, mock_post, mock_poll):
        response = MagicMock()
        response.json.return_value = {"task_id": "task_123"}
        response.text = '{"task_id":"task_123"}'
        response.status_code = 200
        response.raise_for_status.return_value = None
        mock_post.return_value = response
        mock_poll.return_value = MagicMock(success=False, error_message="stop")
        images = []
        try:
            for _ in range(3):
                image = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                image.write(b"image")
                image.close()
                images.append(image.name)
            self.service.generate("prompt", ref_image_paths=images, orientation="portrait", duration=8)
        finally:
            import os
            for path in images:
                os.remove(path)

        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-key")
        self.assertNotIn("Content-Type", kwargs["headers"])
        self.assertEqual(len([item for item in kwargs["files"] if item[0] == "input_reference[]"]), 3)
        self.assertEqual(kwargs["data"]["model"], "veo_3_1-fast-portrait")
        self.assertEqual(kwargs["data"]["duration"], "8")

    @patch("app.services.omni.bandianwa.requests.post")
    def test_generate_rejects_zero_or_more_than_three_images_without_posting(self, mock_post):
        self.assertFalse(self.service.generate("prompt", ref_image_paths=[]).success)
        self.assertFalse(self.service.generate("prompt", ref_image_paths=["a", "b", "c", "d"]).success)
        mock_post.assert_not_called()
```

- [ ] **Step 2: Write tests for completed task parsing and independent registry selection**

```python
from app.constants import SettingKeys
from app.services.media_generation import media_generation_registry

    @patch("app.services.omni.bandianwa.requests.get")
    def test_poll_task_reads_completed_video_url(self, mock_get):
        response = MagicMock()
        response.json.return_value = {
            "status": "completed",
            "data": [{"url": "https://example.com/omni.mp4"}],
        }
        response.text = '{"status":"completed"}'
        response.status_code = 200
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        result = self.service._poll_task("task_123", timeout_seconds=1, interval_seconds=0)

        self.assertTrue(result.success)
        self.assertEqual(result.video_url, "https://example.com/omni.mp4")


class OmniRegistryTests(unittest.TestCase):
    def test_resolve_video_generator_uses_omni_setting_for_omni_platform(self):
        settings = {
            SettingKeys.OMNI_MODEL: "bandianwa",
            SettingKeys.BANDIANWA_API_KEY: "test-key",
        }

        generator, platform, provider = media_generation_registry.resolve_video_generator(
            settings, platform="omni", provider=""
        )

        self.assertIsNotNone(generator)
        self.assertEqual(platform, "omni")
        self.assertEqual(provider, "bandianwa")
```

- [ ] **Step 3: Run the new test module to confirm RED**

Run: `python -m unittest tests.test_bandianwa_omni -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.omni'` because the Omni service has not yet been created.

- [ ] **Step 4: Commit the failing protocol tests**

```bash
git add tests/test_bandianwa_omni.py
git commit -m "test: define bdw omni video contract"
```

### Task 2: Implement The BDW Omni Service

**Files:**
- Create: `app/services/omni/__init__.py`
- Create: `app/services/omni/bandianwa.py`

- [ ] **Step 1: Implement the service package export**

```python
from .bandianwa import OmniBandianwa

__all__ = ["OmniBandianwa"]
```

- [ ] **Step 2: Implement a service that submits only multi-reference mode**

```python
"""斑点蛙 Omni 视频生成：仅支持 1 至 3 张参考图。"""

import mimetypes
import os
import time
from typing import Optional

import requests

from ...logger import logger
from ..veo.base import VeoResult
from ..veo.utils import download_video

BDW_BASE = "https://api.hellobabygo.com"
_PENDING_STATUSES = {"queued", "in_progress", "processing", "running"}
_FAILED_STATUSES = {"failed", "error", "cancelled"}
_MODELS = {
    "portrait": "veo_3_1-fast-portrait",
    "landscape": "veo_3_1-fast-landscape",
}


class OmniBandianwa:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def generate(self, prompt, orientation="portrait", duration=8, ref_image_paths=None, download_dir=None):
        paths = list(ref_image_paths or [])
        if not 1 <= len(paths) <= 3:
            return VeoResult(success=False, error_message="Omni BDW 仅支持 1 至 3 张参考图")
        if any(not os.path.isfile(path) for path in paths):
            return VeoResult(success=False, error_message="参考图文件不存在")

        result = self._submit_and_poll(prompt, _MODELS.get(orientation, _MODELS["portrait"]), duration, paths)
        if result.success and result.video_url and download_dir:
            result.file_path = download_video(result.video_url, download_dir, "omni_bdw")
        return result

    def _submit_and_poll(self, prompt, model, duration, paths):
        url = f"{BDW_BASE}/v1/videos"
        files = []
        handles = []
        try:
            for path in paths:
                handle = open(path, "rb")
                handles.append(handle)
                mime = mimetypes.guess_type(path)[0] or "image/png"
                files.append(("input_reference[]", (os.path.basename(path), handle, mime)))
            response = requests.post(
                url,
                headers={"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"},
                data={"model": model, "prompt": prompt, "duration": str(duration)},
                files=files,
                timeout=120,
            )
            response.raise_for_status()
            data = response.json()
            task_id = data.get("task_id") or data.get("id")
            if not task_id:
                return VeoResult(success=False, error_message="响应中未找到 task_id")
            return self._poll_task(task_id)
        except Exception as exc:
            logger.error(f"[Omni/BDW] 提交视频任务失败: {exc}")
            return VeoResult(success=False, error_message=str(exc))
        finally:
            for handle in handles:
                handle.close()

    def _poll_task(self, task_id, timeout_seconds=600, interval_seconds=10):
        deadline = time.time() + timeout_seconds
        url = f"{BDW_BASE}/v1/videos/{task_id}"
        headers = {"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"}
        while time.time() < deadline:
            try:
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                data = response.json()
                status = str(data.get("status") or "").lower()
                if status == "completed":
                    items = data.get("data") or []
                    video_url = (
                        (items[0].get("url") or items[0].get("video_url"))
                        if items and isinstance(items[0], dict)
                        else None
                    ) or data.get("url") or data.get("video_url")
                    if video_url:
                        return VeoResult(success=True, video_url=video_url)
                    return VeoResult(success=False, error_message="未找到视频数据")
                if status in _FAILED_STATUSES:
                    error = data.get("error")
                    if isinstance(error, dict):
                        error = error.get("message") or error.get("detail")
                    return VeoResult(success=False, error_message=str(error or data.get("message") or "任务执行失败"))
                if status not in _PENDING_STATUSES and status:
                    logger.warning(f"[Omni/BDW] 未识别状态: {status}")
                time.sleep(interval_seconds)
            except requests.exceptions.Timeout:
                time.sleep(interval_seconds)
            except Exception as exc:
                logger.error(f"[Omni/BDW] 轮询失败: {exc}")
                time.sleep(interval_seconds)
        return VeoResult(success=False, error_message="轮询视频结果超时")
```

- [ ] **Step 3: Run the service tests**

Run: `python -m unittest tests.test_bandianwa_omni.OmniBandianwaTests -v`

Expected: PASS for multipart validation and polling tests; the registry test remains failing until Task 3.

- [ ] **Step 4: Commit the new service**

```bash
git add app/services/omni tests/test_bandianwa_omni.py
git commit -m "feat: add bdw omni video service"
```

### Task 3: Register The Omni Video Platform

**Files:**
- Modify: `app/constants.py`
- Modify: `app/services/media_generation.py`
- Test: `tests/test_bandianwa_omni.py`

- [ ] **Step 1: Add the independent saved provider key**

```python
    OMNI_MODEL = "omni_model"
```

Insert this constant immediately after `VEO`/`SORA2` provider-selection settings in `SettingKeys`.

- [ ] **Step 2: Add temporary-image-list handling and the Omni generator**

Add a sibling helper to `_write_temp_image` that writes every reference image and cleans them after use:

```python
def _write_temp_images(ref_images: list) -> list[str]:
    paths = []
    for image in ref_images or []:
        image_data = image.get("base64", "")
        if not image_data:
            continue
        ext = _IMAGE_EXT_MAP.get(image.get("mime", "image/png"), ".png")
        tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
        try:
            tmp.write(base64.b64decode(image_data))
            tmp.flush()
            paths.append(tmp.name)
        finally:
            tmp.close()
    return paths
```

Import `OmniBandianwa`, then add:

```python
class BandianwaOmniGenerator(BaseVideoGenerator):
    platform = "omni"
    provider = "bandianwa"
    platform_label = "Omni"
    provider_label = "BDW"
    setting_key = SettingKeys.BANDIANWA_API_KEY

    def generate(self, request: VideoGenerationRequest, settings: dict) -> VideoGenerationResult:
        api_key = self.get_api_key(settings)
        if not api_key:
            return VideoGenerationResult(success=False, error_message=self.get_missing_key_message())
        if not 1 <= len(request.ref_images or []) <= 3:
            return VideoGenerationResult(success=False, error_message="Omni BDW 仅支持 1 至 3 张参考图")
        image_paths = _write_temp_images(request.ref_images)
        try:
            result = OmniBandianwa(api_key).generate(
                prompt=request.prompt,
                orientation=request.orientation,
                duration=request.duration,
                ref_image_paths=image_paths,
                download_dir=str(request.download_dir) if request.download_dir else None,
            )
            return VideoGenerationResult(
                success=result.success,
                video_url=result.video_url,
                file_path=result.file_path,
                error_message=result.error_message,
            )
        finally:
            for image_path in image_paths:
                if os.path.exists(image_path):
                    os.remove(image_path)
```

- [ ] **Step 3: Resolve and list `omni/bandianwa` independently**

In `resolve_video_generator()` include the independent candidate:

```python
("omni", settings.get(SettingKeys.OMNI_MODEL, "bandianwa")),
```

Register it without altering the existing VEO item:

```python
media_generation_registry.register_video(BandianwaOmniGenerator())
```

- [ ] **Step 4: Run the Omni and existing provider tests**

Run: `python -m unittest tests.test_bandianwa_omni tests.test_bandianwa_veo tests.test_xiaobanshou_veo tests.test_zyg_veo -v`

Expected: PASS; specifically, `veo3/bandianwa` continues its prior tests while `omni/bandianwa` resolves independently.

- [ ] **Step 5: Commit registry integration**

```bash
git add app/constants.py app/services/media_generation.py tests/test_bandianwa_omni.py
git commit -m "feat: register omni bdw generator"
```

### Task 4: Add The Single-Stage Omni Product Page

**Files:**
- Create: `frontend/src/components/OmniProduct.vue`
- Modify: `frontend/src/App.vue`

- [ ] **Step 1: Create the Omni task model and video queue**

Implement a focused component using `VeoProduct.vue` styles, with state shaped as:

```javascript
const taskList = ref([])
const dialogImages = ref([])
const dialogPrompt = ref('')
const dialogOrientation = ref('portrait')
const dialogDuration = ref(8)
const dialogCount = ref(1)

const buildTask = (images) => reactive({
  id: ++taskIdCounter,
  images: images.map(img => ({ ...img })),
  prompt: dialogPrompt.value.trim(),
  orientation: dialogOrientation.value,
  duration: dialogDuration.value,
  videoUrl: '',
  filePath: '',
  status: 'pending',
  statusText: '待处理',
})
```

The uploader must reject additions once `dialogImages.value.length >= 3` with `Omni BDW 最多支持 3 张参考图`.

- [ ] **Step 2: Generate directly from the saved references**

```javascript
const generateVideo = async (task) => {
  task.status = 'video_processing'
  task.statusText = '视频生成中...'
  const settings = await window.pywebview.api.get_all_settings().catch(() => ({}))
  const maxRetry = settings.auto_retry === 'true' ? parseInt(settings.video_max_retry || '3', 10) : 0
  const provider = settings.omni_model || 'bandianwa'
  let lastError = ''
  for (let attempt = 0; attempt <= maxRetry; attempt++) {
    if (attempt > 0) task.statusText = `视频重试中 (${attempt}/${maxRetry})...`
    const refs = task.images.map(img => ({ base64: img.base64, mime: img.mime }))
    const res = await window.pywebview.api.generate_media_video(
      task.prompt, refs, task.orientation, task.duration, 'omni', provider,
    ).catch(err => ({ ok: false, msg: String(err) }))
    if (res.ok && res.video_url) {
      task.videoUrl = res.video_url
      task.filePath = res.file_path || ''
      task.status = 'completed'
      task.statusText = '已完成'
      return
    }
    lastError = res.msg || '视频生成失败'
  }
  task.status = 'failed'
  task.statusText = `视频失败: ${lastError}`
}
```

- [ ] **Step 3: Build the UI without image-generation controls**

The component template must include:

```vue
<h2 class="page-title">omni 带货</h2>
<span class="field-label">参考图（必填，1 至 3 张）</span>
<textarea v-model="dialogPrompt" placeholder="描述视频生成效果" rows="4"></textarea>
```

The finished template uses list columns for reference images, video prompt, direction, duration, status and actions. It provides add/edit/delete/retry/preview/download/export actions and does not render any input or command for image prompt, image ratio, image quality, `generate_media_image`, or generated-image download.

- [ ] **Step 4: Mount the page from the navigation shell**

```javascript
import OmniProduct from './components/OmniProduct.vue'
```

Add a navigation item whose active page is `omni_product` and mount:

```vue
<OmniProduct
  v-show="currentPage === 'omni_product'"
  @toast="(msg, type) => toastRef?.show(msg, type)"
/>
```

- [ ] **Step 5: Build the frontend to verify compile-time integration**

Run: `npm run build`

Working directory: `frontend`

Expected: Vite build succeeds with no Vue template or import errors.

- [ ] **Step 6: Commit the page**

```bash
git add frontend/src/App.vue frontend/src/components/OmniProduct.vue
git commit -m "feat: add omni product page"
```

### Task 5: Add Omni Channel Settings

**Files:**
- Modify: `frontend/src/components/Settings.vue`
- Modify: `tests/test_bandianwa_omni.py`

- [ ] **Step 1: Add a backend expectation for the setting key**

Extend `OmniRegistryTests`:

```python
    def test_omni_setting_key_is_independent_from_veo_setting(self):
        self.assertEqual(SettingKeys.OMNI_MODEL, "omni_model")
        self.assertNotEqual(SettingKeys.OMNI_MODEL, "veo_model")
```

- [ ] **Step 2: Verify the new assertion passes after Task 3**

Run: `python -m unittest tests.test_bandianwa_omni.OmniRegistryTests -v`

Expected: PASS.

- [ ] **Step 3: Read and save the setting in Vue**

Add state and persistence:

```javascript
const omni_model = ref('bandianwa')
// inside saveSettings()
omni_model: omni_model.value,
// inside loadSettings()
if (settings.omni_model) omni_model.value = settings.omni_model
```

Add a card under `渠道与重试`:

```vue
<div class="settings-card">
  <div class="card-header"><h3 class="card-title">Omni 视频渠道</h3></div>
  <div class="card-body">
    <div class="radio-group">
      <label class="radio-item">
        <input type="radio" v-model="omni_model" value="bandianwa" />
        <span class="radio-label">BDW</span>
      </label>
    </div>
  </div>
</div>
```

- [ ] **Step 4: Build and run the focused registry tests**

Run: `python -m unittest tests.test_bandianwa_omni -v && npm run build`

Working directories: repository root for Python; `frontend` for npm.

Expected: both commands PASS.

- [ ] **Step 5: Commit settings integration**

```bash
git add frontend/src/components/Settings.vue tests/test_bandianwa_omni.py
git commit -m "feat: add omni channel setting"
```

### Task 6: Document The New Capability And Run Full Verification

**Files:**
- Create: `docs/omni/bandianwa.md`
- Modify: `docs/README.md`
- Modify: `README.md`

- [ ] **Step 1: Add the channel protocol documentation**

Create `docs/omni/bandianwa.md` with this initial content and extend it only with request/response examples consistent with these URLs:

```markdown
# Omni - 斑点蛙渠道

| 项目 | 值 |
|------|----|
| 代码标识 | `omni / bandianwa` |
| 配置键 | `omni_model=bandianwa` + `bandianwa_api_key` |
| 创建接口 | `POST /v1/videos` |
| 请求模式 | `multipart/form-data`，1 至 3 个 `input_reference[]` |

Omni 带货仅提交普通参考图模式，不支持无图片和首尾图模式，也不修改 `veo3 / bandianwa` 的既有行为。

## 参考文档

- 参数说明：https://xxp0w23uvv.apifox.cn/folder-83486592
- 参考图任务创建：https://xxp0w23uvv.apifox.cn/api-445857184
- 任务查询：https://xxp0w23uvv.apifox.cn/api-445857186
- 获取视频内容：https://xxp0w23uvv.apifox.cn/api-445857182
```

- [ ] **Step 2: Update documentation indexes and user-facing capability tables**

Add `Omni 视频生成 | 斑点蛙 | omni/bandianwa` to `README.md` and an `omni/` channel entry to `docs/README.md`. List `omni_model` as an independent provider-selection setting and note reuse of `bandianwa_api_key`.

- [ ] **Step 3: Run backend regression tests**

Run: `python -m unittest discover -s tests -v`

Expected: PASS for the existing providers and new Omni cases.

- [ ] **Step 4: Run the production frontend build**

Run: `npm run build`

Working directory: `frontend`

Expected: Vite production build succeeds.

- [ ] **Step 5: Inspect the worktree and commit documentation**

Run: `git status --short`

Expected: only the planned Omni documentation files are staged/unstaged for this commit; pre-existing `.claude/settings.local.json` remains untouched and excluded.

```bash
git add README.md docs/README.md docs/omni/bandianwa.md
git commit -m "docs: document omni bdw provider"
```

## Completion Check

- `omni带货` is visible as a distinct navigation entry and launches a direct-to-video workflow.
- A task cannot be created with no references or with more than three references.
- Two uploaded images remain ordinary BDW reference images and never select an `-fl` model.
- `omni_model` is stored separately from `veo_model`, while BDW reuses `bandianwa_api_key`.
- Existing VEO and Sora2 behavior remains covered by passing regression tests.
- No pre-existing user change, including `.claude/settings.local.json`, is committed as part of implementation.
