<script setup>
import { ref, reactive, computed, onMounted } from 'vue'

const props = defineProps({
  pageTitle: {
    type: String,
    default: 'Sora2多镜头',
  },
  videoPlatform: {
    type: String,
    default: 'sora2',
  },
  settingsKeyPrefix: {
    type: String,
    default: 'multi_shot_sora2',
  },
})

const emit = defineEmits(['toast'])

const imageGeneratorOptions = ref([])
const videoGeneratorOptions = ref([])

const selectedImagePlatform = ref('nanobanana')
const selectedImageProvider = ref('yunwu')
const selectedVideoPlatform = ref(props.videoPlatform)
const selectedVideoProvider = ref(props.videoPlatform === 'veo3' ? 'hetang' : 'dayangyu')

// ==================== 默认提示词 ====================
const MULTI_SHOT_PROMPT_ARRAY_KEY = 'multi_shot_product_prompt_pairs'
const MULTI_SHOT_PROMPT_RECORD_ENABLED_KEY = 'multi_shot_prompt_record_enabled'
const DEFAULT_MULTI_SHOT_IMAGE_PROMPT = '请根据图片中的产品，为其绘制一个真实、自然的展示场景。场景需要与产品类型相匹配，突出产品本身，背景环境要逼真有质感。注意：画面中不要出现任何文字、标签或水印。'
const DEFAULT_MULTI_SHOT_VIDEO_PROMPT = '根据图片内容生成一段自然流畅的展示视频'

const imagePlatformSettingKey = `${props.settingsKeyPrefix}_image_platform`
const imageProviderSettingKey = `${props.settingsKeyPrefix}_image_provider`
const videoPlatformSettingKey = `${props.settingsKeyPrefix}_video_platform`
const videoProviderSettingKey = `${props.settingsKeyPrefix}_video_provider`

const isSora2Mode = computed(() => selectedVideoPlatform.value === 'sora2')
const batchDialogTitle = computed(() => `批量添加${props.pageTitle}任务`)
const addDialogTitle = computed(() => `添加${props.pageTitle}任务`)
const emptyStateTitle = computed(() => `暂无${props.pageTitle}任务`)

const resolveImageDefaults = (settings = {}) => {
  if (settings.nanobanana_model === 'gpt-image:bandianwa') {
    return { platform: 'gpt-image', provider: 'bandianwa' }
  }
  if (settings.nanobanana_model === 'gpt-image:xiaobanshou') {
    return { platform: 'gpt-image', provider: 'xiaobanshou' }
  }
  if (settings.nanobanana_model) {
    return { platform: 'nanobanana', provider: settings.nanobanana_model }
  }
  return {
    platform: settings[imagePlatformSettingKey] || 'nanobanana',
    provider: settings[imageProviderSettingKey] || 'yunwu',
  }
}

const resolveVideoDefaults = (settings = {}) => {
  if (props.videoPlatform === 'veo3') {
    return {
      platform: 'veo3',
      provider: settings.veo_model || settings[videoProviderSettingKey] || 'hetang',
    }
  }
  return {
    platform: 'sora2',
    provider: settings.sora2_model || settings[videoProviderSettingKey] || 'dayangyu',
  }
}

const defaultImagePrompt = ref(DEFAULT_MULTI_SHOT_IMAGE_PROMPT)
const defaultVideoPrompt = ref(DEFAULT_MULTI_SHOT_VIDEO_PROMPT)
const savedPromptPairs = ref([])
const isPromptRecordEnabled = ref(true)

const showPromptDialog = ref(false)
const promptDialogType = ref('image')
const promptDialogText = ref('')

const buildDefaultPromptPairs = () => ([{
  imagePrompt: DEFAULT_MULTI_SHOT_IMAGE_PROMPT,
  videoPrompt: DEFAULT_MULTI_SHOT_VIDEO_PROMPT,
}])

const buildEmptyPromptPairs = () => ([{
  imagePrompt: '',
  videoPrompt: '',
}])

const parseBooleanSetting = (value, fallback = true) => {
  if (value === undefined || value === null || value === '') return fallback
  if (typeof value === 'boolean') return value
  return String(value).toLowerCase() === 'true'
}

const normalizePromptText = (value) => (
  typeof value === 'string' ? value.trim() : ''
)

const normalizeStoredPromptPairs = (raw) => {
  let parsed = raw
  if (typeof raw === 'string') {
    try {
      parsed = JSON.parse(raw)
    } catch {
      return buildDefaultPromptPairs()
    }
  }
  if (!Array.isArray(parsed)) {
    return buildDefaultPromptPairs()
  }
  const pairs = parsed
    .map(item => ({
      imagePrompt: normalizePromptText(item?.imagePrompt),
      videoPrompt: normalizePromptText(item?.videoPrompt),
    }))
    .filter(item => item.imagePrompt || item.videoPrompt)
    .map(item => ({
      imagePrompt: item.imagePrompt || DEFAULT_MULTI_SHOT_IMAGE_PROMPT,
      videoPrompt: item.videoPrompt || DEFAULT_MULTI_SHOT_VIDEO_PROMPT,
    }))
  return pairs.length ? pairs : buildDefaultPromptPairs()
}

const applySavedPromptPairs = (raw, recordEnabled = isPromptRecordEnabled.value) => {
  isPromptRecordEnabled.value = recordEnabled
  if (!recordEnabled) {
    savedPromptPairs.value = []
    defaultImagePrompt.value = ''
    defaultVideoPrompt.value = ''
    return buildEmptyPromptPairs()
  }
  const pairs = normalizeStoredPromptPairs(raw)
  savedPromptPairs.value = pairs
  defaultImagePrompt.value = pairs[0].imagePrompt
  defaultVideoPrompt.value = pairs[0].videoPrompt
  return pairs
}

const loadSavedPromptPairs = async (settingsOverride = null) => {
  try {
    const settings = settingsOverride || await window.pywebview.api.get_all_settings()
    const recordEnabled = parseBooleanSetting(settings?.[MULTI_SHOT_PROMPT_RECORD_ENABLED_KEY], true)
    return applySavedPromptPairs(settings?.[MULTI_SHOT_PROMPT_ARRAY_KEY], recordEnabled)
  } catch {
    return applySavedPromptPairs(null, isPromptRecordEnabled.value)
  }
}

const persistSavedPromptPairs = async (pairs) => {
  const normalized = normalizeStoredPromptPairs(pairs)
  await window.pywebview.api.save_settings({
    [MULTI_SHOT_PROMPT_ARRAY_KEY]: JSON.stringify(normalized),
  })
  return applySavedPromptPairs(normalized)
}

const getProviderOptions = (options, platform) =>
  options.filter(item => item.platform === platform)

const formatGeneratorLabel = (options, platform, provider) => {
  if (!platform) return ''
  const matched = options.find(item => item.platform === platform && item.provider === provider)
  if (matched) return `${matched.platform_label} / ${matched.provider_label}`
  return provider ? `${platform} / ${provider}` : platform
}

const normalizeGeneratorSelection = (options, platform, provider) => {
  const providerOptions = getProviderOptions(options, platform)
  if (!providerOptions.length) {
    return { platform, provider }
  }
  const matched = providerOptions.find(item => item.provider === provider)
  if (matched) {
    return { platform: matched.platform, provider: matched.provider }
  }
  const fallback = providerOptions.find(item => item.configured) || providerOptions[0]
  return { platform: fallback.platform, provider: fallback.provider }
}

const applyGeneratorSelections = (settings = {}, generatorRes = null) => {
  if (generatorRes?.ok) {
    imageGeneratorOptions.value = generatorRes.image_options || []
    videoGeneratorOptions.value = generatorRes.video_options || []
  }

  const imagePreference = resolveImageDefaults(settings)
  const imageDefaults = normalizeGeneratorSelection(
    imageGeneratorOptions.value,
    imagePreference.platform,
    imagePreference.provider,
  )
  selectedImagePlatform.value = imageDefaults.platform
  selectedImageProvider.value = imageDefaults.provider

  const videoPreference = resolveVideoDefaults(settings)
  const videoDefaults = normalizeGeneratorSelection(
    videoGeneratorOptions.value,
    videoPreference.platform,
    videoPreference.provider,
  )
  selectedVideoPlatform.value = videoDefaults.platform
  selectedVideoProvider.value = videoDefaults.provider
}

const refreshGeneratorSelections = async (settingsOverride = null) => {
  const [settings, generatorRes] = await Promise.all([
    settingsOverride ? Promise.resolve(settingsOverride) : window.pywebview.api.get_all_settings(),
    window.pywebview.api.get_media_generator_options(),
  ])
  applyGeneratorSelections(settings, generatorRes)
  return settings
}

const openPromptDialog = async (type) => {
  await loadSavedPromptPairs()
  if (!isPromptRecordEnabled.value) {
    emit('toast', '已关闭多镜头提示词记录，请在添加任务弹窗中直接填写', 'error')
    return
  }
  promptDialogType.value = type
  promptDialogText.value = type === 'image' ? defaultImagePrompt.value : defaultVideoPrompt.value
  showPromptDialog.value = true
}
const closePromptDialog = () => { showPromptDialog.value = false }
const savePromptDialog = async () => {
  const text = promptDialogText.value.trim()
  if (!text) { emit('toast', '提示词不能为空', 'error'); return }
  if (!isPromptRecordEnabled.value) {
    emit('toast', '已关闭多镜头提示词记录', 'error')
    return
  }
  try {
    const currentPairs = normalizeStoredPromptPairs(savedPromptPairs.value)
    const firstPair = { ...currentPairs[0] }
    if (promptDialogType.value === 'image') {
      firstPair.imagePrompt = text
    } else {
      firstPair.videoPrompt = text
    }
    currentPairs[0] = firstPair
    await persistSavedPromptPairs(currentPairs)
    emit('toast', '提示词已保存', 'success')
    showPromptDialog.value = false
  } catch { emit('toast', '保存失败', 'error') }
}

onMounted(async () => {
  try {
    const [settings, generatorRes] = await Promise.all([
      window.pywebview.api.get_all_settings(),
      window.pywebview.api.get_media_generator_options(),
    ])
    applySavedPromptPairs(settings?.[MULTI_SHOT_PROMPT_ARRAY_KEY])
    if (settings.glin_nanobanana_ratio) dialogImageRatio.value = settings.glin_nanobanana_ratio
    if (settings.glin_nanobanana_quality) dialogImageQuality.value = settings.glin_nanobanana_quality
    if (settings.hetang_veo_orientation) dialogVideoOrientation.value = settings.hetang_veo_orientation
    if (settings.sora2_duration) {
      const duration = parseInt(settings.sora2_duration, 10) || 10
      dialogVideoDuration.value = duration
      batchVideoDuration.value = duration
    }
    applyGeneratorSelections(settings, generatorRes)
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
let dialogPromptPairIdCounter = 0
const createDialogPromptPair = (imagePrompt = defaultImagePrompt.value, videoPrompt = defaultVideoPrompt.value) => ({
  id: ++dialogPromptPairIdCounter,
  imagePrompt,
  videoPrompt,
})
const dialogPromptPairs = ref([])
const dialogImageRatio = ref('9:16')
const dialogImageQuality = ref('1K')
const dialogVideoOrientation = ref('portrait')
const dialogVideoDuration = ref(10)
const dialogAutoVideo = ref(true)
const dialogTaskCount = computed(() => dialogPromptPairs.value.length || 1)
const dialogIsDragging = ref(false)
const dialogFileInput = ref(null)

const openAddDialog = async () => {
  dialogImages.value = []
  const settings = await refreshGeneratorSelections().catch(() => null)
  const pairs = await loadSavedPromptPairs(settings)
  dialogPromptPairs.value = pairs.map(pair => createDialogPromptPair(pair.imagePrompt, pair.videoPrompt))
  showDialog.value = true
}

const closeDialog = () => { showDialog.value = false }

const addDialogPromptPair = () => {
  const lastPair = dialogPromptPairs.value[dialogPromptPairs.value.length - 1]
  dialogPromptPairs.value.push(
    createDialogPromptPair(
      lastPair?.imagePrompt || defaultImagePrompt.value,
      lastPair?.videoPrompt || defaultVideoPrompt.value,
    ),
  )
}

const removeDialogPromptPair = (idx) => {
  if (dialogPromptPairs.value.length <= 1) return
  dialogPromptPairs.value.splice(idx, 1)
}

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
  await openBatchDialog(imgs)
}

// ==================== 批量添加弹窗 ====================
const showBatchDialog = ref(false)
const batchImages = ref([])
const batchImagePrompt = ref('')
const batchVideoPrompt = ref('')
const batchImageRatio = ref('9:16')
const batchImageQuality = ref('1K')
const batchVideoOrientation = ref('portrait')
const batchVideoDuration = ref(10)
const batchAutoVideo = ref(true)

const persistGeneratorDefaults = () => {
  window.pywebview.api.save_settings({
    [imagePlatformSettingKey]: selectedImagePlatform.value,
    [imageProviderSettingKey]: selectedImageProvider.value,
    [videoPlatformSettingKey]: selectedVideoPlatform.value,
    [videoProviderSettingKey]: selectedVideoProvider.value,
  }).catch(() => {})
}

const openBatchDialog = async (imgs) => {
  const settings = await refreshGeneratorSelections().catch(() => null)
  const pairs = await loadSavedPromptPairs(settings)
  batchImages.value = imgs
  batchImagePrompt.value = pairs[0].imagePrompt
  batchVideoPrompt.value = pairs[0].videoPrompt
  showBatchDialog.value = true
}
const closeBatchDialog = () => { showBatchDialog.value = false; batchImages.value = [] }
const removeBatchImage = (idx) => {
  batchImages.value.splice(idx, 1)
  if (!batchImages.value.length) closeBatchDialog()
}

const submitBatchDialog = () => {
  if (!batchImages.value.length) { emit('toast', '没有可用的图片', 'error'); return }
  const imagePrompt = batchImagePrompt.value.trim()
  const videoPrompt = batchVideoPrompt.value.trim()
  if (!imagePrompt) { emit('toast', '请输入图片提示词', 'error'); return }
  if (!videoPrompt) { emit('toast', '请输入视频提示词', 'error'); return }

  window.pywebview.api.save_settings({
    glin_nanobanana_ratio: batchImageRatio.value,
    glin_nanobanana_quality: batchImageQuality.value,
    hetang_veo_orientation: batchVideoOrientation.value,
    sora2_duration: String(batchVideoDuration.value),
    [imagePlatformSettingKey]: selectedImagePlatform.value,
    [imageProviderSettingKey]: selectedImageProvider.value,
    [videoPlatformSettingKey]: selectedVideoPlatform.value,
    [videoProviderSettingKey]: selectedVideoProvider.value,
  }).catch(() => {})

  const tasks = batchImages.value.map(img => reactive({
    id: ++taskIdCounter,
    images: [{ ...img }],
    imagePrompt,
    imageRatio: batchImageRatio.value,
    imageQuality: batchImageQuality.value,
    videoPrompt,
    videoOrientation: batchVideoOrientation.value,
    videoDuration: batchVideoDuration.value,
    imagePlatform: selectedImagePlatform.value,
    imageProvider: selectedImageProvider.value,
    videoPlatform: selectedVideoPlatform.value,
    videoProvider: selectedVideoProvider.value,
    autoVideo: batchAutoVideo.value,
    resultImageSrc: '',
    resultImageBase64: '',
    resultImageMime: '',
    resultImagePath: '',
    videoUrl: '',
    filePath: '',
    actualImagePlatform: '',
    actualImageProvider: '',
    actualVideoPlatform: '',
    actualVideoProvider: '',
    status: 'pending',
    statusText: '待处理',
  }))

  taskList.value.unshift(...tasks)
  showBatchDialog.value = false
  batchImages.value = []

  emit('toast', `已添加 ${tasks.length} 条任务，开始生成...`, 'success')
  persistGeneratorDefaults()
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

const applyActualGenerator = (task, type, res) => {
  const platformKey = type === 'image' ? 'actualImagePlatform' : 'actualVideoPlatform'
  const providerKey = type === 'image' ? 'actualImageProvider' : 'actualVideoProvider'
  task[platformKey] = res?.platform || ''
  task[providerKey] = res?.provider || ''
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
const submitDialog = async () => {
  if (!dialogImages.value.length) { emit('toast', '请先选择图片', 'error'); return }
  const promptPairs = dialogPromptPairs.value.map((pair) => ({
    imagePrompt: pair.imagePrompt.trim(),
    videoPrompt: pair.videoPrompt.trim(),
  }))
  const invalidPairIndex = promptPairs.findIndex(pair => !pair.imagePrompt || !pair.videoPrompt)
  if (invalidPairIndex !== -1) {
    emit('toast', `请完善第 ${invalidPairIndex + 1} 组提示词`, 'error')
    return
  }

  if (isPromptRecordEnabled.value) {
    defaultImagePrompt.value = promptPairs[0].imagePrompt
    defaultVideoPrompt.value = promptPairs[0].videoPrompt
  } else {
    defaultImagePrompt.value = ''
    defaultVideoPrompt.value = ''
  }

  window.pywebview.api.save_settings({
    glin_nanobanana_ratio: dialogImageRatio.value,
    glin_nanobanana_quality: dialogImageQuality.value,
    hetang_veo_orientation: dialogVideoOrientation.value,
    sora2_duration: String(dialogVideoDuration.value),
    [imagePlatformSettingKey]: selectedImagePlatform.value,
    [imageProviderSettingKey]: selectedImageProvider.value,
    [videoPlatformSettingKey]: selectedVideoPlatform.value,
    [videoProviderSettingKey]: selectedVideoProvider.value,
  }).catch(() => {})
  if (isPromptRecordEnabled.value) {
    try {
      await persistSavedPromptPairs(promptPairs)
    } catch {
      emit('toast', '多分镜提示词保存失败', 'error')
    }
  }

  const images = dialogImages.value.map(img => ({ ...img }))
  const tasks = promptPairs.map((pair) => reactive({
      id: ++taskIdCounter,
      images: images.map(img => ({ ...img })),
      imagePrompt: pair.imagePrompt,
      imageRatio: dialogImageRatio.value,
      imageQuality: dialogImageQuality.value,
      videoPrompt: pair.videoPrompt,
      videoOrientation: dialogVideoOrientation.value,
      videoDuration: dialogVideoDuration.value,
      imagePlatform: selectedImagePlatform.value,
      imageProvider: selectedImageProvider.value,
      videoPlatform: selectedVideoPlatform.value,
      videoProvider: selectedVideoProvider.value,
      autoVideo: dialogAutoVideo.value,
      resultImageSrc: '',
      resultImageBase64: '',
      resultImageMime: '',
      resultImagePath: '',
      videoUrl: '',
      filePath: '',
      actualImagePlatform: '',
      actualImageProvider: '',
      actualVideoPlatform: '',
      actualVideoProvider: '',
      status: 'pending',
      statusText: '待处理',
    }))
  taskList.value.unshift(...tasks)
  showDialog.value = false

  persistGeneratorDefaults()
  emit('toast', `已添加 ${tasks.length} 条任务，开始生成...`, 'success')
  startBatchGeneration(tasks)
}

// ==================== 图片生成 → 自动生成视频 ====================
const generateImage = async (task) => {
  task.status = 'image_processing'
  task.statusText = '图片生成中...'
  task.resultImageSrc = ''
  task.resultImageBase64 = ''
  task.resultImageMime = ''
  task.resultImagePath = ''
  task.actualImagePlatform = ''
  task.actualImageProvider = ''
  task.actualVideoPlatform = ''
  task.actualVideoProvider = ''

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
        task.imagePlatform,
        task.imageProvider,
      )
      applyActualGenerator(task, 'image', res)
      if (res.ok && res.image_data && res.mime_type) {
        task.resultImageSrc = `data:${res.mime_type};base64,${res.image_data}`
        task.resultImageBase64 = res.image_data
        task.resultImageMime = res.mime_type
        task.resultImagePath = res.file_path || ''
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
  task.actualVideoPlatform = ''
  task.actualVideoProvider = ''

  let maxRetry = 0
  try {
    const settings = await window.pywebview.api.get_all_settings()
    if (settings.auto_retry === 'true') {
      maxRetry = parseInt(settings.video_max_retry || '3', 10)
    }
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
        task.videoDuration || 10,
        task.videoPlatform,
        task.videoProvider,
      )
      applyActualGenerator(task, 'video', res)
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
  task.actualVideoPlatform = ''
  task.actualVideoProvider = ''
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
    const res = await window.pywebview.api.download_image(task.resultImageBase64, task.resultImageMime, 'video_product')
    if (res.ok) {
      task.resultImagePath = res.path || task.resultImagePath
      emit('toast', '图片已保存', 'success')
    }
    else emit('toast', res.msg || '下载失败', 'error')
  } catch { emit('toast', '下载异常', 'error') }
}

const downloadVideo = async (task, silent = false) => {
  if (!task.videoUrl) { if (!silent) emit('toast', '暂无视频链接', 'error'); return }
  try {
    if (!silent) emit('toast', '开始下载视频...', 'success')
    const res = await window.pywebview.api.download_veo_video(task.videoUrl)
    if (res.ok) {
      task.filePath = res.path || task.filePath
      if (!silent) emit('toast', '视频已保存', 'success')
    }
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
const editVideoPlatform = ref(props.videoPlatform)
const editVideoOrientation = ref('portrait')
const editVideoDuration = ref(10)

const openEditDialog = (task) => {
  if (isTaskBusy(task)) return
  editingTask.value = task
  editImagePrompt.value = task.imagePrompt
  editVideoPrompt.value = task.videoPrompt
  editImageRatio.value = task.imageRatio
  editImageQuality.value = task.imageQuality
  editVideoPlatform.value = task.videoPlatform || task.actualVideoPlatform || selectedVideoPlatform.value
  editVideoOrientation.value = task.videoOrientation
  editVideoDuration.value = task.videoDuration || 10
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
  task.videoDuration = editVideoDuration.value
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
      <h2 class="page-title">{{ props.pageTitle }}</h2>
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
          <span>默认图片提示词</span>
        </button>
        <button class="tool-btn prompt-btn" @click="openPromptDialog('video')">
          <svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>
          </svg>
          <span>默认视频提示词</span>
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
        <p class="drag-text">松开鼠标批量添加商品图</p>
        <p class="drag-hint">每张图片将创建一条独立任务</p>
      </div>

      <!-- 空状态 -->
      <div v-if="taskList.length === 0 && !pageDragging" class="empty-state">
        <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
          <line x1="8" y1="21" x2="16" y2="21"/>
          <line x1="12" y1="17" x2="12" y2="21"/>
        </svg>
        <p class="empty-text">{{ emptyStateTitle }}</p>
        <p class="empty-hint">点击"添加任务"，用同一组图片录入多组提示词</p>
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
            <div
              v-if="task.actualImagePlatform || task.actualVideoPlatform"
              class="channel-meta"
            >
              <div v-if="task.actualImagePlatform" class="channel-line">
                实际图片: {{ formatGeneratorLabel(imageGeneratorOptions, task.actualImagePlatform, task.actualImageProvider) }}
              </div>
              <div v-if="task.actualVideoPlatform" class="channel-line">
                实际视频: {{ formatGeneratorLabel(videoGeneratorOptions, task.actualVideoPlatform, task.actualVideoProvider) }}
              </div>
            </div>
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
            <h3 class="dialog-title">{{ batchDialogTitle }}（{{ batchImages.length }} 张图 = {{ batchImages.length }} 条任务）</h3>
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
              <div v-if="isSora2Mode" class="form-row">
                <div class="field field-inline">
                  <span class="field-label">视频时长</span>
                  <div class="toggle-group">
                    <button :class="['toggle-btn', { active: batchVideoDuration === 10 }]" @click="batchVideoDuration = 10">10S</button>
                    <button :class="['toggle-btn', { active: batchVideoDuration === 15 }]" @click="batchVideoDuration = 15">15S</button>
                  </div>
                </div>
              </div>
              <div v-else class="form-row">
                <div class="field field-inline">
                  <span class="field-label">视频时长</span>
                  <div class="fixed-value">约 8 秒（渠道固定）</div>
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
        <div class="dialog dialog--image dialog--multi-shot">
          <div class="dialog-header">
            <h3 class="dialog-title">{{ addDialogTitle }}</h3>
            <button class="dialog-close" @click="closeDialog">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>
          <div class="dialog-body dialog-body--split dialog-body--multi-shot">
            <div class="dialog-left dialog-left--config">
              <div class="field">
                <span class="field-label">商品图片（必填，支持多图拖拽）</span>
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
                  <span class="upload-hint">支持 JPG / PNG / WebP，最大 10MB</span>
                </div>
              </div>

              <div class="dialog-config-panel">
                <div class="dialog-section-title">参数设置</div>
                <div class="dialog-section-hint">这一套参数会应用到右侧所有任务</div>
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
                <div class="field field-inline dialog-field-gap">
                  <span class="field-label">图片清晰度</span>
                  <div class="toggle-group">
                    <button :class="['toggle-btn', { active: dialogImageQuality === '1K' }]" @click="dialogImageQuality = '1K'">1K</button>
                    <button :class="['toggle-btn', { active: dialogImageQuality === '2K' }]" @click="dialogImageQuality = '2K'">2K</button>
                    <button :class="['toggle-btn', { active: dialogImageQuality === '4K' }]" @click="dialogImageQuality = '4K'">4K</button>
                  </div>
                </div>
                <div class="field field-inline dialog-field-gap">
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
                <div v-if="isSora2Mode" class="field field-inline dialog-field-gap">
                  <span class="field-label">视频时长</span>
                  <div class="toggle-group">
                    <button :class="['toggle-btn', { active: dialogVideoDuration === 10 }]" @click="dialogVideoDuration = 10">10S</button>
                    <button :class="['toggle-btn', { active: dialogVideoDuration === 15 }]" @click="dialogVideoDuration = 15">15S</button>
                  </div>
                </div>
                <div v-else class="field field-inline dialog-field-gap">
                  <span class="field-label">视频时长</span>
                  <div class="fixed-value">约 8 秒（渠道固定）</div>
                </div>
                <label class="switch-field dialog-field-gap dialog-switch-field">
                  <span class="switch-label">自动生成视频</span>
                  <button
                    :class="['switch-track', { active: dialogAutoVideo }]"
                    @click="dialogAutoVideo = !dialogAutoVideo"
                  >
                    <span class="switch-thumb" />
                  </button>
                  <span class="switch-hint">{{ dialogAutoVideo ? '图片完成后自动生成视频' : '图片完成后暂停，手动确认再生成' }}</span>
                </label>
              </div>
            </div>

            <div class="dialog-right dialog-right--prompts">
              <div class="prompt-pairs-header">
                <div>
                  <div class="dialog-section-title">任务提示词</div>
                  <div class="dialog-section-hint">同一组图片会复用到每条任务，每组提示词对应一条任务</div>
                </div>
                <button class="pair-add-btn" @click="addDialogPromptPair">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="12" y1="5" x2="12" y2="19"/>
                    <line x1="5" y1="12" x2="19" y2="12"/>
                  </svg>
                  <span>添加一组</span>
                </button>
              </div>
              <div class="prompt-pairs">
                <div
                  v-for="(pair, idx) in dialogPromptPairs"
                  :key="pair.id"
                  class="prompt-pair-card"
                >
                  <div class="prompt-pair-header">
                    <span class="prompt-pair-title">任务 {{ idx + 1 }}</span>
                    <button
                      v-if="dialogPromptPairs.length > 1"
                      class="pair-remove-btn"
                      @click="removeDialogPromptPair(idx)"
                    >
                      删除
                    </button>
                  </div>
                  <div class="field">
                    <span class="field-label">图片提示词（必填）</span>
                    <textarea v-model="pair.imagePrompt" placeholder="描述图片生成效果" rows="4"></textarea>
                  </div>
                  <div class="field dialog-field-gap">
                    <span class="field-label">视频提示词（必填）</span>
                    <textarea v-model="pair.videoPrompt" placeholder="描述视频生成效果" rows="4"></textarea>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div class="dialog-footer">
            <button class="cancel-btn" @click="closeDialog">取消</button>
            <button class="primary-btn save-btn" @click="submitDialog">
              {{ `添加 ${dialogTaskCount} 条任务并开始生成` }}
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
            <div class="form-row">
              <div v-if="editVideoPlatform === 'sora2'" class="field field-inline">
                <span class="field-label">视频时长</span>
                <div class="toggle-group">
                  <button :class="['toggle-btn', { active: editVideoDuration === 10 }]" @click="editVideoDuration = 10">10S</button>
                  <button :class="['toggle-btn', { active: editVideoDuration === 15 }]" @click="editVideoDuration = 15">15S</button>
                </div>
              </div>
              <div v-else class="field field-inline">
                <span class="field-label">视频时长</span>
                <div class="fixed-value">约 8 秒（渠道固定）</div>
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
            <h3 class="dialog-title">{{ promptDialogType === 'image' ? '默认图片提示词' : '默认视频提示词' }}</h3>
            <button class="dialog-close" @click="closePromptDialog">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>
          <div class="dialog-body">
            <label class="field">
              <span class="field-label">{{ promptDialogType === 'image' ? '用于回填首组任务的默认图片提示词' : '用于回填首组任务的默认视频提示词' }}</span>
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
.toolbar-actions { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; justify-content: flex-end; }
.generator-select-row { display: flex; gap: 8px; flex-wrap: wrap; }
.generator-select-box { position: relative; flex: 1; min-width: 0; }
.generator-select {
  width: 100%;
  min-width: 116px;
  padding: 10px 36px 10px 12px;
  border-radius: 12px;
  border: 1px solid var(--border-medium);
  background: linear-gradient(180deg, var(--bg-surface) 0%, var(--border-subtle) 100%);
  color: var(--text-primary);
  font-size: 13px;
  outline: none;
  appearance: none;
  -webkit-appearance: none;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
}
.generator-select:hover { border-color: var(--border-strong); background: var(--bg-surface); }
.generator-select:focus { border-color: rgba(200,96,122,0.45); box-shadow: 0 0 0 3px var(--accent-bg-strong); background: var(--bg-surface); }
.generator-chevron {
  position: absolute;
  right: 14px;
  top: 50%;
  width: 8px;
  height: 8px;
  border-right: 2px solid var(--text-hint);
  border-bottom: 2px solid var(--text-hint);
  transform: translateY(-65%) rotate(45deg);
  pointer-events: none;
}
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
.channel-meta { margin-top: 6px; display: flex; flex-direction: column; gap: 2px; }
.channel-line { font-size: 11px; line-height: 1.35; color: var(--text-hint); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

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
.dialog--multi-shot { width: min(1080px, calc(100% - 40px)); }
.dialog--prompt { width: min(520px, calc(100% - 40px)); }
.dialog-header { display: flex; align-items: center; justify-content: space-between; padding: 18px 24px; border-bottom: 1px solid var(--border); flex-shrink: 0; }
.dialog-title { margin: 0; font-size: 16px; font-weight: 600; color: var(--text-primary); }
.dialog-close { display: flex; align-items: center; justify-content: center; width: 32px; height: 32px; padding: 0; border-radius: 8px; border: none; background: transparent; color: var(--text-muted); cursor: pointer; transition: background 0.15s ease, color 0.15s ease; }
.dialog-close:hover { background: var(--border-medium); color: var(--text-primary); }
.dialog-close svg { width: 18px; height: 18px; }
.dialog-body { padding: 24px; overflow-y: auto; flex: 1; }
.dialog-body--split { display: flex; gap: 24px; }
.dialog-body--multi-shot { align-items: flex-start; }
.dialog-left { width: 280px; flex-shrink: 0; display: flex; flex-direction: column; }
.dialog-left--config { width: 320px; gap: 16px; }
.dialog-left .upload-area { min-height: 120px; }
.ref-images-grid { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }
.ref-images-grid .ref-image-preview img { width: 80px; height: 80px; object-fit: cover; display: block; }
.dialog-right { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.dialog-right--prompts { gap: 16px; }
.dialog-footer { display: flex; justify-content: flex-end; gap: 12px; padding: 16px 24px; border-top: 1px solid var(--border); flex-shrink: 0; }
.cancel-btn { padding: 10px 20px; border-radius: 10px; border: 1px solid var(--border-strong); background: var(--border-subtle); color: var(--text-secondary); font-size: 13px; font-weight: 500; cursor: pointer; transition: background 0.2s ease, color 0.2s ease; }
.cancel-btn:hover { background: var(--border-strong); color: var(--text-primary); }
.save-btn { width: auto; padding: 10px 24px; font-size: 13px; }

.field { display: flex; flex-direction: column; gap: 8px; }
.field-label { font-size: 13px; color: var(--text-tertiary); }
.dialog-section-title { font-size: 14px; font-weight: 600; color: var(--text-primary); }
.dialog-section-hint { margin-top: 4px; font-size: 12px; line-height: 1.5; color: var(--text-hint); }
.dialog-config-panel { padding: 16px; border-radius: 14px; border: 1px solid var(--border); background: linear-gradient(180deg, var(--bg-surface), var(--bg-card)); }
.dialog-field-gap { margin-top: 14px; }
.dialog-switch-field { align-items: flex-start; }

.dialog-body textarea { width: 100%; padding: 12px 14px; border-radius: 12px; border: 1px solid var(--border-medium); background: var(--bg-surface); color: var(--text-primary); font-size: 14px; font-family: inherit; outline: none; resize: vertical; transition: border-color 0.2s ease, box-shadow 0.2s ease; }
.dialog-body textarea::placeholder { color: var(--text-placeholder); }
.dialog-body textarea:focus { border-color: rgba(200,96,122,0.6); box-shadow: 0 0 0 3px var(--accent-bg-strong); }
.count-input { width: 90px; padding: 6px 10px; border-radius: 8px; border: 1px solid var(--border-medium); background: var(--bg-surface); color: var(--text-primary); font-size: 13px; font-family: inherit; outline: none; transition: border-color 0.2s ease, box-shadow 0.2s ease; -moz-appearance: textfield; }
.count-input::-webkit-outer-spin-button, .count-input::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
.count-input:focus { border-color: rgba(200,96,122,0.6); box-shadow: 0 0 0 3px var(--accent-bg-strong); }
.dialog-body .generator-select-box { flex: 1; }

/* 表单行 */
.form-row { display: flex; gap: 24px; margin-top: 12px; align-items: flex-start; }
.field-inline { flex: 1; }

/* 切换按钮组 */
.toggle-group { display: flex; gap: 6px; flex-wrap: wrap; }
.toggle-btn { display: flex; align-items: center; gap: 5px; padding: 7px 14px; border-radius: 8px; border: 1px solid var(--border-strong); background: var(--border-light); color: var(--text-tertiary); font-size: 12px; font-weight: 500; cursor: pointer; transition: all 0.2s ease; }
.toggle-btn:hover { background: var(--accent-bg); border-color: rgba(200,96,122,0.2); color: var(--text-secondary); }
.toggle-btn.active { background: var(--accent-bg-strong); border-color: rgba(200,96,122,0.4); color: var(--accent); }
.toggle-icon { width: 16px; height: 16px; flex-shrink: 0; }
.fixed-value { padding: 10px 12px; border-radius: 10px; border: 1px solid var(--border-medium); background: var(--bg-surface); color: var(--text-secondary); font-size: 12px; }

/* 开关 */
.switch-field { display: flex; align-items: center; gap: 10px; cursor: pointer; }
.switch-label { font-size: 13px; font-weight: 500; color: var(--text-secondary); }
.switch-track { position: relative; width: 40px; height: 22px; border-radius: 11px; border: none; background: var(--border-strong); cursor: pointer; transition: background 0.2s ease; padding: 0; flex-shrink: 0; }
.switch-track.active { background: var(--success, #34c759); }
.switch-thumb { position: absolute; top: 2px; left: 2px; width: 18px; height: 18px; border-radius: 50%; background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,0.2); transition: transform 0.2s ease; }
.switch-track.active .switch-thumb { transform: translateX(18px); }
.switch-hint { font-size: 11px; color: var(--text-hint); }

.prompt-pairs-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.prompt-pairs { display: flex; flex-direction: column; gap: 14px; }
.prompt-pair-card { padding: 16px; border-radius: 14px; border: 1px solid var(--border); background: linear-gradient(180deg, var(--bg-surface), var(--bg-card)); }
.prompt-pair-header { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 12px; }
.prompt-pair-title { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.pair-add-btn,
.pair-remove-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border-radius: 10px;
  border: 1px solid var(--border-strong);
  background: var(--border-subtle);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease, color 0.2s ease;
}
.pair-add-btn { padding: 9px 14px; flex-shrink: 0; }
.pair-add-btn svg { width: 14px; height: 14px; }
.pair-add-btn:hover { background: rgba(52,199,89,0.15); border-color: rgba(52,199,89,0.35); color: var(--success); }
.pair-remove-btn { padding: 6px 10px; }
.pair-remove-btn:hover { background: rgba(255,69,58,0.14); border-color: rgba(255,69,58,0.35); color: var(--error); }

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

@media (max-width: 980px) {
  .dialog--multi-shot { width: min(760px, calc(100% - 24px)); }
  .dialog-body--multi-shot { flex-direction: column; }
  .dialog-left--config { width: 100%; }
  .dialog-right--prompts { width: 100%; }
  .prompt-pairs-header { flex-direction: column; align-items: stretch; }
}
</style>
