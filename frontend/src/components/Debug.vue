<script setup>
import { ref, onMounted, computed } from 'vue'

const emit = defineEmits(['toast'])

// ── 顶层 Tab（平台）────────────────────────────────────────────────────
const activePlatform = ref('nanobanana')
const platforms = [
  { key: 'nanobanana', label: '🍌 NanoBanana', icon: '🍌' },
  { key: 'veo',        label: '🎬 VEO',        icon: '🎬' },
  { key: 'sora2',      label: '🌊 Sora2',      icon: '🌊' },
]

// ── 渠道列表（从后端加载）──────────────────────────────────────────────
const allChannels = ref([])
const channelsLoading = ref(true)

const platformChannels = computed(() =>
  allChannels.value.filter(c => c.tab === activePlatform.value)
)

// 每个平台选中的渠道 key
const selectedChannel = ref({
  nanobanana: null,
  veo:        null,
  sora2:      null,
})

async function loadChannels() {
  channelsLoading.value = true
  try {
    const res = await window.pywebview.api.debug_get_channels()
    if (res.ok) {
      allChannels.value = res.channels
      // 自动选中每个平台第一个已配置渠道
      for (const tab of ['nanobanana', 'veo', 'sora2']) {
        const first = res.channels.find(c => c.tab === tab && c.configured)
        if (first) selectedChannel.value[tab] = first.key
      }
    } else {
      emit('toast', res.msg || '加载渠道失败', 'error')
    }
  } catch (e) {
    emit('toast', '无法调用后端接口: ' + e, 'error')
  } finally {
    channelsLoading.value = false
  }
}

// ── 表单状态（三个平台公用同一套响应式数据）────────────────────────────
const prompt = ref('')
const orientation = ref('portrait')
const duration = ref(10)
const aspectRatio = ref('9:16')
const imageSize = ref('1K')
const refImagePath = ref('')    // 本地绝对路径

// 上传参考图（转 base64 供展示，路径通过 webview 文件对话框获取）
const refPreview = ref('')
const refBase64 = ref('')
const refMime = ref('')
const fileInput = ref(null)

function handleFileSelect(e) {
  const file = e.target.files[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = ev => {
    refPreview.value = ev.target.result
    refMime.value = file.type
    refBase64.value = ev.target.result.split(',')[1]
  }
  reader.readAsDataURL(file)
}

function removeRef() {
  refPreview.value = ''
  refBase64.value = ''
  refMime.value = ''
  refImagePath.value = ''
  if (fileInput.value) fileInput.value.value = ''
}

// ── 生成任务 ─────────────────────────────────────────────────────────
const loading = ref(false)
const result = ref(null)   // { success, file_path, preview_b64, mime_type, video_url, error }
const logs = ref([])       // [{ time, level, msg }]

function addLog(level, msg) {
  const time = new Date().toLocaleTimeString('zh-CN', { hour12: false })
  logs.value.push({ time, level, msg })
}

async function runGenerate() {
  const platform = activePlatform.value
  const chKey = selectedChannel.value[platform]

  if (!chKey) {
    emit('toast', '请先选择一个渠道', 'error')
    return
  }
  if (!prompt.value.trim()) {
    emit('toast', '提示词不能为空', 'error')
    return
  }

  loading.value = true
  result.value = null

  const params = { prompt: prompt.value.trim() }
  if (platform === 'nanobanana') {
    params.aspect_ratio = aspectRatio.value
    params.image_size = imageSize.value
    if (refBase64.value) {
      params.ref_base64 = refBase64.value
      params.ref_mime = refMime.value
    }
  } else {
    params.orientation = orientation.value
    params.duration = duration.value
    if (refBase64.value) {
      params.ref_base64 = refBase64.value
      params.ref_mime = refMime.value
    }
  }

  addLog('info', `发起生成 | channel=${chKey} | prompt="${params.prompt.slice(0, 40)}..."`)
  const t0 = Date.now()

  try {
    const res = await window.pywebview.api.debug_generate(chKey, params)
    const elapsed = ((Date.now() - t0) / 1000).toFixed(1)

    if (res.ok) {
      addLog('ok', `生成成功 (${elapsed}s)${res.file_path ? ' → ' + res.file_path : ''}`)
      emit('toast', '生成成功', 'success')
    } else {
      addLog('error', `生成失败 (${elapsed}s): ${res.msg}`)
      emit('toast', res.msg || '生成失败', 'error')
    }
    result.value = res
  } catch (e) {
    const elapsed = ((Date.now() - t0) / 1000).toFixed(1)
    addLog('error', `请求异常 (${elapsed}s): ${e}`)
    emit('toast', '请求异常', 'error')
    result.value = { ok: false, msg: String(e) }
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadChannels()
})
</script>

<template>
  <div class="debug-page">
    <!-- ── 顶部平台 TabBar ───────────────────────────────────────── -->
    <div class="platform-tabs">
      <div class="tabs-group">
        <button
          v-for="p in platforms"
          :key="p.key"
          :class="['ptab', { active: activePlatform === p.key }]"
          @click="activePlatform = p.key; result = null"
        >
          {{ p.label }}
        </button>
      </div>
      <div class="ptab-spacer"></div>
      <button class="reload-btn" @click="loadChannels" title="刷新渠道">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
          <polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/>
          <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
        </svg>
        刷新渠道
      </button>
    </div>

    <div class="debug-body">
      <!-- ── 左侧：渠道列表 + 参数表单 ──────────────────────────────── -->
      <div class="left-panel">
        <!-- 渠道列表 -->
        <div class="section">
          <div class="section-title">渠道选择</div>
          <div v-if="channelsLoading" class="channels-loading">加载中...</div>
          <div v-else-if="platformChannels.length === 0" class="channels-empty">暂无渠道</div>
          <div v-else class="channel-list">
            <div
              v-for="ch in platformChannels"
              :key="ch.key"
              :class="['channel-item', {
                selected: selectedChannel[activePlatform] === ch.key,
                unconfigured: !ch.configured
              }]"
              @click="ch.configured && (selectedChannel[activePlatform] = ch.key)"
            >
              <span :class="['ch-dot', ch.configured ? 'ok' : 'no']"></span>
              <span class="ch-label">{{ ch.label }}</span>
              <span class="ch-badge">{{ ch.configured ? '已配置' : '未配置' }}</span>
            </div>
          </div>
        </div>

        <!-- 公共参数 -->
        <div class="section">
          <div class="section-title">生成参数</div>

          <div class="field">
            <label>提示词</label>
            <textarea v-model="prompt" rows="4" placeholder="描述要生成的内容..."></textarea>
          </div>

          <!-- NanoBanana 专属 -->
          <template v-if="activePlatform === 'nanobanana'">
            <div class="field">
              <label>宽高比</label>
              <select v-model="aspectRatio">
                <option value="9:16">9:16 竖屏</option>
                <option value="16:9">16:9 横屏</option>
                <option value="1:1">1:1 正方形</option>
              </select>
            </div>
            <div class="field">
              <label>清晰度</label>
              <select v-model="imageSize">
                <option value="1K">1K</option>
                <option value="2K">2K</option>
                <option value="4K">4K</option>
              </select>
            </div>
          </template>

          <!-- VEO / Sora2 专属 -->
          <template v-if="activePlatform !== 'nanobanana'">
            <div class="field">
              <label>方向</label>
              <select v-model="orientation">
                <option value="portrait">竖屏 Portrait</option>
                <option value="landscape">横屏 Landscape</option>
              </select>
            </div>
            <!-- VEO 渠道时长由模型固定（约 8 秒），不支持自定义 -->
            <div class="field" v-if="activePlatform === 'veo'">
              <label>时长（秒）</label>
              <div class="duration-fixed">约 8 秒（渠道固定，不可调节）</div>
            </div>
            <div class="field" v-if="activePlatform === 'sora2'">
              <label>时长（秒）</label>
              <select v-model="duration">
                <option :value="10">10 秒</option>
                <option :value="15">15 秒</option>
              </select>
            </div>
          </template>

          <!-- 参考图（通用） -->
          <div class="field">
            <label>参考图（可选）</label>
            <div v-if="!refPreview" class="upload-area" @click="fileInput?.click()">
              <input ref="fileInput" type="file" accept="image/*" style="display:none" @change="handleFileSelect" />
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="28" height="28"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
              <span>点击选择图片</span>
            </div>
            <div v-else class="ref-preview">
              <img :src="refPreview" alt="参考图" />
              <button class="remove-btn" @click="removeRef">✕</button>
            </div>
          </div>

          <button class="run-btn" :disabled="loading" @click="runGenerate">
            <span v-if="loading">⏳ 生成中...</span>
            <span v-else>▶ 开始生成</span>
          </button>
        </div>
      </div>

      <!-- ── 右侧：预览 + 日志 ────────────────────────────────────── -->
      <div class="right-panel">
        <!-- 预览区 -->
        <div class="preview-area">
          <div v-if="loading" class="preview-spinner">
            <div class="spinner"></div>
            <span>生成中，请稍候...</span>
          </div>
          <template v-else-if="result">
            <!-- 成功：图片 -->
            <img
              v-if="result.ok && result.mime_type && result.preview_b64"
              :src="`data:${result.mime_type};base64,${result.preview_b64}`"
              class="preview-img"
              alt="生成结果"
            />
            <!-- 成功：视频 -->
            <video
              v-else-if="result.ok && result.video_url"
              :src="result.video_url"
              class="preview-video"
              controls autoplay muted
            ></video>
            <!-- 成功：仅路径 -->
            <div v-else-if="result.ok" class="preview-ok">
              <div class="ok-icon">✅</div>
              <div class="ok-label">生成完成</div>
              <div v-if="result.file_path" class="ok-path">{{ result.file_path }}</div>
            </div>
            <!-- 失败 -->
            <div v-else class="preview-error">
              <div class="err-icon">❌</div>
              <div class="err-msg">{{ result.msg }}</div>
            </div>
          </template>
          <div v-else class="preview-placeholder">
            <div class="placeholder-icon">{{ platforms.find(p=>p.key===activePlatform)?.icon }}</div>
            <div>选择渠道，填写提示词，点击「开始生成」</div>
          </div>
        </div>

        <!-- 本地路径 -->
        <div v-if="result?.ok && result?.file_path" class="file-path">
          📁 {{ result.file_path }}
        </div>

        <!-- 日志区 -->
        <div class="log-panel">
          <div v-if="logs.length === 0" class="log-empty">日志将在此显示</div>
          <div v-for="(l, i) in logs" :key="i" class="log-line">
            <span class="log-time">{{ l.time }}</span>
            <span :class="['log-level', l.level]">{{ l.level.toUpperCase() }}</span>
            <span class="log-msg">{{ l.msg }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.debug-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  font-size: 13px;
}

/* ── Platform Tabs ── */
.platform-tabs {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 0 24px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-surface);
  flex-shrink: 0;
}
.tabs-group {
  display: flex;
  gap: 2px;
}
.ptab {
  padding: 0 20px;
  height: 44px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  font-family: inherit;
  font-size: 13px;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: color .2s, border-color .2s;
}
.ptab:hover { color: var(--text-primary); }
.ptab.active { color: var(--accent); border-bottom-color: var(--accent); }
.ptab-spacer { flex: 1; }
.reload-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 5px 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: transparent;
  color: var(--text-muted);
  font-size: 11px;
  cursor: pointer;
  transition: color .2s, border-color .2s;
}
.reload-btn:hover { color: var(--accent); border-color: var(--accent); }

/* ── Body layout ── */
.debug-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* ── Left Panel ── */
.left-panel {
  width: 300px;
  min-width: 260px;
  border-right: 1px solid var(--border);
  background: var(--bg-surface);
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}
.section {
  padding: 14px 16px;
  border-bottom: 1px solid var(--border);
}
.section-title {
  font-size: 10px;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--text-muted);
  margin-bottom: 10px;
}

/* ── Channel List ── */
.channel-list { display: flex; flex-direction: column; gap: 5px; }
.channels-loading, .channels-empty { font-size: 12px; color: var(--text-muted); padding: 4px 0; }
.channel-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid var(--border);
  cursor: pointer;
  transition: background .15s, border-color .15s;
}
.channel-item:hover:not(.unconfigured) { background: var(--bg-card); }
.channel-item.selected { background: var(--accent-bg-subtle); border-color: var(--accent); }
.channel-item.unconfigured { opacity: .4; cursor: not-allowed; }
.ch-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.ch-dot.ok { background: var(--success); }
.ch-dot.no { background: var(--error); }
.ch-label { flex: 1; color: var(--text-primary); }
.ch-badge {
  font-size: 9px;
  padding: 1px 6px;
  border-radius: 8px;
  background: var(--bg-card);
  color: var(--text-muted);
  border: 1px solid var(--border);
}

/* ── Form ── */
.field { display: flex; flex-direction: column; gap: 6px; margin-bottom: 12px; }
.field label { font-size: 11px; color: var(--text-muted); }
textarea, select {
  width: 100%;
  padding: 8px 10px;
  background: var(--bg-card);
  border: 1px solid var(--border-strong);
  border-radius: 8px;
  color: var(--text-primary);
  font-family: inherit;
  font-size: 12px;
  outline: none;
  resize: vertical;
  transition: border-color .2s;
}
textarea:focus, select:focus { border-color: var(--accent); }

.upload-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 18px;
  border: 2px dashed var(--border-strong);
  border-radius: 8px;
  background: var(--bg-card);
  cursor: pointer;
  font-size: 12px;
  color: var(--text-muted);
  transition: border-color .2s;
}
.upload-area:hover { border-color: var(--accent); }
.ref-preview {
  position: relative;
  display: inline-block;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid var(--border);
}
.ref-preview img { display: block; max-width: 100%; max-height: 140px; object-fit: contain; }
.remove-btn {
  position: absolute; top: 5px; right: 5px;
  width: 22px; height: 22px;
  border-radius: 50%;
  border: none;
  background: rgba(0,0,0,.6);
  color: #fff;
  font-size: 11px;
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
}
.remove-btn:hover { background: rgba(220,50,50,.8); }

.duration-fixed {
  padding: 8px 10px;
  background: var(--bg-card);
  border: 1px solid var(--border-strong);
  border-radius: 8px;
  color: var(--text-muted);
  font-size: 12px;
}

.run-btn {
  width: 100%;
  padding: 9px;
  border: none;
  border-radius: 8px;
  background: var(--accent);
  color: #fff;
  font-family: inherit;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity .2s;
}
.run-btn:hover { opacity: .85; }
.run-btn:disabled { opacity: .4; cursor: not-allowed; }

/* ── Right Panel ── */
.right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.preview-area {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  overflow: auto;
  background: var(--bg-main);
}
.preview-spinner { display: flex; flex-direction: column; align-items: center; gap: 12px; color: var(--text-muted); font-size: 12px; }
.spinner {
  width: 36px; height: 36px;
  border: 3px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin .8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.preview-img { max-width: 100%; max-height: 100%; border-radius: 8px; box-shadow: 0 6px 30px rgba(0,0,0,.4); }
.preview-video { max-width: 100%; max-height: 100%; border-radius: 8px; }
.preview-ok, .preview-error { text-align: center; color: var(--text-muted); font-size: 12px; }
.ok-icon, .err-icon { font-size: 40px; margin-bottom: 8px; }
.ok-path, .err-msg { margin-top: 6px; word-break: break-all; max-width: 400px; }
.err-msg { color: var(--error); }
.preview-placeholder { text-align: center; color: var(--text-muted); font-size: 12px; line-height: 1.8; }
.placeholder-icon { font-size: 44px; margin-bottom: 10px; }

.file-path {
  padding: 6px 16px;
  background: var(--bg-surface);
  border-top: 1px solid var(--border);
  font-size: 11px;
  color: var(--accent);
  word-break: break-all;
}

/* ── Log Panel ── */
.log-panel {
  height: 180px;
  border-top: 1px solid var(--border);
  background: var(--bg-surface);
  overflow-y: auto;
  padding: 10px 14px;
  font-size: 11px;
  font-family: 'SF Mono', Monaco, monospace;
  line-height: 1.7;
  flex-shrink: 0;
}
.log-empty { color: var(--text-muted); }
.log-line { display: flex; gap: 8px; }
.log-time { color: var(--text-muted); flex-shrink: 0; }
.log-level { width: 44px; flex-shrink: 0; text-align: right; }
.log-level.info { color: var(--accent); }
.log-level.ok   { color: var(--success); }
.log-level.warn { color: #ffd43b; }
.log-level.error { color: var(--error); }
.log-msg { color: var(--text-primary); word-break: break-all; }
</style>