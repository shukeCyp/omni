<script setup>
import { ref, reactive, computed } from 'vue'

const emit = defineEmits(['toast'])

const activeTab = ref('t2i')

// ==================== 模型列表 ====================
const imageModels = [
  { label: 'Gemini 2.5 Flash 横屏', value: 'gemini-2.5-flash-image-landscape' },
  { label: 'Gemini 2.5 Flash 竖屏', value: 'gemini-2.5-flash-image-portrait' },
  { label: 'Gemini 3.0 Pro 横屏', value: 'gemini-3.0-pro-image-landscape' },
  { label: 'Gemini 3.0 Pro 竖屏', value: 'gemini-3.0-pro-image-portrait' },
  { label: 'Gemini 3.0 Pro 方图', value: 'gemini-3.0-pro-image-square' },
  { label: 'Gemini 3.0 Pro 横屏4:3', value: 'gemini-3.0-pro-image-four-three' },
  { label: 'Gemini 3.0 Pro 竖屏3:4', value: 'gemini-3.0-pro-image-three-four' },
  { label: 'Gemini 3.0 Pro 横屏 2K', value: 'gemini-3.0-pro-image-landscape-2k' },
  { label: 'Gemini 3.0 Pro 竖屏 2K', value: 'gemini-3.0-pro-image-portrait-2k' },
  { label: 'Gemini 3.0 Pro 方图 2K', value: 'gemini-3.0-pro-image-square-2k' },
  { label: 'Gemini 3.0 Pro 横屏 4K', value: 'gemini-3.0-pro-image-landscape-4k' },
  { label: 'Gemini 3.0 Pro 竖屏 4K', value: 'gemini-3.0-pro-image-portrait-4k' },
  { label: 'Gemini 3.0 Pro 方图 4K', value: 'gemini-3.0-pro-image-square-4k' },
  { label: 'Gemini 3.1 Flash 横屏', value: 'gemini-3.1-flash-image-landscape' },
  { label: 'Gemini 3.1 Flash 竖屏', value: 'gemini-3.1-flash-image-portrait' },
  { label: 'Gemini 3.1 Flash 方图', value: 'gemini-3.1-flash-image-square' },
  { label: 'Gemini 3.1 Flash 横屏4:3', value: 'gemini-3.1-flash-image-four-three' },
  { label: 'Gemini 3.1 Flash 竖屏3:4', value: 'gemini-3.1-flash-image-three-four' },
  { label: 'Gemini 3.1 Flash 横屏 2K', value: 'gemini-3.1-flash-image-landscape-2k' },
  { label: 'Gemini 3.1 Flash 竖屏 2K', value: 'gemini-3.1-flash-image-portrait-2k' },
  { label: 'Gemini 3.1 Flash 方图 2K', value: 'gemini-3.1-flash-image-square-2k' },
  { label: 'Gemini 3.1 Flash 横屏 4K', value: 'gemini-3.1-flash-image-landscape-4k' },
  { label: 'Gemini 3.1 Flash 竖屏 4K', value: 'gemini-3.1-flash-image-portrait-4k' },
  { label: 'Gemini 3.1 Flash 方图 4K', value: 'gemini-3.1-flash-image-square-4k' },
  { label: 'Imagen 4.0 横屏', value: 'imagen-4.0-generate-preview-landscape' },
  { label: 'Imagen 4.0 竖屏', value: 'imagen-4.0-generate-preview-portrait' },
]

const t2vModels = [
  { label: 'Veo 3.1 Fast 竖屏', value: 'veo_3_1_t2v_fast_portrait' },
  { label: 'Veo 3.1 Fast 横屏', value: 'veo_3_1_t2v_fast_landscape' },
  { label: 'Veo 3.1 竖屏', value: 'veo_3_1_t2v_portrait' },
  { label: 'Veo 3.1 横屏', value: 'veo_3_1_t2v_landscape' },
  { label: 'Veo 3.1 Fast Ultra 竖屏', value: 'veo_3_1_t2v_fast_portrait_ultra' },
  { label: 'Veo 3.1 Fast Ultra 横屏', value: 'veo_3_1_t2v_fast_ultra' },
  { label: 'Veo 3.1 Fast Ultra Relaxed 竖屏', value: 'veo_3_1_t2v_fast_portrait_ultra_relaxed' },
  { label: 'Veo 3.1 Fast Ultra Relaxed 横屏', value: 'veo_3_1_t2v_fast_ultra_relaxed' },
  { label: 'Veo 2.1 Fast 竖屏', value: 'veo_2_1_fast_d_15_t2v_portrait' },
  { label: 'Veo 2.1 Fast 横屏', value: 'veo_2_1_fast_d_15_t2v_landscape' },
  { label: 'Veo 2.0 竖屏', value: 'veo_2_0_t2v_portrait' },
  { label: 'Veo 2.0 横屏', value: 'veo_2_0_t2v_landscape' },
]

const i2vModels = [
  { label: 'Veo 3.1 I2V Fast 竖屏', value: 'veo_3_1_i2v_s_fast_portrait_fl' },
  { label: 'Veo 3.1 I2V Fast 横屏', value: 'veo_3_1_i2v_s_fast_fl' },
  { label: 'Veo 3.1 I2V 竖屏', value: 'veo_3_1_i2v_s_portrait' },
  { label: 'Veo 3.1 I2V 横屏', value: 'veo_3_1_i2v_s_landscape' },
  { label: 'Veo 3.1 I2V Ultra 竖屏', value: 'veo_3_1_i2v_s_fast_portrait_ultra_fl' },
  { label: 'Veo 3.1 I2V Ultra 横屏', value: 'veo_3_1_i2v_s_fast_ultra_fl' },
  { label: 'Veo 3.1 I2V Ultra Relaxed 竖屏', value: 'veo_3_1_i2v_s_fast_portrait_ultra_relaxed' },
  { label: 'Veo 3.1 I2V Ultra Relaxed 横屏', value: 'veo_3_1_i2v_s_fast_ultra_relaxed' },
  { label: 'Veo 2.1 I2V 竖屏', value: 'veo_2_1_fast_d_15_i2v_portrait' },
  { label: 'Veo 2.1 I2V 横屏', value: 'veo_2_1_fast_d_15_i2v_landscape' },
  { label: 'Veo 2.0 I2V 竖屏', value: 'veo_2_0_i2v_portrait' },
  { label: 'Veo 2.0 I2V 横屏', value: 'veo_2_0_i2v_landscape' },
]

const r2vModels = [
  { label: 'Veo 3.1 R2V Fast 竖屏', value: 'veo_3_1_r2v_fast_portrait' },
  { label: 'Veo 3.1 R2V Fast 横屏', value: 'veo_3_1_r2v_fast' },
  { label: 'Veo 3.1 R2V Ultra 竖屏', value: 'veo_3_1_r2v_fast_portrait_ultra' },
  { label: 'Veo 3.1 R2V Ultra 横屏', value: 'veo_3_1_r2v_fast_ultra' },
  { label: 'Veo 3.1 R2V Ultra Relaxed 竖屏', value: 'veo_3_1_r2v_fast_portrait_ultra_relaxed' },
  { label: 'Veo 3.1 R2V Ultra Relaxed 横屏', value: 'veo_3_1_r2v_fast_ultra_relaxed' },
]

const upsampleModels = [
  { label: 'T2V Fast 竖屏 4K', value: 'veo_3_1_t2v_fast_portrait_4k' },
  { label: 'T2V Fast 横屏 4K', value: 'veo_3_1_t2v_fast_4k' },
  { label: 'T2V Fast Ultra 竖屏 4K', value: 'veo_3_1_t2v_fast_portrait_ultra_4k' },
  { label: 'T2V Fast Ultra 横屏 4K', value: 'veo_3_1_t2v_fast_ultra_4k' },
  { label: 'T2V Fast 竖屏 1080P', value: 'veo_3_1_t2v_fast_portrait_1080p' },
  { label: 'T2V Fast 横屏 1080P', value: 'veo_3_1_t2v_fast_1080p' },
  { label: 'T2V Fast Ultra 竖屏 1080P', value: 'veo_3_1_t2v_fast_portrait_ultra_1080p' },
  { label: 'T2V Fast Ultra 横屏 1080P', value: 'veo_3_1_t2v_fast_ultra_1080p' },
  { label: 'I2V Ultra 竖屏 4K', value: 'veo_3_1_i2v_s_fast_portrait_ultra_fl_4k' },
  { label: 'I2V Ultra 横屏 4K', value: 'veo_3_1_i2v_s_fast_ultra_fl_4k' },
  { label: 'I2V Ultra 竖屏 1080P', value: 'veo_3_1_i2v_s_fast_portrait_ultra_fl_1080p' },
  { label: 'I2V Ultra 横屏 1080P', value: 'veo_3_1_i2v_s_fast_ultra_fl_1080p' },
  { label: 'R2V Ultra 竖屏 4K', value: 'veo_3_1_r2v_fast_portrait_ultra_4k' },
  { label: 'R2V Ultra 横屏 4K', value: 'veo_3_1_r2v_fast_ultra_4k' },
  { label: 'R2V Ultra 竖屏 1080P', value: 'veo_3_1_r2v_fast_portrait_ultra_1080p' },
  { label: 'R2V Ultra 横屏 1080P', value: 'veo_3_1_r2v_fast_ultra_1080p' },
]

const tabs = [
  { key: 't2i', label: '文生图' },
  { key: 'i2i', label: '图生图' },
  { key: 't2v', label: '文生视频' },
  { key: 'i2v', label: '图生视频' },
  { key: 'r2v', label: '多图生视频' },
  { key: 'upsample', label: '视频放大' },
]

// ==================== 任务列表 ====================
const taskList = ref([])
let taskIdCounter = 0

const stats = computed(() => {
  const total = taskList.value.length
  const completed = taskList.value.filter(t => t.status === 'completed').length
  const processing = taskList.value.filter(t => t.status === 'processing').length
  const failed = taskList.value.filter(t => t.status === 'failed').length
  return { total, completed, processing, failed }
})

// ==================== 添加任务弹窗 ====================
const showAddDialog = ref(false)
const addPrompt = ref('')
const addModel = ref('')
const addCount = ref(1)
const addSubmitting = ref(false)
const addBatchMode = ref(false)
// 图片上传（图生图/图生视频/多图/放大用）
const addImages = ref([])
const addIsDragging = ref(false)
const addFileInput = ref(null)

const currentTabForDialog = ref('t2i')

const openAddDialog = () => {
  currentTabForDialog.value = activeTab.value
  addPrompt.value = ''
  addCount.value = 1
  addSubmitting.value = false
  addBatchMode.value = false
  addImages.value = []

  // 设置默认模型
  if (activeTab.value === 't2i' || activeTab.value === 'i2i') {
    addModel.value = imageModels[0].value
  } else if (activeTab.value === 't2v') {
    addModel.value = t2vModels[0].value
  } else if (activeTab.value === 'i2v') {
    addModel.value = i2vModels[0].value
  } else if (activeTab.value === 'r2v') {
    addModel.value = r2vModels[0].value
  } else if (activeTab.value === 'upsample') {
    addModel.value = upsampleModels[0].value
  }

  showAddDialog.value = true
}
const closeAddDialog = () => { showAddDialog.value = false }

const needsImages = computed(() => {
  return ['i2i', 'i2v', 'r2v'].includes(currentTabForDialog.value)
})

const maxImages = computed(() => {
  if (addBatchMode.value) return 50
  if (currentTabForDialog.value === 'i2i') return 1
  if (currentTabForDialog.value === 'i2v') return 2
  return 10
})

const currentModels = computed(() => {
  const t = currentTabForDialog.value
  if (t === 't2i' || t === 'i2i') return imageModels
  if (t === 't2v') return t2vModels
  if (t === 'i2v') return i2vModels
  if (t === 'r2v') return r2vModels
  if (t === 'upsample') return upsampleModels
  return []
})

const handleAddImage = (file) => {
  if (!file) return
  if (!file.type.startsWith('image/')) { emit('toast', '请选择图片文件', 'error'); return }
  if (file.size > 10 * 1024 * 1024) { emit('toast', '图片不能超过 10MB', 'error'); return }
  if (addImages.value.length >= maxImages.value) {
    emit('toast', `最多上传 ${maxImages.value} 张图片`, 'error')
    return
  }
  const reader = new FileReader()
  reader.onload = (e) => {
    const dataUrl = e.target.result
    addImages.value.push({
      preview: dataUrl,
      base64: dataUrl.split(',')[1],
      mime_type: file.type,
    })
  }
  reader.readAsDataURL(file)
}

const handleAddFileSelect = (event) => {
  const files = event.target.files
  for (let i = 0; i < files.length; i++) {
    handleAddImage(files[i])
  }
  if (addFileInput.value) addFileInput.value.value = ''
}

const onDragEnter = (e) => { e.preventDefault(); addIsDragging.value = true }
const onDragOver = (e) => { e.preventDefault(); addIsDragging.value = true }
const onDragLeave = (e) => {
  e.preventDefault()
  if (e.currentTarget.contains(e.relatedTarget)) return
  addIsDragging.value = false
}
const onDrop = (e) => {
  e.preventDefault()
  addIsDragging.value = false
  const files = e.dataTransfer?.files
  if (files) {
    for (let i = 0; i < files.length; i++) {
      handleAddImage(files[i])
    }
  }
}
const removeImage = (idx) => { addImages.value.splice(idx, 1) }

// ==================== 提交任务 ====================
const makeTask = (tab, prompt, images) => {
  const isImageTask = (tab === 't2i' || tab === 'i2i')
  return reactive({
    id: ++taskIdCounter,
    tab,
    prompt,
    model: addModel.value,
    modelLabel: currentModels.value.find(m => m.value === addModel.value)?.label || addModel.value,
    images,
    status: 'pending',
    statusText: '待处理',
    resultType: isImageTask ? 'image' : 'video',
    resultSrc: '',
    resultBase64: '',
    resultMime: '',
    videoUrl: '',
  })
}

const submitAddTask = () => {
  if (!addPrompt.value.trim()) {
    emit('toast', '请输入提示词', 'error')
    return
  }
  if (needsImages.value && addImages.value.length === 0) {
    emit('toast', '请至少上传一张图片', 'error')
    return
  }

  const tab = currentTabForDialog.value
  const count = Math.max(1, Math.min(100, parseInt(addCount.value) || 1))
  const lines = addPrompt.value.split('\n').map(l => l.trim()).filter(l => l)

  const newTasks = []

  if (addBatchMode.value) {
    if (needsImages.value && ['i2i', 'i2v'].includes(tab)) {
      for (const img of addImages.value) {
        for (let i = 0; i < count; i++) {
          const task = makeTask(tab, lines[0], [img])
          newTasks.push(task)
          taskList.value.unshift(task)
        }
      }
    } else {
      for (const line of lines) {
        for (let i = 0; i < count; i++) {
          const task = makeTask(tab, line, needsImages.value ? [...addImages.value] : [])
          newTasks.push(task)
          taskList.value.unshift(task)
        }
      }
    }
  } else {
    for (let i = 0; i < count; i++) {
      const prompt = lines.length > 1 ? lines[Math.floor(Math.random() * lines.length)] : lines[0]
      const task = makeTask(tab, prompt, needsImages.value ? [...addImages.value] : [])
      newTasks.push(task)
      taskList.value.unshift(task)
    }
  }

  showAddDialog.value = false
  emit('toast', `已添加 ${newTasks.length} 条任务，开始生成...`, 'success')
  startGeneration(newTasks)
}

// ==================== 生成逻辑 ====================
const startGeneration = async (tasks) => {
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
        await generateTask(task)
      }
    }
  }
  const workers = []
  for (let i = 0; i < Math.min(concurrency, tasks.length); i++) {
    workers.push(runNext())
  }
}

const withTimeout = (promise, ms) => {
  return Promise.race([
    promise,
    new Promise((_, reject) => setTimeout(() => reject(new Error('请求超时')), ms))
  ])
}

const generateTask = async (task) => {
  if (task.status === 'processing') return
  task.status = 'processing'
  task.statusText = '生成中...'
  task.resultSrc = ''
  task.videoUrl = ''

  let maxRetry = 0
  try {
    const settings = await window.pywebview.api.get_all_settings()
    if (settings.auto_retry === 'true') {
      const key = task.resultType === 'image' ? 'image_max_retry' : 'video_max_retry'
      maxRetry = parseInt(settings[key] || '3', 10)
    }
  } catch { /* ignore */ }

  let attempts = 0
  let lastError = ''

  while (attempts <= maxRetry) {
    if (attempts > 0) {
      task.statusText = `重试中 (${attempts}/${maxRetry})...`
    }
    try {
      let res
      if (task.resultType === 'image') {
        const refImage = task.images.length > 0 ? task.images[0].base64 : ''
        const refMime = task.images.length > 0 ? task.images[0].mime_type : ''
        // #region agent log
        fetch('http://127.0.0.1:7245/ingest/8dff99d0-fbea-493b-89fa-39b8c697a46c',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'GlineFlow.vue:generateTask:beforeCall',message:'about to call glineflow_image',data:{taskId:task.id,model:task.model,hasRefImage:refImage.length>0,refImageLen:refImage.length},timestamp:Date.now(),hypothesisId:'D'})}).catch(()=>{});
        // #endregion
        res = await withTimeout(
          window.pywebview.api.glineflow_image(task.prompt, task.model, refImage, refMime),
          300000
        )
        // #region agent log
        fetch('http://127.0.0.1:7245/ingest/8dff99d0-fbea-493b-89fa-39b8c697a46c',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'GlineFlow.vue:generateTask:afterCall',message:'glineflow_image returned',data:{taskId:task.id,resOk:res.ok,hasImageData:!!res.image_data,imageDataLen:res.image_data?res.image_data.length:0,mimeType:res.mime_type,resMsg:res.msg||''},timestamp:Date.now(),hypothesisId:'A,B,D'})}).catch(()=>{});
        // #endregion
        if (res.ok && res.image_data) {
          task.resultSrc = `data:${res.mime_type};base64,${res.image_data}`
          task.resultBase64 = res.image_data
          task.resultMime = res.mime_type
          task.status = 'completed'
          task.statusText = '已完成'
          return
        }
        lastError = res.msg || '生成失败'
      } else {
        const imagesJson = task.images.length > 0
          ? JSON.stringify(task.images.map(i => ({ base64: i.base64, mime_type: i.mime_type })))
          : ''
        const timeout = 650000
        res = await withTimeout(
          window.pywebview.api.glineflow_video(task.prompt, task.model, imagesJson),
          timeout
        )
        if (res.ok && res.video_url) {
          task.videoUrl = res.video_url
          task.status = 'completed'
          task.statusText = '已完成'
          downloadVideo(task, true)
          return
        }
        lastError = res.msg || '生成失败'
      }
    } catch (e) {
      lastError = String(e)
      // #region agent log
      fetch('http://127.0.0.1:7245/ingest/8dff99d0-fbea-493b-89fa-39b8c697a46c',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'GlineFlow.vue:generateTask:catch',message:'exception caught',data:{taskId:task.id,error:String(e),attempt:attempts},timestamp:Date.now(),hypothesisId:'C,D'})}).catch(()=>{});
      // #endregion
    }
    attempts++
  }

  // #region agent log
  fetch('http://127.0.0.1:7245/ingest/8dff99d0-fbea-493b-89fa-39b8c697a46c',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'GlineFlow.vue:generateTask:failed',message:'task marked failed',data:{taskId:task.id,lastError,attempts},timestamp:Date.now(),hypothesisId:'B,C'})}).catch(()=>{});
  // #endregion
  task.status = 'failed'
  task.statusText = lastError
}

// ==================== 操作 ====================
const deleteTask = (idx) => {
  const task = taskList.value[idx]
  if (task.status === 'processing') {
    emit('toast', '任务正在处理中，无法删除', 'error')
    return
  }
  taskList.value.splice(idx, 1)
}

const deleteAllTasks = () => {
  if (taskList.value.some(t => t.status === 'processing')) {
    emit('toast', '有任务正在处理中，无法全部删除', 'error')
    return
  }
  taskList.value = []
}

const retryTask = (task) => {
  task.status = 'pending'
  task.statusText = '待处理'
  generateTask(task)
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
    const res = await window.pywebview.api.download_image(task.resultBase64, task.resultMime, 'glineflow')
    if (res.ok) emit('toast', '图片已保存', 'success')
    else emit('toast', res.msg || '下载失败', 'error')
  } catch { emit('toast', '下载异常', 'error') }
}

const downloadVideo = async (task, silent = false) => {
  if (!task.videoUrl) { if (!silent) emit('toast', '暂无视频链接', 'error'); return }
  try {
    if (!silent) emit('toast', '开始下载...', 'success')
    const res = await window.pywebview.api.download_veo_video(task.videoUrl)
    if (res.ok) { if (!silent) emit('toast', '视频已保存', 'success') }
    else { if (!silent) emit('toast', res.msg || '下载失败', 'error') }
  } catch { if (!silent) emit('toast', '下载异常', 'error') }
}

// ==================== 预览 ====================
const previewSrc = ref('')
const previewType = ref('image')
const showPreview = ref(false)
const openPreview = (src, type = 'image') => { previewSrc.value = src; previewType.value = type; showPreview.value = true }
const closePreview = () => { showPreview.value = false; previewSrc.value = '' }

// ==================== 过滤任务列表 ====================
const filteredTasks = computed(() => {
  return taskList.value.filter(t => t.tab === activeTab.value)
})

const tabLabel = (key) => {
  const t = tabs.find(x => x.key === key)
  return t ? t.label : key
}
</script>

<template>
  <div class="page">
    <!-- 顶栏 -->
    <div class="page-toolbar">
      <h2 class="page-title">Glin Flow</h2>
      <div class="toolbar-actions">
        <span v-if="stats.total > 0" class="stats-text">
          共 {{ stats.total }} 条
          <template v-if="stats.processing > 0"> · <span class="stats-processing">{{ stats.processing }} 处理中</span></template>
          <template v-if="stats.completed > 0"> · <span class="stats-completed">{{ stats.completed }} 完成</span></template>
          <template v-if="stats.failed > 0"> · <span class="stats-failed">{{ stats.failed }} 失败</span></template>
        </span>
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

    <!-- TabLayout -->
    <div class="tab-bar">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        :class="['tab-item', { active: activeTab === tab.key }]"
        @click="activeTab = tab.key"
      >{{ tab.label }}</button>
    </div>

    <!-- 内容区 -->
    <div class="page-body">
      <!-- 空状态 -->
      <div v-if="filteredTasks.length === 0" class="empty-state">
        <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/>
          <polyline points="13 2 13 9 20 9"/>
        </svg>
        <p class="empty-text">暂无{{ tabLabel(activeTab) }}任务</p>
        <p class="empty-hint">点击"添加任务"按钮开始生成</p>
      </div>

      <!-- 列表 -->
      <div v-else class="list-wrap">
        <div class="list-header">
          <div class="col col-index">#</div>
          <div v-if="activeTab === 'i2i' || activeTab === 'i2v' || activeTab === 'r2v'" class="col col-origin">原图</div>
          <div class="col col-prompt">提示词</div>
          <div class="col col-model">模型</div>
          <div class="col col-status">状态</div>
          <div v-if="activeTab === 't2i' || activeTab === 'i2i'" class="col col-result">结果</div>
          <div class="col col-actions">操作</div>
        </div>
        <div
          v-for="(task, idx) in filteredTasks"
          :key="task.id"
          class="list-row"
        >
          <div class="col col-index">{{ filteredTasks.length - idx }}</div>
          <div v-if="activeTab === 'i2i' || activeTab === 'i2v' || activeTab === 'r2v'" class="col col-origin">
            <div class="thumb-group">
              <div
                v-for="(img, i) in task.images.slice(0, 3)"
                :key="i"
                class="thumb clickable"
                @click="openPreview(img.preview)"
              ><img :src="img.preview" alt="原图" /></div>
              <span v-if="task.images.length > 3" class="thumb-more">+{{ task.images.length - 3 }}</span>
            </div>
          </div>
          <div
            class="col col-prompt copyable"
            :title="task.prompt + '\n（点击复制）'"
            @click="copyPrompt(task.prompt)"
          >{{ task.prompt }}</div>
          <div class="col col-model">
            <span class="model-tag" :title="task.model">{{ task.modelLabel }}</span>
          </div>
          <div class="col col-status">
            <span :class="['status-tag', task.status]">{{ task.statusText }}</span>
          </div>
          <div v-if="activeTab === 't2i' || activeTab === 'i2i'" class="col col-result">
            <div v-if="task.resultSrc" class="thumb clickable" @click="openPreview(task.resultSrc)"><img :src="task.resultSrc" alt="结果" /></div>
            <span v-else class="no-result">—</span>
          </div>
          <div class="col col-actions">
            <!-- 图片结果操作 -->
            <template v-if="task.resultType === 'image'">
              <button v-if="task.resultSrc" class="action-btn view-btn" @click="openPreview(task.resultSrc)" title="查看">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
              </button>
              <button v-if="task.resultSrc" class="action-btn download-btn" @click="downloadImage(task)" title="下载">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
              </button>
            </template>
            <!-- 视频结果操作 -->
            <template v-else>
              <button v-if="task.videoUrl" class="action-btn view-btn" @click="openPreview(task.videoUrl, 'video')" title="播放">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>
              </button>
              <button v-if="task.videoUrl" class="action-btn download-btn" @click="downloadVideo(task)" title="下载">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
              </button>
            </template>
            <button v-if="task.status === 'failed'" class="action-btn retry-btn" @click="retryTask(task)" title="重试">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
            </button>
            <button class="action-btn delete-btn" @click="deleteTask(taskList.indexOf(task))" :disabled="task.status === 'processing'" title="删除">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
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
            <h3 class="dialog-title">添加{{ tabLabel(currentTabForDialog) }}任务</h3>
            <button class="dialog-close" @click="closeAddDialog">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>
          <div class="dialog-body">
            <!-- 模型选择 -->
            <label class="field">
              <span class="field-label">模型</span>
              <select v-model="addModel" class="model-select">
                <option v-for="m in currentModels" :key="m.value" :value="m.value">{{ m.label }}</option>
              </select>
            </label>

            <!-- 批量模式切换 -->
            <div class="batch-toggle" style="margin-top: 14px;">
              <label class="batch-switch" @click.prevent="addBatchMode = !addBatchMode">
                <span class="batch-switch-track" :class="{ active: addBatchMode }">
                  <span class="batch-switch-thumb"></span>
                </span>
                <span class="batch-switch-label">批量模式</span>
              </label>
              <span v-if="addBatchMode" class="batch-hint">
                {{ needsImages && ['i2i','i2v'].includes(currentTabForDialog) ? '每张图片生成独立任务' : '每行提示词生成独立任务' }}
              </span>
            </div>

            <!-- 图片上传区 -->
            <div v-if="needsImages" class="field" style="margin-top: 16px;">
              <span class="field-label">
                <template v-if="addBatchMode && ['i2i','i2v'].includes(currentTabForDialog)">图片（每张图片生成一个独立任务）</template>
                <template v-else>图片{{ currentTabForDialog === 'i2i' ? '（1张）' : currentTabForDialog === 'i2v' ? '（1-2张：首帧/尾帧）' : '（多张参考图）' }}</template>
              </span>
              <div
                v-if="addImages.length < maxImages"
                class="upload-area"
                :class="{ 'drag-active': addIsDragging }"
                @click="addFileInput?.click()"
                @dragenter="onDragEnter"
                @dragover="onDragOver"
                @dragleave="onDragLeave"
                @drop="onDrop"
              >
                <input ref="addFileInput" type="file" accept="image/*" :multiple="maxImages > 1" class="upload-input" @change="handleAddFileSelect" />
                <svg class="upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
                </svg>
                <span class="upload-text">点击或拖拽图片到此处</span>
                <span class="upload-hint">已选 {{ addImages.length }} / {{ maxImages }} 张</span>
              </div>
              <div v-if="addImages.length > 0" class="image-preview-list">
                <div v-for="(img, i) in addImages" :key="i" class="ref-image-preview">
                  <img :src="img.preview" alt="参考图" />
                  <button class="remove-btn" @click="removeImage(i)" title="移除">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                  </button>
                </div>
              </div>
            </div>

            <!-- 提示词 -->
            <label class="field" style="margin-top: 16px;">
              <span class="field-label">
                <template v-if="addBatchMode && !(needsImages && ['i2i','i2v'].includes(currentTabForDialog))">提示词（每行一条，每行生成独立任务）</template>
                <template v-else-if="addBatchMode">提示词（所有任务共用）</template>
                <template v-else>提示词{{ (currentTabForDialog === 't2v' || currentTabForDialog === 'upsample') ? '（每行一条，随机选取）' : '' }}</template>
              </span>
              <textarea
                v-model="addPrompt"
                :placeholder="currentTabForDialog === 'upsample' ? '输入视频描述提示词' : '输入提示词'"
                rows="5"
              ></textarea>
            </label>

            <!-- 生成数量 -->
            <div class="form-row" style="margin-top: 16px;">
              <label class="field field-inline">
                <span class="field-label">{{ addBatchMode ? (needsImages && ['i2i','i2v'].includes(currentTabForDialog) ? '每张图片生成次数' : '每条提示词生成次数') : '生成数量' }}</span>
                <input v-model.number="addCount" type="number" min="1" max="100" class="num-input" />
              </label>
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

    <!-- 预览 -->
    <Teleport to="body">
      <div v-if="showPreview" class="preview-overlay" @click="closePreview">
        <button class="preview-close" @click="closePreview">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
        <img v-if="previewType === 'image'" :src="previewSrc" class="preview-img" @click.stop alt="预览" />
        <video v-else :src="previewSrc" class="preview-video" controls autoplay @click.stop />
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.page { position: relative; min-height: 100%; display: flex; flex-direction: column; }

/* ============ 顶栏 ============ */
.page-toolbar { display: flex; align-items: center; justify-content: space-between; padding: 20px 32px 12px; flex-shrink: 0; }
.page-title { margin: 0; font-size: 18px; font-weight: 600; color: var(--text-primary); }
.toolbar-actions { display: flex; gap: 10px; align-items: center; }
.stats-text { font-size: 13px; color: var(--text-muted); margin-right: 8px; }
.stats-processing { color: var(--accent); }
.stats-completed { color: var(--success); }
.stats-failed { color: var(--error); }
.tool-btn { display: flex; align-items: center; gap: 8px; padding: 8px 16px; border-radius: 10px; border: 1px solid var(--border-strong); background: var(--border-subtle); color: var(--text-secondary); font-size: 13px; font-weight: 500; cursor: pointer; transition: background 0.2s ease, border-color 0.2s ease, color 0.2s ease; }
.tool-btn:hover { background: var(--accent-bg-strong); border-color: var(--accent-border); color: var(--accent); }
.add-btn { border-color: rgba(52,199,89,0.3); background: rgba(52,199,89,0.08); color: var(--success); }
.add-btn:hover { background: rgba(52,199,89,0.18); border-color: rgba(52,199,89,0.5); color: var(--success); }
.delete-all-btn { border-color: rgba(255,69,58,0.3); background: var(--error-bg); color: var(--error); }
.delete-all-btn:hover { background: rgba(255,69,58,0.18); border-color: rgba(255,69,58,0.5); color: var(--error); }
.tool-icon { width: 16px; height: 16px; flex-shrink: 0; }

/* ============ TabLayout ============ */
.tab-bar { display: flex; gap: 0; padding: 0 32px; border-bottom: 1px solid var(--border); flex-shrink: 0; }
.tab-item { position: relative; padding: 10px 20px; border: none; background: transparent; color: var(--text-muted); font-size: 13px; font-weight: 500; cursor: pointer; transition: color 0.2s ease; }
.tab-item:hover { color: var(--text-secondary); }
.tab-item.active { color: var(--accent); }
.tab-item.active::after { content: ''; position: absolute; bottom: -1px; left: 16px; right: 16px; height: 2px; background: var(--accent); border-radius: 2px 2px 0 0; }

/* ============ 内容区 ============ */
.page-body { flex: 1; padding: 24px 32px; overflow-y: auto; position: relative; }

/* ============ 空状态 ============ */
.empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 80px 20px; }
.empty-icon { width: 64px; height: 64px; color: var(--border-strong); margin-bottom: 20px; }
.empty-text { margin: 0; font-size: 16px; font-weight: 500; color: var(--text-placeholder); }
.empty-hint { margin: 8px 0 0; font-size: 13px; color: var(--text-hint); }

/* ============ 列表 ============ */
.list-wrap { border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }
.list-header, .list-row { display: flex; align-items: center; }
.list-header { background: var(--bg-card); padding: 10px 16px; border-bottom: 1px solid var(--border); }
.list-header .col { font-size: 12px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
.list-row { padding: 12px 16px; border-bottom: 1px solid var(--border-light); transition: background 0.15s ease; }
.list-row:last-child { border-bottom: none; }
.list-row:hover { background: var(--border-subtle); }

.col-index { width: 40px; flex-shrink: 0; text-align: center; }
.col-origin { width: 100px; flex-shrink: 0; }
.col-prompt { flex: 1; min-width: 0; padding: 0 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; color: var(--text-secondary); }
.col-prompt.copyable { cursor: pointer; transition: color 0.15s ease; }
.col-prompt.copyable:hover { color: var(--accent); }
.col-model { width: 160px; flex-shrink: 0; padding: 0 8px; }
.col-status { width: 120px; flex-shrink: 0; text-align: center; }
.col-result { width: 80px; flex-shrink: 0; }
.col-actions { width: 160px; flex-shrink: 0; display: flex; justify-content: center; gap: 6px; }

/* 模型标签 */
.model-tag { display: inline-block; padding: 2px 8px; border-radius: 5px; font-size: 11px; font-weight: 500; background: var(--accent-bg); color: var(--accent); max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* 缩略图 */
.thumb-group { display: flex; gap: 4px; align-items: center; }
.thumb { width: 42px; height: 42px; border-radius: 6px; overflow: hidden; background: var(--bg-surface); border: 1px solid var(--border); flex-shrink: 0; }
.thumb img { width: 100%; height: 100%; object-fit: cover; display: block; }
.thumb.clickable { cursor: pointer; transition: opacity 0.15s ease; }
.thumb.clickable:hover { opacity: 0.8; }
.thumb-more { font-size: 11px; color: var(--text-placeholder); }
.no-result { font-size: 13px; color: var(--text-dim); display: flex; width: 42px; height: 42px; align-items: center; justify-content: center; }

/* 状态标签 */
.status-tag { display: inline-block; padding: 3px 10px; border-radius: 6px; font-size: 11px; font-weight: 600; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.status-tag.pending { background: rgba(255,214,10,0.1); color: #ffd60a; }
.status-tag.processing { background: var(--accent-bg); color: var(--accent); }
.status-tag.completed { background: var(--success-bg); color: var(--success); }
.status-tag.failed { background: var(--error-bg); color: var(--error); }

/* 操作按钮 */
.action-btn { width: 34px; height: 34px; padding: 0; display: flex; align-items: center; justify-content: center; border-radius: 8px; border: 1px solid var(--border-medium); background: var(--border-light); color: var(--text-tertiary); cursor: pointer; transition: all 0.15s ease; }
.action-btn:disabled { opacity: 0.35; cursor: not-allowed; }
.action-btn svg { width: 15px; height: 15px; }
.view-btn:hover { background: var(--accent-bg-strong); border-color: var(--accent-border); color: var(--accent); }
.download-btn:hover { background: rgba(52,199,89,0.15); border-color: rgba(52,199,89,0.4); color: var(--success); }
.retry-btn:hover { background: rgba(255,214,10,0.15); border-color: rgba(255,214,10,0.4); color: #ffd60a; }
.delete-btn:hover:not(:disabled) { background: var(--error-bg); border-color: rgba(255,69,58,0.4); color: var(--error); }

/* ============ 弹窗 ============ */
.dialog-overlay { position: fixed; inset: 0; z-index: 1000; display: flex; align-items: center; justify-content: center; background: rgba(0,0,0,0.6); backdrop-filter: blur(4px); }
.dialog { width: min(580px, calc(100% - 40px)); max-height: 90vh; border-radius: 16px; background: linear-gradient(180deg, var(--bg-card), var(--bg-surface)); border: 1px solid var(--border-medium); box-shadow: 0 24px 60px rgba(0,0,0,0.12); overflow: hidden; display: flex; flex-direction: column; }
.dialog-header { display: flex; align-items: center; justify-content: space-between; padding: 18px 24px; border-bottom: 1px solid var(--border); flex-shrink: 0; }
.dialog-title { margin: 0; font-size: 16px; font-weight: 600; color: var(--text-primary); }
.dialog-close { display: flex; align-items: center; justify-content: center; width: 32px; height: 32px; padding: 0; border-radius: 8px; border: none; background: transparent; color: var(--text-muted); cursor: pointer; transition: background 0.15s ease, color 0.15s ease; }
.dialog-close:hover { background: var(--border-medium); color: var(--text-strong); }
.dialog-close svg { width: 18px; height: 18px; }
.dialog-body { padding: 24px; overflow-y: auto; flex: 1; }
.dialog-footer { display: flex; justify-content: flex-end; gap: 12px; padding: 16px 24px; border-top: 1px solid var(--border); flex-shrink: 0; }
.cancel-btn { padding: 10px 20px; border-radius: 10px; border: 1px solid var(--border-strong); background: var(--border-subtle); color: var(--text-secondary); font-size: 13px; font-weight: 500; cursor: pointer; transition: background 0.2s ease, color 0.2s ease; }
.cancel-btn:hover { background: var(--border-strong); color: var(--text-strong); }
.save-btn { width: auto; padding: 10px 24px; font-size: 13px; }
.save-btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none !important; box-shadow: none !important; }

.field { display: flex; flex-direction: column; gap: 8px; }
.field-label { font-size: 13px; color: var(--text-tertiary); }

/* 模型选择 */
.model-select { width: 100%; padding: 10px 14px; border-radius: 10px; border: 1px solid var(--border-medium); background: var(--bg-surface); color: var(--text-primary); font-size: 14px; outline: none; transition: border-color 0.2s ease, box-shadow 0.2s ease; appearance: none; -webkit-appearance: none; background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%23888' stroke-width='2'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E"); background-repeat: no-repeat; background-position: right 14px center; padding-right: 36px; }
.model-select:focus { border-color: var(--accent-focus); box-shadow: 0 0 0 3px var(--accent-bg-strong); }
.model-select option { background: var(--bg-surface); color: var(--text-primary); }

.dialog-body textarea { width: 100%; padding: 12px 14px; border-radius: 12px; border: 1px solid var(--border-medium); background: var(--bg-surface); color: var(--text-primary); font-size: 14px; font-family: inherit; outline: none; resize: vertical; transition: border-color 0.2s ease, box-shadow 0.2s ease; }
.dialog-body textarea::placeholder { color: var(--text-placeholder); }
.dialog-body textarea:focus { border-color: var(--accent-focus); box-shadow: 0 0 0 3px var(--accent-bg-strong); }

.form-row { display: flex; gap: 24px; align-items: flex-start; }
.field-inline { flex: 1; }
.num-input { width: 100%; padding: 10px 14px; border-radius: 10px; border: 1px solid var(--border-medium); background: var(--bg-surface); color: var(--text-primary); font-size: 14px; outline: none; transition: border-color 0.2s ease, box-shadow 0.2s ease; }
.num-input:focus { border-color: var(--accent-focus); box-shadow: 0 0 0 3px var(--accent-bg-strong); }

/* 上传区 */
/* 批量模式开关 */
.batch-toggle { display: flex; align-items: center; gap: 12px; }
.batch-switch { display: flex; align-items: center; gap: 8px; cursor: pointer; user-select: none; }
.batch-switch-track { position: relative; width: 36px; height: 20px; border-radius: 10px; background: var(--border-strong); transition: background 0.2s ease; }
.batch-switch-track.active { background: var(--accent-focus); }
.batch-switch-thumb { position: absolute; top: 2px; left: 2px; width: 16px; height: 16px; border-radius: 50%; background: var(--text-tertiary); transition: transform 0.2s ease, background 0.2s ease; }
.batch-switch-track.active .batch-switch-thumb { transform: translateX(16px); background: #fff; }
.batch-switch-label { font-size: 13px; font-weight: 500; color: var(--text-secondary); }
.batch-hint { font-size: 12px; color: var(--accent); }

.upload-area { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; padding: 24px 20px; border-radius: 12px; border: 2px dashed var(--border-strong); background: var(--bg-surface); cursor: pointer; transition: border-color 0.2s ease, background 0.2s ease; }
.upload-area:hover, .upload-area.drag-active { border-color: var(--accent-border); background: var(--accent-bg-subtle); }
.upload-input { display: none; }
.upload-icon { width: 32px; height: 32px; color: var(--text-hint); }
.upload-text { font-size: 14px; color: var(--text-tertiary); }
.upload-hint { font-size: 12px; color: var(--text-hint); }

.image-preview-list { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px; }
.ref-image-preview { position: relative; display: inline-block; border-radius: 10px; overflow: hidden; border: 1px solid var(--border-medium); background: var(--bg-surface); }
.ref-image-preview img { display: block; width: 80px; height: 80px; object-fit: cover; }
.remove-btn { position: absolute; top: 4px; right: 4px; width: 22px; height: 22px; padding: 0; display: flex; align-items: center; justify-content: center; border-radius: 6px; border: none; background: var(--bg-card); color: var(--text-strong); cursor: pointer; transition: background 0.2s ease; box-shadow: 0 1px 4px rgba(0,0,0,0.15); }
.remove-btn:hover { background: rgba(255,69,58,0.8); }
.remove-btn svg { width: 12px; height: 12px; }

/* ============ 预览 ============ */
.preview-overlay { position: fixed; inset: 0; z-index: 2000; display: flex; align-items: center; justify-content: center; background: rgba(0,0,0,0.85); backdrop-filter: blur(8px); cursor: zoom-out; }
.preview-close { position: absolute; top: 20px; right: 20px; width: 40px; height: 40px; padding: 0; display: flex; align-items: center; justify-content: center; border-radius: 10px; border: none; background: rgba(255,255,255,0.2); color: rgba(255,255,255,0.95); cursor: pointer; transition: background 0.15s ease; z-index: 1; }
.preview-close:hover { background: var(--border-strong); }
.preview-close svg { width: 20px; height: 20px; }
.preview-img { max-width: 90vw; max-height: 90vh; object-fit: contain; border-radius: 8px; cursor: default; }
.preview-video { max-width: 90vw; max-height: 90vh; border-radius: 8px; cursor: default; outline: none; }
</style>
