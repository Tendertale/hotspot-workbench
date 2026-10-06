<script setup>
import { Bot, CheckCircle2, Clock3, FileText, LoaderCircle, Save, X } from 'lucide-vue-next'
import { ref, watch } from 'vue'
import AIAnalysisPanel from './AIAnalysisPanel.vue'
const props = defineProps({ open: Boolean, hotspot: { type: Object, default: null }, loading: Boolean, analyzing: Boolean, actionPending: Boolean, analysisMode: { type: String, default: 'deepseek' } })
const emit = defineEmits(['close', 'analyze', 'confirm', 'edit', 'status-change'])
const selectedStatus = ref('pending')
const statusNote = ref('')
watch(() => props.hotspot, (item) => { if (item) { selectedStatus.value = item.status; statusNote.value = '' } })
const statuses = { pending: '待研判', tracking: '跟踪中', archived: '已归档' }
const eventIcons = { created: FileText, analysis_generated: Bot, analysis_modified: Bot, analysis_confirmed: CheckCircle2, status_changed: Clock3 }
function formatDate(value) { return value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '待补充' }
function submitStatus() { if (props.hotspot && selectedStatus.value !== props.hotspot.status && !props.actionPending) emit('status-change', { status: selectedStatus.value, note: statusNote.value }) }
</script>

<template>
  <Teleport to="body">
    <Transition name="fade"><button v-if="open" class="fixed inset-0 z-[55] cursor-pointer bg-gray-950/30" aria-label="关闭线索详情" @click="emit('close')" /></Transition>
    <Transition name="drawer"><aside v-if="open" class="fixed inset-y-0 right-0 z-[60] flex w-full max-w-[760px] flex-col bg-white shadow-drawer" aria-label="线索详情">
      <header class="flex min-h-16 shrink-0 items-center justify-between border-b border-gray-200 px-5 sm:px-7"><div><h2 class="font-semibold text-gray-950">线索详情</h2><p v-if="hotspot" class="text-xs text-gray-500">{{ hotspot.hotspot_no }}</p></div><button class="rounded-lg p-2 text-gray-500 hover:bg-gray-100" aria-label="关闭" @click="emit('close')"><X :size="20" /></button></header>
      <div v-if="loading || !hotspot" class="flex-1 space-y-5 overflow-hidden p-7"><div class="h-8 w-3/4 animate-pulse rounded bg-gray-100" /><div class="h-20 animate-pulse rounded bg-gray-100" /></div>
      <div v-else class="flex-1 overflow-y-auto"><div class="space-y-7 px-5 py-6 sm:px-7">
        <section>
          <div class="flex flex-wrap items-start justify-between gap-3"><h1 class="max-w-xl text-xl font-semibold leading-8 text-gray-950">{{ hotspot.title }}</h1><span class="rounded-md border border-gray-200 px-2.5 py-1 text-xs font-semibold">{{ statuses[hotspot.status] || hotspot.status }}</span></div>
          <dl class="mt-4 grid grid-cols-1 gap-2 text-xs text-gray-600 sm:grid-cols-2">
            <div><dt class="inline font-semibold">来源：</dt><dd class="inline">{{ hotspot.source_platform || '待补充' }}</dd></div>
            <div><dt class="inline font-semibold">发布时间：</dt><dd class="inline">{{ formatDate(hotspot.published_at) }}</dd></div>
            <div><dt class="inline font-semibold">采集时间：</dt><dd class="inline">{{ formatDate(hotspot.collected_at) }}</dd></div>
            <div><dt class="inline font-semibold">当前互动量：</dt><dd class="inline">{{ hotspot.engagement_count ?? '未记录' }}</dd></div>
          </dl>
          <a v-if="hotspot.source_url" :href="hotspot.source_url" target="_blank" rel="noopener noreferrer" class="mt-3 block break-all text-sm text-blue-700 underline">查看原文来源</a>
          <div class="mt-5 border-t border-gray-200 pt-5"><p class="text-xs font-semibold text-gray-500">内容摘录</p><p class="mt-2 whitespace-pre-wrap text-sm leading-7 text-gray-700">{{ hotspot.content_excerpt }}</p></div>
          <p class="mt-4 rounded-lg bg-gray-50 p-3 text-xs text-gray-600">当前应用分类：{{ hotspot.category || '待确认' }} · 关注等级：{{ { high: '高', medium: '中', low: '低' }[hotspot.attention_level] || '待确认' }}</p>
        </section>
        <AIAnalysisPanel :analysis="hotspot.analysis" :analyzing="analyzing" :action-pending="actionPending" :analysis-mode="analysisMode" @analyze="emit('analyze')" @confirm="emit('confirm')" @edit="emit('edit')" />
        <section><h3 class="text-sm font-semibold text-gray-900">操作记录</h3><div v-for="event in hotspot.events || []" :key="event.id" class="mt-4 flex gap-3"><span class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-gray-200 text-gray-500"><component :is="eventIcons[event.event_type] || Clock3" :size="15" /></span><div><p class="text-sm font-medium text-gray-800">{{ event.title }}</p><p v-if="event.detail" class="mt-1 text-xs text-gray-600">{{ event.detail }}</p><p class="mt-1 text-xs text-gray-400">{{ event.actor }} · {{ formatDate(event.created_at) }}</p></div></div></section>
      </div></div>
      <footer v-if="hotspot && !loading" class="shrink-0 border-t border-gray-200 bg-gray-50 px-5 py-4 sm:px-7"><div class="flex flex-col gap-3 sm:flex-row sm:items-end"><label class="sm:w-44"><span class="mb-1.5 block text-xs font-medium text-gray-600">线索状态</span><select v-model="selectedStatus" class="form-input"><option value="pending">待研判</option><option value="tracking">跟踪中</option><option value="archived">已归档</option></select></label><label class="min-w-0 flex-1"><span class="mb-1.5 block text-xs font-medium text-gray-600">备注</span><input v-model="statusNote" class="form-input" maxlength="300" placeholder="选填" /></label><button class="btn-secondary shrink-0" :disabled="selectedStatus === hotspot.status || actionPending" @click="submitStatus"><LoaderCircle v-if="actionPending" :size="16" class="animate-spin" /><Save v-else :size="16" />更新状态</button></div></footer>
    </aside></Transition>
  </Teleport>
</template>
