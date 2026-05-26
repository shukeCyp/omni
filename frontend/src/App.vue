<script setup>
import { computed, ref, onMounted } from 'vue'
import Toast from './components/Toast.vue'
import Settings from './components/Settings.vue'
import OmniProduct from './components/OmniProduct.vue'

const toastRef = ref(null)
const currentPage = ref('omni_text')

const omniNavItems = [
  { page: 'omni_text', mode: 'text', label: '文生视频' },
  { page: 'omni_components', mode: 'components', label: '多参考视频' },
]

const currentOmniMode = computed(() => {
  return omniNavItems.find(item => item.page === currentPage.value)?.mode || 'text'
})

const loadTheme = async () => {
  try {
    const settings = await window.pywebview.api.get_all_settings()
    if (settings.theme) {
      document.documentElement.setAttribute('data-theme', settings.theme)
    }
  } catch { /* ignore */ }
}

onMounted(() => {
  loadTheme()
})
</script>

<template>
  <div class="app-shell">
    <div class="bg-glow bg-glow--top"></div>
    <div class="bg-glow bg-glow--bottom"></div>

    <div class="main-layout">
      <aside class="sidebar">
        <div class="sidebar-header">
          <div class="brand brand--small">
            <div class="brand-mark"></div>
            <div class="brand-title">荷塘omni</div>
          </div>
        </div>

        <nav class="sidebar-nav">
          <button
            v-for="item in omniNavItems"
            :key="item.page"
            :class="['nav-item', { active: currentPage === item.page }]"
            @click="currentPage = item.page"
          >
            <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
              <polygon points="10 8 16 11 10 14 10 8"/>
              <path d="M7 21h10"/>
            </svg>
            <span>{{ item.label }}</span>
          </button>
        </nav>

        <div class="sidebar-footer">
          <button
            :class="['nav-item', { active: currentPage === 'settings' }]"
            @click="currentPage = 'settings'"
          >
            <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="3"></circle>
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
            </svg>
            <span>设置</span>
          </button>
        </div>
      </aside>

      <main class="main-content">
        <OmniProduct
          v-show="currentPage.startsWith('omni_')"
          :mode="currentOmniMode"
          @toast="(msg, type) => toastRef?.show(msg, type)"
        />

        <Settings
          v-show="currentPage === 'settings'"
          @toast="(msg, type) => toastRef?.show(msg, type)"
        />
      </main>
    </div>

    <Toast ref="toastRef" />
  </div>
</template>
