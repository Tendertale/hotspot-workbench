<script setup>
import { Bot, Inbox, Settings, Sparkles, X } from 'lucide-vue-next'

defineProps({
  activeView: { type: String, required: true },
  mobileOpen: { type: Boolean, default: false },
  awaitingReview: { type: Number, default: 0 },
  aiStatus: { type: String, default: 'unconfigured' },
  analysisMode: { type: String, default: 'deepseek' },
})

const emit = defineEmits(['navigate', 'close', 'configure'])

const navigation = [
  { id: 'hotspots', label: '热点线索', icon: Inbox },
  { id: 'ai-center', label: '研判中心', icon: Sparkles },
]
</script>

<template>
  <Transition name="fade">
    <button
      v-if="mobileOpen"
      class="fixed inset-0 z-40 cursor-pointer bg-gray-950/30 lg:hidden"
      aria-label="关闭导航"
      @click="emit('close')"
    />
  </Transition>

  <aside
    class="fixed inset-y-0 left-0 z-50 flex w-60 flex-col border-r border-gray-200 bg-white transition-transform duration-200 lg:translate-x-0"
    :class="mobileOpen ? 'translate-x-0' : '-translate-x-full'"
  >
    <div class="flex h-16 shrink-0 items-center justify-between border-b border-gray-200 px-5">
      <div class="flex items-center gap-3">
        <span class="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600 text-white">
          <Bot :size="20" stroke-width="2.2" />
        </span>
        <div>
          <p class="text-[15px] font-semibold text-gray-950">热点研判</p>
          <p class="text-xs text-gray-500">Insight Console</p>
        </div>
      </div>
      <button class="cursor-pointer rounded-lg p-2 text-gray-500 hover:bg-gray-100 lg:hidden" @click="emit('close')">
        <X :size="19" />
      </button>
    </div>

    <nav class="flex-1 space-y-1 px-3 py-5" aria-label="主导航">
      <button
        v-for="item in navigation"
        :key="item.id"
        class="flex h-11 w-full cursor-pointer items-center gap-3 rounded-lg px-3 text-sm font-medium transition-colors"
        :class="activeView === item.id ? 'bg-blue-50 text-blue-700' : 'text-gray-600 hover:bg-gray-50 hover:text-gray-950'"
        @click="emit('navigate', item.id)"
      >
        <component :is="item.icon" :size="19" />
        <span>{{ item.label }}</span>
        <span
          v-if="item.id === 'ai-center' && awaitingReview"
          class="ml-auto min-w-6 rounded-full bg-amber-100 px-1.5 py-0.5 text-center text-xs font-semibold text-amber-700"
        >
          {{ awaitingReview }}
        </span>
      </button>
      <button
        class="flex h-11 w-full cursor-pointer items-center gap-3 rounded-lg px-3 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-50 hover:text-gray-950"
        @click="emit('configure')"
      >
        <Settings :size="19" />
        <span>AI 接入设置</span>
        <span
          class="ml-auto h-2 w-2 rounded-full"
          :class="analysisMode === 'rules' ? 'bg-gray-400' : aiStatus === 'ready' ? 'bg-emerald-500' : 'bg-amber-500'"
        />
      </button>
    </nav>

    <div class="border-t border-gray-200 p-4">
      <div class="flex items-center gap-3 rounded-lg bg-gray-50 px-3 py-3">
        <span class="flex h-9 w-9 items-center justify-center rounded-full bg-gray-900 text-sm font-semibold text-white">研</span>
        <div class="min-w-0">
          <p class="truncate text-sm font-medium text-gray-900">研判员</p>
          <p class="text-xs text-gray-500">人工复核席</p>
        </div>
      </div>
    </div>
  </aside>
</template>
