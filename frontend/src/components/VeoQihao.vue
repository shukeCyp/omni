<script setup>
import { ref, reactive, computed, onMounted } from 'vue'

const emit = defineEmits(['toast'])

// ==================== 默认提示词 ====================
const defaultImagePrompt = ref('')
const defaultVideoPrompt = ref('')

const showPromptDialog = ref(false)
const promptDialogType = ref('image')
const promptDialogText = ref('')

const openPromptDialog = (type) => {
  promptDialogType.value = type
  promptDialogText.value = type === 'image' ? defaultImagePrompt.value : defaultVideoPrompt.value
  showPromptDialog.value = true
}
const closePromptDialog = () => { showPromptDialog.value = false }
const savePromptDialog = async () => {
  const text = promptDialogText.value.trim()
  if (!text) { emit('toast', '提示词不能为空', 'error'); return }
  try {
    if (promptDialogType.value === 'image') {
      await window.pywebview.api.set_qihao_image_prompt(text)
      defaultImagePrompt.value = text
    } else {
      await window.pywebview.api.set_qihao_video_prompt(text)
      defaultVideoPrompt.value = text
    }
    emit('toast', '提示词已保存', 'success')
    showPromptDialog.value = false
  } catch { emit('toast', '保存失败', 'error') }
}

onMounted(async () => {
  try {
    const [imgRes, vidRes, settings] = await Promise.all([
      window.pywebview.api.get_qihao_image_prompt(),
      window.pywebview.api.get_qihao_video_prompt(),
      window.pywebview.api.get_all_settings(),
    ])
    if (imgRes.ok) defaultImagePrompt.value = imgRes.prompt
    if (vidRes.ok) defaultVideoPrompt.value = vidRes.prompt
    if (settings.glin_nanobanana_ratio) dialogImageRatio.value = settings.glin_nanobanana_ratio
    if (settings.glin_nanobanana_quality) dialogImageQuality.value = settings.glin_nanobanana_quality
    if (settings.hetang_veo_orientation) dialogVideoOrientation.value = settings.hetang_veo_orientation
  } catch { /* ignore */ }
})

// ==================== 任务列表（内存中，不持久化） ====================
const taskList = ref([])
let taskIdCounter = 0
const videoQueue = []
let activeVideoCount = 0
let videoQueueLimit = 3

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
    if (!task || task.status !== 'video_queued' || !task.resultImageBase64) continue
    activeVideoCount++
    generateVideo(task).finally(() => {
      activeVideoCount--
      pumpVideoQueue()
    })
  }
}

const enqueueVideoGeneration = async (task) => {
  if (!task || !task.resultImageBase64) return false
  if (['video_queued', 'video_processing'].includes(task.status)) return false
  await resolveVideoConcurrency()
  task.status = 'video_queued'
  task.statusText = '视频排队中...'
  videoQueue.push(task)
  pumpVideoQueue()
  return true
}

// ==================== 添加任务 弹窗 ====================
const showDialog = ref(false)

const dialogImages = ref([])
const dialogImagePrompt = ref('')
const dialogVideoPrompt = ref('')
const dialogImageRatio = ref('9:16')
const dialogImageQuality = ref('1K')
const dialogVideoOrientation = ref('portrait')
const dialogAutoVideo = ref(true)
const dialogCount = ref(1)
const dialogIsDragging = ref(false)
const dialogFileInput = ref(null)

const openAddDialog = () => {
  dialogImages.value = []
  dialogCount.value = 1
  dialogImagePrompt.value = defaultImagePrompt.value
  dialogVideoPrompt.value = defaultVideoPrompt.value
  showDialog.value = true
}

const closeDialog = () => { showDialog.value = false }

const handleDialogImage = (file) => {
  if (!file) return
  if (!file.type.startsWith('image/')) { emit('toast', '请选择图片文件', 'error'); return }
  if (file.size > 10 * 1024 * 1024) { emit('toast', '图片不能超过 10MB', 'error'); return }
  const reader = new FileReader()
  reader.onload = (e) => {
    dialogImages.value.push({
      preview: e.target.result,
      base64: e.target.result.split(',')[1],
      mime: file.type,
    })
  }
  reader.readAsDataURL(file)
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

// ==================== 页面拖拽 → 批量添加 ====================
const pageDragging = ref(false)

const onPageDragEnter = (e) => { e.preventDefault(); pageDragging.value = true }
const onPageDragOver  = (e) => { e.preventDefault(); pageDragging.value = true }
const onPageDragLeave = (e) => {
  e.preventDefault()
  if (e.currentTarget.contains(e.relatedTarget)) return
  pageDragging.value = false
}

const readImageFile = (file) => {
  return new Promise((resolve) => {
    if (!file.type.startsWith('image/')) { resolve(null); return }
    if (file.size > 10 * 1024 * 1024) { resolve(null); return }
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

const onPageDrop = async (e) => {
  e.preventDefault()
  pageDragging.value = false
  const files = Array.from(e.dataTransfer?.files || []).filter(f => f.type.startsWith('image/'))
  if (!files.length) return
  const imgs = (await Promise.all(files.map(readImageFile))).filter(Boolean)
  if (!imgs.length) return
  openBatchDialog(imgs)
}

// ==================== 批量添加弹窗 ====================
const showBatchDialog = ref(false)
const batchImages = ref([])
const batchImagePrompt = ref('')
const batchVideoPrompt = ref('')
const batchImageRatio = ref('9:16')
const batchImageQuality = ref('1K')
const batchVideoOrientation = ref('portrait')
const batchAutoVideo = ref(true)

const openBatchDialog = (imgs) => {
  batchImages.value = imgs
  batchImagePrompt.value = defaultImagePrompt.value
  batchVideoPrompt.value = defaultVideoPrompt.value
  showBatchDialog.value = true
}
const closeBatchDialog = () => { showBatchDialog.value = false; batchImages.value = [] }
const removeBatchImage = (idx) => {
  batchImages.value.splice(idx, 1)
  if (!batchImages.value.length) closeBatchDialog()
}

const submitBatchDialog = () => {
  if (!batchImages.value.length) { emit('toast', '没有可用的图片', 'error'); return }
  if (!batchImagePrompt.value.trim()) { emit('toast', '请输入图片提示词', 'error'); return }
  if (!batchVideoPrompt.value.trim()) { emit('toast', '请输入视频提示词', 'error'); return }

  defaultImagePrompt.value = batchImagePrompt.value.trim()
  defaultVideoPrompt.value = batchVideoPrompt.value.trim()

  window.pywebview.api.save_settings({
    glin_nanobanana_ratio: batchImageRatio.value,
    glin_nanobanana_quality: batchImageQuality.value,
    hetang_veo_orientation: batchVideoOrientation.value,
  }).catch(() => {})
  window.pywebview.api.set_image_process_prompt(defaultImagePrompt.value).catch(() => {})
  window.pywebview.api.set_video_process_prompt(defaultVideoPrompt.value).catch(() => {})

  const tasks = batchImages.value.map(img => reactive({
    id: ++taskIdCounter,
    images: [{ ...img }],
    imagePrompt: defaultImagePrompt.value,
    imageRatio: batchImageRatio.value,
    imageQuality: batchImageQuality.value,
    videoPrompt: defaultVideoPrompt.value,
    videoOrientation: batchVideoOrientation.value,
    autoVideo: batchAutoVideo.value,
    resultImageSrc: '',
    resultImageBase64: '',
    resultImageMime: '',
    videoUrl: '',
    filePath: '',
    status: 'pending',
    statusText: '待处理',
  }))

  taskList.value.unshift(...tasks)
  showBatchDialog.value = false
  batchImages.value = []

  emit('toast', `已添加 ${tasks.length} 条任务，开始生成...`, 'success')
  startBatchGeneration(tasks)
}

const startBatchGeneration = async (tasks) => {
  let concurrency = 3
  try {
    const settings = await window.pywebview.api.get_all_settings()
    concurrency = parseInt(settings.thread_pool_size || '3', 10)
    if (concurrency < 1) concurrency = 1
    if (concurrency > 50) concurrency = 50
  } catch { /* ignore */ }

  let idx = 0
  const runNext = async () => {
    while (idx < tasks.length) {
      const task = tasks[idx++]
      if (task.status === 'pending') {
        await generateImage(task)
      }
    }
  }
  const workers = []
  for (let i = 0; i < Math.min(concurrency, tasks.length); i++) {
    workers.push(runNext())
  }
}

// ==================== 统计信息 ====================
const stats = computed(() => {
  const total = taskList.value.length
  const completed = taskList.value.filter(t => t.status === 'completed').length
  const processing = taskList.value.filter(t => ['image_processing', 'video_queued', 'video_processing'].includes(t.status)).length
  const failed = taskList.value.filter(t => t.status === 'failed').length
  return { total, completed, processing, failed }
})

// ==================== 提交任务 ====================
const submitDialog = () => {
  if (!dialogImagePrompt.value.trim()) { emit('toast', '请输入图片提示词', 'error'); return }
  if (!dialogVideoPrompt.value.trim()) { emit('toast', '请输入视频提示词', 'error'); return }

  defaultImagePrompt.value = dialogImagePrompt.value.trim()
  defaultVideoPrompt.value = dialogVideoPrompt.value.trim()

  window.pywebview.api.save_settings({
    glin_nanobanana_ratio: dialogImageRatio.value,
    glin_nanobanana_quality: dialogImageQuality.value,
    hetang_veo_orientation: dialogVideoOrientation.value,
  }).catch(() => {})
  window.pywebview.api.set_qihao_image_prompt(defaultImagePrompt.value).catch(() => {})
  window.pywebview.api.set_qihao_video_prompt(defaultVideoPrompt.value).catch(() => {})

  const hasImages = dialogImages.value.length > 0
  const count = hasImages ? 1 : Math.max(1, Math.min(1000, dialogCount.value || 1))
  const images = dialogImages.value.map(img => ({ ...img }))

  const newTasks = []
  for (let i = 0; i < count; i++) {
    const task = reactive({
      id: ++taskIdCounter,
      images: hasImages ? images : [],
      imagePrompt: defaultImagePrompt.value,
      imageRatio: dialogImageRatio.value,
      imageQuality: dialogImageQuality.value,
      videoPrompt: defaultVideoPrompt.value,
      videoOrientation: dialogVideoOrientation.value,
      autoVideo: dialogAutoVideo.value,
      resultImageSrc: '',
      resultImageBase64: '',
      resultImageMime: '',
      videoUrl: '',
      filePath: '',
      status: 'pending',
      statusText: '待处理',
    })
    newTasks.push(task)
  }
  taskList.value.unshift(...newTasks)
  showDialog.value = false

  if (count > 1) emit('toast', `已添加 ${count} 条任务，开始生成...`, 'success')
  startBatchGeneration(newTasks)
}

// ==================== 图片生成 → 自动生成视频 ====================
const generateImage = async (task) => {
  task.status = 'image_processing'
  task.statusText = '图片生成中...'
  task.resultImageSrc = ''
  task.resultImageBase64 = ''
  task.resultImageMime = ''

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
    if (attempts > 0) task.statusText = `图片重试中 (${attempts}/${maxRetry})...`
    try {
      const refImages = (task.images || []).map(img => ({ base64: img.base64, mime: img.mime }))
      const res = await window.pywebview.api.generate_media_image(
        task.imagePrompt,
        refImages,
        task.imageRatio,
        task.imageQuality,
        '',
        '',
      )
      if (res.ok && res.image_data && res.mime_type) {
        task.resultImageSrc = `data:${res.mime_type};base64,${res.image_data}`
        task.resultImageBase64 = res.image_data
        task.resultImageMime = res.mime_type
        task.status = 'image_done'
        if (task.autoVideo) {
          task.statusText = '图片完成，等待生成视频...'
          enqueueVideoGeneration(task)
        } else {
          task.statusText = '图片已完成，待手动生成视频'
        }
        return true
      } else {
        lastError = res.msg || '图片生成失败'
      }
    } catch (e) {
      lastError = String(e)
    }
    attempts++
  }

  task.status = 'failed'
  task.statusText = `图片失败: ${lastError}`
  return false
}

// ==================== 视频生成 ====================
const generateVideo = async (task) => {
  task.status = 'video_processing'
  task.statusText = '视频生成中...'
  task.videoUrl = ''
  task.filePath = ''

  let maxRetry = 0
  let veoProvider = 'hetang'
  try {
    const settings = await window.pywebview.api.get_all_settings()
    if (settings.auto_retry === 'true') {
      maxRetry = parseInt(settings.video_max_retry || '3', 10)
    }
    // 从设置中读取 VEO 渠道
    veoProvider = settings.veo_model || 'hetang'
  } catch { /* ignore */ }

  let attempts = 0
  let lastError = ''

  while (attempts <= maxRetry) {
    if (attempts > 0) task.statusText = `视频重试中 (${attempts}/${maxRetry})...`
    try {
      const refImages = [{ base64: task.resultImageBase64, mime: task.resultImageMime }]
      const res = await window.pywebview.api.generate_media_video(
        task.videoPrompt,
        refImages,
        task.videoOrientation,
        10,
        'veo3',
        veoProvider,
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
      } else {
        lastError = res.msg || '视频生成失败'
      }
    } catch (e) {
      lastError = String(e)
    }
    attempts++
  }

  task.status = 'failed'
  task.statusText = `视频失败: ${lastError}`
  return false
}

// ==================== 操作 ====================
const isTaskBusy = (task) => ['image_processing', 'video_queued', 'video_processing'].includes(task.status)

const regenImage = (task) => {
  if (isTaskBusy(task)) return
  task.videoUrl = ''
  task.filePath = ''
  generateImage(task)
}

const regenVideo = (task) => {
  if (isTaskBusy(task)) return
  if (!task.resultImageBase64) {
    emit('toast', '暂无生成图片，请先重新生成图片', 'error')
    return
  }
  enqueueVideoGeneration(task)
}

const deleteTask = (idx) => {
  if (isTaskBusy(taskList.value[idx])) {
    emit('toast', '任务正在处理中，无法删除', 'error')
    return
  }
  taskList.value.splice(idx, 1)
}

const deleteAllTasks = () => {
  if (taskList.value.some(t => isTaskBusy(t))) {
    emit('toast', '有任务正在处理中，无法全部删除', 'error')
    return
  }
  taskList.value = []
}

const downloadImage = async (task) => {
  if (!task.resultImageBase64) { emit('toast', '暂无生成图片', 'error'); return }
  try {
    emit('toast', '开始下载图片...', 'success')
    const res = await window.pywebview.api.download_image(task.resultImageBase64, task.resultImageMime, 'veo_qihao')
    if (res.ok) emit('toast', '图片已保存', 'success')
    else emit('toast', res.msg || '下载失败', 'error')
  } catch { emit('toast', '下载异常', 'error') }
}

const downloadVideo = async (task, silent = false) => {
  if (!task.videoUrl) { if (!silent) emit('toast', '暂无视频链接', 'error'); return }
  try {
    if (!silent) emit('toast', '开始下载视频...', 'success')
    const res = await window.pywebview.api.download_veo_video(task.videoUrl)
    if (res.ok) { if (!silent) emit('toast', '视频已保存', 'success') }
    else { if (!silent) emit('toast', res.msg || '下载失败', 'error') }
  } catch { if (!silent) emit('toast', '下载异常', 'error') }
}

// ==================== 预览 ====================
const previewType = ref('')
const previewSrc = ref('')
const showPreview = ref(false)
const openImagePreview = (src) => { previewType.value = 'image'; previewSrc.value = src; showPreview.value = true }
const openVideoPreview = (url) => { previewType.value = 'video'; previewSrc.value = url; showPreview.value = true }
const closePreview = () => { showPreview.value = false; previewSrc.value = ''; previewType.value = '' }

// ==================== 一键生成视频 ====================
const pendingVideoCount = computed(() =>
  taskList.value.filter(t => t.status === 'image_done').length
)

const batchGenerateVideo = async () => {
  const tasks = taskList.value.filter(t => t.status === 'image_done' && t.resultImageBase64)
  if (!tasks.length) { emit('toast', '暂无待生成视频的任务', 'error'); return }

  const concurrency = await resolveVideoConcurrency()

  emit('toast', `开始生成 ${tasks.length} 条视频，并发 ${concurrency}`, 'success')
  for (const task of tasks) {
    await enqueueVideoGeneration(task)
  }
}

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

// ==================== 编辑任务 ====================
const showEditDialog = ref(false)
const editingTask = ref(null)
const editImagePrompt = ref('')
const editVideoPrompt = ref('')
const editImageRatio = ref('9:16')
const editImageQuality = ref('1K')
const editVideoOrientation = ref('portrait')

const openEditDialog = (task) => {
  if (isTaskBusy(task)) return
  editingTask.value = task
  editImagePrompt.value = task.imagePrompt
  editVideoPrompt.value = task.videoPrompt
  editImageRatio.value = task.imageRatio
  editImageQuality.value = task.imageQuality
  editVideoOrientation.value = task.videoOrientation
  showEditDialog.value = true
}
const closeEditDialog = () => { showEditDialog.value = false; editingTask.value = null }
const saveEditDialog = () => {
  if (!editImagePrompt.value.trim()) { emit('toast', '请输入图片提示词', 'error'); return }
  if (!editVideoPrompt.value.trim()) { emit('toast', '请输入视频提示词', 'error'); return }
  const task = editingTask.value
  if (!task) return
  task.imagePrompt = editImagePrompt.value.trim()
  task.videoPrompt = editVideoPrompt.value.trim()
  task.imageRatio = editImageRatio.value
  task.imageQuality = editImageQuality.value
  task.videoOrientation = editVideoOrientation.value
  showEditDialog.value = false
  editingTask.value = null
  emit('toast', '任务参数已更新', 'success')
}

// 状态标签样式类
const statusClass = (status) => {
  if (status === 'pending') return 'pending'
  if (status === 'image_processing' || status === 'video_queued' || status === 'video_processing') return 'processing'
  if (status === 'image_done') return 'image-done'
  if (status === 'completed') return 'completed'
  return 'failed'
}
</script>

<template>
  <div class="page">
    <!-- 顶栏 -->
    <div class="page-toolbar">
      <h2 class="page-title">VEO 起号</h2>
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
        <button class="tool-btn prompt-btn" @click="openPromptDialog('image')">
          <svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/>
          </svg>
          <span>图片提示词</span>
        </button>
        <button class="tool-btn prompt-btn" @click="openPromptDialog('video')">
          <svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>
          </svg>
          <span>视频提示词</span>
        </button>
        <button v-if="taskList.some(t => t.filePath)" class="tool-btn export-btn" @click="exportAll">
          <svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          <span>一键下载</span>
        </button>
        <button v-if="pendingVideoCount > 0" class="tool-btn batch-video-btn" @click="batchGenerateVideo">
          <svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="5 3 19 12 5 21 5 3"/>
          </svg>
          <span>一键生成视频 ({{ pendingVideoCount }})</span>
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
      <div v-if="pageDragging" class="drag-overlay">
        <svg class="drag-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
          <polyline points="17 8 12 3 7 8"/>
          <line x1="12" y1="3" x2="12" y2="15"/>
        </svg>
        <p class="drag-text">松开鼠标批量添加参考图</p>
        <p class="drag-hint">每张图片将创建一条独立任务</p>
      </div>

      <!-- 空状态 -->
      <div v-if="taskList.length === 0 && !pageDragging" class="empty-state">
        <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
          <line x1="8" y1="21" x2="16" y2="21"/>
          <line x1="12" y1="17" x2="12" y2="21"/>
        </svg>
        <p class="empty-text">暂无起号任务</p>
        <p class="empty-hint">点击"添加任务"或拖拽参考图到此处</p>
      </div>

      <!-- 列表 -->
      <div v-else-if="!pageDragging" class="list-wrap">
        <div class="list-header">
          <div class="col col-index">#</div>
          <div class="col col-origin">原图</div>
          <div class="col col-result">生成图</div>
          <div class="col col-status">状态</div>
          <div class="col col-actions">操作</div>
        </div>
        <div
          v-for="(task, idx) in taskList"
          :key="task.id"
          class="list-row"
        >
          <div class="col col-index">{{ taskList.length - idx }}</div>
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
            <div v-if="task.resultImageSrc" class="thumb clickable" @click="openImagePreview(task.resultImageSrc)">
              <img :src="task.resultImageSrc" alt="生成图" />
            </div>
            <span v-else class="no-result">—</span>
          </div>
          <div class="col col-status">
            <span :class="['status-tag', statusClass(task.status)]">{{ task.statusText }}</span>
          </div>
          <div class="col col-actions">
            <!-- 图片重新生成 -->
            <button
              class="action-btn regen-img-btn"
              @click="regenImage(task)"
              :disabled="isTaskBusy(task)"
              title="图片重新生成"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/>
              </svg>
            </button>
            <!-- 视频重新生成 -->
            <button
              class="action-btn gen-vid-btn"
              @click="regenVideo(task)"
              :disabled="isTaskBusy(task) || !task.resultImageBase64"
              title="视频重新生成"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>
              </svg>
            </button>
            <!-- 下载图片 -->
            <button
              v-if="task.resultImageBase64"
              class="action-btn download-btn"
              @click="downloadImage(task)"
              title="下载图片"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/>
                <line x1="12" y1="16" x2="12" y2="22" stroke-width="0"/>
              </svg>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="download-overlay-icon">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
              </svg>
            </button>
            <!-- 下载视频 -->
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
            <!-- 播放视频 -->
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
            <!-- 编辑 -->
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
            <!-- 删除 -->
            <button
              class="action-btn delete-btn"
              @click="deleteTask(idx)"
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

    <!-- 批量添加弹窗 -->
    <Teleport to="body">
      <div v-if="showBatchDialog" class="dialog-overlay" @click.self="closeBatchDialog">
        <div class="dialog dialog--image">
          <div class="dialog-header">
            <h3 class="dialog-title">批量添加起号任务（{{ batchImages.length }} 张图 = {{ batchImages.length }} 条任务）</h3>
            <button class="dialog-close" @click="closeBatchDialog">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>
          <div class="dialog-body dialog-body--split">
            <!-- 左侧：图片预览 -->
            <div class="dialog-left">
              <div class="field">
                <span class="field-label">商品图片（每张图片 = 一条任务）</span>
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
            <!-- 右侧：参数 -->
            <div class="dialog-right">
              <div class="field">
                <span class="field-label">图片提示词（必填）</span>
                <textarea v-model="batchImagePrompt" placeholder="描述图片生成效果" rows="3"></textarea>
              </div>
              <div class="field" style="margin-top: 12px;">
                <span class="field-label">视频提示词（必填）</span>
                <textarea v-model="batchVideoPrompt" placeholder="描述视频生成效果" rows="3"></textarea>
              </div>
              <div class="form-row">
                <div class="field field-inline">
                  <span class="field-label">图片比例</span>
                  <div class="toggle-group">
                    <button :class="['toggle-btn', { active: batchImageRatio === '9:16' }]" @click="batchImageRatio = '9:16'">9:16 竖屏</button>
                    <button :class="['toggle-btn', { active: batchImageRatio === '16:9' }]" @click="batchImageRatio = '16:9'">16:9 横屏</button>
                    <button :class="['toggle-btn', { active: batchImageRatio === '1:1' }]" @click="batchImageRatio = '1:1'">1:1 方图</button>
                    <button :class="['toggle-btn', { active: batchImageRatio === '4:3' }]" @click="batchImageRatio = '4:3'">4:3</button>
                    <button :class="['toggle-btn', { active: batchImageRatio === '3:4' }]" @click="batchImageRatio = '3:4'">3:4</button>
                  </div>
                </div>
              </div>
              <div class="form-row">
                <div class="field field-inline">
                  <span class="field-label">图片清晰度</span>
                  <div class="toggle-group">
                    <button :class="['toggle-btn', { active: batchImageQuality === '1K' }]" @click="batchImageQuality = '1K'">1K</button>
                    <button :class="['toggle-btn', { active: batchImageQuality === '2K' }]" @click="batchImageQuality = '2K'">2K</button>
                    <button :class="['toggle-btn', { active: batchImageQuality === '4K' }]" @click="batchImageQuality = '4K'">4K</button>
                  </div>
                </div>
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
              <div class="form-row" style="margin-top: 16px;">
                <label class="switch-field">
                  <span class="switch-label">自动生成视频</span>
                  <button
                    :class="['switch-track', { active: batchAutoVideo }]"
                    @click="batchAutoVideo = !batchAutoVideo"
                  >
                    <span class="switch-thumb" />
                  </button>
                  <span class="switch-hint">{{ batchAutoVideo ? '图片完成后自动生成视频' : '图片完成后暂停，手动确认再生成' }}</span>
                </label>
              </div>
            </div>
          </div>
          <div class="dialog-footer">
            <button class="cancel-btn" @click="closeBatchDialog">取消</button>
            <button class="primary-btn save-btn" @click="submitBatchDialog">添加 {{ batchImages.length }} 条任务并开始生成</button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 添加任务弹窗 -->
    <Teleport to="body">
      <div v-if="showDialog" class="dialog-overlay" @click.self="closeDialog">
        <div class="dialog dialog--image">
          <div class="dialog-header">
            <h3 class="dialog-title">添加起号任务</h3>
            <button class="dialog-close" @click="closeDialog">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>
          <div class="dialog-body dialog-body--split">
            <!-- 左侧：图片上传（可选） -->
            <div class="dialog-left">
              <div class="field">
                <span class="field-label">参考图片（可选，不上传则文生图）</span>
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
                  <span class="upload-hint">支持 JPG / PNG / WebP，最大 10MB（不上传则文生图）</span>
                </div>
              </div>
            </div>

            <!-- 右侧：提示词 + 参数 -->
            <div class="dialog-right">
              <div class="field">
                <span class="field-label">图片提示词（必填）</span>
                <textarea v-model="dialogImagePrompt" placeholder="描述图片生成效果" rows="3"></textarea>
              </div>
              <div class="field" style="margin-top: 12px;">
                <span class="field-label">视频提示词（必填）</span>
                <textarea v-model="dialogVideoPrompt" placeholder="描述视频生成效果" rows="3"></textarea>
              </div>
              <div class="form-row">
                <div class="field field-inline">
                  <span class="field-label">图片比例</span>
                  <div class="toggle-group">
                    <button :class="['toggle-btn', { active: dialogImageRatio === '9:16' }]" @click="dialogImageRatio = '9:16'">9:16 竖屏</button>
                    <button :class="['toggle-btn', { active: dialogImageRatio === '16:9' }]" @click="dialogImageRatio = '16:9'">16:9 横屏</button>
                    <button :class="['toggle-btn', { active: dialogImageRatio === '1:1' }]" @click="dialogImageRatio = '1:1'">1:1 方图</button>
                    <button :class="['toggle-btn', { active: dialogImageRatio === '4:3' }]" @click="dialogImageRatio = '4:3'">4:3</button>
                    <button :class="['toggle-btn', { active: dialogImageRatio === '3:4' }]" @click="dialogImageRatio = '3:4'">3:4</button>
                  </div>
                </div>
              </div>
              <div class="form-row">
                <div class="field field-inline">
                  <span class="field-label">图片清晰度</span>
                  <div class="toggle-group">
                    <button :class="['toggle-btn', { active: dialogImageQuality === '1K' }]" @click="dialogImageQuality = '1K'">1K</button>
                    <button :class="['toggle-btn', { active: dialogImageQuality === '2K' }]" @click="dialogImageQuality = '2K'">2K</button>
                    <button :class="['toggle-btn', { active: dialogImageQuality === '4K' }]" @click="dialogImageQuality = '4K'">4K</button>
                  </div>
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
              <div class="form-row" style="margin-top: 16px; align-items: center;">
                <label class="switch-field" style="flex: 1;">
                  <span class="switch-label">自动生成视频</span>
                  <button
                    :class="['switch-track', { active: dialogAutoVideo }]"
                    @click="dialogAutoVideo = !dialogAutoVideo"
                  >
                    <span class="switch-thumb" />
                  </button>
                  <span class="switch-hint">{{ dialogAutoVideo ? '自动生成' : '手动确认' }}</span>
                </label>
                <div v-if="!dialogImages.length" class="field field-inline" style="flex: 0 0 auto;">
                  <span class="field-label">数量</span>
                  <input v-model.number="dialogCount" type="number" min="1" max="1000" class="count-input" />
                </div>
              </div>
            </div>
          </div>
          <div class="dialog-footer">
            <button class="cancel-btn" @click="closeDialog">取消</button>
            <button class="primary-btn save-btn" @click="submitDialog">
              {{ dialogImages.length ? '添加并开始生成' : `添加 ${Math.max(1, dialogCount || 1)} 条任务并开始生成` }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 编辑任务弹窗 -->
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
              <span class="field-label">图片提示词</span>
              <textarea v-model="editImagePrompt" placeholder="描述图片生成效果" rows="3"></textarea>
            </div>
            <div class="field" style="margin-top: 12px;">
              <span class="field-label">视频提示词</span>
              <textarea v-model="editVideoPrompt" placeholder="描述视频生成效果" rows="3"></textarea>
            </div>
            <div class="form-row">
              <div class="field field-inline">
                <span class="field-label">图片比例</span>
                <div class="toggle-group">
                  <button :class="['toggle-btn', { active: editImageRatio === '9:16' }]" @click="editImageRatio = '9:16'">9:16 竖屏</button>
                  <button :class="['toggle-btn', { active: editImageRatio === '16:9' }]" @click="editImageRatio = '16:9'">16:9 横屏</button>
                  <button :class="['toggle-btn', { active: editImageRatio === '1:1' }]" @click="editImageRatio = '1:1'">1:1 方图</button>
                  <button :class="['toggle-btn', { active: editImageRatio === '4:3' }]" @click="editImageRatio = '4:3'">4:3</button>
                  <button :class="['toggle-btn', { active: editImageRatio === '3:4' }]" @click="editImageRatio = '3:4'">3:4</button>
                </div>
              </div>
            </div>
            <div class="form-row">
              <div class="field field-inline">
                <span class="field-label">图片清晰度</span>
                <div class="toggle-group">
                  <button :class="['toggle-btn', { active: editImageQuality === '1K' }]" @click="editImageQuality = '1K'">1K</button>
                  <button :class="['toggle-btn', { active: editImageQuality === '2K' }]" @click="editImageQuality = '2K'">2K</button>
                  <button :class="['toggle-btn', { active: editImageQuality === '4K' }]" @click="editImageQuality = '4K'">4K</button>
                </div>
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
          </div>
          <div class="dialog-footer">
            <button class="cancel-btn" @click="closeEditDialog">取消</button>
            <button class="primary-btn save-btn" @click="saveEditDialog">保存</button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 提示词编辑弹窗 -->
    <Teleport to="body">
      <div v-if="showPromptDialog" class="dialog-overlay" @click.self="closePromptDialog">
        <div class="dialog dialog--prompt">
          <div class="dialog-header">
            <h3 class="dialog-title">{{ promptDialogType === 'image' ? '图片提示词' : '视频提示词' }}</h3>
            <button class="dialog-close" @click="closePromptDialog">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>
          <div class="dialog-body">
            <label class="field">
              <span class="field-label">{{ promptDialogType === 'image' ? '所有任务的图片生成提示词' : '所有任务的视频生成提示词' }}</span>
              <textarea
                v-model="promptDialogText"
                :placeholder="promptDialogType === 'image' ? '描述图片生成效果' : '描述视频生成效果'"
                rows="6"
              ></textarea>
            </label>
          </div>
          <div class="dialog-footer">
            <button class="cancel-btn" @click="closePromptDialog">取消</button>
            <button class="primary-btn save-btn" @click="savePromptDialog">保存</button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 预览弹窗 -->
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

/* ============ 顶栏 ============ */
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
.batch-video-btn { border-color: rgba(175,82,222,0.3); background: rgba(175,82,222,0.08); color: #bf5af2; }
.batch-video-btn:hover { background: rgba(175,82,222,0.18); border-color: rgba(175,82,222,0.5); color: #bf5af2; }
.delete-all-btn { border-color: rgba(255,69,58,0.3); background: rgba(255,69,58,0.08); color: var(--error); }
.delete-all-btn:hover { background: rgba(255,69,58,0.18); border-color: rgba(255,69,58,0.5); color: var(--error); }
.tool-icon { width: 16px; height: 16px; flex-shrink: 0; }

/* ============ 内容区 ============ */
.page-body { flex: 1; padding: 24px 32px; overflow-y: auto; position: relative; transition: background 0.2s ease; }
.page-body.drag-active { background: var(--accent-bg-subtle); }

/* ============ 拖拽 ============ */
.drag-overlay { position: absolute; inset: 16px; z-index: 10; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; border-radius: 16px; border: 2px dashed var(--accent-focus); background: var(--accent-bg); pointer-events: none; }
.drag-icon { width: 48px; height: 48px; color: rgba(200,96,122,0.7); }
.drag-text { margin: 0; font-size: 16px; font-weight: 500; color: rgba(200,96,122,0.8); }
.drag-hint { margin: 0; font-size: 12px; color: var(--text-hint); }

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
.col-origin { width: 120px; flex-shrink: 0; }
.col-result { width: 80px; flex-shrink: 0; }
.col-status { flex: 1; min-width: 0; padding: 0 12px; }
.col-actions { width: 300px; flex-shrink: 0; display: flex; justify-content: center; gap: 5px; flex-wrap: wrap; }

.thumb { width: 56px; height: 56px; border-radius: 8px; overflow: hidden; background: var(--bg-surface); border: 1px solid var(--border); }
.thumb img { width: 100%; height: 100%; object-fit: cover; display: block; }
.thumb.clickable { cursor: pointer; transition: opacity 0.15s ease; }
.thumb.clickable:hover { opacity: 0.8; }
.no-result { font-size: 13px; color: var(--text-hint); display: flex; width: 56px; height: 56px; align-items: center; justify-content: center; }
.thumb-group { display: flex; gap: 3px; align-items: center; flex-wrap: wrap; }
.thumb.mini { width: 36px; height: 36px; border-radius: 6px; }
.thumb-more { font-size: 11px; color: var(--text-hint); margin-left: 2px; }

/* 状态标签 */
.status-tag { display: inline-block; padding: 3px 10px; border-radius: 6px; font-size: 11px; font-weight: 600; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.status-tag.pending { background: rgba(255,214,10,0.1); color: #ffd60a; }
.status-tag.processing { background: var(--accent-bg); color: var(--accent); }
.status-tag.image-done { background: rgba(100,210,255,0.1); color: #64d2ff; }
.status-tag.completed { background: var(--success-bg); color: var(--success); }
.status-tag.failed { background: var(--error-bg); color: var(--error); }

/* 操作按钮 */
.action-btn { width: 34px; height: 34px; padding: 0; display: flex; align-items: center; justify-content: center; border-radius: 8px; border: 1px solid var(--border-medium); background: var(--border-light); color: var(--text-tertiary); cursor: pointer; transition: all 0.15s ease; position: relative; }
.action-btn:disabled { opacity: 0.35; cursor: not-allowed; }
.action-btn svg { width: 15px; height: 15px; }
.regen-img-btn:hover:not(:disabled) { background: rgba(100,210,255,0.15); border-color: rgba(100,210,255,0.4); color: #64d2ff; }
.gen-vid-btn:hover:not(:disabled) { background: rgba(175,82,222,0.15); border-color: rgba(175,82,222,0.4); color: #bf5af2; }
.download-btn:hover:not(:disabled) { background: rgba(52,199,89,0.15); border-color: rgba(52,199,89,0.4); color: var(--success); }
.download-btn { overflow: hidden; }
.download-btn svg:first-child { width: 15px; height: 15px; }
.download-overlay-icon { position: absolute; width: 10px !important; height: 10px !important; bottom: 2px; right: 2px; }
.download-vid-btn:hover:not(:disabled) { background: rgba(52,199,89,0.15); border-color: rgba(52,199,89,0.4); color: var(--success); }
.view-btn:hover:not(:disabled) { background: var(--accent-bg-strong); border-color: rgba(200,96,122,0.4); color: var(--accent); }
.edit-btn:hover:not(:disabled) { background: rgba(255,214,10,0.15); border-color: rgba(255,214,10,0.4); color: #ffd60a; }
.delete-btn:hover:not(:disabled) { background: rgba(255,69,58,0.15); border-color: rgba(255,69,58,0.4); color: var(--error); }

/* ============ 弹窗通用 ============ */
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

.field { display: flex; flex-direction: column; gap: 8px; }
.field-label { font-size: 13px; color: var(--text-tertiary); }

.dialog-body textarea { width: 100%; padding: 12px 14px; border-radius: 12px; border: 1px solid var(--border-medium); background: var(--bg-surface); color: var(--text-primary); font-size: 14px; font-family: inherit; outline: none; resize: vertical; transition: border-color 0.2s ease, box-shadow 0.2s ease; }
.dialog-body textarea::placeholder { color: var(--text-placeholder); }
.dialog-body textarea:focus { border-color: rgba(200,96,122,0.6); box-shadow: 0 0 0 3px var(--accent-bg-strong); }

/* 表单行 */
.form-row { display: flex; gap: 24px; margin-top: 12px; align-items: flex-start; }
.field-inline { flex: 1; }

/* 切换按钮组 */
.toggle-group { display: flex; gap: 6px; flex-wrap: wrap; }
.count-input { width: 90px; padding: 6px 10px; border-radius: 8px; border: 1px solid var(--border-medium); background: var(--bg-surface); color: var(--text-primary); font-size: 13px; font-family: inherit; outline: none; transition: border-color 0.2s ease, box-shadow 0.2s ease; -moz-appearance: textfield; }
.count-input::-webkit-outer-spin-button, .count-input::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
.count-input:focus { border-color: rgba(200,96,122,0.6); box-shadow: 0 0 0 3px var(--accent-bg-strong); }
.toggle-btn { display: flex; align-items: center; gap: 5px; padding: 7px 14px; border-radius: 8px; border: 1px solid var(--border-strong); background: var(--border-light); color: var(--text-tertiary); font-size: 12px; font-weight: 500; cursor: pointer; transition: all 0.2s ease; }
.toggle-btn:hover { background: var(--accent-bg); border-color: rgba(200,96,122,0.2); color: var(--text-secondary); }
.toggle-btn.active { background: var(--accent-bg-strong); border-color: rgba(200,96,122,0.4); color: var(--accent); }
.toggle-icon { width: 16px; height: 16px; flex-shrink: 0; }

/* 开关 */
.switch-field { display: flex; align-items: center; gap: 10px; cursor: pointer; }
.switch-label { font-size: 13px; font-weight: 500; color: var(--text-secondary); }
.switch-track { position: relative; width: 40px; height: 22px; border-radius: 11px; border: none; background: var(--border-strong); cursor: pointer; transition: background 0.2s ease; padding: 0; flex-shrink: 0; }
.switch-track.active { background: var(--success, #34c759); }
.switch-thumb { position: absolute; top: 2px; left: 2px; width: 18px; height: 18px; border-radius: 50%; background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,0.2); transition: transform 0.2s ease; }
.switch-track.active .switch-thumb { transform: translateX(18px); }
.switch-hint { font-size: 11px; color: var(--text-hint); }

/* 上传区 */
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

/* ============ 预览 ============ */
.preview-overlay { position: fixed; inset: 0; z-index: 2000; display: flex; align-items: center; justify-content: center; background: rgba(0,0,0,0.85); backdrop-filter: blur(8px); cursor: zoom-out; }
.preview-close { position: absolute; top: 20px; right: 20px; width: 40px; height: 40px; padding: 0; display: flex; align-items: center; justify-content: center; border-radius: 10px; border: none; background: rgba(255,255,255,0.15); color: rgba(255,255,255,0.9); cursor: pointer; transition: background 0.15s ease; z-index: 1; }
.preview-close:hover { background: rgba(255,255,255,0.25); }
.preview-close svg { width: 20px; height: 20px; }
.preview-img { max-width: 90vw; max-height: 90vh; object-fit: contain; border-radius: 8px; cursor: default; }
.preview-video { max-width: 90vw; max-height: 90vh; border-radius: 8px; cursor: default; outline: none; }
</style>
