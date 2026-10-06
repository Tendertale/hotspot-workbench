<script setup>
import { Bot, ChevronRight, Inbox } from 'lucide-vue-next'
defineProps({ hotspots: { type: Array, default: () => [] }, loading: Boolean, emptyText: { type: String, default: '暂无符合条件的线索' } })
const emit = defineEmits(['select'])
const attention = { high: ['高', 'bg-red-50 text-red-700'], medium: ['中', 'bg-amber-50 text-amber-700'], low: ['低', 'bg-blue-50 text-blue-700'] }
const statuses = { pending: '待研判', tracking: '跟踪中', archived: '已归档' }
const analyses = { generated: '待复核', modified: '已修改', confirmed: '已确认' }
function formatDate(value) { return value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '待补充' }
</script>

<template>
  <div class="overflow-x-auto">
    <table class="w-full min-w-[1000px] table-fixed text-left">
      <thead><tr class="border-b border-gray-200 bg-gray-50 text-xs font-semibold text-gray-500">
        <th class="w-32 px-5 py-3">线索编号</th><th class="w-[30%] px-4 py-3">标题 / 来源</th><th class="w-28 px-4 py-3">类别</th>
        <th class="w-24 px-4 py-3">关注等级</th><th class="w-24 px-4 py-3">状态</th><th class="w-32 px-4 py-3">分析</th>
        <th class="w-36 px-4 py-3">发布时间</th><th class="w-20 px-4 py-3 text-right">操作</th>
      </tr></thead>
      <tbody v-if="loading"><tr v-for="index in 6" :key="index" class="border-b border-gray-100"><td v-for="cell in 8" :key="cell" class="px-4 py-4"><div class="h-4 animate-pulse rounded bg-gray-100" /></td></tr></tbody>
      <tbody v-else-if="hotspots.length"><tr v-for="item in hotspots" :key="item.id" class="cursor-pointer border-b border-gray-100 text-sm hover:bg-gray-50" @click="emit('select', item)">
        <td class="px-5 py-4 font-medium text-gray-600">{{ item.hotspot_no }}</td>
        <td class="px-4 py-4"><p class="truncate font-medium text-gray-950" :title="item.title">{{ item.title }}</p><p class="mt-1 truncate text-xs text-gray-500">{{ item.source_platform || '来源待补充' }}</p></td>
        <td class="px-4 py-4 text-gray-600">{{ item.category || '待确认' }}</td>
        <td class="px-4 py-4"><span v-if="item.attention_level" class="rounded-md px-2 py-1 text-xs font-semibold" :class="attention[item.attention_level]?.[1]">{{ attention[item.attention_level]?.[0] }}</span><span v-else class="text-xs text-gray-400">待确认</span></td>
        <td class="px-4 py-4 text-gray-700">{{ statuses[item.status] || item.status }}</td>
        <td class="px-4 py-4"><span v-if="item.analysis_status" class="inline-flex items-center gap-1 text-xs text-blue-700"><Bot :size="14" />{{ analyses[item.analysis_status] || item.analysis_status }} <span v-if="item.analysis_confidence != null">{{ Math.round(item.analysis_confidence * 100) }}%</span></span><span v-else class="text-xs text-gray-400">未分析</span></td>
        <td class="px-4 py-4 text-xs text-gray-500">{{ formatDate(item.published_at) }}</td>
        <td class="px-4 py-4 text-right"><button class="inline-flex items-center gap-1 text-sm font-medium text-blue-600 hover:text-blue-800" @click.stop="emit('select', item)">详情<ChevronRight :size="16" /></button></td>
      </tr></tbody>
    </table>
    <div v-if="!loading && !hotspots.length" class="flex min-h-64 flex-col items-center justify-center px-6 text-center"><Inbox :size="30" class="text-gray-400" /><p class="mt-3 text-sm font-medium text-gray-700">{{ emptyText }}</p></div>
  </div>
</template>
