<script setup>
import { ref, reactive, onMounted } from 'vue'

const emit = defineEmits(['toast', 'add-veo-task'])

const taskList = ref([])
let taskIdCounter = 0

const ratioOptions = [
  { value: '9:16', label: '9:16 竖屏' },
  { value: '16:9', label: '16:9 横屏' },
  { value: '1:1',  label: '1:1 方图' },
  { value: '4:3',  label: '4:3 横屏' },
  { value: '3:4',  label: '3:4 竖屏' },
]

const qualityOptions = [
  { value: '1K', label: '1K' },
  { value: '2K', label: '2K' },
  { value: '4K', label: '4K' },
]

// ==================== 添加任务弹窗 ====================
const showAddDialog = ref(false)
const addPrompt = ref('')
const addRatio = ref('9:16')
const addQuality = ref('1K')
const addImages = ref([])   // [{preview, base64, mime}]
const addSubmitting = ref(false)
const addIsDragging = ref(false)
const addFileInput = ref(null)

const pageDragging = ref(false)

onMounted(async () => {
  try {
    const settings = await window.pywebview.api.get_all_settings()
    if (settings.glin_nanobanana_ratio) addRatio.value = settings.glin_nanobanana_ratio
    if (settings.glin_nanobanana_quality) addQuality.value = settings.glin_nanobanana_quality
  } catch { /* ignore */ }
})

const openAddDialog = (file = null) => {
  addPrompt.value = ''
  addImages.value = []
  addSubmitting.value = false
  showAddDialog.value = true
  if (file) handleAddImage(file)
}
const closeAddDialog = () => { showAddDialog.value = false }

const handleAddImage = (file) => {
  if (!file) return
  if (!file.type.startsWith('image/')) { emit('toast', '请选择图片文件', 'error'); return }
  if (file.size > 10 * 1024 * 1024) { emit('toast', '图片不能超过 10MB', 'error'); return }
  const reader = new FileReader()
  reader.onload = (e) => {
    addImages.value.push({
      preview: e.target.result,
      base64: e.target.result.split(',')[1],
      mime: file.type,
    })
  }
  reader.readAsDataURL(file)
}

const handleAddFileSelect = (e) => {
  const files = Array.from(e.target.files || [])
  files.forEach(f => handleAddImage(f))
  if (addFileInput.value) addFileInput.value.value = ''
}

const onDialogDragEnter = (e) => { e.preventDefault(); addIsDragging.value = true }
const onDialogDragOver  = (e) => { e.preventDefault(); addIsDragging.value = true }
const onDialogDragLeave = (e) => {
  e.preventDefault()
  if (e.currentTarget.contains(e.relatedTarget)) return
  addIsDragging.value = false
}
const onDialogDrop = (e) => {
  e.preventDefault()
  addIsDragging.value = false
  const files = Array.from(e.dataTransfer?.files || [])
  files.forEach(f => handleAddImage(f))
}
const removeAddImage = (idx) => { addImages.value.splice(idx, 1) }

const onPageDragEnter = (e) => { e.preventDefault(); pageDragging.value = true }
const onPageDragOver  = (e) => { e.preventDefault(); pageDragging.value = true }
const onPageDragLeave = (e) => {
  e.preventDefault()
  if (e.currentTarget.contains(e.relatedTarget)) return
  pageDragging.value = false
}
const onPageDrop = (e) => {
  e.preventDefault()
  pageDragging.value = false
  const files = Array.from(e.dataTransfer?.files || [])
  const imgs = files.filter(f => f.type.startsWith('image/'))
  if (imgs.length) {
    openAddDialog()
    imgs.forEach(f => handleAddImage(f))
  }
}

// 提交添加任务
const submitAddTask = () => {
  if (!addPrompt.value.trim()) { emit('toast', '请输入提示词', 'error'); return }
  addSubmitting.value = true

  window.pywebview.api.save_settings({
    glin_nanobanana_ratio: addRatio.value,
    glin_nanobanana_quality: addQuality.value,
  }).catch(() => {})

  const images = addImages.value.map(img => ({ ...img }))
  const task = reactive({
    id: ++taskIdCounter,
    prompt: addPrompt.value,
    ratio: addRatio.value,
    quality: addQuality.value,
    images,
    status: 'pending',
    statusText: '待处理',
    resultSrc: '',
    resultBase64: '',
    resultMime: '',
    filePath: '',
    resultPlatform: '',
    resultProvider: '',
  })
  taskList.value.unshift(task)
  showAddDialog.value = false
  addSubmitting.value = false
  generateTask(task)
}

// ==================== 生成逻辑 ====================
const withTimeout = (promise, ms) =>
  Promise.race([promise, new Promise((_, reject) => setTimeout(() => reject(new Error('请求超时')), ms))])

const generateTask = async (task) => {
  if (task.status === 'processing') return
  task.status = 'processing'
  task.statusText = '生成中...'
  task.resultSrc = ''
  task.resultBase64 = ''
  task.resultMime = ''
  task.filePath = ''

  let maxRetry = 0
  try {
    const settings = await window.pywebview.api.get_all_settings()
    if (settings.auto_retry === 'true') {
      maxRetry = parseInt(settings.image_max_retry || '3', 10)
    }
  } catch { /* ignore */ }

  let attempts = 0
  let lastError = ''

  while (attempts <= maxRetry) {
    if (attempts > 0) task.statusText = `重试中 (${attempts}/${maxRetry})...`
    try {
      const refImages = (task.images || []).map(img => ({ base64: img.base64, mime: img.mime }))
      const res = await withTimeout(
        window.pywebview.api.generate_media_image(
          task.prompt,
          refImages,
          task.ratio,
          task.quality,
          '',
          '',
        ),
        300000,
      )
      if (res.ok && res.image_data && res.mime_type) {
        task.resultSrc = `data:${res.mime_type};base64,${res.image_data}`
        task.resultBase64 = res.image_data
        task.resultMime = res.mime_type
        task.filePath = res.file_path || ''
        task.resultPlatform = res.platform || ''
        task.resultProvider = res.provider || ''
        task.status = 'completed'
        task.statusText = '已完成'
        if (task.filePath) {
          emit('toast', `图片已保存: ${task.filePath.split(/[\\/]/).pop()}`, 'success')
        }
        return
      } else {
        lastError = res.msg || '生成失败'
      }
    } catch (e) {
      lastError = String(e)
    }
    attempts++
  }

  task.status = 'failed'
  task.statusText = lastError
}

// ==================== 操作 ====================
const deleteTask = (idx) => { taskList.value.splice(idx, 1) }

const deleteAllTasks = () => {
  if (taskList.value.some(t => t.status === 'processing')) {
    emit('toast', '有任务正在处理中，无法全部删除', 'error')
    return
  }
  taskList.value = []
}

const copyPrompt = async (text) => {
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    emit('toast', '提示词已复制', 'success')
  } catch { emit('toast', '复制失败', 'error') }
}

const downloadImage = async (task) => {
  if (!task.resultBase64) { emit('toast', '暂无生成结果', 'error'); return }
  try {
    emit('toast', '开始下载...', 'success')
    const prefix = task.resultPlatform === 'gpt-image' ? 'gpt_image' : 'nanobanana'
    const res = await window.pywebview.api.download_image(task.resultBase64, task.resultMime, prefix)
    if (res.ok) {
      emit('toast', '图片已保存', 'success')
    } else {
      emit('toast', res.msg || '下载失败', 'error')
    }
  } catch { emit('toast', '下载异常', 'error') }
}

const createVideoTask = async (task) => {
  if (!task.resultBase64) { emit('toast', '暂无生成结果', 'error'); return }
  try {
    const settings = await window.pywebview.api.get_all_settings()
    const promptRes = await window.pywebview.api.get_video_process_prompt()
    const prompt = promptRes.prompt || ''
    const orientation = settings.hetang_veo_orientation || 'portrait'
    const images = [{ base64: task.resultBase64, mime: task.resultMime }]
    emit('add-veo-task', { prompt, orientation, images })
    emit('toast', '已添加到 VEO 视频列表', 'success')
  } catch (e) { emit('toast', `添加失败: ${e}`, 'error') }
}

// ==================== 预览 ====================
const previewSrc = ref('')
const showPreview = ref(false)
const openPreview = (src) => { previewSrc.value = src; showPreview.value = true }
const closePreview = () => { showPreview.value = false; previewSrc.value = '' }

// ==================== 一键下载 ====================
const exportAll = async () => {
  const paths = taskList.value.filter(t => t.filePath).map(t => t.filePath)
  if (!paths.length) { emit('toast', '暂无已下载的文件', 'error'); return }
  try {
    const res = await window.pywebview.api.batch_export_files(paths)
    if (res.ok) emit('toast', res.msg, 'success')
    else emit('toast', res.msg || '导出取消', 'error')
  } catch { emit('toast', '导出异常', 'error') }
}

// ==================== 格式化 ====================
const ratioLabel = (val) => ratioOptions.find(o => o.value === val)?.label || val
</script>

<template>
  <div class="page">
    <!-- 顶栏 -->
    <div class="page-toolbar">
      <h2 class="page-title">图片生成</h2>
      <div class="toolbar-actions">
        <button class="tool-btn refresh-btn" @click="() => window.location.reload()">
          <svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
          </svg>
          <span>刷新</span>
        </button>
        <button v-if="taskList.some(t => t.filePath)" class="tool-btn export-btn" @click="exportAll">
          <svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          <span>一键下载</span>
        </button>
        <button v-if="taskList.length > 0" class="tool-btn delete-all-btn" @click="deleteAllTasks">
          <svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
          </svg>
          <span>全部删除</span>
        </button>
        <button class="tool-btn add-btn" @click="openAddDialog()">
          <svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          <span>添加任务</span>
        </button>
      </div>
    </div>

    <!-- 内容区 -->
    <div
      class="page-body"
      :class="{ 'drag-active': pageDragging }"
      @dragenter="onPageDragEnter"
      @dragover="onPageDragOver"
      @dragleave="onPageDragLeave"
      @drop="onPageDrop"
    >
      <!-- 拖拽遮罩 -->
      <div v-if="pageDragging" class="drag-overlay">
        <svg class="drag-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
          <polyline points="17 8 12 3 7 8"/>
          <line x1="12" y1="3" x2="12" y2="15"/>
        </svg>
        <p class="drag-text">松开鼠标添加参考图片</p>
      </div>

      <!-- 空状态 -->
      <div v-if="taskList.length === 0 && !pageDragging" class="empty-state">
        <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
          <circle cx="8.5" cy="8.5" r="1.5"/>
          <polyline points="21 15 16 10 5 21"/>
        </svg>
        <p class="empty-text">暂无生图任务</p>
        <p class="empty-hint">点击"添加任务"或拖拽参考图片到此处</p>
      </div>

      <!-- 列表 -->
      <div v-else-if="!pageDragging" class="list-wrap">
        <div class="list-header">
          <div class="col col-index">#</div>
          <div class="col col-origin">参考图</div>
          <div class="col col-prompt">提示词</div>
          <div class="col col-params">参数</div>
          <div class="col col-status">状态</div>
          <div class="col col-result">结果</div>
          <div class="col col-actions">操作</div>
        </div>
        <div v-for="(task, idx) in taskList" :key="task.id" class="list-row">
          <div class="col col-index">{{ taskList.length - idx }}</div>
          <div class="col col-origin">
            <div v-if="task.images && task.images.length" class="thumb-group">
              <div
                v-for="(img, i) in task.images.slice(0, 3)" :key="i"
                class="thumb mini clickable"
                @click="openPreview(img.preview)"
              ><img :src="img.preview" alt="参考图" /></div>
              <span v-if="task.images.length > 3" class="thumb-more">+{{ task.images.length - 3 }}</span>
            </div>
            <span v-else class="no-result label-text">文生图</span>
          </div>
          <div
            class="col col-prompt copyable"
            :title="task.prompt + '\n（点击复制）'"
            @click="copyPrompt(task.prompt)"
          >{{ task.prompt }}</div>
          <div class="col col-params">
            <span class="param-tag">{{ ratioLabel(task.ratio) }}</span>
            <span class="param-tag quality">{{ task.quality }}</span>
          </div>
          <div class="col col-status">
            <span :class="['status-tag', task.status]">{{ task.statusText }}</span>
          </div>
          <div class="col col-result">
            <div v-if="task.resultSrc" class="thumb clickable" @click="openPreview(task.resultSrc)">
              <img :src="task.resultSrc" alt="结果" />
            </div>
            <span v-else class="no-result">—</span>
          </div>
          <div class="col col-actions">
            <button v-if="task.resultSrc" class="action-btn view-btn" @click="openPreview(task.resultSrc)" title="查看">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>
              </svg>
            </button>
            <button v-if="task.resultSrc" class="action-btn download-btn" @click="downloadImage(task)" title="下载">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
              </svg>
            </button>
            <button v-if="task.resultSrc" class="action-btn video-btn" @click="createVideoTask(task)" title="生成视频">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polygon points="23 7 16 12 23 17 23 7"/>
                <rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>
              </svg>
            </button>
            <button v-if="task.status === 'failed'" class="action-btn retry-btn" @click="generateTask(task)" title="重试">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
              </svg>
            </button>
            <button class="action-btn delete-btn" @click="deleteTask(idx)" :disabled="task.status === 'processing'" title="删除">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 添加任务弹窗 -->
    <Teleport to="body">
      <div v-if="showAddDialog" class="dialog-overlay" @click.self="closeAddDialog">
        <div class="dialog">
          <div class="dialog-header">
            <h3 class="dialog-title">添加生图任务</h3>
            <button class="dialog-close" @click="closeAddDialog">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>
          <div class="dialog-body">
            <!-- 提示词 -->
            <label class="field">
              <span class="field-label">提示词（必填）</span>
              <textarea v-model="addPrompt" placeholder="描述你想要生成的图片内容" rows="3"></textarea>
            </label>

            <!-- 比例 & 清晰度 -->
            <div class="params-row">
              <div class="field param-field">
                <span class="field-label">画面比例</span>
                <div class="seg-group">
                  <button
                    v-for="opt in ratioOptions" :key="opt.value"
                    :class="['seg-btn', { active: addRatio === opt.value }]"
                    @click="addRatio = opt.value"
                  >{{ opt.label }}</button>
                </div>
              </div>
              <div class="field param-field">
                <span class="field-label">清晰度</span>
                <div class="seg-group">
                  <button
                    v-for="opt in qualityOptions" :key="opt.value"
                    :class="['seg-btn', { active: addQuality === opt.value }]"
                    @click="addQuality = opt.value"
                  >{{ opt.label }}</button>
                </div>
              </div>
            </div>

            <!-- 参考图（可选，支持多图） -->
            <div class="field" style="margin-top: 16px;">
              <span class="field-label">参考图片（可选，支持多图，拖拽或点击上传）</span>
              <div class="ref-images-grid" v-if="addImages.length">
                <div v-for="(img, idx) in addImages" :key="idx" class="ref-image-preview">
                  <img :src="img.preview" alt="参考图" />
                  <button class="remove-btn" @click="removeAddImage(idx)" title="移除">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                  </button>
                </div>
              </div>
              <div
                class="upload-area"
                :class="{ 'drag-active': addIsDragging }"
                @click="addFileInput?.click()"
                @dragenter="onDialogDragEnter"
                @dragover="onDialogDragOver"
                @dragleave="onDialogDragLeave"
                @drop="onDialogDrop"
              >
                <input ref="addFileInput" type="file" accept="image/*" multiple class="upload-input" @change="handleAddFileSelect" />
                <svg class="upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
                </svg>
                <span class="upload-text">{{ addImages.length ? '继续添加图片' : '点击或拖拽图片' }}</span>
                <span class="upload-hint">不上传则为文生图模式</span>
              </div>
            </div>
          </div>
          <div class="dialog-footer">
            <button class="cancel-btn" @click="closeAddDialog">取消</button>
            <button class="primary-btn save-btn" @click="submitAddTask" :disabled="addSubmitting">
              {{ addSubmitting ? '添加中...' : '添加并生成' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 图片预览 -->
    <Teleport to="body">
      <div v-if="showPreview" class="preview-overlay" @click="closePreview">
        <button class="preview-close" @click="closePreview">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
        <img :src="previewSrc" class="preview-img" @click.stop alt="预览" />
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.page { position: relative; min-height: 100%; display: flex; flex-direction: column; }

/* ============ 顶栏 ============ */
.page-toolbar { display: flex; align-items: center; justify-content: space-between; padding: 20px 32px; border-bottom: 1px solid var(--border); flex-shrink: 0; }
.page-title { margin: 0; font-size: 18px; font-weight: 600; color: var(--text-primary); }
.toolbar-actions { display: flex; gap: 10px; align-items: center; }
.tool-btn { display: flex; align-items: center; gap: 8px; padding: 8px 16px; border-radius: 10px; border: 1px solid var(--border-strong); background: var(--border-subtle); color: var(--text-secondary); font-size: 13px; font-weight: 500; cursor: pointer; transition: background 0.2s ease, border-color 0.2s ease, color 0.2s ease; }
.tool-btn:hover { background: var(--accent-bg-strong); border-color: var(--accent-border); color: var(--accent); }
.refresh-btn:hover { background: var(--accent-bg-strong); border-color: var(--accent-border); color: var(--accent); }
.export-btn { border-color: rgba(100,210,255,0.3); background: rgba(100,210,255,0.08); color: #64d2ff; }
.export-btn:hover { background: rgba(100,210,255,0.18); border-color: rgba(100,210,255,0.5); color: #64d2ff; }
.delete-all-btn { border-color: rgba(255,69,58,0.3); background: rgba(255,69,58,0.08); color: var(--error); }
.delete-all-btn:hover { background: rgba(255,69,58,0.18); border-color: rgba(255,69,58,0.5); color: var(--error); }
.add-btn { border-color: rgba(52,199,89,0.3); background: rgba(52,199,89,0.08); color: var(--success); }
.add-btn:hover { background: rgba(52,199,89,0.18); border-color: rgba(52,199,89,0.5); color: var(--success); }
.tool-icon { width: 16px; height: 16px; flex-shrink: 0; }

/* ============ 内容区 ============ */
.page-body { flex: 1; padding: 24px 32px; overflow-y: auto; position: relative; transition: background 0.2s ease; }
.page-body.drag-active { background: var(--accent-bg-subtle); }

/* ============ 拖拽 ============ */
.drag-overlay { position: absolute; inset: 16px; z-index: 10; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; border-radius: 16px; border: 2px dashed var(--accent-focus); background: var(--accent-bg); pointer-events: none; }
.drag-icon { width: 48px; height: 48px; color: rgba(200,96,122,0.7); }
.drag-text { margin: 0; font-size: 16px; font-weight: 500; color: rgba(200,96,122,0.8); }

/* ============ 空状态 ============ */
.empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 80px 20px; }
.empty-icon { width: 64px; height: 64px; color: var(--border-strong); margin-bottom: 20px; }
.empty-text { margin: 0; font-size: 16px; font-weight: 500; color: var(--text-placeholder); }
.empty-hint { margin: 8px 0 0; font-size: 13px; color: var(--text-hint); }

/* ============ 列表 ============ */
.list-wrap { border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }
.list-header, .list-row { display: flex; align-items: center; }
.list-header { background: var(--bg-surface); padding: 10px 16px; border-bottom: 1px solid var(--border); }
.list-header .col { font-size: 12px; font-weight: 600; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.5px; }
.list-row { padding: 12px 16px; border-bottom: 1px solid var(--border-light); transition: background 0.15s ease; }
.list-row:last-child { border-bottom: none; }
.list-row:hover { background: var(--border-subtle); }

.col-index { width: 40px; flex-shrink: 0; text-align: center; }
.col-origin { width: 72px; flex-shrink: 0; }
.col-prompt { flex: 1; min-width: 0; padding: 0 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; color: var(--text-secondary); }
.col-prompt.copyable { cursor: pointer; transition: color 0.15s ease; }
.col-prompt.copyable:hover { color: var(--accent); }
.col-params { width: 130px; flex-shrink: 0; display: flex; gap: 4px; flex-wrap: wrap; justify-content: center; }
.col-status { width: 100px; flex-shrink: 0; text-align: center; }
.col-result { width: 72px; flex-shrink: 0; }
.col-actions { width: 200px; flex-shrink: 0; display: flex; justify-content: center; gap: 6px; }

.thumb { width: 56px; height: 56px; border-radius: 8px; overflow: hidden; background: var(--bg-surface); border: 1px solid var(--border); }
.thumb img { width: 100%; height: 100%; object-fit: cover; display: block; }
.thumb.clickable { cursor: pointer; transition: opacity 0.15s ease; }
.thumb.clickable:hover { opacity: 0.8; }
.no-result { font-size: 13px; color: var(--text-hint); display: flex; width: 56px; height: 56px; align-items: center; justify-content: center; }
.label-text { font-size: 11px; color: var(--text-dim); text-align: center; line-height: 1.3; }

/* 参数标签 */
.param-tag { display: inline-block; padding: 2px 8px; border-radius: 5px; font-size: 11px; font-weight: 500; background: var(--border-subtle); color: var(--text-tertiary); border: 1px solid var(--border); }
.param-tag.quality { background: var(--accent-bg-subtle); color: var(--accent); border-color: rgba(200,96,122,0.2); }

/* 状态标签 */
.status-tag { display: inline-block; padding: 3px 10px; border-radius: 6px; font-size: 11px; font-weight: 600; max-width: 96px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.status-tag.pending { background: rgba(255,214,10,0.1); color: #ffd60a; }
.status-tag.processing { background: var(--accent-bg); color: var(--accent); }
.status-tag.completed { background: var(--success-bg); color: var(--success); }
.status-tag.failed { background: var(--error-bg); color: var(--error); }

/* 操作按钮 */
.action-btn { width: 34px; height: 34px; padding: 0; display: flex; align-items: center; justify-content: center; border-radius: 8px; border: 1px solid var(--border-medium); background: var(--border-light); color: var(--text-tertiary); cursor: pointer; transition: all 0.15s ease; }
.action-btn:disabled { opacity: 0.35; cursor: not-allowed; }
.action-btn svg { width: 15px; height: 15px; }
.view-btn:hover { background: var(--accent-bg-strong); border-color: rgba(200,96,122,0.4); color: var(--accent); }
.download-btn:hover { background: rgba(52,199,89,0.15); border-color: rgba(52,199,89,0.4); color: var(--success); }
.video-btn:hover:not(:disabled) { background: var(--accent-bg-strong); border-color: rgba(200,96,122,0.4); color: var(--accent); }
.retry-btn:hover { background: rgba(255,214,10,0.15); border-color: rgba(255,214,10,0.4); color: #ffd60a; }
.delete-btn:hover:not(:disabled) { background: rgba(255,69,58,0.15); border-color: rgba(255,69,58,0.4); color: var(--error); }

/* ============ 弹窗 ============ */
.dialog-overlay { position: fixed; inset: 0; z-index: 1000; display: flex; align-items: center; justify-content: center; background: rgba(0,0,0,0.6); backdrop-filter: blur(4px); }
.dialog { width: min(560px, calc(100% - 40px)); max-height: 90vh; border-radius: 16px; background: var(--bg-card); border: 1px solid var(--border-medium); box-shadow: var(--shadow-dialog); overflow: hidden; display: flex; flex-direction: column; }
.dialog-header { display: flex; align-items: center; justify-content: space-between; padding: 18px 24px; border-bottom: 1px solid var(--border); flex-shrink: 0; }
.dialog-title { margin: 0; font-size: 16px; font-weight: 600; color: var(--text-primary); }
.dialog-close { display: flex; align-items: center; justify-content: center; width: 32px; height: 32px; padding: 0; border-radius: 8px; border: none; background: transparent; color: var(--text-muted); cursor: pointer; transition: background 0.15s ease, color 0.15s ease; }
.dialog-close:hover { background: var(--border-medium); color: var(--text-primary); }
.dialog-close svg { width: 18px; height: 18px; }
.dialog-body { padding: 24px; overflow-y: auto; flex: 1; }
.dialog-footer { display: flex; justify-content: flex-end; gap: 12px; padding: 16px 24px; border-top: 1px solid var(--border); flex-shrink: 0; }
.cancel-btn { padding: 10px 20px; border-radius: 10px; border: 1px solid var(--border-strong); background: var(--border-subtle); color: var(--text-secondary); font-size: 13px; font-weight: 500; cursor: pointer; transition: background 0.2s ease, color 0.2s ease; }
.cancel-btn:hover { background: var(--border-strong); color: var(--text-primary); }
.save-btn { width: auto; padding: 10px 24px; font-size: 13px; }
.save-btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none !important; box-shadow: none !important; }

.field { display: flex; flex-direction: column; gap: 8px; }
.field-label { font-size: 13px; color: var(--text-tertiary); }

.dialog-body textarea { width: 100%; padding: 12px 14px; border-radius: 12px; border: 1px solid var(--border-medium); background: var(--bg-surface); color: var(--text-primary); font-size: 14px; font-family: inherit; outline: none; resize: vertical; transition: border-color 0.2s ease, box-shadow 0.2s ease; }
.dialog-body textarea::placeholder { color: var(--text-placeholder); }
.dialog-body textarea:focus { border-color: rgba(200,96,122,0.6); box-shadow: 0 0 0 3px var(--accent-bg-strong); }

/* 参数行 */
.params-row { display: flex; gap: 20px; margin-top: 16px; }
.param-field { flex: 1; }
.seg-group { display: flex; gap: 6px; flex-wrap: wrap; }
.seg-btn { padding: 6px 12px; border-radius: 8px; border: 1px solid var(--border-strong); background: var(--bg-surface); color: var(--text-tertiary); font-size: 12px; font-weight: 500; cursor: pointer; transition: all 0.15s ease; }
.seg-btn:hover { border-color: var(--accent-border); color: var(--text-secondary); }
.seg-btn.active { background: var(--accent-bg-strong); border-color: var(--accent); color: var(--accent); font-weight: 600; }

/* 上传区 */
.upload-area { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; padding: 24px 20px; border-radius: 12px; border: 2px dashed var(--border-strong); background: var(--bg-surface); cursor: pointer; transition: border-color 0.2s ease, background 0.2s ease; }
.upload-area:hover, .upload-area.drag-active { border-color: rgba(200,96,122,0.4); background: var(--accent-bg-subtle); }
.upload-input { display: none; }
.upload-icon { width: 28px; height: 28px; color: var(--text-hint); }
.upload-text { font-size: 13px; color: var(--text-tertiary); }
.upload-hint { font-size: 11px; color: var(--text-hint); }

/* 多图网格 */
.ref-images-grid { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }
.ref-image-preview { position: relative; display: inline-block; border-radius: 12px; overflow: hidden; border: 1px solid var(--border-medium); background: var(--bg-surface); }
.ref-images-grid .ref-image-preview img { width: 100px; height: 100px; object-fit: cover; display: block; }
.ref-image-preview img { display: block; max-width: 100%; max-height: 180px; object-fit: contain; }

/* 列表多图缩略 */
.thumb-group { display: flex; gap: 3px; align-items: center; }
.thumb.mini { width: 36px; height: 36px; border-radius: 6px; }
.thumb-more { font-size: 11px; color: var(--text-hint); margin-left: 2px; }
.remove-btn { position: absolute; top: 8px; right: 8px; width: 28px; height: 28px; padding: 0; display: flex; align-items: center; justify-content: center; border-radius: 8px; border: none; background: rgba(0,0,0,0.7); color: rgba(255,255,255,0.9); cursor: pointer; transition: background 0.2s ease; }
.remove-btn:hover { background: rgba(255,69,58,0.8); }
.remove-btn svg { width: 14px; height: 14px; }

/* ============ 图片预览 ============ */
.preview-overlay { position: fixed; inset: 0; z-index: 2000; display: flex; align-items: center; justify-content: center; background: rgba(0,0,0,0.85); backdrop-filter: blur(8px); cursor: zoom-out; }
.preview-close { position: absolute; top: 20px; right: 20px; width: 40px; height: 40px; padding: 0; display: flex; align-items: center; justify-content: center; border-radius: 10px; border: none; background: rgba(255,255,255,0.15); color: rgba(255,255,255,0.9); cursor: pointer; transition: background 0.15s ease; z-index: 1; }
.preview-close:hover { background: rgba(255,255,255,0.25); }
.preview-close svg { width: 20px; height: 20px; }
.preview-img { max-width: 90vw; max-height: 90vh; object-fit: contain; border-radius: 8px; cursor: default; }
</style>
