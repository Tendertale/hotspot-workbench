<script setup>
import { Bot, CircleAlert, Clock3, Newspaper } from 'lucide-vue-next'

const props = defineProps({
  stats: { type: Object, required: true },
  loading: { type: Boolean, default: false },
})

const cards = [
  { key: 'total', label: '线索总数', icon: Newspaper, tone: 'bg-blue-50 text-blue-700', note: '当前全部记录' },
  { key: 'pending', label: '待研判', icon: Clock3, tone: 'bg-amber-50 text-amber-700', note: '等待分析与复核' },
  { key: 'high_attention', label: '高关注', icon: CircleAlert, tone: 'bg-red-50 text-red-700', note: '已确认并应用' },
  { key: 'analyzed', label: '已分析', icon: Bot, tone: 'bg-emerald-50 text-emerald-700', note: '已有研判依据' },
]
</script>

<template>
  <section class="grid grid-cols-2 gap-4 xl:grid-cols-4" aria-label="热点统计">
    <article v-for="card in cards" :key="card.key" class="panel min-h-[130px] p-5">
      <div class="flex items-start justify-between gap-3">
        <div>
          <p class="text-sm font-medium text-gray-500">{{ card.label }}</p>
          <div v-if="loading" class="mt-3 h-9 w-16 animate-pulse rounded bg-gray-100" />
          <p v-else class="mt-2 text-3xl font-semibold tabular-nums text-gray-950">{{ props.stats[card.key] ?? 0 }}</p>
        </div>
        <span class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg" :class="card.tone">
          <component :is="card.icon" :size="20" />
        </span>
      </div>
      <p class="mt-3 text-xs text-gray-500">{{ card.note }}</p>
    </article>
  </section>
</template>

