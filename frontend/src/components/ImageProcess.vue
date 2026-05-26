<script setup>
import { ref, computed, onMounted } from 'vue'

const emit = defineEmits(['toast'])

// 图片列表
const imageList = ref([])

// 导入相关
const fileInput = ref(null)
const folderInput = ref(null)
const isDragging = ref(false)

const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif', 'image/bmp']
const ACCEPTED_EXTS = ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp']

const isImageFile = (file) => {
  if (ACCEPTED_TYPES.includes(file.type)) return true
  const name = file.name.toLowerCase()
  return ACCEPTED_EXTS.some(ext => name.endsWith(ext))
}

const addFiles = (files) => {
  const newImages = []
  for (const file of files) {
    if (!isImageFile(file)) continue
    const exists = imageList.value.some(
      img => img.name === file.name && img.size === file.size
    )
    if (exists) continue
    const src = URL.createObjectURL(file)
    newImages.push({
      name: file.name,
      size: file.size,
      file: file,
      src: src,
      status: 'pending',
      statusText: '待处理',
      resultSrc: '',
    })
  }
  if (newImages.length > 0) {
    imageList.value.push(...newImages)
    emit('toast', `已导入 ${newImages.length} 张图片`, 'success')
  } else {
    emit('toast', '没有发现新的图片文件', 'error')
  }
}

const handleFileSelect = (event) => {
  const files = event.target.files
  if (files && files.length > 0) addFiles(Array.from(files))
  if (fileInput.value) fileInput.value.value = ''
}

const handleFolderSelect = (event) => {
  const files = event.target.files
  if (files && files.length > 0) addFiles(Array.from(files))
  if (folderInput.value) folderInput.value.value = ''
}

// 拖拽
const onDragEnter = (e) => { e.preventDefault(); isDragging.value = true }
const onDragOver = (e) => { e.preventDefault(); isDragging.value = true }
const onDragLeave = (e) => {
  e.preventDefault()
  if (e.currentTarget.contains(e.relatedTarget)) return
  isDragging.value = false
}
const onDrop = (e) => {
  e.preventDefault()
  isDragging.value = false
  const items = e.dataTransfer?.items
  if (items) {
    const files = []
    for (const item of items) {
      if (item.kind === 'file') { const f = item.getAsFile(); if (f) files.push(f) }
    }
    if (files.length > 0) { addFiles(files); return }
  }
  const files = e.dataTransfer?.files
  if (files && files.length > 0) addFiles(Array.from(files))
}

const removeImage = (idx) => {
  const img = imageList.value[idx]
  if (img?.src) URL.revokeObjectURL(img.src)
  imageList.value.splice(idx, 1)
}

// ==================== 生成逻辑 ====================
const withTimeout = (promise, ms) => {
  return Promise.race([
    promise,
    new Promise((_, reject) => setTimeout(() => reject(new Error('请求超时')), ms))
  ])
}

const fileToBase64 = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const dataUrl = reader.result
      resolve(dataUrl.split(',')[1])
    }
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

const generateSingle = async (img) => {
  if (img.status === 'processing') return
  img.status = 'processing'
  img.statusText = '生成中...'
  img.resultSrc = ''

  // 读取图片最大重试次数
  let maxRetry = 0
  try {
    const settings = await window.pywebview.api.get_all_settings()
    if (settings.auto_retry === 'true') {
      maxRetry = parseInt(settings.image_max_retry || '3', 10)
    }
  } catch { /* ignore */ }

  const base64 = await fileToBase64(img.file)
  let attempts = 0
  let lastError = ''

  while (attempts <= maxRetry) {
    if (attempts > 0) {
      img.statusText = `重试中 (${attempts}/${maxRetry})...`
    }
    try {
      const refImages = [{ base64, mime: img.file.type || 'image/jpeg' }]
      const res = await withTimeout(
        window.pywebview.api.generate_media_image(promptText.value, refImages),
        200000
      )
      if (res.ok && res.image_data && res.mime_type) {
        img.resultSrc = `data:${res.mime_type};base64,${res.image_data}`
        img.status = 'completed'
        img.statusText = '已完成'
        // 自动添加到视频生成任务
        try {
          await window.pywebview.api.auto_create_video_task(res.image_data, res.mime_type)
        } catch { /* 静默失败，不影响图片处理流程 */ }
        return
      } else {
        lastError = res.msg || '生成失败'
      }
    } catch (e) {
      lastError = String(e)
    }
    attempts++
  }

  img.status = 'failed'
  img.statusText = lastError
}

const batchGenerating = ref(false)

const pendingCount = computed(() =>
  imageList.value.filter(img => img.status === 'pending' || img.status === 'failed').length
)

const batchGenerate = async () => {
  const targets = imageList.value.filter(img => img.status === 'pending' || img.status === 'failed')
  if (targets.length === 0) {
    emit('toast', '没有待处理的图片', 'error')
    return
  }
  batchGenerating.value = true

  // 读取并发数（使用线程池大小设置，默认 10）
  let concurrency = 10
  try {
    const settings = await window.pywebview.api.get_all_settings()
    const poolSize = parseInt(settings.thread_pool_size || '10', 10)
    if (poolSize > 0) concurrency = poolSize
  } catch { /* ignore */ }

  let success = 0
  let fail = 0
  let idx = 0

  // 并发池：同时处理 concurrency 个任务
  const runNext = async () => {
    while (idx < targets.length) {
      const currentIdx = idx++
      const img = targets[currentIdx]
      await generateSingle(img)
      if (img.status === 'completed') success++
      else fail++
    }
  }

  const workers = []
  for (let i = 0; i < Math.min(concurrency, targets.length); i++) {
    workers.push(runNext())
  }
  await Promise.all(workers)

  batchGenerating.value = false
  emit('toast', `批量处理完成：成功 ${success}，失败 ${fail}`, success > 0 ? 'success' : 'error')
}

// ==================== 图片预览 ====================
const previewSrc = ref('')
const showPreview = ref(false)

const openPreview = (src) => {
  previewSrc.value = src
  showPreview.value = true
}

const closePreview = () => {
  showPreview.value = false
  previewSrc.value = ''
}

// ==================== 提示词弹窗 ====================
const showPromptDialog = ref(false)
const defaultPrompt = '请根据图片中的产品，为其绘制一个真实、自然的展示场景。场景需要与产品类型相匹配，突出产品本身，背景环境要逼真有质感。注意：画面中不要出现任何文字、标签或水印。'
const promptText = ref(defaultPrompt)
const promptSaving = ref(false)

const loadPrompt = async () => {
  try {
    const res = await window.pywebview.api.get_image_process_prompt()
    if (res.ok && res.prompt) promptText.value = res.prompt
  } catch { /* ignore */ }
}

const openPromptDialog = () => { showPromptDialog.value = true }
const closePromptDialog = () => { showPromptDialog.value = false }

const savePrompt = async () => {
  promptSaving.value = true
  try {
    const res = await window.pywebview.api.set_image_process_prompt(promptText.value)
    if (res.ok) {
      emit('toast', '提示词已保存', 'success')
      showPromptDialog.value = false
    } else {
      emit('toast', res.msg || '保存失败', 'error')
    }
  } catch { emit('toast', '保存异常', 'error') }
  finally { promptSaving.value = false }
}

onMounted(() => { loadPrompt() })
</script>

<template>
  <div class="page">
    <!-- 隐藏 input -->
    <input ref="fileInput" type="file" accept="image/*" multiple class="hidden-input" @change="handleFileSelect" />
    <input ref="folderInput" type="file" accept="image/*" multiple webkitdirectory class="hidden-input" @change="handleFolderSelect" />

    <!-- 顶栏 -->
    <div class="page-toolbar">
      <h2 class="page-title">图片处理</h2>
      <div class="toolbar-actions">
        <button class="tool-btn" @click="folderInput?.click()">
          <svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
          </svg>
          <span>导入文件夹</span>
        </button>
        <button class="tool-btn" @click="fileInput?.click()">
          <svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
            <circle cx="8.5" cy="8.5" r="1.5"/>
            <polyline points="21 15 16 10 5 21"/>
          </svg>
          <span>导入图片</span>
        </button>
        <button
          class="tool-btn batch-btn"
          @click="batchGenerate"
          :disabled="batchGenerating || pendingCount === 0"
        >
          <svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="5 3 19 12 5 21 5 3"/>
          </svg>
          <span>{{ batchGenerating ? '批量生成中...' : `批量生成 (${pendingCount})` }}</span>
        </button>
        <button class="tool-btn" @click="openPromptDialog">
          <svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 20h9"/>
            <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
          </svg>
          <span>提示词设置</span>
        </button>
      </div>
    </div>

    <!-- 内容区 -->
    <div
      class="page-body"
      :class="{ 'drag-active': isDragging }"
      @dragenter="onDragEnter"
      @dragover="onDragOver"
      @dragleave="onDragLeave"
      @drop="onDrop"
    >
      <!-- 拖拽遮罩 -->
      <div v-if="isDragging" class="drag-overlay">
        <svg class="drag-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
          <polyline points="17 8 12 3 7 8"/>
          <line x1="12" y1="3" x2="12" y2="15"/>
        </svg>
        <p class="drag-text">松开鼠标导入图片</p>
      </div>

      <!-- 空状态 -->
      <div v-if="imageList.length === 0 && !isDragging" class="empty-state">
        <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
          <circle cx="8.5" cy="8.5" r="1.5"/>
          <polyline points="21 15 16 10 5 21"/>
        </svg>
        <p class="empty-text">暂无图片</p>
        <p class="empty-hint">点击上方按钮导入图片 / 文件夹，或直接拖拽图片到此处</p>
      </div>

      <!-- 列表 -->
      <div v-else-if="!isDragging" class="list-wrap">
        <!-- 表头 -->
        <div class="list-header">
          <div class="col col-index">#</div>
          <div class="col col-origin">原图</div>
          <div class="col col-name">文件名</div>
          <div class="col col-status">状态</div>
          <div class="col col-result">生成结果</div>
          <div class="col col-actions">操作</div>
        </div>
        <!-- 行 -->
        <div
          v-for="(img, idx) in imageList"
          :key="img.name + img.size"
          class="list-row"
        >
          <div class="col col-index">{{ idx + 1 }}</div>
          <div class="col col-origin">
            <div class="thumb clickable" @click="openPreview(img.src)"><img :src="img.src" :alt="img.name" /></div>
          </div>
          <div class="col col-name" :title="img.name">{{ img.name }}</div>
          <div class="col col-status">
            <span :class="['status-tag', img.status]">{{ img.statusText }}</span>
          </div>
          <div class="col col-result">
            <div v-if="img.resultSrc" class="thumb clickable" @click="openPreview(img.resultSrc)"><img :src="img.resultSrc" alt="生成结果" /></div>
            <span v-else class="no-result">—</span>
          </div>
          <div class="col col-actions">
            <button
              class="action-btn generate-btn"
              @click="generateSingle(img)"
              :disabled="img.status === 'processing'"
              title="生成图片"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                <circle cx="8.5" cy="8.5" r="1.5"/>
                <polyline points="21 15 16 10 5 21"/>
              </svg>
            </button>
            <button
              class="action-btn video-btn"
              :disabled="img.status === 'processing'"
              title="生成视频"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polygon points="23 7 16 12 23 17 23 7"/>
                <rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>
              </svg>
            </button>
            <button
              class="action-btn delete-btn"
              @click="removeImage(idx)"
              :disabled="img.status === 'processing'"
              title="删除"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="3 6 5 6 21 6"/>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 图片预览 -->
    <Teleport to="body">
      <div v-if="showPreview" class="preview-overlay" @click="closePreview">
        <button class="preview-close" @click="closePreview">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
        <img :src="previewSrc" class="preview-img" @click.stop alt="预览" />
      </div>
    </Teleport>

    <!-- 提示词设置弹窗 -->
    <Teleport to="body">
      <div v-if="showPromptDialog" class="dialog-overlay" @click.self="closePromptDialog">
        <div class="dialog">
          <div class="dialog-header">
            <h3 class="dialog-title">提示词设置</h3>
            <button class="dialog-close" @click="closePromptDialog">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>
          <div class="dialog-body">
            <label class="field">
              <span class="field-label">NanoBanana 图片处理提示词</span>
              <textarea
                v-model="promptText"
                placeholder="请输入图片处理的提示词，将应用于列表中所有图片的 NanoBanana 处理"
                rows="10"
              ></textarea>
            </label>
          </div>
          <div class="dialog-footer">
            <button class="cancel-btn" @click="closePromptDialog">取消</button>
            <button class="primary-btn save-btn" @click="savePrompt" :disabled="promptSaving">
              {{ promptSaving ? '保存中...' : '保存' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.page {
  position: relative;
  min-height: 100%;
  display: flex;
  flex-direction: column;
}

.hidden-input { display: none; }

/* ============ 顶栏 ============ */
.page-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 32px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.page-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.toolbar-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.tool-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 10px;
  border: 1px solid var(--border-strong);
  background: var(--border-subtle);
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease, color 0.2s ease;
}

.tool-btn:hover {
  background: var(--accent-bg-strong);
  border-color: var(--accent-border);
  color: var(--accent);
}

.tool-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.tool-btn:disabled:hover {
  background: var(--border-subtle);
  border-color: var(--border-strong);
  color: var(--text-secondary);
}

.batch-btn {
  border-color: rgba(52, 199, 89, 0.3);
  background: rgba(52, 199, 89, 0.08);
  color: var(--success);
}

.batch-btn:hover:not(:disabled) {
  background: rgba(52, 199, 89, 0.18);
  border-color: rgba(52, 199, 89, 0.5);
  color: var(--success);
}

.tool-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

/* ============ 内容区 ============ */
.page-body {
  flex: 1;
  padding: 24px 32px;
  position: relative;
  transition: background 0.2s ease;
  overflow-y: auto;
}

.page-body.drag-active {
  background: var(--accent-bg-subtle);
}

/* ============ 拖拽 ============ */
.drag-overlay {
  position: absolute;
  inset: 16px;
  z-index: 10;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  border-radius: 16px;
  border: 2px dashed var(--accent-focus);
  background: var(--accent-bg);
  pointer-events: none;
}

.drag-icon { width: 48px; height: 48px; color: rgba(200,96,122, 0.7); }
.drag-text { margin: 0; font-size: 16px; font-weight: 500; color: rgba(200,96,122, 0.8); }

/* ============ 空状态 ============ */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
}

.empty-icon { width: 64px; height: 64px; color: var(--border-strong); margin-bottom: 20px; }
.empty-text { margin: 0; font-size: 16px; font-weight: 500; color: var(--text-placeholder); }
.empty-hint { margin: 8px 0 0; font-size: 13px; color: var(--text-hint); }

/* ============ 列表 ============ */
.list-wrap {
  border: 1px solid var(--border);
  border-radius: 12px;
  overflow: hidden;
}

.list-header,
.list-row {
  display: flex;
  align-items: center;
}

.list-header {
  background: var(--bg-card);
  padding: 10px 16px;
  border-bottom: 1px solid var(--border);
}

.list-header .col {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.list-row {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-light);
  transition: background 0.15s ease;
}

.list-row:last-child {
  border-bottom: none;
}

.list-row:hover {
  background: var(--border-subtle);
}

/* 列宽 */
.col-index  { width: 40px; flex-shrink: 0; text-align: center; }
.col-origin { width: 80px; flex-shrink: 0; }
.col-name   { flex: 1; min-width: 0; padding: 0 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; color: var(--text-secondary); }
.col-status { width: 100px; flex-shrink: 0; text-align: center; }
.col-result { width: 80px; flex-shrink: 0; }
.col-actions { width: 130px; flex-shrink: 0; display: flex; justify-content: center; gap: 8px; }

/* 缩略图 */
.thumb {
  width: 56px;
  height: 56px;
  border-radius: 8px;
  overflow: hidden;
  background: var(--bg-surface);
  border: 1px solid var(--border);
}

.thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.no-result {
  font-size: 13px;
  color: var(--text-hint);
  display: flex;
  width: 56px;
  height: 56px;
  align-items: center;
  justify-content: center;
}

/* 状态标签 */
.status-tag {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
}

.status-tag.pending {
  background: rgba(255, 214, 10, 0.1);
  color: #ffd60a;
}

.status-tag.processing {
  background: var(--accent-bg);
  color: var(--accent);
}

.status-tag.completed {
  background: var(--success-bg);
  color: var(--success);
}

.status-tag.failed {
  background: var(--error-bg);
  color: var(--error);
}

/* 操作按钮 */
.action-btn {
  width: 34px;
  height: 34px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  border: 1px solid var(--border-medium);
  background: var(--border-light);
  color: var(--text-tertiary);
  cursor: pointer;
  transition: all 0.15s ease;
}

.action-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.action-btn svg {
  width: 15px;
  height: 15px;
}

.generate-btn:hover:not(:disabled) {
  background: rgba(52, 199, 89, 0.15);
  border-color: rgba(52, 199, 89, 0.4);
  color: var(--success);
}

.video-btn:hover:not(:disabled) {
  background: var(--accent-bg-strong);
  border-color: rgba(200,96,122,0.4);
  color: var(--accent);
}

.delete-btn:hover:not(:disabled) {
  background: rgba(255, 69, 58, 0.15);
  border-color: rgba(255, 69, 58, 0.4);
  color: var(--error);
}

/* ============ 弹窗 ============ */
.dialog-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
}

.dialog {
  width: min(520px, calc(100% - 40px));
  border-radius: 16px;
  background: linear-gradient(180deg, var(--bg-card), var(--bg-card));
  border: 1px solid var(--border-medium);
  box-shadow: 0 24px 60px rgba(5, 7, 12, 0.8);
  overflow: hidden;
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 24px;
  border-bottom: 1px solid var(--border);
}

.dialog-title { margin: 0; font-size: 16px; font-weight: 600; color: var(--text-primary); }

.dialog-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  padding: 0;
  border-radius: 8px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}

.dialog-close:hover { background: var(--border-medium); color: var(--text-primary); }
.dialog-close svg { width: 18px; height: 18px; }

.dialog-body { padding: 24px; }

.dialog-body textarea {
  width: 100%;
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid var(--border-medium);
  background: var(--bg-surface);
  color: var(--text-primary);
  font-size: 14px;
  font-family: inherit;
  outline: none;
  resize: vertical;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.dialog-body textarea::placeholder { color: var(--text-placeholder); }
.dialog-body textarea:focus { border-color: rgba(200,96,122,0.6); box-shadow: 0 0 0 3px var(--accent-bg-strong); }

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid var(--border);
}

.cancel-btn {
  padding: 10px 20px;
  border-radius: 10px;
  border: 1px solid var(--border-strong);
  background: var(--border-subtle);
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s ease, color 0.2s ease;
}

.cancel-btn:hover { background: var(--border-strong); color: var(--text-primary); }

.save-btn { width: auto; padding: 10px 24px; font-size: 13px; }
.save-btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none !important; box-shadow: none !important; }

/* ============ 图片预览 ============ */
.thumb.clickable {
  cursor: pointer;
  transition: opacity 0.15s ease;
}

.thumb.clickable:hover {
  opacity: 0.8;
}

.preview-overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.85);
  backdrop-filter: blur(8px);
  cursor: zoom-out;
}

.preview-close {
  position: absolute;
  top: 20px;
  right: 20px;
  width: 40px;
  height: 40px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  border: none;
  background: rgba(255,255,255,0.15);
  color: rgba(255,255,255,0.95);
  cursor: pointer;
  transition: background 0.15s ease;
  z-index: 1;
}

.preview-close:hover {
  background: rgba(255,255,255,0.25);
}

.preview-close svg {
  width: 20px;
  height: 20px;
}

.preview-img {
  max-width: 90vw;
  max-height: 90vh;
  object-fit: contain;
  border-radius: 8px;
  cursor: default;
}
</style>
