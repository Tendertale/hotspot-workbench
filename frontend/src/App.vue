<script setup>
import { AlertCircle, Bell, CheckCircle2, ChevronDown, Cloud, Menu, Plus, Search, X } from 'lucide-vue-next'
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { api } from './api'
import AISettingsModal from './components/AISettingsModal.vue'
import CreateTicketModal from './components/CreateTicketModal.vue'
import EditAnalysisModal from './components/EditAnalysisModal.vue'
import Sidebar from './components/Sidebar.vue'
import StatsCards from './components/StatsCards.vue'
import TicketDetailDrawer from './components/TicketDetailDrawer.vue'
import TicketTable from './components/TicketTable.vue'

const activeView = ref('hotspots')
const mobileNavOpen = ref(false)
const loading = ref(true)
const detailLoading = ref(false)
const actionPending = ref(false)
const analyzing = ref(false)
const hotspots = ref([])
const total = ref(0)
const stats = reactive({ total: 0, pending: 0, tracking: 0, archived: 0, high_attention: 0, analyzed: 0, pending_review: 0, auto_eligible: 0, by_category: [], by_source: [] })
const filters = reactive({ search: '', source_platform: '', category: '', attention_level: '', status: '', analysis_status: '', page: 1, page_size: 20 })
const selectedHotspot = ref(null)
const drawerOpen = ref(false)
const createOpen = ref(false)
const createSaving = ref(false)
const editOpen = ref(false)
const aiSettingsOpen = ref(false)
const analysisMode = ref('deepseek')
const deepseekApiKey = ref('')
const verifiedApiKey = ref('')
const connectionStatus = ref('unconfigured')
const statusBeforeSettings = ref('unconfigured')
const connectionError = ref('')
const connectionTesting = ref(false)
const pendingAnalyze = ref(false)
const aiConfig = reactive({ provider: 'deepseek', base_url: 'https://api.deepseek.com', model: 'deepseek-v4-flash', key_persistence: 'memory_only', fallback_mode: 'rules' })
const errorMessage = ref('')
const toast = reactive({ visible: false, type: 'success', message: '' })
let toastTimer
let searchTimer
let listRequestId = 0

const pageCount = computed(() => Math.max(1, Math.ceil(total.value / filters.page_size)))
const hasFilters = computed(() => ['search', 'source_platform', 'category', 'attention_level', 'status', 'analysis_status'].some((key) => filters[key]))
const categories = ['社会民生', '科技互联网', '商业财经', '公共政策', '文娱体育', '其他']

function notify(message, type = 'success') {
  clearTimeout(toastTimer)
  Object.assign(toast, { visible: true, type, message })
  toastTimer = setTimeout(() => { toast.visible = false }, 3500)
}

function showError(error) { notify(error instanceof Error ? error.message : '操作失败，请稍后重试', 'error') }

async function loadList(silent = false) {
  const requestId = ++listRequestId
  if (!silent) loading.value = true
  errorMessage.value = ''
  try {
    const result = await api.listHotspots(filters)
    if (requestId !== listRequestId) return
    hotspots.value = result.items || []
    total.value = result.total || 0
  } catch (error) {
    if (requestId === listRequestId) errorMessage.value = error instanceof Error ? error.message : '线索加载失败'
  } finally {
    if (requestId === listRequestId) loading.value = false
  }
}

async function loadStats() {
  try { Object.assign(stats, await api.stats()) }
  catch (error) { showError(error) }
}

async function refreshOverview(silent = true) { await Promise.all([loadList(silent), loadStats()]) }

async function openHotspot(item) {
  drawerOpen.value = true
  detailLoading.value = true
  selectedHotspot.value = null
  try { selectedHotspot.value = await api.hotspot(item.id) }
  catch (error) { drawerOpen.value = false; showError(error) }
  finally { detailLoading.value = false }
}

async function refreshSelected() {
  if (selectedHotspot.value) selectedHotspot.value = await api.hotspot(selectedHotspot.value.id)
}

async function createHotspot(payload) {
  createSaving.value = true
  try {
    const created = await api.createHotspot(payload)
    createOpen.value = false
    filters.page = 1
    await refreshOverview()
    notify('热点线索已录入')
    await openHotspot(created)
  } catch (error) { showError(error) }
  finally { createSaving.value = false }
}

async function handleConflict(error) {
  if (error?.status === 409) {
    try { await refreshSelected(); await refreshOverview() }
    catch (refreshError) { showError(refreshError) }
  }
  showError(error)
}

async function analyzeSelected() {
  if (!selectedHotspot.value || actionPending.value) return
  if (analysisMode.value === 'deepseek' && !deepseekApiKey.value) {
    pendingAnalyze.value = true
    verifiedApiKey.value = ''
    statusBeforeSettings.value = connectionStatus.value
    aiSettingsOpen.value = true
    notify('请先配置 DeepSeek API 密钥', 'error')
    return
  }
  analyzing.value = true
  actionPending.value = true
  try {
    await api.analyze(selectedHotspot.value.id, { mode: analysisMode.value, expected_version: selectedHotspot.value.version, apiKey: analysisMode.value === 'deepseek' ? deepseekApiKey.value : '' })
    await Promise.all([refreshSelected(), refreshOverview()])
    if (analysisMode.value === 'deepseek') connectionStatus.value = 'ready'
    notify('分析完成，请人工复核')
  } catch (error) {
    if (analysisMode.value === 'deepseek' && error?.status !== 409) { connectionStatus.value = 'error'; connectionError.value = error.message }
    await handleConflict(error)
  } finally { analyzing.value = false; actionPending.value = false }
}

async function saveAnalysis(payload) {
  if (!selectedHotspot.value || actionPending.value) return
  actionPending.value = true
  try {
    await api.editAnalysis(selectedHotspot.value.id, { ...payload, expected_version: selectedHotspot.value.version })
    editOpen.value = false
    await Promise.all([refreshSelected(), refreshOverview()])
    notify('人工修改已保存')
  } catch (error) { await handleConflict(error) }
  finally { actionPending.value = false }
}

async function confirmAnalysis() {
  if (!selectedHotspot.value || actionPending.value) return
  actionPending.value = true
  try {
    selectedHotspot.value = await api.confirmAnalysis(selectedHotspot.value.id, { expected_version: selectedHotspot.value.version, review_note: '' })
    await refreshOverview()
    notify('研判已确认并应用到线索')
  } catch (error) { await handleConflict(error) }
  finally { actionPending.value = false }
}

async function updateStatus(payload) {
  if (!selectedHotspot.value || actionPending.value) return
  actionPending.value = true
  try {
    selectedHotspot.value = await api.updateStatus(selectedHotspot.value.id, { ...payload, expected_version: selectedHotspot.value.version })
    await refreshOverview()
    notify('线索状态已更新')
  } catch (error) { await handleConflict(error) }
  finally { actionPending.value = false }
}

function openAISettings() {
  mobileNavOpen.value = false
  pendingAnalyze.value = false
  verifiedApiKey.value = ''
  statusBeforeSettings.value = connectionStatus.value
  connectionError.value = ''
  aiSettingsOpen.value = true
}

function closeAISettings() {
  aiSettingsOpen.value = false
  pendingAnalyze.value = false
  verifiedApiKey.value = ''
  connectionStatus.value = statusBeforeSettings.value
  connectionError.value = ''
}

async function verifyAIConnection(apiKey) {
  connectionTesting.value = true
  connectionError.value = ''
  connectionStatus.value = 'testing'
  try {
    const result = await api.verifyDeepSeek(apiKey)
    verifiedApiKey.value = apiKey
    connectionStatus.value = 'ready'
    aiConfig.model = result.model || aiConfig.model
    notify('DeepSeek 连接成功')
  } catch (error) { connectionStatus.value = 'error'; connectionError.value = error.message }
  finally { connectionTesting.value = false }
}

async function saveAISettings(payload) {
  const nextKey = payload.apiKey.trim()
  if (payload.mode === 'deepseek') {
    const verified = verifiedApiKey.value === nextKey || (deepseekApiKey.value === nextKey && statusBeforeSettings.value === 'ready')
    deepseekApiKey.value = nextKey
    connectionStatus.value = verified ? 'ready' : 'configured'
  } else {
    connectionStatus.value = 'local'
    connectionError.value = ''
  }
  analysisMode.value = payload.mode
  verifiedApiKey.value = ''
  aiSettingsOpen.value = false
  notify(payload.mode === 'deepseek' ? '已启用 DeepSeek 分析' : '已切换到本地规则')
  if (pendingAnalyze.value) { pendingAnalyze.value = false; await analyzeSelected() }
}

function clearFilters() {
  Object.assign(filters, { search: '', source_platform: '', category: '', attention_level: '', status: '', analysis_status: '', page: 1 })
}

function navigate(view) {
  activeView.value = view
  mobileNavOpen.value = false
  filters.analysis_status = view === 'ai-center' ? 'generated' : ''
}

function handleKeydown(event) {
  if (event.key !== 'Escape') return
  if (aiSettingsOpen.value) closeAISettings()
  else if (editOpen.value) editOpen.value = false
  else if (createOpen.value) createOpen.value = false
  else if (drawerOpen.value) drawerOpen.value = false
  else mobileNavOpen.value = false
}

watch(() => [filters.search, filters.source_platform, filters.category, filters.attention_level, filters.status, filters.analysis_status], () => {
  filters.page = 1
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => loadList(), 250)
})
watch(() => filters.page, () => loadList())
watch([drawerOpen, createOpen, editOpen, aiSettingsOpen], ([drawer, create, edit, settings]) => {
  document.body.style.overflow = drawer || create || edit || settings ? 'hidden' : ''
})
onMounted(() => {
  refreshOverview(false)
  api.aiConfig().then((config) => Object.assign(aiConfig, config)).catch(() => {})
  window.addEventListener('keydown', handleKeydown)
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeydown)
  document.body.style.overflow = ''
  clearTimeout(toastTimer)
  clearTimeout(searchTimer)
})
</script>

<template>
  <div class="min-h-screen bg-gray-100">
    <Sidebar :active-view="activeView" :mobile-open="mobileNavOpen" :awaiting-review="stats.pending_review" :ai-status="connectionStatus" :analysis-mode="analysisMode" @navigate="navigate" @close="mobileNavOpen = false" @configure="openAISettings" />
    <div class="min-h-screen lg:pl-60">
      <header class="sticky top-0 z-30 flex h-16 items-center gap-4 border-b border-gray-200 bg-white/95 px-4 backdrop-blur sm:px-6 lg:px-8">
        <button class="rounded-lg p-2 text-gray-600 hover:bg-gray-100 lg:hidden" aria-label="打开导航" @click="mobileNavOpen = true"><Menu :size="20" /></button>
        <div class="relative max-w-xl flex-1"><Search class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" :size="18" /><input v-model="filters.search" class="form-input h-10 pl-10" placeholder="搜索标题、内容或线索编号" /><button v-if="filters.search" class="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-gray-400" aria-label="清除搜索" @click="filters.search = ''"><X :size="15" /></button></div>
        <button class="ml-auto inline-flex h-10 items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 text-sm text-gray-600" @click="openAISettings"><Cloud :size="17" /><span class="hidden sm:inline">{{ analysisMode === 'rules' ? '本地规则' : connectionStatus === 'ready' ? 'DeepSeek 已连接' : '配置 DeepSeek' }}</span></button>
        <Bell :size="18" class="text-gray-500" /><span class="flex h-9 w-9 items-center justify-center rounded-full bg-gray-900 text-sm font-semibold text-white">研</span>
      </header>
      <main class="mx-auto max-w-[1600px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
        <div class="flex flex-wrap items-start justify-between gap-4"><div><h1 class="text-2xl font-semibold text-gray-950">{{ activeView === 'hotspots' ? '热点线索' : '研判中心' }}</h1><p class="mt-1 text-sm text-gray-500">{{ activeView === 'hotspots' ? '录入、核验并跟踪热点信息' : '复核分析结论与自动归类建议' }}</p></div><button v-if="activeView === 'hotspots'" class="btn-primary" @click="createOpen = true"><Plus :size="18" />录入线索</button></div>
        <div v-if="errorMessage" class="mt-6 flex items-center justify-between gap-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"><span class="flex items-center gap-2"><AlertCircle :size="17" />{{ errorMessage }}</span><button class="font-medium underline" @click="loadList()">重新加载</button></div>
        <StatsCards class="mt-6" :stats="stats" :loading="loading" />
        <div class="mt-5 flex flex-wrap gap-3 text-sm text-gray-600"><span>待复核 {{ stats.pending_review }}</span><span>跟踪中 {{ stats.tracking }}</span><span>已归档 {{ stats.archived }}</span><span>可自动归类候选 {{ stats.auto_eligible }}</span></div>
        <section class="panel mt-6 overflow-hidden">
          <div class="flex flex-wrap items-end gap-3 border-b border-gray-200 p-4">
            <label class="block w-36"><span class="mb-1 block text-xs text-gray-500">来源平台</span><input v-model="filters.source_platform" class="form-input" placeholder="全部来源" /></label>
            <label class="block w-36"><span class="mb-1 block text-xs text-gray-500">类别</span><select v-model="filters.category" class="form-input"><option value="">全部类别</option><option v-for="category in categories" :key="category" :value="category">{{ category }}</option></select></label>
            <label class="block w-32"><span class="mb-1 block text-xs text-gray-500">关注等级</span><select v-model="filters.attention_level" class="form-input"><option value="">全部等级</option><option value="high">高</option><option value="medium">中</option><option value="low">低</option></select></label>
            <label class="block w-32"><span class="mb-1 block text-xs text-gray-500">线索状态</span><select v-model="filters.status" class="form-input"><option value="">全部状态</option><option value="pending">待研判</option><option value="tracking">跟踪中</option><option value="archived">已归档</option></select></label>
            <label class="block w-32"><span class="mb-1 block text-xs text-gray-500">分析状态</span><select v-model="filters.analysis_status" class="form-input"><option value="">全部分析</option><option value="generated">待复核</option><option value="modified">已修改</option><option value="confirmed">已确认</option></select></label>
            <button v-if="hasFilters" class="ml-auto inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-800" @click="clearFilters"><X :size="15" />清除筛选</button>
          </div>
          <TicketTable :hotspots="hotspots" :loading="loading" :empty-text="activeView === 'ai-center' ? '暂无待复核线索' : '暂无符合条件的线索'" @select="openHotspot" />
          <div class="flex items-center justify-between border-t border-gray-200 px-4 py-3 text-sm text-gray-600"><span>共 {{ total }} 条 · 第 {{ filters.page }} / {{ pageCount }} 页</span><div class="flex gap-2"><button class="btn-secondary" :disabled="loading || filters.page <= 1" @click="filters.page--">上一页</button><button class="btn-secondary" :disabled="loading || filters.page >= pageCount" @click="filters.page++">下一页</button></div></div>
        </section>
        <section v-if="stats.by_category?.length || stats.by_source?.length" class="mt-6 grid gap-4 md:grid-cols-2">
          <div class="panel p-5"><h2 class="font-semibold">类别分布</h2><p class="mt-3 text-sm text-gray-600">{{ stats.by_category.map(item => (item.category || item.name) + ' ' + item.count).join(' · ') || '暂无数据' }}</p></div>
          <div class="panel p-5"><h2 class="font-semibold">来源分布</h2><p class="mt-3 text-sm text-gray-600">{{ stats.by_source.map(item => (item.source_platform || item.name || '未填写') + ' ' + item.count).join(' · ') || '暂无数据' }}</p></div>
        </section>
      </main>
    </div>
    <TicketDetailDrawer :open="drawerOpen" :hotspot="selectedHotspot" :loading="detailLoading" :analyzing="analyzing" :action-pending="actionPending" :analysis-mode="analysisMode" @close="drawerOpen = false" @analyze="analyzeSelected" @confirm="confirmAnalysis" @edit="editOpen = true" @status-change="updateStatus" />
    <CreateTicketModal :open="createOpen" :saving="createSaving" @close="createOpen = false" @submit="createHotspot" />
    <EditAnalysisModal :open="editOpen" :analysis="selectedHotspot?.analysis" :saving="actionPending" @close="editOpen = false" @submit="saveAnalysis" />
    <AISettingsModal :open="aiSettingsOpen" :mode="analysisMode" :api-key="deepseekApiKey" :verified-api-key="verifiedApiKey" :config="aiConfig" :connection-status="connectionStatus" :connection-error="connectionError" :testing="connectionTesting" @close="closeAISettings" @verify="verifyAIConnection" @save="saveAISettings" />
    <Transition name="fade"><div v-if="toast.visible" class="fixed bottom-6 right-6 z-[100] flex max-w-sm items-center gap-3 rounded-lg border bg-white px-4 py-3 text-sm font-medium shadow-lg" :class="toast.type === 'error' ? 'border-red-200 text-red-800' : 'border-emerald-200 text-gray-800'" role="status"><AlertCircle v-if="toast.type === 'error'" :size="18" class="shrink-0 text-red-600" /><CheckCircle2 v-else :size="18" class="shrink-0 text-emerald-600" />{{ toast.message }}</div></Transition>
  </div>
</template>
