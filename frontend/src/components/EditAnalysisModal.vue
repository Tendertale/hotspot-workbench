<script setup>
import { LoaderCircle, Save, X } from 'lucide-vue-next'
import { reactive, watch } from 'vue'
const props = defineProps({ open: Boolean, analysis: { type: Object, default: null }, saving: Boolean })
const emit = defineEmits(['close', 'submit'])
const form = reactive({ category: '', attention_level: 'medium', summary: '', keywords_text: '', entities_text: '', can_auto_handle: false, action_suggestion: '', missing_information_text: '', review_note: '' })
watch(() => [props.open, props.analysis], () => {
  if (props.open && props.analysis) Object.assign(form, {
    category: props.analysis.category || '',
    attention_level: props.analysis.attention_level || 'medium',
    summary: props.analysis.summary || '',
    keywords_text: (props.analysis.keywords || []).join('、'),
    entities_text: (props.analysis.entities || []).join('、'),
    can_auto_handle: Boolean(props.analysis.can_auto_handle),
    action_suggestion: props.analysis.action_suggestion || '',
    missing_information_text: (props.analysis.missing_information || []).join('、'),
    review_note: '',
  })
})
const split = (text) => text.split(/[、,，\n]/).map((x) => x.trim()).filter(Boolean)
function submit() {
  if (props.saving) return
  emit('submit', {
    category: form.category.trim(), attention_level: form.attention_level, summary: form.summary.trim(),
    keywords: split(form.keywords_text), entities: split(form.entities_text),
    can_auto_handle: form.can_auto_handle, action_suggestion: form.action_suggestion.trim(),
    missing_information: split(form.missing_information_text), review_note: form.review_note.trim(),
  })
}
</script>

<template>
  <Teleport to="body"><Transition name="fade">
    <div v-if="open && analysis" class="fixed inset-0 z-[80] flex items-center justify-center bg-gray-950/45 p-4" @mousedown.self="emit('close')">
      <form class="panel max-h-[92vh] w-full max-w-2xl overflow-y-auto p-6" @submit.prevent="submit">
        <div class="flex items-start justify-between gap-4"><div><h2 class="text-lg font-semibold text-gray-950">人工修改研判</h2><p class="mt-1 text-sm text-gray-500">保存后仍需确认，才会应用到线索</p></div><button type="button" class="rounded-lg p-2 text-gray-500 hover:bg-gray-100" aria-label="关闭" @click="emit('close')"><X :size="19" /></button></div>
        <div class="mt-6 grid grid-cols-1 gap-5 sm:grid-cols-2">
          <label><span class="mb-2 block text-sm font-medium text-gray-700">热点类别</span><input v-model="form.category" class="form-input" required /></label>
          <label><span class="mb-2 block text-sm font-medium text-gray-700">关注等级建议</span><select v-model="form.attention_level" class="form-input"><option value="high">高</option><option value="medium">中</option><option value="low">低</option></select></label>
          <label class="sm:col-span-2"><span class="mb-2 block text-sm font-medium text-gray-700">摘要</span><textarea v-model="form.summary" class="form-input min-h-24" required /></label>
          <label><span class="mb-2 block text-sm font-medium text-gray-700">关键词（逗号分隔）</span><input v-model="form.keywords_text" class="form-input" /></label>
          <label><span class="mb-2 block text-sm font-medium text-gray-700">相关实体（逗号分隔）</span><input v-model="form.entities_text" class="form-input" /></label>
          <label class="sm:col-span-2"><span class="mb-2 block text-sm font-medium text-gray-700">建议动作</span><textarea v-model="form.action_suggestion" class="form-input min-h-20" required /></label>
          <label class="sm:col-span-2"><span class="mb-2 block text-sm font-medium text-gray-700">待补充信息（逗号分隔）</span><input v-model="form.missing_information_text" class="form-input" /></label>
          <label class="sm:col-span-2 flex items-center gap-2 text-sm text-gray-700"><input v-model="form.can_auto_handle" type="checkbox" />符合自动归类条件（不对外发布）</label>
          <label class="sm:col-span-2"><span class="mb-2 block text-sm font-medium text-gray-700">复核备注</span><input v-model="form.review_note" class="form-input" maxlength="300" /></label>
        </div>
        <div class="mt-7 flex justify-end gap-3 border-t border-gray-200 pt-5"><button type="button" class="btn-secondary" :disabled="saving" @click="emit('close')">取消</button><button type="submit" class="btn-primary" :disabled="saving"><LoaderCircle v-if="saving" :size="17" class="animate-spin" /><Save v-else :size="17" />保存修改</button></div>
      </form>
    </div>
  </Transition></Teleport>
</template>
