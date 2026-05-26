<script setup>
import { computed, reactive, ref, onMounted } from 'vue'

const emit = defineEmits(['toast'])
const props = defineProps({
  mode: {
    type: String,
    default: 'text',
  },
})

const defaultVideoPrompt = ref('')
const showPromptDialog = ref(false)
const promptDialogText = ref('')
const activeMode = computed(() => {
  return ['text', 'components'].includes(props.mode) ? props.mode : 'text'
})
const modeLabelMap = {
  text: '文生视频',
  components: '多参考视频',
}
const getModeLabel = (mode) => modeLabelMap[mode] || '视频任务'

const openPromptDialog = () => {
  promptDialogText.value = defaultVideoPrompt.value
  showPromptDialog.value = true
}
const closePromptDialog = () => { showPromptDialog.value = false }
const savePromptDialog = async () => {
  const text = promptDialogText.value.trim()
  if (!text) { emit('toast', '提示词不能为空', 'error'); return }
  try {
    await window.pywebview.api.set_video_process_prompt(text)
    defaultVideoPrompt.value = text
    emit('toast', '提示词已保存', 'success')
    showPromptDialog.value = false
  } catch {
    emit('toast', '保存失败', 'error')
  }
}

onMounted(async () => {
  try {
    const [vidRes, settings] = await Promise.all([
      window.pywebview.api.get_video_process_prompt(),
      window.pywebview.api.get_all_settings(),
    ])
    if (vidRes.ok) defaultVideoPrompt.value = vidRes.prompt
    if (settings.omni_orientation) {
      dialogVideoOrientation.value = settings.omni_orientation
      batchVideoOrientation.value = settings.omni_orientation
    }
    if (settings.omni_resolution) {
      dialogResolution.value = settings.omni_resolution
      batchResolution.value = settings.omni_resolution
    }
  } catch { /* ignore */ }
})

const taskList = ref([])
let taskIdCounter = 0
let videoQueueLimit = 3
let activeVideoCount = 0
const videoQueue = []

const showDialog = ref(false)
const dialogImages = ref([])
const dialogVideoPrompt = ref('')
const dialogVideoOrientation = ref('portrait')
const dialogDuration = ref(10)
const dialogResolution = ref('720P')
const dialogGenerationMode = ref('components')
const dialogCount = ref(1)
const dialogIsDragging = ref(false)
const dialogFileInput = ref(null)

const showBatchDialog = ref(false)
const batchImages = ref([])
const batchVideoPrompt = ref('')
const batchVideoOrientation = ref('portrait')
const batchDuration = ref(10)
const batchResolution = ref('720P')
const pageDragging = ref(false)

const showEditDialog = ref(false)
const editingTask = ref(null)
const editVideoPrompt = ref('')
const editVideoOrientation = ref('portrait')
const editDuration = ref(10)
const editResolution = ref('720P')
const editGenerationMode = ref('components')

const previewType = ref('')
const previewSrc = ref('')
const showPreview = ref(false)

const visibleTaskList = computed(() => taskList.value.filter(t => t.generationMode === activeMode.value))
const stats = computed(() => {
  const tasks = visibleTaskList.value
  const total = tasks.length
  const completed = tasks.filter(t => t.status === 'completed').length
  const processing = tasks.filter(t => ['video_queued', 'video_processing'].includes(t.status)).length
  const failed = tasks.filter(t => t.status === 'failed').length
  return { total, completed, processing, failed }
})

const isTaskBusy = (task) => ['video_queued', 'video_processing'].includes(task.status)

const resolveVideoConcurrency = async () => {
  let concurrency = 3
  try {
    const settings = await window.pywebview.api.get_all_settings()
    concurrency = parseInt(settings.thread_pool_size || '3', 10)
    if (concurrency < 1) concurrency = 1
    if (concurrency > 50) concurrency = 50
  } catch { /* ignore */ }
  videoQueueLimit = concurrency
  return concurrency
}

const pumpVideoQueue = () => {
  while (activeVideoCount < videoQueueLimit && videoQueue.length) {
    const task = videoQueue.shift()
    if (!task || task.status !== 'video_queued') continue
    activeVideoCount++
    generateVideo(task).finally(() => {
      activeVideoCount--
      pumpVideoQueue()
    })
  }
}

const enqueueVideoGeneration = async (task) => {
  if (!task || isTaskBusy(task)) return false
  await resolveVideoConcurrency()
  task.status = 'video_queued'
  task.statusText = '视频排队中...'
  videoQueue.push(task)
  pumpVideoQueue()
  return true
}

const readImageFile = (file, showToast = true) => {
  return new Promise((resolve) => {
    if (!file?.type?.startsWith('image/')) {
      if (showToast) emit('toast', '请选择图片文件', 'error')
      resolve(null)
      return
    }
    if (file.size > 10 * 1024 * 1024) {
      if (showToast) emit('toast', '图片不能超过 10MB', 'error')
      resolve(null)
      return
    }
    const reader = new FileReader()
    reader.onload = (e) => {
      resolve({
        preview: e.target.result,
        base64: e.target.result.split(',')[1],
        mime: file.type,
      })
    }
    reader.onerror = () => resolve(null)
    reader.readAsDataURL(file)
  })
}

const handleDialogImage = async (file) => {
  if (dialogImages.value.length >= 3) {
    emit('toast', 'Omni 最多支持 3 张参考图', 'error')
    return
  }
  const image = await readImageFile(file)
  if (image) dialogImages.value.push(image)
}
const handleDialogFileSelect = (event) => {
  const files = Array.from(event.target.files || [])
  files.forEach(f => handleDialogImage(f))
  if (dialogFileInput.value) dialogFileInput.value.value = ''
}
const onDragEnter = (e) => { e.preventDefault(); dialogIsDragging.value = true }
const onDragOver = (e) => { e.preventDefault(); dialogIsDragging.value = true }
const onDragLeave = (e) => {
  e.preventDefault()
  if (e.currentTarget.contains(e.relatedTarget)) return
  dialogIsDragging.value = false
}
const onDrop = (e) => {
  e.preventDefault()
  dialogIsDragging.value = false
  const files = Array.from(e.dataTransfer?.files || [])
  files.forEach(f => handleDialogImage(f))
}
const removeDialogImage = (idx) => { dialogImages.value.splice(idx, 1) }

const openAddDialog = () => {
  dialogImages.value = []
  dialogVideoPrompt.value = defaultVideoPrompt.value
  dialogVideoOrientation.value = dialogVideoOrientation.value || 'portrait'
  dialogDuration.value = 10
  dialogResolution.value = dialogResolution.value || '720P'
  dialogGenerationMode.value = activeMode.value
  dialogCount.value = 1
  showDialog.value = true
}
const closeDialog = () => { showDialog.value = false }

const onPageDragEnter = (e) => { e.preventDefault(); pageDragging.value = true }
const onPageDragOver = (e) => { e.preventDefault(); pageDragging.value = true }
const onPageDragLeave = (e) => {
  e.preventDefault()
  if (e.currentTarget.contains(e.relatedTarget)) return
  pageDragging.value = false
}
const onPageDrop = async (e) => {
  e.preventDefault()
  pageDragging.value = false
  if (activeMode.value === 'text') {
    emit('toast', '文生视频不需要参考图，请点击添加任务', 'error')
    return
  }
  const files = Array.from(e.dataTransfer?.files || []).filter(f => f.type.startsWith('image/'))
  if (!files.length) return
  const images = (await Promise.all(files.map(file => readImageFile(file, false)))).filter(Boolean)
  if (!images.length) return
  openBatchDialog(images)
}

const openBatchDialog = (imgs) => {
  batchImages.value = imgs
  batchVideoPrompt.value = defaultVideoPrompt.value
  batchResolution.value = batchResolution.value || '720P'
  showBatchDialog.value = true
}
const closeBatchDialog = () => { showBatchDialog.value = false; batchImages.value = [] }
const removeBatchImage = (idx) => {
  batchImages.value.splice(idx, 1)
  if (!batchImages.value.length) closeBatchDialog()
}

const buildTask = (images, prompt, orientation, duration, resolution, generationMode) => reactive({
  id: ++taskIdCounter,
  images: images.map(img => ({ ...img })),
  videoPrompt: prompt.trim(),
  videoOrientation: orientation,
  duration,
  resolution,
  generationMode,
  videoUrl: '',
  filePath: '',
  status: 'pending',
  statusText: '待处理',
})

const submitDialog = () => {
  if (dialogGenerationMode.value === 'components' && !dialogImages.value.length) { emit('toast', '多参考视频请先选择图片', 'error'); return }
  if (dialogGenerationMode.value === 'components' && dialogImages.value.length > 3) { emit('toast', 'Omni 最多支持 3 张参考图', 'error'); return }
  if (!dialogVideoPrompt.value.trim()) { emit('toast', '请输入视频提示词', 'error'); return }

  defaultVideoPrompt.value = dialogVideoPrompt.value.trim()
  window.pywebview.api.set_video_process_prompt(defaultVideoPrompt.value).catch(() => {})
  window.pywebview.api.save_settings({
    omni_orientation: dialogVideoOrientation.value,
    omni_resolution: dialogResolution.value,
    omni_model: 'cloudy',
  }).catch(() => {})

  const images = dialogImages.value.map(img => ({ ...img }))
  const count = Math.max(1, Math.min(1000, dialogCount.value || 1))
  const tasks = []
  for (let i = 0; i < count; i++) {
    tasks.push(buildTask(
      images,
      defaultVideoPrompt.value,
      dialogVideoOrientation.value,
      dialogDuration.value,
      dialogResolution.value,
      dialogGenerationMode.value,
    ))
  }
  taskList.value.unshift(...tasks)
  showDialog.value = false
  emit('toast', `已添加 ${tasks.length} 条任务，开始生成...`, 'success')
  tasks.forEach(task => enqueueVideoGeneration(task))
}

const submitBatchDialog = () => {
  if (!batchImages.value.length) { emit('toast', '没有可用的图片', 'error'); return }
  if (!batchVideoPrompt.value.trim()) { emit('toast', '请输入视频提示词', 'error'); return }

  defaultVideoPrompt.value = batchVideoPrompt.value.trim()
  window.pywebview.api.set_video_process_prompt(defaultVideoPrompt.value).catch(() => {})
  window.pywebview.api.save_settings({
    omni_orientation: batchVideoOrientation.value,
    omni_resolution: batchResolution.value,
    omni_model: 'cloudy',
  }).catch(() => {})

  const tasks = batchImages.value.map(img => buildTask(
    [{ ...img }],
    defaultVideoPrompt.value,
    batchVideoOrientation.value,
    batchDuration.value,
    batchResolution.value,
    'components',
  ))
  taskList.value.unshift(...tasks)
  closeBatchDialog()
  emit('toast', `已添加 ${tasks.length} 条任务，开始生成...`, 'success')
  tasks.forEach(task => enqueueVideoGeneration(task))
}

const generateVideo = async (task) => {
  task.status = 'video_processing'
  task.statusText = '视频生成中...'
  task.videoUrl = ''
  task.filePath = ''

  let maxRetry = 0
  let provider = 'cloudy'
  try {
    const settings = await window.pywebview.api.get_all_settings()
    if (settings.auto_retry === 'true') {
      maxRetry = parseInt(settings.video_max_retry || '3', 10)
    }
    provider = 'cloudy'
  } catch { /* ignore */ }

  let attempts = 0
  let lastError = ''

  while (attempts <= maxRetry) {
    if (attempts > 0) task.statusText = `视频重试中 (${attempts}/${maxRetry})...`
    try {
      const refs = (task.images || []).map(img => ({ base64: img.base64, mime: img.mime }))
      const res = await window.pywebview.api.generate_media_video(
        task.videoPrompt,
        refs,
        task.videoOrientation,
        task.duration,
        'omni',
        provider,
        task.resolution || '720P',
        task.generationMode || 'components',
        '',
      )
      if (res.ok && res.video_url) {
        task.videoUrl = res.video_url
        task.filePath = res.file_path || ''
        task.status = 'completed'
        task.statusText = '已完成'
        if (task.filePath) {
          emit('toast', `视频已保存: ${task.filePath.split(/[\\/]/).pop()}`, 'success')
        }
        return true
      }
      lastError = res.msg || '视频生成失败'
    } catch (e) {
      lastError = String(e)
    }
    attempts++
  }

  task.status = 'failed'
  task.statusText = `视频失败: ${lastError}`
  return false
}

const regenVideo = (task) => {
  if (isTaskBusy(task)) return
  enqueueVideoGeneration(task)
}
const deleteTask = (task) => {
  if (isTaskBusy(task)) {
    emit('toast', '任务正在处理中，无法删除', 'error')
    return
  }
  const idx = taskList.value.findIndex(item => item.id === task.id)
  if (idx >= 0) taskList.value.splice(idx, 1)
}
const deleteAllTasks = () => {
  if (visibleTaskList.value.some(t => isTaskBusy(t))) {
    emit('toast', '有任务正在处理中，无法全部删除', 'error')
    return
  }
  taskList.value = taskList.value.filter(t => t.generationMode !== activeMode.value)
}
const downloadVideo = async (task, silent = false) => {
  if (!task.videoUrl) { if (!silent) emit('toast', '暂无视频链接', 'error'); return }
  try {
    if (!silent) emit('toast', '开始下载视频...', 'success')
    const res = await window.pywebview.api.download_omni_video(task.videoUrl)
    if (res.ok) { if (!silent) emit('toast', '视频已保存', 'success') }
    else { if (!silent) emit('toast', res.msg || '下载失败', 'error') }
  } catch {
    if (!silent) emit('toast', '下载异常', 'error')
  }
}
const exportAll = async () => {
  const paths = visibleTaskList.value.filter(t => t.filePath).map(t => t.filePath)
  if (!paths.length) { emit('toast', '暂无已下载的文件', 'error'); return }
  try {
    const res = await window.pywebview.api.batch_export_files(paths)
    if (res.ok) emit('toast', res.msg, 'success')
    else emit('toast', res.msg || '导出取消', 'error')
  } catch { emit('toast', '导出异常', 'error') }
}

const openImagePreview = (src) => { previewType.value = 'image'; previewSrc.value = src; showPreview.value = true }
const openVideoPreview = (url) => { previewType.value = 'video'; previewSrc.value = url; showPreview.value = true }
const closePreview = () => { showPreview.value = false; previewSrc.value = ''; previewType.value = '' }

const openEditDialog = (task) => {
  if (isTaskBusy(task)) return
  editingTask.value = task
  editVideoPrompt.value = task.videoPrompt
  editVideoOrientation.value = task.videoOrientation
  editDuration.value = task.duration
  editResolution.value = task.resolution || '720P'
  editGenerationMode.value = task.generationMode || 'components'
  showEditDialog.value = true
}
const closeEditDialog = () => { showEditDialog.value = false; editingTask.value = null }
const saveEditDialog = () => {
  if (!editVideoPrompt.value.trim()) { emit('toast', '请输入视频提示词', 'error'); return }
  const task = editingTask.value
  if (!task) return
  if (task.generationMode === 'components' && !(task.images || []).length) { emit('toast', '多参考视频需要参考图片', 'error'); return }
  task.videoPrompt = editVideoPrompt.value.trim()
  task.videoOrientation = editVideoOrientation.value
  task.duration = editDuration.value
  task.resolution = editResolution.value
  showEditDialog.value = false
  editingTask.value = null
  emit('toast', '任务参数已更新', 'success')
}

const statusClass = (status) => {
  if (status === 'pending') return 'pending'
  if (status === 'video_queued' || status === 'video_processing') return 'processing'
  if (status === 'completed') return 'completed'
  return 'failed'
}
</script>

<template>
  <div class="page">
    <div class="page-toolbar">
      <h2 class="page-title">Omni {{ getModeLabel(activeMode) }}</h2>
      <div class="toolbar-actions">
        <button class="tool-btn refresh-btn" @click="() => window.location.reload()">
          <svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
          </svg>
          <span>刷新</span>
        </button>
        <span v-if="stats.total > 0" class="stats-text">
          共 {{ stats.total }} 条
          <template v-if="stats.processing > 0"> · <span class="stats-processing">{{ stats.processing }} 处理中</span></template>
          <template v-if="stats.completed > 0"> · <span class="stats-completed">{{ stats.completed }} 完成</span></template>
          <template v-if="stats.failed > 0"> · <span class="stats-failed">{{ stats.failed }} 失败</span></template>
        </span>
        <button class="tool-btn prompt-btn" @click="openPromptDialog">
          <svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>
          </svg>
          <span>视频提示词</span>
        </button>
        <button v-if="visibleTaskList.some(t => t.filePath)" class="tool-btn export-btn" @click="exportAll">
          <svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          <span>一键下载</span>
        </button>
        <button v-if="visibleTaskList.length > 0" class="tool-btn delete-all-btn" @click="deleteAllTasks">
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

    <div
      class="page-body"
      :class="{ 'drag-active': pageDragging }"
      @dragenter="onPageDragEnter"
      @dragover="onPageDragOver"
      @dragleave="onPageDragLeave"
      @drop="onPageDrop"
    >
      <div v-if="pageDragging" class="drag-overlay">
        <svg class="drag-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
          <polyline points="17 8 12 3 7 8"/>
          <line x1="12" y1="3" x2="12" y2="15"/>
        </svg>
        <p class="drag-text">松开鼠标批量添加参考图</p>
        <p class="drag-hint">每张图片将创建一条独立任务</p>
      </div>

      <div v-if="visibleTaskList.length === 0 && !pageDragging" class="empty-state">
        <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
          <line x1="8" y1="21" x2="16" y2="21"/>
          <line x1="12" y1="17" x2="12" y2="21"/>
        </svg>
        <p class="empty-text">暂无{{ getModeLabel(activeMode) }}任务</p>
        <p class="empty-hint">点击"添加任务"创建{{ getModeLabel(activeMode) }}任务</p>
      </div>

      <div v-else-if="!pageDragging" class="list-wrap">
        <div class="list-header">
          <div class="col col-index">#</div>
          <div class="col col-origin">原图</div>
          <div class="col col-result">视频</div>
          <div class="col col-status">状态</div>
          <div class="col col-actions">操作</div>
        </div>
        <div
          v-for="(task, idx) in visibleTaskList"
          :key="task.id"
          class="list-row"
        >
          <div class="col col-index">{{ visibleTaskList.length - idx }}</div>
          <div class="col col-origin">
            <div v-if="task.images && task.images.length" class="thumb-group">
              <div
                v-for="(img, i) in task.images.slice(0, 3)" :key="i"
                class="thumb mini clickable"
                @click="openImagePreview(img.preview)"
              ><img :src="img.preview" alt="原图" /></div>
              <span v-if="task.images.length > 3" class="thumb-more">+{{ task.images.length - 3 }}</span>
            </div>
          </div>
          <div class="col col-result">
            <button v-if="task.videoUrl" class="video-pill" @click="openVideoPreview(task.videoUrl)">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polygon points="5 3 19 12 5 21 5 3"/>
              </svg>
              播放
            </button>
            <span v-else class="no-result">—</span>
          </div>
          <div class="col col-status">
            <span :class="['status-tag', statusClass(task.status)]">{{ task.statusText }}</span>
          </div>
          <div class="col col-actions">
            <button
              class="action-btn gen-vid-btn"
              @click="regenVideo(task)"
              :disabled="isTaskBusy(task)"
              title="视频重新生成"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>
              </svg>
            </button>
            <button
              v-if="task.videoUrl"
              class="action-btn download-vid-btn"
              @click="downloadVideo(task)"
              title="下载视频"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
              </svg>
            </button>
            <button
              v-if="task.videoUrl"
              class="action-btn view-btn"
              @click="openVideoPreview(task.videoUrl)"
              title="播放视频"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polygon points="5 3 19 12 5 21 5 3"/>
              </svg>
            </button>
            <button
              class="action-btn edit-btn"
              @click="openEditDialog(task)"
              :disabled="isTaskBusy(task)"
              title="编辑参数"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
              </svg>
            </button>
            <button
              class="action-btn delete-btn"
              @click="deleteTask(task)"
              :disabled="isTaskBusy(task)"
              title="删除"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>

    <Teleport to="body">
      <div v-if="showBatchDialog" class="dialog-overlay" @click.self="closeBatchDialog">
        <div class="dialog dialog--image">
          <div class="dialog-header">
            <h3 class="dialog-title">批量添加{{ getModeLabel(activeMode) }}任务（{{ batchImages.length }} 张图 = {{ batchImages.length }} 条任务）</h3>
            <button class="dialog-close" @click="closeBatchDialog">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>
          <div class="dialog-body dialog-body--split">
            <div class="dialog-left">
              <div class="field">
                <span class="field-label">参考图片（每张图片 = 一条任务）</span>
                <div class="ref-images-grid" v-if="batchImages.length">
                  <div v-for="(img, idx) in batchImages" :key="idx" class="ref-image-preview">
                    <img :src="img.preview" alt="商品图片" />
                    <button class="remove-btn" @click="removeBatchImage(idx)" title="移除">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                    </button>
                  </div>
                </div>
              </div>
            </div>
            <div class="dialog-right">
              <div class="field">
                <span class="field-label">视频提示词（必填）</span>
                <textarea v-model="batchVideoPrompt" placeholder="描述视频生成效果" rows="4"></textarea>
              </div>
              <div class="form-row">
                <div class="field field-inline">
                  <span class="field-label">视频方向</span>
                  <div class="toggle-group">
                    <button :class="['toggle-btn', { active: batchVideoOrientation === 'portrait' }]" @click="batchVideoOrientation = 'portrait'">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="toggle-icon"><rect x="5" y="2" width="14" height="20" rx="2"/></svg>
                      竖屏
                    </button>
                    <button :class="['toggle-btn', { active: batchVideoOrientation === 'landscape' }]" @click="batchVideoOrientation = 'landscape'">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="toggle-icon"><rect x="2" y="5" width="20" height="14" rx="2"/></svg>
                      横屏
                    </button>
                  </div>
                </div>
              </div>
              <div class="form-row">
                <div class="field field-inline">
                  <span class="field-label">视频时长</span>
                  <div class="toggle-group">
                    <button :class="['toggle-btn', { active: batchDuration === 4 }]" @click="batchDuration = 4">4 秒</button>
                    <button :class="['toggle-btn', { active: batchDuration === 6 }]" @click="batchDuration = 6">6 秒</button>
                    <button :class="['toggle-btn', { active: batchDuration === 8 }]" @click="batchDuration = 8">8 秒</button>
                    <button :class="['toggle-btn', { active: batchDuration === 10 }]" @click="batchDuration = 10">10 秒</button>
                  </div>
                </div>
              </div>
              <div class="form-row">
                <div class="field field-inline">
                  <span class="field-label">分辨率</span>
                  <div class="toggle-group">
                    <button :class="['toggle-btn', { active: batchResolution === '720P' }]" @click="batchResolution = '720P'">720P</button>
                    <button :class="['toggle-btn', { active: batchResolution === '1080P' }]" @click="batchResolution = '1080P'">1080P</button>
                    <button :class="['toggle-btn', { active: batchResolution === '4K' }]" @click="batchResolution = '4K'">4K</button>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div class="dialog-footer">
            <button class="cancel-btn" @click="closeBatchDialog">取消</button>
            <button class="primary-btn save-btn" @click="submitBatchDialog">添加 {{ batchImages.length }} 条{{ getModeLabel(activeMode) }}任务并开始生成</button>
          </div>
        </div>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="showDialog" class="dialog-overlay" @click.self="closeDialog">
        <div class="dialog dialog--image">
          <div class="dialog-header">
            <h3 class="dialog-title">添加{{ getModeLabel(dialogGenerationMode) }}任务</h3>
            <button class="dialog-close" @click="closeDialog">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>
          <div class="dialog-body dialog-body--split">
            <div class="dialog-left">
              <div v-if="dialogGenerationMode !== 'text'" class="field">
                <span class="field-label">参考图片（必填 1 至 3 张）</span>
                <div class="ref-images-grid" v-if="dialogImages.length">
                  <div v-for="(img, idx) in dialogImages" :key="idx" class="ref-image-preview">
                    <img :src="img.preview" alt="商品图片" />
                    <button class="remove-btn" @click="removeDialogImage(idx)" title="移除">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                    </button>
                  </div>
                </div>
                <div
                  class="upload-area"
                  :class="{ 'drag-active': dialogIsDragging }"
                  @click="dialogFileInput?.click()"
                  @dragenter="onDragEnter"
                  @dragover="onDragOver"
                  @dragleave="onDragLeave"
                  @drop="onDrop"
                >
                  <input ref="dialogFileInput" type="file" accept="image/*" multiple class="upload-input" @change="handleDialogFileSelect" />
                  <svg class="upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
                  </svg>
                  <span class="upload-text">{{ dialogImages.length ? '继续添加图片' : '点击或拖拽图片到此处' }}</span>
                  <span class="upload-hint">支持 JPG / PNG / WebP，最多 3 张，最大 10MB</span>
                </div>
              </div>
            </div>

            <div class="dialog-right">
              <div class="field">
                <span class="field-label">视频提示词（必填）</span>
                <textarea v-model="dialogVideoPrompt" placeholder="描述视频生成效果" rows="4"></textarea>
              </div>
              <div class="form-row">
                <div class="field field-inline" style="flex: 0 0 auto;">
                  <span class="field-label">数量</span>
                  <input v-model.number="dialogCount" type="number" min="1" max="1000" class="count-input" />
                </div>
              </div>
              <div class="form-row">
                <div class="field field-inline">
                  <span class="field-label">视频方向</span>
                  <div class="toggle-group">
                    <button :class="['toggle-btn', { active: dialogVideoOrientation === 'portrait' }]" @click="dialogVideoOrientation = 'portrait'">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="toggle-icon"><rect x="5" y="2" width="14" height="20" rx="2"/></svg>
                      竖屏
                    </button>
                    <button :class="['toggle-btn', { active: dialogVideoOrientation === 'landscape' }]" @click="dialogVideoOrientation = 'landscape'">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="toggle-icon"><rect x="2" y="5" width="20" height="14" rx="2"/></svg>
                      横屏
                    </button>
                  </div>
                </div>
              </div>
              <div class="form-row">
                <div class="field field-inline">
                  <span class="field-label">视频时长</span>
                  <div class="toggle-group">
                    <button :class="['toggle-btn', { active: dialogDuration === 4 }]" @click="dialogDuration = 4">4 秒</button>
                    <button :class="['toggle-btn', { active: dialogDuration === 6 }]" @click="dialogDuration = 6">6 秒</button>
                    <button :class="['toggle-btn', { active: dialogDuration === 8 }]" @click="dialogDuration = 8">8 秒</button>
                    <button :class="['toggle-btn', { active: dialogDuration === 10 }]" @click="dialogDuration = 10">10 秒</button>
                  </div>
                </div>
              </div>
              <div class="form-row">
                <div class="field field-inline">
                  <span class="field-label">分辨率</span>
                  <div class="toggle-group">
                    <button :class="['toggle-btn', { active: dialogResolution === '720P' }]" @click="dialogResolution = '720P'">720P</button>
                    <button :class="['toggle-btn', { active: dialogResolution === '1080P' }]" @click="dialogResolution = '1080P'">1080P</button>
                    <button :class="['toggle-btn', { active: dialogResolution === '4K' }]" @click="dialogResolution = '4K'">4K</button>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div class="dialog-footer">
            <button class="cancel-btn" @click="closeDialog">取消</button>
            <button class="primary-btn save-btn" @click="submitDialog">
              {{ `添加 ${Math.max(1, dialogCount || 1)} 条任务并开始生成` }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="showEditDialog" class="dialog-overlay" @click.self="closeEditDialog">
        <div class="dialog dialog--prompt">
          <div class="dialog-header">
            <h3 class="dialog-title">编辑任务参数</h3>
            <button class="dialog-close" @click="closeEditDialog">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>
          <div class="dialog-body">
            <div class="field">
              <span class="field-label">视频提示词</span>
              <textarea v-model="editVideoPrompt" placeholder="描述视频生成效果" rows="4"></textarea>
            </div>
            <div class="form-row">
              <div class="field field-inline">
                <span class="field-label">生成方式</span>
                <div class="readonly-mode">{{ getModeLabel(editGenerationMode) }}</div>
              </div>
            </div>
            <div class="form-row">
              <div class="field field-inline">
                <span class="field-label">视频方向</span>
                <div class="toggle-group">
                  <button :class="['toggle-btn', { active: editVideoOrientation === 'portrait' }]" @click="editVideoOrientation = 'portrait'">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="toggle-icon"><rect x="5" y="2" width="14" height="20" rx="2"/></svg>
                    竖屏
                  </button>
                  <button :class="['toggle-btn', { active: editVideoOrientation === 'landscape' }]" @click="editVideoOrientation = 'landscape'">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="toggle-icon"><rect x="2" y="5" width="20" height="14" rx="2"/></svg>
                    横屏
                  </button>
                </div>
              </div>
            </div>
            <div class="form-row">
              <div class="field field-inline">
                <span class="field-label">视频时长</span>
                <div class="toggle-group">
                  <button :class="['toggle-btn', { active: editDuration === 4 }]" @click="editDuration = 4">4 秒</button>
                  <button :class="['toggle-btn', { active: editDuration === 6 }]" @click="editDuration = 6">6 秒</button>
                  <button :class="['toggle-btn', { active: editDuration === 8 }]" @click="editDuration = 8">8 秒</button>
                  <button :class="['toggle-btn', { active: editDuration === 10 }]" @click="editDuration = 10">10 秒</button>
                </div>
              </div>
            </div>
            <div class="form-row">
              <div class="field field-inline">
                <span class="field-label">分辨率</span>
                <div class="toggle-group">
                  <button :class="['toggle-btn', { active: editResolution === '720P' }]" @click="editResolution = '720P'">720P</button>
                  <button :class="['toggle-btn', { active: editResolution === '1080P' }]" @click="editResolution = '1080P'">1080P</button>
                  <button :class="['toggle-btn', { active: editResolution === '4K' }]" @click="editResolution = '4K'">4K</button>
                </div>
              </div>
            </div>
          </div>
          <div class="dialog-footer">
            <button class="cancel-btn" @click="closeEditDialog">取消</button>
            <button class="primary-btn save-btn" @click="saveEditDialog">保存</button>
          </div>
        </div>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="showPromptDialog" class="dialog-overlay" @click.self="closePromptDialog">
        <div class="dialog dialog--prompt">
          <div class="dialog-header">
            <h3 class="dialog-title">视频提示词</h3>
            <button class="dialog-close" @click="closePromptDialog">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>
          <div class="dialog-body">
            <label class="field">
              <span class="field-label">所有任务的视频生成提示词</span>
              <textarea v-model="promptDialogText" placeholder="描述视频生成效果" rows="6"></textarea>
            </label>
          </div>
          <div class="dialog-footer">
            <button class="cancel-btn" @click="closePromptDialog">取消</button>
            <button class="primary-btn save-btn" @click="savePromptDialog">保存</button>
          </div>
        </div>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="showPreview" class="preview-overlay" @click="closePreview">
        <button class="preview-close" @click="closePreview">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
        <img v-if="previewType === 'image'" :src="previewSrc" class="preview-img" @click.stop alt="预览" />
        <video v-else-if="previewType === 'video'" :src="previewSrc" class="preview-video" controls autoplay @click.stop />
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.page { position: relative; min-height: 100%; display: flex; flex-direction: column; }
.page-toolbar { display: flex; align-items: center; justify-content: space-between; padding: 20px 32px; border-bottom: 1px solid var(--border); flex-shrink: 0; }
.page-title { margin: 0; font-size: 18px; font-weight: 600; color: var(--text-primary); }
.toolbar-actions { display: flex; gap: 10px; align-items: center; }
.stats-text { font-size: 13px; color: var(--text-dim); margin-right: 8px; }
.stats-processing { color: var(--accent); }
.stats-completed { color: var(--success); }
.stats-failed { color: var(--error); }
.tool-btn { display: flex; align-items: center; gap: 8px; padding: 8px 16px; border-radius: 10px; border: 1px solid var(--border-strong); background: var(--border-subtle); color: var(--text-secondary); font-size: 13px; font-weight: 500; cursor: pointer; transition: background 0.2s ease, border-color 0.2s ease, color 0.2s ease; }
.tool-btn:hover { background: var(--accent-bg-strong); border-color: var(--accent-border); color: var(--accent); }
.add-btn { border-color: rgba(52,199,89,0.3); background: rgba(52,199,89,0.08); color: var(--success); }
.add-btn:hover { background: rgba(52,199,89,0.18); border-color: rgba(52,199,89,0.5); color: var(--success); }
.prompt-btn { border-color: rgba(100,210,255,0.3); background: rgba(100,210,255,0.08); color: #64d2ff; }
.prompt-btn:hover { background: rgba(100,210,255,0.18); border-color: rgba(100,210,255,0.5); color: #64d2ff; }
.export-btn { border-color: rgba(100,210,255,0.3); background: rgba(100,210,255,0.08); color: #64d2ff; }
.export-btn:hover { background: rgba(100,210,255,0.18); border-color: rgba(100,210,255,0.5); color: #64d2ff; }
.delete-all-btn { border-color: rgba(255,69,58,0.3); background: rgba(255,69,58,0.08); color: var(--error); }
.delete-all-btn:hover { background: rgba(255,69,58,0.18); border-color: rgba(255,69,58,0.5); color: var(--error); }
.tool-icon { width: 16px; height: 16px; flex-shrink: 0; }

.page-body { flex: 1; padding: 24px 32px; overflow-y: auto; position: relative; transition: background 0.2s ease; }
.page-body.drag-active { background: var(--accent-bg-subtle); }
.drag-overlay { position: absolute; inset: 16px; z-index: 10; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; border-radius: 16px; border: 2px dashed var(--accent-focus); background: var(--accent-bg); pointer-events: none; }
.drag-icon { width: 48px; height: 48px; color: rgba(200,96,122,0.7); }
.drag-text { margin: 0; font-size: 16px; font-weight: 500; color: rgba(200,96,122,0.8); }
.drag-hint { margin: 0; font-size: 12px; color: var(--text-hint); }

.empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 80px 20px; }
.empty-icon { width: 64px; height: 64px; color: var(--border-strong); margin-bottom: 20px; }
.empty-text { margin: 0; font-size: 16px; font-weight: 500; color: var(--text-placeholder); }
.empty-hint { margin: 8px 0 0; font-size: 13px; color: var(--text-hint); }

.list-wrap { border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }
.list-header, .list-row { display: flex; align-items: center; }
.list-header { background: var(--bg-surface); padding: 10px 16px; border-bottom: 1px solid var(--border); }
.list-header .col { font-size: 12px; font-weight: 600; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.5px; }
.list-row { padding: 12px 16px; border-bottom: 1px solid var(--border-light); transition: background 0.15s ease; }
.list-row:last-child { border-bottom: none; }
.list-row:hover { background: var(--border-subtle); }
.col-index { width: 40px; flex-shrink: 0; text-align: center; }
.col-origin { width: 120px; flex-shrink: 0; }
.col-result { width: 90px; flex-shrink: 0; }
.col-status { flex: 1; min-width: 0; padding: 0 12px; }
.col-actions { width: 240px; flex-shrink: 0; display: flex; justify-content: center; gap: 5px; flex-wrap: wrap; }
.thumb { width: 56px; height: 56px; border-radius: 8px; overflow: hidden; background: var(--bg-surface); border: 1px solid var(--border); }
.thumb img { width: 100%; height: 100%; object-fit: cover; display: block; }
.thumb.clickable { cursor: pointer; transition: opacity 0.15s ease; }
.thumb.clickable:hover { opacity: 0.8; }
.no-result { font-size: 13px; color: var(--text-hint); display: flex; width: 56px; height: 56px; align-items: center; justify-content: center; }
.thumb-group { display: flex; gap: 3px; align-items: center; flex-wrap: wrap; }
.thumb.mini { width: 36px; height: 36px; border-radius: 6px; }
.thumb-more { font-size: 11px; color: var(--text-hint); margin-left: 2px; }
.video-pill { display: inline-flex; align-items: center; gap: 5px; height: 32px; padding: 0 10px; border-radius: 8px; border: 1px solid rgba(175,82,222,0.3); background: rgba(175,82,222,0.08); color: #bf5af2; cursor: pointer; font-size: 12px; }
.video-pill svg { width: 13px; height: 13px; }
.video-pill:hover { background: rgba(175,82,222,0.18); border-color: rgba(175,82,222,0.5); }

.status-tag { display: inline-block; padding: 3px 10px; border-radius: 6px; font-size: 11px; font-weight: 600; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.status-tag.pending { background: rgba(255,214,10,0.1); color: #ffd60a; }
.status-tag.processing { background: var(--accent-bg); color: var(--accent); }
.status-tag.completed { background: var(--success-bg); color: var(--success); }
.status-tag.failed { background: var(--error-bg); color: var(--error); }

.action-btn { width: 34px; height: 34px; padding: 0; display: flex; align-items: center; justify-content: center; border-radius: 8px; border: 1px solid var(--border-medium); background: var(--border-light); color: var(--text-tertiary); cursor: pointer; transition: all 0.15s ease; position: relative; }
.action-btn:disabled { opacity: 0.35; cursor: not-allowed; }
.action-btn svg { width: 15px; height: 15px; }
.gen-vid-btn:hover:not(:disabled) { background: rgba(175,82,222,0.15); border-color: rgba(175,82,222,0.4); color: #bf5af2; }
.download-vid-btn:hover:not(:disabled) { background: rgba(52,199,89,0.15); border-color: rgba(52,199,89,0.4); color: var(--success); }
.view-btn:hover:not(:disabled) { background: var(--accent-bg-strong); border-color: rgba(200,96,122,0.4); color: var(--accent); }
.edit-btn:hover:not(:disabled) { background: rgba(255,214,10,0.15); border-color: rgba(255,214,10,0.4); color: #ffd60a; }
.delete-btn:hover:not(:disabled) { background: rgba(255,69,58,0.15); border-color: rgba(255,69,58,0.4); color: var(--error); }

.dialog-overlay { position: fixed; inset: 0; z-index: 1000; display: flex; align-items: center; justify-content: center; background: rgba(0,0,0,0.6); backdrop-filter: blur(4px); }
.dialog { max-height: calc(100vh - 60px); border-radius: 16px; background: var(--bg-card); border: 1px solid var(--border-medium); box-shadow: var(--shadow-dialog); overflow: hidden; display: flex; flex-direction: column; }
.dialog--image { width: min(860px, calc(100% - 40px)); }
.dialog--prompt { width: min(520px, calc(100% - 40px)); }
.dialog-header { display: flex; align-items: center; justify-content: space-between; padding: 18px 24px; border-bottom: 1px solid var(--border); flex-shrink: 0; }
.dialog-title { margin: 0; font-size: 16px; font-weight: 600; color: var(--text-primary); }
.dialog-close { display: flex; align-items: center; justify-content: center; width: 32px; height: 32px; padding: 0; border-radius: 8px; border: none; background: transparent; color: var(--text-muted); cursor: pointer; transition: background 0.15s ease, color 0.15s ease; }
.dialog-close:hover { background: var(--border-medium); color: var(--text-primary); }
.dialog-close svg { width: 18px; height: 18px; }
.dialog-body { padding: 24px; overflow-y: auto; flex: 1; }
.dialog-body--split { display: flex; gap: 24px; }
.dialog-left { width: 280px; flex-shrink: 0; display: flex; flex-direction: column; }
.dialog-left .upload-area { min-height: 120px; }
.ref-images-grid { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }
.ref-images-grid .ref-image-preview img { width: 80px; height: 80px; object-fit: cover; display: block; }
.dialog-right { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.dialog-footer { display: flex; justify-content: flex-end; gap: 12px; padding: 16px 24px; border-top: 1px solid var(--border); flex-shrink: 0; }
.cancel-btn { padding: 10px 20px; border-radius: 10px; border: 1px solid var(--border-strong); background: var(--border-subtle); color: var(--text-secondary); font-size: 13px; font-weight: 500; cursor: pointer; transition: background 0.2s ease, color 0.2s ease; }
.cancel-btn:hover { background: var(--border-strong); color: var(--text-primary); }
.save-btn { width: auto; padding: 10px 24px; font-size: 13px; }
.primary-btn { border: 1px solid var(--accent); background: var(--accent); color: var(--btn-text); border-radius: 10px; font-weight: 600; cursor: pointer; }

.field { display: flex; flex-direction: column; gap: 8px; }
.field-label { font-size: 13px; color: var(--text-tertiary); }
.dialog-body textarea { width: 100%; padding: 12px 14px; border-radius: 12px; border: 1px solid var(--border-medium); background: var(--bg-surface); color: var(--text-primary); font-size: 14px; font-family: inherit; outline: none; resize: vertical; transition: border-color 0.2s ease, box-shadow 0.2s ease; }
.dialog-body textarea::placeholder { color: var(--text-placeholder); }
.dialog-body textarea:focus { border-color: rgba(200,96,122,0.6); box-shadow: 0 0 0 3px var(--accent-bg-strong); }
.count-input { width: 90px; padding: 6px 10px; border-radius: 8px; border: 1px solid var(--border-medium); background: var(--bg-surface); color: var(--text-primary); font-size: 13px; font-family: inherit; outline: none; transition: border-color 0.2s ease, box-shadow 0.2s ease; -moz-appearance: textfield; }
.count-input::-webkit-outer-spin-button, .count-input::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
.count-input:focus { border-color: rgba(200,96,122,0.6); box-shadow: 0 0 0 3px var(--accent-bg-strong); }
.form-row { display: flex; gap: 24px; margin-top: 12px; align-items: flex-start; }
.field-inline { flex: 1; }
.toggle-group { display: flex; gap: 6px; flex-wrap: wrap; }
.toggle-btn { display: flex; align-items: center; gap: 5px; padding: 7px 14px; border-radius: 8px; border: 1px solid var(--border-strong); background: var(--border-light); color: var(--text-tertiary); font-size: 12px; font-weight: 500; cursor: pointer; transition: all 0.2s ease; }
.toggle-btn:hover { background: var(--accent-bg); border-color: rgba(200,96,122,0.2); color: var(--text-secondary); }
.toggle-btn.active { background: var(--accent-bg-strong); border-color: rgba(200,96,122,0.4); color: var(--accent); }
.toggle-icon { width: 16px; height: 16px; flex-shrink: 0; }
.readonly-mode { min-height: 34px; display: inline-flex; align-items: center; width: fit-content; padding: 0 14px; border-radius: 8px; border: 1px solid var(--border-medium); background: var(--bg-surface); color: var(--text-secondary); font-size: 12px; font-weight: 600; }

.upload-area { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; padding: 28px 20px; border-radius: 12px; border: 2px dashed var(--border-strong); background: var(--bg-surface); cursor: pointer; transition: border-color 0.2s ease, background 0.2s ease; }
.upload-area:hover, .upload-area.drag-active { border-color: rgba(200,96,122,0.4); background: var(--accent-bg-subtle); }
.upload-input { display: none; }
.upload-icon { width: 32px; height: 32px; color: var(--text-hint); }
.upload-text { font-size: 14px; color: var(--text-tertiary); }
.upload-hint { font-size: 12px; color: var(--text-hint); }
.ref-image-preview { position: relative; display: inline-block; border-radius: 12px; overflow: hidden; border: 1px solid var(--border-medium); background: var(--bg-surface); }
.ref-image-preview img { display: block; max-width: 100%; max-height: 200px; object-fit: contain; }
.remove-btn { position: absolute; top: 8px; right: 8px; width: 28px; height: 28px; padding: 0; display: flex; align-items: center; justify-content: center; border-radius: 8px; border: none; background: rgba(0,0,0,0.7); color: rgba(255,255,255,0.9); cursor: pointer; transition: background 0.2s ease; }
.remove-btn:hover { background: rgba(255,69,58,0.8); }
.remove-btn svg { width: 14px; height: 14px; }

.preview-overlay { position: fixed; inset: 0; z-index: 2000; display: flex; align-items: center; justify-content: center; background: rgba(0,0,0,0.85); backdrop-filter: blur(8px); cursor: zoom-out; }
.preview-close { position: absolute; top: 20px; right: 20px; width: 40px; height: 40px; padding: 0; display: flex; align-items: center; justify-content: center; border-radius: 10px; border: none; background: rgba(255,255,255,0.15); color: rgba(255,255,255,0.9); cursor: pointer; transition: background 0.15s ease; z-index: 1; }
.preview-close:hover { background: rgba(255,255,255,0.25); }
.preview-close svg { width: 20px; height: 20px; }
.preview-img { max-width: 90vw; max-height: 90vh; object-fit: contain; border-radius: 8px; cursor: default; }
.preview-video { max-width: 90vw; max-height: 90vh; border-radius: 8px; cursor: default; outline: none; }
</style>
