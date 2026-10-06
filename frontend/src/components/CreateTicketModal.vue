<script setup>
import { LoaderCircle, Plus, X } from 'lucide-vue-next'
import { reactive, watch } from 'vue'

const props = defineProps({ open: Boolean, saving: Boolean })
const emit = defineEmits(['close', 'submit'])
const empty = () => ({ title: '', content_excerpt: '', source_platform: '', source_url: '', published_at: '', engagement_count: '' })
const form = reactive(empty())
watch(() => props.open, (open) => { if (open) Object.assign(form, empty()) })

function submit() {
  if (props.saving) return
  emit('submit', {
    title: form.title.trim(),
    content_excerpt: form.content_excerpt.trim(),
    source_platform: form.source_platform.trim(),
    source_url: form.source_url.trim() || null,
    published_at: form.published_at ? new Date(form.published_at).toISOString() : null,
    engagement_count: form.engagement_count === '' ? null : Number(form.engagement_count),
  })
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="open" class="fixed inset-0 z-[70] flex items-center justify-center bg-gray-950/40 p-4" @mousedown.self="emit('close')">
        <form class="panel max-h-[92vh] w-full max-w-xl overflow-y-auto p-6" @submit.prevent="submit">
          <div class="flex items-start justify-between gap-4">
            <div><h2 class="text-lg font-semibold text-gray-950">录入热点线索</h2><p class="mt-1 text-sm text-gray-500">保存来源与时间，便于后续研判和核验</p></div>
            <button type="button" class="rounded-lg p-2 text-gray-500 hover:bg-gray-100" aria-label="关闭" @click="emit('close')"><X :size="19" /></button>
          </div>
          <div class="mt-6 space-y-4">
            <label class="block"><span class="mb-2 block text-sm font-medium text-gray-700">标题 *</span><input v-model="form.title" class="form-input" minlength="4" maxlength="200" required placeholder="简要概括热点" /></label>
            <label class="block"><span class="mb-2 block text-sm font-medium text-gray-700">内容摘录 *</span><textarea v-model="form.content_excerpt" class="form-input min-h-32 resize-y" minlength="8" maxlength="5000" required placeholder="摘录原文关键内容，不加入未经核实的判断" /></label>
            <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <label class="block"><span class="mb-2 block text-sm font-medium text-gray-700">来源平台</span><input v-model="form.source_platform" class="form-input" maxlength="80" placeholder="例如：微博" /></label>
              <label class="block"><span class="mb-2 block text-sm font-medium text-gray-700">发布时间</span><input v-model="form.published_at" type="datetime-local" class="form-input" /></label>
            </div>
            <label class="block"><span class="mb-2 block text-sm font-medium text-gray-700">原文链接</span><input v-model="form.source_url" type="url" class="form-input" maxlength="2000" placeholder="https://..." /></label>
            <label class="block"><span class="mb-2 block text-sm font-medium text-gray-700">互动量（可选）</span><input v-model="form.engagement_count" type="number" min="0" step="1" class="form-input" placeholder="仅记录当前数值，不代表增长趋势" /></label>
          </div>
          <div class="mt-7 flex justify-end gap-3 border-t border-gray-200 pt-5">
            <button type="button" class="btn-secondary" :disabled="saving" @click="emit('close')">取消</button>
            <button type="submit" class="btn-primary" :disabled="saving || form.title.trim().length < 4 || form.content_excerpt.trim().length < 8">
              <LoaderCircle v-if="saving" :size="17" class="animate-spin" /><Plus v-else :size="17" />{{ saving ? '正在保存' : '录入线索' }}
            </button>
          </div>
        </form>
      </div>
    </Transition>
  </Teleport>
</template>
