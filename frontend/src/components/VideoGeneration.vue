<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const emit = defineEmits(['toast'])

// 任务列表
const taskList = ref([])
const loading = ref(false)

// 轮询
let pollTimer = null

const loadTasks = async () => {
  try {
    const res = await window.pywebview.api.get_video_tasks()
    if (res.ok) {
      taskList.value = res.tasks
    }
  } catch { /* ignore */ }
}

const startPolling = () => {
  pollTimer = setInterval(loadTasks, 5000)
}

const stopPolling = () => {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

// 删除任务
const deleteTask = async (taskId) => {
  try {
    const res = await window.pywebview.api.delete_video_task(taskId)
    if (res.ok) {
      emit('toast', '任务已删除', 'success')
      await loadTasks()
    } else {
      emit('toast', res.msg || '删除失败', 'error')
    }
  } catch {
    emit('toast', '删除异常', 'error')
  }
}

// 删除全部任务
const showDeleteAllConfirm = ref(false)
const deleteAllTasks = async () => {
  try {
    const res = await window.pywebview.api.delete_all_video_tasks()
    if (res.ok) {
      emit('toast', `已删除全部任务（共 ${res.count} 条）`, 'success')
      showDeleteAllConfirm.value = false
      await loadTasks()
    } else {
      emit('toast', res.msg || '删除失败', 'error')
    }
  } catch {
    emit('toast', '删除异常', 'error')
  }
}

// 重试失败任务
const retryTask = async (taskId) => {
  try {
    const res = await window.pywebview.api.retry_video_task(taskId)
    if (res.ok) {
      emit('toast', '任务已重新加入队列', 'success')
      await loadTasks()
    } else {
      emit('toast', res.msg || '重试失败', 'error')
    }
  } catch {
    emit('toast', '重试异常', 'error')
  }
}

// ==================== 视频提示词弹窗 ====================
const showPromptDialog = ref(false)
const defaultVideoPrompt = '根据图片内容生成一段自然流畅的展示视频'
const videoPromptText = ref(defaultVideoPrompt)
const promptSaving = ref(false)

const loadVideoPrompt = async () => {
  try {
    const res = await window.pywebview.api.get_video_process_prompt()
    if (res.ok && res.prompt) videoPromptText.value = res.prompt
  } catch { /* ignore */ }
}

const openPromptDialog = () => { showPromptDialog.value = true }
const closePromptDialog = () => { showPromptDialog.value = false }

const saveVideoPrompt = async () => {
  promptSaving.value = true
  try {
    const res = await window.pywebview.api.set_video_process_prompt(videoPromptText.value)
    if (res.ok) {
      emit('toast', '视频提示词已保存', 'success')
      showPromptDialog.value = false
    } else {
      emit('toast', res.msg || '保存失败', 'error')
    }
  } catch { emit('toast', '保存异常', 'error') }
  finally { promptSaving.value = false }
}

// ==================== 添加任务弹窗 ====================
const showAddDialog = ref(false)
const addTaskPrompt = ref('')
const addTaskImagePreview = ref('')
const addTaskImageBase64 = ref('')
const addTaskImageMime = ref('')
const addTaskSubmitting = ref(false)
const addTaskIsDragging = ref(false)
const addTaskFileInput = ref(null)

const openAddDialog = () => {
  addTaskPrompt.value = ''
  addTaskImagePreview.value = ''
  addTaskImageBase64.value = ''
  addTaskImageMime.value = ''
  showAddDialog.value = true
}
const closeAddDialog = () => { showAddDialog.value = false }

const handleAddTaskImage = (file) => {
  if (!file) return
  if (!file.type.startsWith('image/')) { emit('toast', '请选择图片文件', 'error'); return }
  if (file.size > 10 * 1024 * 1024) { emit('toast', '图片不能超过 10MB', 'error'); return }
  const reader = new FileReader()
  reader.onload = (e) => {
    const dataUrl = e.target.result
    addTaskImagePreview.value = dataUrl
    addTaskImageMime.value = file.type
    addTaskImageBase64.value = dataUrl.split(',')[1]
  }
  reader.readAsDataURL(file)
}

const handleAddTaskFileSelect = (event) => {
  const file = event.target.files[0]
  handleAddTaskImage(file)
  if (addTaskFileInput.value) addTaskFileInput.value.value = ''
}

const onAddDragEnter = (e) => { e.preventDefault(); addTaskIsDragging.value = true }
const onAddDragOver = (e) => { e.preventDefault(); addTaskIsDragging.value = true }
const onAddDragLeave = (e) => {
  e.preventDefault()
  if (e.currentTarget.contains(e.relatedTarget)) return
  addTaskIsDragging.value = false
}
const onAddDrop = (e) => {
  e.preventDefault()
  addTaskIsDragging.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) handleAddTaskImage(file)
}

const removeAddTaskImage = () => {
  addTaskImagePreview.value = ''
  addTaskImageBase64.value = ''
  addTaskImageMime.value = ''
}

const submitAddTask = async () => {
  if (!addTaskImageBase64.value) { emit('toast', '请先选择图片', 'error'); return }
  if (!addTaskPrompt.value.trim()) { emit('toast', '请输入提示词', 'error'); return }
  addTaskSubmitting.value = true
  try {
    const res = await window.pywebview.api.create_video_task(
      addTaskImageBase64.value, addTaskImageMime.value, addTaskPrompt.value
    )
    if (res.ok) {
      emit('toast', '任务已添加', 'success')
      showAddDialog.value = false
      await loadTasks()
    } else {
      emit('toast', res.msg || '添加失败', 'error')
    }
  } catch { emit('toast', '添加异常', 'error') }
  finally { addTaskSubmitting.value = false }
}

// 状态颜色映射
const statusMap = {
  pending: { text: '待处理', cls: 'pending' },
  processing: { text: '处理中', cls: 'processing' },
  completed: { text: '已完成', cls: 'completed' },
  failed: { text: '失败', cls: 'failed' },
}

const getStatusInfo = (status) => statusMap[status] || { text: status, cls: 'pending' }

// 复制提示词到剪贴板
const copyPrompt = async (text) => {
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    emit('toast', '提示词已复制', 'success')
  } catch {
    emit('toast', '复制失败', 'error')
  }
}

// 下载视频
const downloadTask = async (taskId) => {
  try {
    emit('toast', '开始下载...', 'success')
    const res = await window.pywebview.api.download_video_task(taskId)
    if (res.ok) {
      emit('toast', '下载完成', 'success')
      await loadTasks()
    } else {
      emit('toast', res.msg || '下载失败', 'error')
    }
  } catch {
    emit('toast', '下载异常', 'error')
  }
}

// ==================== 页面级拖拽批量添加 ====================
const pageDragging = ref(false)
const batchAdding = ref(false)

const onPageDragEnter = (e) => { e.preventDefault(); pageDragging.value = true }
const onPageDragOver = (e) => { e.preventDefault(); pageDragging.value = true }
const onPageDragLeave = (e) => {
  e.preventDefault()
  if (e.currentTarget.contains(e.relatedTarget)) return
  pageDragging.value = false
}

const fileToBase64 = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const dataUrl = reader.result
      resolve({ base64: dataUrl.split(',')[1], mime: file.type })
    }
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

const onPageDrop = async (e) => {
  e.preventDefault()
  pageDragging.value = false

  // 收集所有图片文件
  const files = []
  const items = e.dataTransfer?.items
  if (items) {
    for (const item of items) {
      if (item.kind === 'file') {
        const f = item.getAsFile()
        if (f && f.type.startsWith('image/')) files.push(f)
      }
    }
  }
  if (files.length === 0) {
    const rawFiles = e.dataTransfer?.files
    if (rawFiles) {
      for (const f of rawFiles) {
        if (f.type.startsWith('image/')) files.push(f)
      }
    }
  }

  if (files.length === 0) {
    emit('toast', '未检测到图片文件', 'error')
    return
  }

  // 使用已保存的视频提示词
  const prompt = videoPromptText.value || defaultVideoPrompt
  batchAdding.value = true
  let success = 0
  let fail = 0

  for (const file of files) {
    if (file.size > 10 * 1024 * 1024) { fail++; continue }
    try {
      const { base64, mime } = await fileToBase64(file)
      const res = await window.pywebview.api.create_video_task(base64, mime, prompt)
      if (res.ok) success++
      else fail++
    } catch { fail++ }
  }

  batchAdding.value = false
  if (success > 0) {
    emit('toast', `批量添加完成：成功 ${success} 个${fail > 0 ? '，失败 ' + fail + ' 个' : ''}`, 'success')
    await loadTasks()
  } else {
    emit('toast', '批量添加失败', 'error')
  }
}

// ==================== 视频预览弹窗 ====================
const showVideoPreview = ref(false)
const previewVideoUrl = ref('')

const openVideoPreview = (url) => {
  previewVideoUrl.value = url
  showVideoPreview.value = true
}

const closeVideoPreview = () => {
  showVideoPreview.value = false
  previewVideoUrl.value = ''
}

onMounted(() => {
  loadVideoPrompt()
  loadTasks()
  startPolling()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<template>
  <div class="page">
    <!-- 顶栏 -->
    <div class="page-toolbar">
      <h2 class="page-title">视频生成</h2>
      <div class="toolbar-actions">
        <button class="tool-btn" @click="loadTasks">
          <svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
          </svg>
          <span>刷新</span>
        </button>
        <button class="tool-btn" @click="openPromptDialog">
          <svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
          </svg>
          <span>视频提示词</span>
        </button>
        <button class="tool-btn add-btn" @click="openAddDialog">
          <svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          <span>添加任务</span>
        </button>
        <button
          v-if="taskList.length > 0"
          class="tool-btn delete-all-btn"
          @click="showDeleteAllConfirm = true"
        >
          <svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
          </svg>
          <span>删除全部</span>
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
        <p class="drag-text">松开鼠标批量添加视频任务</p>
        <p class="drag-hint">每张图片将使用当前视频提示词创建一个任务</p>
      </div>

      <!-- 批量添加中遮罩 -->
      <div v-if="batchAdding" class="drag-overlay batch-adding-overlay">
        <p class="drag-text">正在批量添加任务...</p>
      </div>

      <!-- 空状态 -->
      <div v-if="taskList.length === 0 && !pageDragging && !batchAdding" class="empty-state">
        <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>
        </svg>
        <p class="empty-text">暂无视频任务</p>
        <p class="empty-hint">点击上方"添加任务"按钮，或直接拖拽图片到此处批量创建任务</p>
      </div>

      <!-- 列表 -->
      <div v-else-if="!pageDragging && !batchAdding" class="list-wrap">
        <div class="list-header">
          <div class="col col-index">#</div>
          <div class="col col-thumb">图片</div>
          <div class="col col-prompt">提示词</div>
          <div class="col col-status">状态</div>
          <div class="col col-url">Video URL</div>
          <div class="col col-actions">操作</div>
        </div>
        <div
          v-for="(task, idx) in taskList"
          :key="task.id"
          class="list-row"
        >
          <div class="col col-index">{{ taskList.length - idx }}</div>
          <div class="col col-thumb">
            <div v-if="task.image_path" class="thumb">
              <img :src="'file://' + task.image_path" alt="图片" @error="(e) => e.target.style.display='none'" />
            </div>
            <span v-else class="no-result">-</span>
          </div>
          <div
            class="col col-prompt copyable"
            :title="task.prompt ? task.prompt + '\n（点击复制）' : ''"
            @click="copyPrompt(task.prompt)"
          >{{ task.prompt || '-' }}</div>
          <div class="col col-status">
            <span :class="['status-tag', getStatusInfo(task.status).cls]">
              {{ getStatusInfo(task.status).text }}
            </span>
          </div>
          <div class="col col-url">
            <button
              v-if="task.video_url"
              class="play-btn"
              @click="openVideoPreview(task.video_url)"
              title="查看视频"
            >
              <svg class="play-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polygon points="5 3 19 12 5 21 5 3"/>
              </svg>
              <span>播放</span>
            </button>
            <span v-else class="no-result">-</span>
          </div>
          <div class="col col-actions">
            <button
              v-if="task.status === 'failed' || task.status === 'completed'"
              class="action-btn retry-btn"
              @click="retryTask(task.id)"
              :title="task.status === 'completed' ? '重新生成' : '重试'"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
              </svg>
            </button>
            <button
              v-if="task.video_url"
              class="action-btn download-btn"
              @click="downloadTask(task.id)"
              title="下载视频"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
              </svg>
            </button>
            <button
              class="action-btn delete-btn"
              @click="deleteTask(task.id)"
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

    <!-- 视频提示词弹窗 -->
    <Teleport to="body">
      <div v-if="showPromptDialog" class="dialog-overlay" @click.self="closePromptDialog">
        <div class="dialog">
          <div class="dialog-header">
            <h3 class="dialog-title">视频提示词设置</h3>
            <button class="dialog-close" @click="closePromptDialog">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>
          <div class="dialog-body">
            <label class="field">
              <span class="field-label">视频生成提示词（将应用于自动创建的视频任务）</span>
              <textarea
                v-model="videoPromptText"
                placeholder="请输入视频生成提示词"
                rows="8"
              ></textarea>
            </label>
          </div>
          <div class="dialog-footer">
            <button class="cancel-btn" @click="closePromptDialog">取消</button>
            <button class="primary-btn save-btn" @click="saveVideoPrompt" :disabled="promptSaving">
              {{ promptSaving ? '保存中...' : '保存' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 添加任务弹窗 -->
    <Teleport to="body">
      <div v-if="showAddDialog" class="dialog-overlay" @click.self="closeAddDialog">
        <div class="dialog">
          <div class="dialog-header">
            <h3 class="dialog-title">添加视频任务</h3>
            <button class="dialog-close" @click="closeAddDialog">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>
          <div class="dialog-body">
            <!-- 拖拽图片区域 -->
            <div class="field">
              <span class="field-label">图片（必填，支持拖拽）</span>
              <div
                v-if="!addTaskImagePreview"
                class="upload-area"
                :class="{ 'drag-active': addTaskIsDragging }"
                @click="addTaskFileInput?.click()"
                @dragenter="onAddDragEnter"
                @dragover="onAddDragOver"
                @dragleave="onAddDragLeave"
                @drop="onAddDrop"
              >
                <input ref="addTaskFileInput" type="file" accept="image/*" class="upload-input" @change="handleAddTaskFileSelect" />
                <svg class="upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
                </svg>
                <span class="upload-text">点击或拖拽图片到此处</span>
                <span class="upload-hint">支持 JPG / PNG / WebP，最大 10MB</span>
              </div>
              <div v-else class="ref-image-preview">
                <img :src="addTaskImagePreview" alt="任务图片" />
                <button class="remove-btn" @click="removeAddTaskImage" title="移除图片">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                </button>
              </div>
            </div>
            <label class="field" style="margin-top: 16px;">
              <span class="field-label">提示词</span>
              <textarea
                v-model="addTaskPrompt"
                placeholder="请输入视频生成提示词"
                rows="4"
              ></textarea>
            </label>
          </div>
          <div class="dialog-footer">
            <button class="cancel-btn" @click="closeAddDialog">取消</button>
            <button class="primary-btn save-btn" @click="submitAddTask" :disabled="addTaskSubmitting">
              {{ addTaskSubmitting ? '添加中...' : '添加任务' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 删除全部确认弹窗 -->
    <Teleport to="body">
      <div v-if="showDeleteAllConfirm" class="dialog-overlay" @click.self="showDeleteAllConfirm = false">
        <div class="dialog" style="width: min(400px, calc(100% - 40px));">
          <div class="dialog-header">
            <h3 class="dialog-title">确认删除全部</h3>
            <button class="dialog-close" @click="showDeleteAllConfirm = false">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>
          <div class="dialog-body">
            <p style="margin: 0; color: var(--text-secondary); font-size: 14px;">确定要删除全部 <strong>{{ taskList.length }}</strong> 条视频任务吗？此操作不可撤销。</p>
          </div>
          <div class="dialog-footer">
            <button class="cancel-btn" @click="showDeleteAllConfirm = false">取消</button>
            <button class="primary-btn save-btn delete-confirm-btn" @click="deleteAllTasks">确认删除</button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 视频预览弹窗 -->
    <Teleport to="body">
      <div v-if="showVideoPreview" class="preview-overlay" @click="closeVideoPreview">
        <button class="preview-close" @click="closeVideoPreview">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
        <div class="preview-video-wrap" @click.stop>
          <video
            :src="previewVideoUrl"
            controls
            autoplay
            preload="auto"
            class="preview-video"
          ></video>
        </div>
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
.add-btn { border-color: rgba(52,199,89,0.3); background: rgba(52,199,89,0.08); color: var(--success); }
.add-btn:hover { background: rgba(52,199,89,0.18); border-color: rgba(52,199,89,0.5); color: var(--success); }
.tool-icon { width: 16px; height: 16px; flex-shrink: 0; }

/* ============ 内容区 ============ */
.page-body { flex: 1; padding: 24px 32px; overflow-y: auto; position: relative; transition: background 0.2s ease; }
.page-body.drag-active { background: var(--accent-bg-subtle); }

/* ============ 拖拽 ============ */
.drag-overlay { position: absolute; inset: 16px; z-index: 10; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; border-radius: 16px; border: 2px dashed var(--accent-focus); background: var(--accent-bg); pointer-events: none; }
.batch-adding-overlay { border-style: solid; border-color: rgba(52,199,89,0.4); background: rgba(52,199,89,0.06); }
.drag-icon { width: 48px; height: 48px; color: rgba(200,96,122,0.7); }
.drag-text { margin: 0; font-size: 16px; font-weight: 500; color: rgba(200,96,122,0.8); }
.drag-hint { margin: 0; font-size: 13px; color: var(--accent-focus); }

/* ============ 空状态 ============ */
.empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 80px 20px; }
.empty-icon { width: 64px; height: 64px; color: var(--border-strong); margin-bottom: 20px; }
.empty-text { margin: 0; font-size: 16px; font-weight: 500; color: var(--text-placeholder); }
.empty-hint { margin: 8px 0 0; font-size: 13px; color: var(--text-hint); }

/* ============ 列表 ============ */
.list-wrap { border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }
.list-header, .list-row { display: flex; align-items: center; }
.list-header { background: var(--bg-card); padding: 10px 16px; border-bottom: 1px solid var(--border); }
.list-header .col { font-size: 12px; font-weight: 600; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.5px; }
.list-row { padding: 12px 16px; border-bottom: 1px solid var(--border-light); transition: background 0.15s ease; }
.list-row:last-child { border-bottom: none; }
.list-row:hover { background: var(--border-subtle); }
.col-index { width: 40px; flex-shrink: 0; text-align: center; }
.col-thumb { width: 70px; flex-shrink: 0; }
.col-prompt { flex: 1; min-width: 0; padding: 0 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; color: var(--text-secondary); }
.col-prompt.copyable { cursor: pointer; transition: color 0.15s ease; }
.col-prompt.copyable:hover { color: var(--accent); }
.col-status { width: 90px; flex-shrink: 0; text-align: center; }
.col-url { width: 100px; flex-shrink: 0; text-align: center; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.col-actions { width: 140px; flex-shrink: 0; display: flex; justify-content: center; gap: 6px; }
.thumb { width: 50px; height: 50px; border-radius: 8px; overflow: hidden; background: var(--bg-surface); border: 1px solid var(--border); }
.thumb img { width: 100%; height: 100%; object-fit: cover; display: block; }
.no-result { font-size: 13px; color: var(--text-hint); }
.url-link { font-size: 12px; color: var(--accent); text-decoration: none; }
.url-link:hover { text-decoration: underline; }

/* 状态标签 */
.status-tag { display: inline-block; padding: 3px 10px; border-radius: 6px; font-size: 11px; font-weight: 600; }
.status-tag.pending { background: rgba(255,214,10,0.1); color: #ffd60a; }
.status-tag.processing { background: var(--accent-bg); color: var(--accent); }
.status-tag.completed { background: var(--success-bg); color: var(--success); }
.status-tag.failed { background: var(--error-bg); color: var(--error); }

/* 操作按钮 */
.action-btn { width: 34px; height: 34px; padding: 0; display: flex; align-items: center; justify-content: center; border-radius: 8px; border: 1px solid var(--border-medium); background: var(--border-light); color: var(--text-tertiary); cursor: pointer; transition: all 0.15s ease; }
.action-btn:disabled { opacity: 0.35; cursor: not-allowed; }
.action-btn svg { width: 15px; height: 15px; }
.delete-btn:hover:not(:disabled) { background: rgba(255,69,58,0.15); border-color: rgba(255,69,58,0.4); color: var(--error); }
.retry-btn:hover { background: rgba(255,214,10,0.15); border-color: rgba(255,214,10,0.4); color: #ffd60a; }
.download-btn:hover { background: rgba(52,199,89,0.15); border-color: rgba(52,199,89,0.4); color: var(--success); }
.delete-all-btn { border-color: rgba(255,69,58,0.3); background: rgba(255,69,58,0.08); color: var(--error); }
.delete-all-btn:hover { background: rgba(255,69,58,0.18); border-color: rgba(255,69,58,0.5); color: var(--error); }
.delete-confirm-btn { background: linear-gradient(135deg, var(--error), #ff6b5e) !important; border-color: rgba(255,69,58,0.5) !important; }

/* ============ 弹窗 ============ */
.dialog-overlay { position: fixed; inset: 0; z-index: 1000; display: flex; align-items: center; justify-content: center; background: rgba(0,0,0,0.6); backdrop-filter: blur(4px); }
.dialog { width: min(520px, calc(100% - 40px)); border-radius: 16px; background: linear-gradient(180deg, var(--bg-card), var(--bg-card)); border: 1px solid var(--border-medium); box-shadow: var(--shadow-dialog); overflow: hidden; }
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
.save-btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none !important; box-shadow: none !important; }

.field { display: flex; flex-direction: column; gap: 8px; }
.field-label { font-size: 13px; color: var(--text-tertiary); }

.dialog-body textarea { width: 100%; padding: 12px 14px; border-radius: 12px; border: 1px solid var(--border-medium); background: var(--bg-surface); color: var(--text-primary); font-size: 14px; font-family: inherit; outline: none; resize: vertical; transition: border-color 0.2s ease, box-shadow 0.2s ease; }
.dialog-body textarea::placeholder { color: var(--text-placeholder); }
.dialog-body textarea:focus { border-color: rgba(200,96,122,0.6); box-shadow: 0 0 0 3px var(--accent-bg-strong); }

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

/* 播放按钮 */
.play-btn { display: inline-flex; align-items: center; gap: 4px; padding: 4px 12px; border-radius: 8px; border: 1px solid var(--accent-border); background: var(--accent-bg); color: var(--accent); font-size: 12px; font-weight: 500; cursor: pointer; transition: all 0.15s ease; }
.play-btn:hover { background: var(--accent-focus); border-color: var(--accent-focus); }
.play-icon { width: 12px; height: 12px; flex-shrink: 0; }

/* 视频预览弹窗 */
.preview-overlay { position: fixed; inset: 0; z-index: 2000; display: flex; align-items: center; justify-content: center; background: rgba(0,0,0,0.85); backdrop-filter: blur(8px); cursor: pointer; }
.preview-close { position: absolute; top: 20px; right: 20px; width: 40px; height: 40px; padding: 0; display: flex; align-items: center; justify-content: center; border-radius: 10px; border: none; background: rgba(255,255,255,0.15); color: rgba(255,255,255,0.95); cursor: pointer; transition: background 0.15s ease; z-index: 1; }
.preview-close:hover { background: rgba(255,255,255,0.25); }
.preview-close svg { width: 20px; height: 20px; }
.preview-video-wrap { max-width: 90vw; max-height: 85vh; border-radius: 12px; overflow: hidden; background: #000; box-shadow: 0 24px 60px rgba(0,0,0,0.6); cursor: default; }
.preview-video { display: block; max-width: 90vw; max-height: 85vh; outline: none; }
</style>
