<script setup>
import { ref, onMounted } from 'vue'

const emit = defineEmits(['toast'])

const themes = [
  { id: 'warm-cream', name: '暖奶油', colors: ['#faf7f5', '#c8607a', '#f5f0ed'] },
  { id: 'dark-rose', name: '暗夜玫瑰', colors: ['#0e0b09', '#d4748a', '#1a1614'] },
  { id: 'forest', name: '森林', colors: ['#f4f7f4', '#3d8b5e', '#eaf0ea'] },
  { id: 'eye-care', name: '护眼', colors: ['#f5f0e6', '#7a9a4a', '#ede8de'] },
  { id: 'ocean', name: '海洋蓝', colors: ['#f5f8fa', '#3a7fc8', '#edf2f6'] },
  { id: 'midnight', name: '午夜蓝', colors: ['#0c1018', '#5b9cff', '#151a26'] },
  { id: 'lavender', name: '薰衣草', colors: ['#f8f5fa', '#8a5cc8', '#f0ecf5'] },
]

const currentTheme = ref('warm-cream')
const holo_veo_api_key = ref('')
const download_path = ref('')
const auto_retry = ref(false)
const video_max_retry = ref('3')
const thread_pool_size = ref('10')

const applyTheme = (themeId) => {
  currentTheme.value = themeId
  document.documentElement.setAttribute('data-theme', themeId)
}

const selectDownloadFolder = async () => {
  try {
    const res = await window.pywebview.api.select_folder()
    if (res.ok && res.path) {
      download_path.value = res.path
      emit('toast', '已选择下载目录', 'success')
    }
  } catch {
    emit('toast', '选择文件夹失败', 'error')
  }
}

const saveSettings = async () => {
  try {
    await window.pywebview.api.save_settings({
      theme: currentTheme.value,
      omni_model: 'cloudy',
      holo_veo_api_key: holo_veo_api_key.value.trim(),
      download_path: download_path.value.trim(),
      auto_retry: auto_retry.value ? 'true' : 'false',
      video_max_retry: String(video_max_retry.value || '0').trim(),
      thread_pool_size: String(thread_pool_size.value || '10').trim(),
    })
    emit('toast', '设置已保存', 'success')
  } catch {
    emit('toast', '保存失败', 'error')
  }
}

const loadSettings = async () => {
  try {
    const settings = await window.pywebview.api.get_all_settings()
    if (settings.theme) applyTheme(settings.theme)
    if (settings.holo_veo_api_key) holo_veo_api_key.value = settings.holo_veo_api_key.trim()
    if (settings.download_path) download_path.value = settings.download_path.trim()
    if (settings.auto_retry) auto_retry.value = settings.auto_retry === 'true'
    if (settings.video_max_retry) video_max_retry.value = settings.video_max_retry
    if (settings.thread_pool_size) thread_pool_size.value = settings.thread_pool_size
  } catch { /* ignore */ }
}

onMounted(loadSettings)
</script>

<template>
  <div class="page">
    <div class="page-body">
      <div class="settings-sections">
        <section class="settings-section-block">
          <h2 class="section-heading">主题配色</h2>
          <div class="theme-grid">
            <button
              v-for="t in themes"
              :key="t.id"
              :class="['theme-card', { active: currentTheme === t.id }]"
              @click="applyTheme(t.id)"
            >
              <div class="theme-preview">
                <div class="theme-dot" :style="{ background: t.colors[0], border: '1px solid rgba(0,0,0,0.1)' }"></div>
                <div class="theme-dot" :style="{ background: t.colors[1] }"></div>
                <div class="theme-dot" :style="{ background: t.colors[2], border: '1px solid rgba(0,0,0,0.08)' }"></div>
              </div>
              <span class="theme-name">{{ t.name }}</span>
            </button>
          </div>
        </section>

        <section class="settings-section-block">
          <h2 class="section-heading">Omni 视频</h2>
          <div class="settings-grid">
            <div class="settings-card">
              <div class="card-header"><h3 class="card-title">重试配置</h3></div>
              <div class="card-body">
                <label class="checkbox-item">
                  <input type="checkbox" v-model="auto_retry" />
                  <span class="checkbox-label">失败后自动重试</span>
                </label>
                <label class="field" style="margin-top: 16px;">
                  <span class="field-label">视频最大重试次数</span>
                  <input v-model="video_max_retry" type="number" min="0" max="10" placeholder="3" />
                </label>
              </div>
            </div>
            <div class="settings-card">
              <div class="card-header"><h3 class="card-title">线程池</h3></div>
              <div class="card-body">
                <label class="field">
                  <span class="field-label">并发数量（修改后需重启生效）</span>
                  <input v-model="thread_pool_size" type="number" min="1" max="50" placeholder="10" />
                </label>
              </div>
            </div>
          </div>
        </section>

        <section class="settings-section-block">
          <h2 class="section-heading">API Keys</h2>
          <div class="settings-grid">
            <div class="settings-card">
              <div class="card-header"><h3 class="card-title">荷塘</h3></div>
              <div class="card-body">
                <label class="field">
                  <span class="field-label">API Key</span>
                  <input v-model="holo_veo_api_key" type="password" placeholder="请输入荷塘 API Key" autocomplete="off" />
                </label>
              </div>
            </div>
          </div>
        </section>

        <section class="settings-section-block">
          <h2 class="section-heading">下载配置</h2>
          <div class="settings-card wide-card">
            <div class="card-header"><h3 class="card-title">单条下载路径</h3></div>
            <div class="card-body">
              <div class="field">
                <span class="field-label">点击列表中的下载按钮时，文件将保存到此目录</span>
                <div class="path-row">
                  <input v-model="download_path" type="text" placeholder="请选择下载目录" readonly class="path-input" />
                  <button class="select-folder-btn" @click="selectDownloadFolder">选择文件夹</button>
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>

    <div class="floating-actions">
      <button class="floating-refresh-btn" @click="() => window.location.reload()">刷新</button>
      <button class="floating-save-btn" @click="saveSettings">保存设置</button>
    </div>
  </div>
</template>

<style scoped>
.page { position: relative; min-height: 100%; }
.page-body { padding: 32px; padding-bottom: 80px; }
.settings-sections { display: flex; flex-direction: column; gap: 36px; }
.section-heading { margin: 0 0 16px 0; font-size: 16px; font-weight: 600; color: var(--accent); letter-spacing: 0.3px; }
.theme-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 12px; }
.theme-card { display: flex; flex-direction: column; align-items: center; gap: 10px; padding: 16px 12px; border-radius: 14px; border: 2px solid var(--border); background: var(--bg-card); cursor: pointer; transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.15s ease; }
.theme-card:hover { border-color: var(--accent-border); transform: translateY(-2px); box-shadow: var(--shadow-card); }
.theme-card.active { border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-focus); }
.theme-preview { display: flex; gap: 6px; align-items: center; }
.theme-dot { width: 22px; height: 22px; border-radius: 50%; }
.theme-name { font-size: 13px; font-weight: 500; color: var(--text-primary); }
.settings-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px; }
.wide-card { grid-column: 1 / -1; }
.settings-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 14px; overflow: hidden; box-shadow: var(--shadow-card); }
.card-header { padding: 14px 20px; border-bottom: 1px solid var(--border-light); }
.card-title { margin: 0; font-size: 14px; font-weight: 600; color: var(--text-primary); }
.card-body { padding: 18px 20px; }
.field { display: flex; flex-direction: column; gap: 8px; }
.field-label { font-size: 13px; color: var(--text-tertiary); }
.radio-group { display: flex; flex-direction: column; gap: 12px; }
.radio-item, .checkbox-item { display: flex; align-items: center; gap: 10px; cursor: pointer; }
.radio-item input[type="radio"], .checkbox-item input[type="checkbox"] { width: 18px; height: 18px; margin: 0; accent-color: var(--accent); cursor: pointer; }
.radio-label, .checkbox-label { font-size: 14px; color: var(--text-strong); }
.path-row { display: flex; gap: 10px; align-items: center; }
.path-input { flex: 1; cursor: default; color: var(--text-muted) !important; }
.select-folder-btn, .floating-refresh-btn { flex-shrink: 0; padding: 10px 18px; border-radius: 10px; border: 1px solid var(--border-strong); background: var(--bg-card); color: var(--text-secondary); font-size: 13px; font-weight: 500; cursor: pointer; white-space: nowrap; transition: background 0.2s ease, border-color 0.2s ease, color 0.2s ease; }
.select-folder-btn:hover, .floating-refresh-btn:hover { background: var(--accent-bg-subtle); border-color: var(--accent-border); color: var(--accent); }
.floating-actions { position: fixed; bottom: 28px; right: 28px; z-index: 100; display: flex; gap: 10px; align-items: center; }
.floating-save-btn { display: flex; align-items: center; gap: 8px; padding: 14px 24px; border-radius: 14px; border: none; background: linear-gradient(135deg, var(--accent), var(--accent-hover)); color: var(--btn-text); font-size: 14px; font-weight: 600; cursor: pointer; box-shadow: var(--shadow-float); transition: transform 0.2s ease, box-shadow 0.2s ease; }
.floating-save-btn:hover, .floating-refresh-btn:hover { transform: translateY(-2px); }
</style>
