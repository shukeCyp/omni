<script setup>
import { ref, onMounted, computed } from 'vue'

const emit = defineEmits(['toast'])

const items = ref([])
const batchRunning = ref(false)
const previewSrc = ref('')
const showPreview = ref(false)
const activeFolder = ref('')

// ==================== 加载列表 ====================
const loadItems = async () => {
  try {
    const res = await window.pywebview.api.get_prompt_items()
    if (res.ok) {
      items.value = res.items || []
    }
  } catch (e) {
    emit('toast', '加载列表失败', 'error')
  }
}

onMounted(() => {
  loadItems()
})

// ==================== 文件夹列表 ====================
const folders = computed(() => {
  const set = new Set()
  for (const it of items.value) {
    if (it.folder_name) set.add(it.folder_name)
  }
  return [...set].sort()
})

// ==================== 筛选后的列表 ====================
const filteredItems = computed(() => {
  if (!activeFolder.value) return items.value
  return items.value.filter(it => it.folder_name === activeFolder.value)
})

const setActiveFolder = (name) => {
  activeFolder.value = activeFolder.value === name ? '' : name
}

// ==================== 统计 ====================
const stats = computed(() => {
  const list = filteredItems.value
  const total = list.length
  const completed = list.filter(t => t.status === 'completed').length
  const processing = list.filter(t => t.status === 'processing').length
  const failed = list.filter(t => t.status === 'failed').length
  const pending = list.filter(t => t.status === 'pending').length
  return { total, completed, processing, failed, pending }
})

// ==================== 图片预览 ====================
const openPreview = async (item) => {
  try {
    const res = await window.pywebview.api.get_prompt_image(item.id)
    if (res.ok && res.base64 && res.mime) {
      previewSrc.value = `data:${res.mime};base64,${res.base64}`
      showPreview.value = true
    } else {
      emit('toast', res.msg || '无法加载图片', 'error')
    }
  } catch (e) {
    emit('toast', '加载图片失败', 'error')
  }
}

const closePreview = () => {
  showPreview.value = false
  previewSrc.value = ''
}

// ==================== 导入 ====================
const importImages = async () => {
  try {
    const res = await window.pywebview.api.select_folder_for_prompt()
    if (res.ok) {
      emit('toast', `成功导入 ${res.total || 0} 张图片`, 'success')
      await loadItems()
    } else if (res.msg) {
      emit('toast', res.msg, 'error')
    }
  } catch (e) {
    emit('toast', '导入失败', 'error')
  }
}

// ==================== 批量执行 ====================
const batchExecute = async () => {
  const pendingItems = filteredItems.value.filter(it => it.status === 'pending' || it.status === 'failed')
  if (pendingItems.length === 0) {
    emit('toast', '没有待生成的项目', 'error')
    return
  }

  batchRunning.value = true

  let concurrency = 3
  try {
    const settings = await window.pywebview.api.get_all_settings()
    concurrency = parseInt(settings.thread_pool_size || '3', 10)
    if (concurrency < 1) concurrency = 1
    if (concurrency > 50) concurrency = 50
  } catch { /* ignore */ }

  let idx = 0
  const runNext = async () => {
    while (idx < pendingItems.length) {
      const item = pendingItems[idx++]
      if (item.status === 'completed') continue
      item.status = 'processing'
      try {
        const res = await window.pywebview.api.generate_prompt(item.id)
        if (res.ok) {
          item.status = 'completed'
          item.error = null
        } else {
          item.status = 'failed'
          item.error = res.msg || '生成失败'
        }
      } catch (e) {
        item.status = 'failed'
        item.error = '生成请求失败'
      }
    }
  }

  const workers = []
  for (let i = 0; i < Math.min(concurrency, pendingItems.length); i++) {
    workers.push(runNext())
  }

  try {
    await Promise.all(workers)
  } catch { /* ignore */ }

  batchRunning.value = false
  await loadItems()

  const completedCount = pendingItems.filter(it => it.status === 'completed').length
  const failedCount = pendingItems.filter(it => it.status === 'failed').length
  if (failedCount > 0) {
    emit('toast', `执行完成：成功 ${completedCount}，失败 ${failedCount}`, 'error')
  } else {
    emit('toast', `全部生成完成，共 ${completedCount} 条`, 'success')
  }
}

// ==================== 单项重新生成 ====================
const regenerateItem = async (item) => {
  item.status = 'processing'
  item.error = null
  try {
    const res = await window.pywebview.api.generate_prompt(item.id)
    if (res.ok) {
      item.status = 'completed'
      emit('toast', '生成成功', 'success')
    } else {
      item.status = 'failed'
      item.error = res.msg || '生成失败'
      emit('toast', res.msg || '生成失败', 'error')
    }
  } catch (e) {
    item.status = 'failed'
    item.error = '生成请求失败'
    emit('toast', '生成失败', 'error')
  }
}

// ==================== 操作 ====================
const openFolder = async (item) => {
  if (item.status === 'completed') {
    try {
      const res = await window.pywebview.api.read_prompt_text(item.id)
      if (res.ok && res.text) {
        await navigator.clipboard.writeText(res.text)
        emit('toast', '已复制到剪贴板', 'success')
      }
    } catch { /* ignore */ }
  }
  try {
    const res = await window.pywebview.api.open_prompt_folder(item.id)
    if (!res.ok) {
      emit('toast', res.msg || '打开失败', 'error')
    }
  } catch (e) {
    emit('toast', '打开失败', 'error')
  }
}

const deleteItem = async (item) => {
  if (!confirm('确定删除该项目？对应文件夹将被删除。')) return
  try {
    const res = await window.pywebview.api.delete_prompt_item(item.id)
    if (res.ok) {
      emit('toast', '已删除', 'success')
      await loadItems()
    } else {
      emit('toast', res.msg || '删除失败', 'error')
    }
  } catch (e) {
    emit('toast', '删除失败', 'error')
  }
}

const batchDelete = async () => {
  const list = filteredItems.value
  if (list.length === 0) {
    emit('toast', '没有可删除的项目', 'error')
    return
  }
  const scope = activeFolder.value ? `"${activeFolder.value}" 中的` : '全部'
  if (!confirm(`确定删除${scope} ${list.length} 个项目？对应文件夹将被删除，此操作不可恢复。`)) return
  let deleted = 0
  for (const item of [...list]) {
    try {
      const res = await window.pywebview.api.delete_prompt_item(item.id)
      if (res.ok) deleted++
    } catch { /* ignore */ }
  }
  emit('toast', `已删除 ${deleted} 个项目`, 'success')
  await loadItems()
}

// ==================== 状态辅助 ====================
const statusLabel = (status) => {
  const map = { pending: '待生成', processing: '生成中', completed: '已完成', failed: '失败' }
  return map[status] || status
}
</script>

<template>
  <div class="page">
    <div class="page-toolbar">
      <div class="toolbar-left">
        <h2 class="page-title">提示词生成</h2>
        <span v-if="items.length > 0" class="stats">
          <span class="stat-item">共 {{ stats.total }}</span>
          <span class="stat-item stat-pending">待生成 {{ stats.pending }}</span>
          <span class="stat-item stat-processing" v-if="stats.processing > 0">生成中 {{ stats.processing }}</span>
          <span class="stat-item stat-completed">已完成 {{ stats.completed }}</span>
          <span class="stat-item stat-failed" v-if="stats.failed > 0">失败 {{ stats.failed }}</span>
        </span>
      </div>
      <div class="toolbar-right">
        <button class="btn btn-primary" @click="batchExecute" :disabled="batchRunning">
          {{ batchRunning ? '执行中...' : '批量执行' }}
        </button>
        <button class="btn btn-secondary" @click="importImages">导入</button>
        <button class="btn btn-danger" @click="batchDelete" v-if="filteredItems.length > 0">批量删除</button>
      </div>
    </div>

    <!-- 文件夹筛选 -->
    <div v-if="folders.length > 0" class="folder-filter">
      <button
        :class="['folder-tag', { active: activeFolder === f }]"
        v-for="f in folders"
        :key="f"
        @click="setActiveFolder(f)"
      >{{ f }}</button>
    </div>

    <div class="page-body">
      <!-- 空状态 -->
      <div v-if="items.length === 0" class="empty-state">
        <div class="empty-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="48" height="48">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="12" y1="18" x2="12" y2="12"/>
            <line x1="9" y1="15" x2="15" y2="15"/>
          </svg>
        </div>
        <p class="empty-text">暂无导入的图片</p>
        <p class="empty-hint">点击右上角"导入"按钮，选择包含产品图片的文件夹</p>
      </div>

      <!-- 列表 -->
      <div v-else class="list-container">
        <div class="list-header">
          <span class="col-index">#</span>
          <span class="col-thumb">图片</span>
          <span class="col-folder">分类</span>
          <span class="col-status">状态</span>
          <span class="col-actions">操作</span>
        </div>
        <div
          v-for="(item, index) in filteredItems"
          :key="item.id"
          class="list-row"
          :class="'row-' + item.status"
        >
          <span class="col-index">{{ index + 1 }}</span>
          <span class="col-thumb">
            <img
              :src="`data:image/jpeg;base64,${item.thumb}`"
              v-if="item.thumb"
              class="thumb-img"
              @click="openPreview(item)"
              title="点击放大查看"
            />
            <span v-else class="thumb-placeholder" @click="openPreview(item)" title="点击查看图片">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="24" height="24">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                <circle cx="8.5" cy="8.5" r="1.5"/>
                <polyline points="21 15 16 10 5 21"/>
              </svg>
            </span>
          </span>
          <span class="col-folder">{{ item.folder_name }}</span>
          <span class="col-status">
            <span class="status-tag" :class="'tag-' + item.status">
              {{ statusLabel(item.status) }}
            </span>
            <span v-if="item.error" class="error-hint" :title="item.error">{{ item.error }}</span>
          </span>
          <span class="col-actions">
            <button class="action-btn" @click="openFolder(item)" title="打开并复制提示词">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
              </svg>
              打开
            </button>
            <button
              class="action-btn"
              @click="regenerateItem(item)"
              :disabled="item.status === 'processing'"
              v-if="item.status === 'pending' || item.status === 'failed'"
              title="重新生成"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                <polyline points="23 4 23 10 17 10"/>
                <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
              </svg>
              重试
            </button>
            <button class="action-btn action-btn-danger" @click="deleteItem(item)" title="删除">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                <polyline points="3 6 5 6 21 6"/>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
              </svg>
              删除
            </button>
          </span>
        </div>
      </div>
    </div>

    <!-- 图片预览弹窗 -->
    <Teleport to="body">
      <div v-if="showPreview" class="preview-overlay" @click="closePreview">
        <div class="preview-box" @click.stop>
          <button class="preview-close" @click="closePreview">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="24" height="24">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
          <img :src="previewSrc" class="preview-img" />
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.page { display: flex; flex-direction: column; height: 100%; }
.page-toolbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 20px; border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.toolbar-left { display: flex; align-items: center; gap: 16px; }
.page-title { font-size: 18px; font-weight: 600; color: var(--text-primary); margin: 0; }
.stats { display: flex; gap: 12px; font-size: 12px; color: var(--text-secondary); }
.stat-pending { color: var(--text-hint); }
.stat-processing { color: var(--accent); }
.stat-completed { color: var(--success); }
.stat-failed { color: var(--error); }
.toolbar-right { display: flex; gap: 8px; }

.btn {
  padding: 7px 16px; border-radius: 6px; border: 1px solid transparent;
  font-size: 13px; cursor: pointer; transition: all 0.15s;
}
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary {
  background: var(--accent); color: #fff; border-color: var(--accent);
}
.btn-primary:hover:not(:disabled) { background: var(--accent-bg-strong); }
.btn-secondary {
  background: transparent; color: var(--text-primary); border-color: var(--border-medium);
}
.btn-secondary:hover { background: var(--bg-surface); }
.btn-danger {
  background: transparent; color: var(--error); border-color: var(--error);
}
.btn-danger:hover { background: var(--error-bg); }

/* 文件夹筛选 */
.folder-filter {
  display: flex; gap: 8px; padding: 10px 20px;
  border-bottom: 1px solid var(--border-light);
  flex-wrap: wrap; flex-shrink: 0;
}
.folder-tag {
  padding: 4px 12px; border-radius: 14px; border: 1px solid var(--border);
  background: transparent; color: var(--text-secondary); font-size: 12px;
  cursor: pointer; transition: all 0.15s;
}
.folder-tag:hover { border-color: var(--accent); color: var(--accent); }
.folder-tag.active { background: var(--accent); color: #fff; border-color: var(--accent); }

.page-body { flex: 1; overflow-y: auto; padding: 0; }

.empty-state {
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; padding: 80px 20px; color: var(--text-tertiary);
}
.empty-icon { margin-bottom: 16px; opacity: 0.4; }
.empty-text { font-size: 15px; margin: 0 0 8px; }
.empty-hint { font-size: 13px; margin: 0; color: var(--text-hint); }

.list-container { padding: 0; }

.list-header {
  display: flex; align-items: center; padding: 10px 20px;
  font-size: 12px; color: var(--text-hint); border-bottom: 1px solid var(--border-light);
  background: var(--bg-surface);
}

.list-row {
  display: flex; align-items: center; padding: 12px 20px;
  border-bottom: 1px solid var(--border-light); transition: background 0.15s;
}
.list-row:hover { background: var(--bg-surface); }

.col-index { flex: 0 0 3%; font-size: 12px; color: var(--text-hint); }
.col-thumb { flex: 0 0 10%; display: flex; align-items: center; }
.thumb-img {
  width: 88px; height: 88px; border-radius: 6px; object-fit: cover;
  border: 1px solid var(--border); cursor: pointer; transition: transform 0.15s;
}
.thumb-img:hover { transform: scale(1.05); }
.thumb-placeholder {
  width: 88px; height: 88px; border-radius: 6px;
  border: 1px dashed var(--border); display: flex; align-items: center;
  justify-content: center; color: var(--text-hint); cursor: pointer;
}
.thumb-placeholder:hover { background: var(--bg-surface); }
.col-folder {
  flex: 1 1 0%; font-size: 13px; color: var(--text-primary);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  padding-right: 12px;
}
.col-status { flex: 0 0 12%; display: flex; align-items: center; gap: 6px; }
.col-actions { flex: 0 0 18%; display: flex; gap: 4px; justify-content: flex-end; }

.status-tag {
  font-size: 11px; padding: 2px 8px; border-radius: 10px;
  white-space: nowrap;
}
.tag-pending { background: var(--bg-surface); color: var(--text-hint); }
.tag-processing { background: var(--accent-bg); color: var(--accent); }
.tag-completed { background: var(--success-bg); color: var(--success); }
.tag-failed { background: var(--error-bg); color: var(--error); }

.error-hint {
  font-size: 11px; color: var(--error); max-width: 120px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

.action-btn {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 4px 8px; border-radius: 4px; border: 1px solid var(--border);
  background: transparent; color: var(--text-secondary); font-size: 12px;
  cursor: pointer; transition: all 0.15s;
}
.action-btn:hover:not(:disabled) { background: var(--bg-surface); color: var(--text-primary); }
.action-btn:disabled { opacity: 0.35; cursor: not-allowed; }
.action-btn-danger:hover:not(:disabled) { color: var(--error); border-color: var(--error); background: var(--error-bg); }

/* 图片预览弹窗 */
.preview-overlay {
  position: fixed; inset: 0; z-index: 9999;
  background: rgba(0, 0, 0, 0.75);
  display: flex; align-items: center; justify-content: center;
}
.preview-box {
  position: relative; max-width: 90vw; max-height: 90vh;
}
.preview-img {
  max-width: 90vw; max-height: 90vh; border-radius: 8px;
  object-fit: contain;
}
.preview-close {
  position: absolute; top: -40px; right: 0;
  background: none; border: none; color: #fff; cursor: pointer;
  padding: 4px; opacity: 0.8;
}
.preview-close:hover { opacity: 1; }
</style>
