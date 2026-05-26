<script setup>
import { ref, reactive, computed } from 'vue'

const emit = defineEmits(['toast'])

const taskList = ref([])
let taskIdCounter = 0

const showAddDialog = ref(false)
const addPrompts = ref('')
const addCount = ref(1)
const addOrientation = ref('landscape')
const addDuration = ref(10)

const openAddDialog = () => {
  addPrompts.value = ''
  addCount.value = 1
  addOrientation.value = 'landscape'
  addDuration.value = 10
  showAddDialog.value = true
}
const closeAddDialog = () => { showAddDialog.value = false }

const stats = computed(() => {
  const total = taskList.value.length
  const completed = taskList.value.filter(t => t.status === 'completed').length
  const processing = taskList.value.filter(t => t.status === 'processing').length
  const failed = taskList.value.filter(t => t.status === 'failed').length
  const pending = taskList.value.filter(t => t.status === 'pending').length
  return { total, completed, processing, failed, pending }
})

const submitAddTask = () => {
  const lines = addPrompts.value.split('\n').map(l => l.trim()).filter(l => l)
  if (lines.length === 0) {
    emit('toast', '请输入至少一条提示词', 'error')
    return
  }
  const count = Math.max(1, Math.min(100, parseInt(addCount.value) || 1))
  const orientation = addOrientation.value
  const duration = parseInt(addDuration.value) || 10

  const newTasks = []
  for (let i = 0; i < count; i++) {
    const prompt = lines[Math.floor(Math.random() * lines.length)]
    const task = reactive({
      id: ++taskIdCounter,
      prompt,
      orientation,
      duration,
      status: 'pending',
      statusText: '待处理',
      videoUrl: '',
    })
    newTasks.push(task)
    taskList.value.unshift(task)
  }

  showAddDialog.value = false
  emit('toast', `已添加 ${count} 条任务，开始生成...`, 'success')

  startGeneration(newTasks)
}

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

const generateTask = async (task) => {
  if (task.status === 'processing') return
  task.status = 'processing'
  task.statusText = '生成中...'
  task.videoUrl = ''

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
    if (attempts > 0) {
      task.statusText = `重试中 (${attempts}/${maxRetry})...`
    }
    try {
      const res = await window.pywebview.api.generate_media_video(
        task.prompt,
        [],
        task.orientation,
        task.duration,
        'sora2',
        '',
      )
      if (res.ok && res.video_url) {
        task.videoUrl = res.video_url
        task.status = 'completed'
        task.statusText = '已完成'
        downloadVideo(task, true)
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

const downloadVideo = async (task, silent = false) => {
  if (!task.videoUrl) {
    if (!silent) emit('toast', '暂无视频链接', 'error')
    return
  }
  try {
    if (!silent) emit('toast', '开始下载...', 'success')
    const res = await window.pywebview.api.download_veo_video(task.videoUrl)
    if (res.ok) {
      if (!silent) emit('toast', '视频已保存', 'success')
    } else {
      if (!silent) emit('toast', res.msg || '下载失败', 'error')
    }
  } catch {
    if (!silent) emit('toast', '下载异常', 'error')
  }
}

const copyPrompt = async (text) => {
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    emit('toast', '提示词已复制', 'success')
  } catch { emit('toast', '复制失败', 'error') }
}

const previewUrl = ref('')
const showPreview = ref(false)
const openPreview = (url) => { previewUrl.value = url; showPreview.value = true }
const closePreview = () => { showPreview.value = false; previewUrl.value = '' }
</script>

<template>
  <div class="page">
    <div class="page-toolbar">
      <h2 class="page-title">Sora2 视频生成</h2>
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

    <div class="page-body">
      <div v-if="taskList.length === 0" class="empty-state">
        <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <polygon points="23 7 16 12 23 17 23 7"></polygon>
          <rect x="1" y="5" width="15" height="14" rx="2" ry="2"></rect>
        </svg>
        <p class="empty-text">暂无 Sora2 视频任务</p>
        <p class="empty-hint">点击"添加任务"按钮批量生成文生视频</p>
      </div>

      <div v-else class="list-wrap">
        <div class="list-header">
          <div class="col col-index">#</div>
          <div class="col col-prompt">提示词</div>
          <div class="col col-orientation">方向</div>
          <div class="col col-duration">时长</div>
          <div class="col col-status">状态</div>
          <div class="col col-actions">操作</div>
        </div>
        <div
          v-for="(task, idx) in taskList"
          :key="task.id"
          class="list-row"
        >
          <div class="col col-index">{{ taskList.length - idx }}</div>
          <div
            class="col col-prompt copyable"
            :title="task.prompt + '\n（点击复制）'"
            @click="copyPrompt(task.prompt)"
          >{{ task.prompt }}</div>
          <div class="col col-orientation">
            <span class="orientation-tag" :class="task.orientation">
              {{ task.orientation === 'landscape' ? '横屏' : '竖屏' }}
            </span>
          </div>
          <div class="col col-duration">{{ task.duration }}s</div>
          <div class="col col-status">
            <span :class="['status-tag', task.status]">{{ task.statusText }}</span>
          </div>
          <div class="col col-actions">
            <button
              v-if="task.videoUrl"
              class="action-btn view-btn"
              @click="openPreview(task.videoUrl)"
              title="播放"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polygon points="5 3 19 12 5 21 5 3"/>
              </svg>
            </button>
            <button
              v-if="task.videoUrl"
              class="action-btn download-btn"
              @click="downloadVideo(task)"
              title="下载"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
              </svg>
            </button>
            <button
              v-if="task.status === 'failed'"
              class="action-btn retry-btn"
              @click="retryTask(task)"
              title="重试"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
              </svg>
            </button>
            <button
              class="action-btn delete-btn"
              @click="deleteTask(idx)"
              :disabled="task.status === 'processing'"
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
      <div v-if="showAddDialog" class="dialog-overlay" @click.self="closeAddDialog">
        <div class="dialog">
          <div class="dialog-header">
            <h3 class="dialog-title">添加 Sora2 视频生成任务</h3>
            <button class="dialog-close" @click="closeAddDialog">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>
          <div class="dialog-body">
            <label class="field">
              <span class="field-label">提示词（每行一条，生成时随机选取）</span>
              <textarea
                v-model="addPrompts"
                placeholder="输入视频提示词，每行一条&#10;例如：&#10;一只小猫在草地上追逐蝴蝶&#10;夕阳下的海边沙滩，海浪轻轻拍打"
                rows="8"
              ></textarea>
            </label>
            <div class="form-row">
              <label class="field field-inline">
                <span class="field-label">生成数量</span>
                <input
                  v-model.number="addCount"
                  type="number"
                  min="1"
                  max="100"
                  class="num-input"
                />
              </label>
              <div class="field field-inline">
                <span class="field-label">视频方向</span>
                <div class="orientation-group">
                  <button
                    :class="['orient-btn', { active: addOrientation === 'landscape' }]"
                    @click="addOrientation = 'landscape'"
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="orient-icon">
                      <rect x="2" y="5" width="20" height="14" rx="2"/>
                    </svg>
                    横屏
                  </button>
                  <button
                    :class="['orient-btn', { active: addOrientation === 'portrait' }]"
                    @click="addOrientation = 'portrait'"
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="orient-icon">
                      <rect x="5" y="2" width="14" height="20" rx="2"/>
                    </svg>
                    竖屏
                  </button>
                </div>
              </div>
            </div>
            <div class="form-row" style="margin-top: 12px;">
              <div class="field field-inline">
                <span class="field-label">视频时长</span>
                <div class="duration-group">
                  <button
                    :class="['duration-btn', { active: addDuration === 10 }]"
                    @click="addDuration = 10"
                  >10秒</button>
                  <button
                    :class="['duration-btn', { active: addDuration === 15 }]"
                    @click="addDuration = 15"
                  >15秒</button>
                </div>
              </div>
            </div>
          </div>
          <div class="dialog-footer">
            <button class="cancel-btn" @click="closeAddDialog">取消</button>
            <button class="primary-btn save-btn" @click="submitAddTask">添加并生成</button>
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
        <video :src="previewUrl" class="preview-video" controls autoplay @click.stop />
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
.delete-all-btn { border-color: rgba(255,69,58,0.3); background: rgba(255,69,58,0.08); color: var(--error); }
.delete-all-btn:hover { background: rgba(255,69,58,0.18); border-color: rgba(255,69,58,0.5); color: var(--error); }
.tool-icon { width: 16px; height: 16px; flex-shrink: 0; }

.page-body { flex: 1; padding: 24px 32px; overflow-y: auto; position: relative; }

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
.col-prompt { flex: 1; min-width: 0; padding: 0 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; color: var(--text-secondary); }
.col-prompt.copyable { cursor: pointer; transition: color 0.15s ease; }
.col-prompt.copyable:hover { color: var(--accent); }
.col-orientation { width: 70px; flex-shrink: 0; text-align: center; }
.col-duration { width: 60px; flex-shrink: 0; text-align: center; font-size: 13px; color: var(--text-secondary); }
.col-status { width: 120px; flex-shrink: 0; text-align: center; }
.col-actions { width: 160px; flex-shrink: 0; display: flex; justify-content: center; gap: 6px; }

.orientation-tag { display: inline-block; padding: 2px 8px; border-radius: 5px; font-size: 11px; font-weight: 600; }
.orientation-tag.landscape { background: var(--accent-bg); color: var(--accent); }
.orientation-tag.portrait { background: rgba(175,82,222,0.1); color: #bf5af2; }

.status-tag { display: inline-block; padding: 3px 10px; border-radius: 6px; font-size: 11px; font-weight: 600; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.status-tag.pending { background: rgba(255,214,10,0.1); color: #ffd60a; }
.status-tag.processing { background: var(--accent-bg); color: var(--accent); }
.status-tag.completed { background: var(--success-bg); color: var(--success); }
.status-tag.failed { background: var(--error-bg); color: var(--error); }

.action-btn { width: 34px; height: 34px; padding: 0; display: flex; align-items: center; justify-content: center; border-radius: 8px; border: 1px solid var(--border-medium); background: var(--border-light); color: var(--text-tertiary); cursor: pointer; transition: all 0.15s ease; }
.action-btn:disabled { opacity: 0.35; cursor: not-allowed; }
.action-btn svg { width: 15px; height: 15px; }
.view-btn:hover { background: var(--accent-bg-strong); border-color: rgba(200,96,122,0.4); color: var(--accent); }
.download-btn:hover { background: rgba(52,199,89,0.15); border-color: rgba(52,199,89,0.4); color: var(--success); }
.retry-btn:hover { background: rgba(255,214,10,0.15); border-color: rgba(255,214,10,0.4); color: #ffd60a; }
.delete-btn:hover:not(:disabled) { background: rgba(255,69,58,0.15); border-color: rgba(255,69,58,0.4); color: var(--error); }

.dialog-overlay { position: fixed; inset: 0; z-index: 1000; display: flex; align-items: center; justify-content: center; background: rgba(0,0,0,0.6); backdrop-filter: blur(4px); }
.dialog { width: min(560px, calc(100% - 40px)); border-radius: 16px; background: var(--bg-card); border: 1px solid var(--border-medium); box-shadow: var(--shadow-dialog); overflow: hidden; }
.dialog-header { display: flex; align-items: center; justify-content: space-between; padding: 18px 24px; border-bottom: 1px solid var(--border); }
.dialog-title { margin: 0; font-size: 16px; font-weight: 600; color: var(--text-primary); }
.dialog-close { display: flex; align-items: center; justify-content: center; width: 32px; height: 32px; padding: 0; border-radius: 8px; border: none; background: transparent; color: var(--text-muted); cursor: pointer; transition: background 0.15s ease, color 0.15s ease; }
.dialog-close:hover { background: var(--border-medium); color: var(--text-primary); }
.dialog-close svg { width: 18px; height: 18px; }
.dialog-body { padding: 24px; }
.dialog-footer { display: flex; justify-content: flex-end; gap: 12px; padding: 16px 24px; border-top: 1px solid var(--border); }
.cancel-btn { padding: 10px 20px; border-radius: 10px; border: 1px solid var(--border-strong); background: var(--border-subtle); color: var(--text-secondary); font-size: 13px; font-weight: 500; cursor: pointer; transition: background 0.2s ease, color 0.2s ease; }
.cancel-btn:hover { background: var(--border-strong); color: var(--text-primary); }
.save-btn { width: auto; padding: 10px 24px; font-size: 13px; }

.field { display: flex; flex-direction: column; gap: 8px; }
.field-label { font-size: 13px; color: var(--text-tertiary); }

.dialog-body textarea { width: 100%; padding: 12px 14px; border-radius: 12px; border: 1px solid var(--border-medium); background: var(--bg-surface); color: var(--text-primary); font-size: 14px; font-family: inherit; outline: none; resize: vertical; transition: border-color 0.2s ease, box-shadow 0.2s ease; }
.dialog-body textarea::placeholder { color: var(--text-placeholder); }
.dialog-body textarea:focus { border-color: rgba(200,96,122,0.6); box-shadow: 0 0 0 3px var(--accent-bg-strong); }

.form-row { display: flex; gap: 24px; margin-top: 16px; align-items: flex-start; }
.field-inline { flex: 1; }

.num-input { width: 100%; padding: 10px 14px; border-radius: 10px; border: 1px solid var(--border-medium); background: var(--bg-surface); color: var(--text-primary); font-size: 14px; outline: none; transition: border-color 0.2s ease, box-shadow 0.2s ease; }
.num-input:focus { border-color: rgba(200,96,122,0.6); box-shadow: 0 0 0 3px var(--accent-bg-strong); }

.orientation-group, .duration-group { display: flex; gap: 8px; }
.orient-btn, .duration-btn { display: flex; align-items: center; gap: 6px; padding: 8px 16px; border-radius: 10px; border: 1px solid var(--border-strong); background: var(--border-light); color: var(--text-tertiary); font-size: 13px; font-weight: 500; cursor: pointer; transition: all 0.2s ease; }
.orient-btn:hover, .duration-btn:hover { background: var(--accent-bg); border-color: var(--accent-focus); color: var(--text-secondary); }
.orient-btn.active, .duration-btn.active { background: var(--accent-bg-strong); border-color: rgba(200,96,122,0.4); color: var(--accent); }
.orient-icon { width: 18px; height: 18px; flex-shrink: 0; }

.preview-overlay { position: fixed; inset: 0; z-index: 2000; display: flex; align-items: center; justify-content: center; background: rgba(0,0,0,0.85); backdrop-filter: blur(8px); cursor: zoom-out; }
.preview-close { position: absolute; top: 20px; right: 20px; width: 40px; height: 40px; padding: 0; display: flex; align-items: center; justify-content: center; border-radius: 10px; border: none; background: rgba(255,255,255,0.15); color: rgba(255,255,255,0.9); cursor: pointer; transition: background 0.15s ease; z-index: 1; }
.preview-close:hover { background: rgba(255,255,255,0.25); }
.preview-close svg { width: 20px; height: 20px; }
.preview-video { max-width: 90vw; max-height: 90vh; border-radius: 8px; cursor: default; outline: none; }
</style>
