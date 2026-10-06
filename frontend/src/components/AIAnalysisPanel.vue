<script setup>
import { Bot, Check, CircleAlert, LoaderCircle, Pencil, RefreshCw, ShieldCheck, Sparkles } from 'lucide-vue-next'
defineProps({ analysis: { type: Object, default: null }, analyzing: Boolean, actionPending: Boolean, analysisMode: { type: String, default: 'deepseek' } })
const emit = defineEmits(['analyze', 'confirm', 'edit'])
const statuses = { generated: '待复核', modified: '已修改', confirmed: '已确认' }
const levels = { high: '高', medium: '中', low: '低' }
</script>

<template>
  <section class="border-l-4 border-blue-500 bg-blue-50 px-5 py-5">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div class="flex items-center gap-3"><span class="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600 text-white"><Bot :size="19" /></span><div><h3 class="text-sm font-semibold text-gray-950">热点研判结果</h3><p v-if="analysis" class="mt-0.5 text-xs text-gray-500">{{ analysis.provider === 'deepseek' ? analysis.model : '本地规则' }} · 分析版本 v{{ analysis.version }}</p></div></div>
      <span v-if="analysis" class="rounded-md bg-white px-2.5 py-1 text-xs font-semibold text-blue-800">{{ statuses[analysis.status] || analysis.status }}</span>
    </div>
    <div v-if="analyzing" class="flex min-h-48 flex-col items-center justify-center text-center"><LoaderCircle class="animate-spin text-blue-600" :size="28" /><p class="mt-4 text-sm font-medium">正在研判线索</p><p class="mt-1 text-xs text-gray-500">{{ analysisMode === 'deepseek' ? 'DeepSeek 正在生成结构化结论' : '正在执行本地规则' }}</p></div>
    <div v-else-if="!analysis" class="flex min-h-48 flex-col items-center justify-center text-center"><Sparkles :size="28" class="text-blue-600" /><p class="mt-4 text-sm font-medium">尚未生成分析结果</p><button class="btn-primary mt-5" @click="emit('analyze')">{{ analysisMode === 'deepseek' ? '使用 DeepSeek 分析' : '使用本地规则分析' }}</button></div>
    <div v-else class="mt-5 space-y-5">
      <div class="grid grid-cols-2 gap-4 border-b border-blue-200 pb-5">
        <div><p class="text-xs text-gray-500">类别建议</p><p class="mt-1 text-sm font-semibold">{{ analysis.category }}</p></div>
        <div><p class="text-xs text-gray-500">关注等级建议</p><p class="mt-1 text-sm font-semibold">{{ levels[analysis.attention_level] || analysis.attention_level }}</p></div>
        <div class="col-span-2"><p class="text-xs text-gray-500">置信度 {{ Math.round((analysis.confidence || 0) * 100) }}%</p><div class="mt-2 h-2 overflow-hidden rounded-full bg-blue-100"><div class="h-full rounded-full bg-blue-600" :style="{ width: Math.round((analysis.confidence || 0) * 100) + '%' }" /></div></div>
      </div>
      <div><p class="text-xs font-semibold text-gray-700">摘要</p><p class="mt-2 whitespace-pre-wrap text-sm leading-6 text-gray-700">{{ analysis.summary }}</p></div>
      <div v-if="analysis.keywords?.length"><p class="text-xs font-semibold text-gray-700">关键词</p><p class="mt-2 text-sm text-gray-700">{{ analysis.keywords.join(' · ') }}</p></div>
      <div v-if="analysis.entities?.length"><p class="text-xs font-semibold text-gray-700">相关实体</p><p class="mt-2 text-sm text-gray-700">{{ analysis.entities.join(' · ') }}</p></div>
      <div><p class="text-xs font-semibold text-gray-700">证据</p><ul class="mt-2 list-disc space-y-1 pl-5 text-sm text-gray-700"><li v-for="(item, index) in analysis.evidence || []" :key="index">{{ item }}</li></ul></div>
      <div v-if="analysis.verification?.length" class="border-y border-blue-200 py-4"><p class="mb-2 flex items-center gap-2 text-xs font-semibold text-gray-700"><ShieldCheck :size="16" />本地规则核验</p><div v-for="(check, index) in analysis.verification" :key="index" class="mt-2 text-sm"><span :class="check.status === 'blocked' ? 'text-red-700' : check.status === 'warning' ? 'text-amber-700' : 'text-emerald-700'">{{ check.name }}：</span><span class="text-gray-700">{{ check.detail }}</span></div></div>
      <div v-if="analysis.risk_flags?.length" class="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800"><p class="flex items-center gap-2 font-semibold"><CircleAlert :size="16" />风险提示</p><p class="mt-1">{{ analysis.risk_flags.join('；') }}</p></div>
      <div class="rounded-lg border p-4" :class="analysis.can_auto_handle ? 'border-emerald-200 bg-emerald-50' : 'border-amber-200 bg-amber-50'">
        <p class="text-sm font-semibold">{{ analysis.can_auto_handle ? '可自动归类候选' : '需人工核验' }}</p>
        <p class="mt-1 text-xs text-gray-600">自动归类不代表自动对外发布</p><p class="mt-2 text-sm leading-6">{{ analysis.action_suggestion }}</p>
        <p v-if="analysis.missing_information?.length" class="mt-2 text-xs">待补充：{{ analysis.missing_information.join('、') }}</p>
      </div>
      <div class="flex flex-wrap gap-2 pt-1"><button class="btn-secondary" :disabled="actionPending" @click="emit('analyze')"><RefreshCw :size="16" />重新分析</button><button class="btn-secondary" :disabled="actionPending || analysis.status === 'confirmed'" @click="emit('edit')"><Pencil :size="16" />人工修改</button><button class="btn-primary ml-auto" :disabled="actionPending || analysis.status === 'confirmed'" @click="emit('confirm')"><Check :size="17" />{{ analysis.status === 'confirmed' ? '已确认应用' : '确认并应用' }}</button></div>
    </div>
  </section>
</template>
