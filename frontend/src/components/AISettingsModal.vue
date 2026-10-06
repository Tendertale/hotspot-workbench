<script setup>
import {
  CheckCircle2,
  Cloud,
  Eye,
  EyeOff,
  KeyRound,
  LoaderCircle,
  Save,
  ShieldCheck,
  X,
} from 'lucide-vue-next'
import { computed, reactive, ref, watch } from 'vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  mode: { type: String, default: 'deepseek' },
  apiKey: { type: String, default: '' },
  verifiedApiKey: { type: String, default: '' },
  config: { type: Object, required: true },
  connectionStatus: { type: String, default: 'unconfigured' },
  connectionError: { type: String, default: '' },
  testing: { type: Boolean, default: false },
})

const emit = defineEmits(['close', 'verify', 'save'])
const showKey = ref(false)
const draft = reactive({ mode: 'deepseek', apiKey: '' })

watch(
  () => props.open,
  (open) => {
    if (open) {
      draft.mode = props.mode
      draft.apiKey = props.apiKey
      showKey.value = false
    }
  },
)

const keyValid = computed(() => draft.apiKey.trim().length >= 16)
const canSave = computed(() => draft.mode === 'rules' || keyValid.value)
const connectionVerified = computed(
  () =>
    props.connectionStatus === 'ready' &&
    draft.apiKey.trim() === (props.verifiedApiKey || props.apiKey),
)

function verify() {
  if (!keyValid.value || props.testing) return
  emit('verify', draft.apiKey.trim())
}

function save() {
  if (!canSave.value || props.testing) return
  emit('save', { mode: draft.mode, apiKey: draft.apiKey.trim() })
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="open" class="fixed inset-0 z-[90] flex items-center justify-center bg-gray-950/45 p-4" @mousedown.self="emit('close')">
        <section class="panel max-h-[92vh] w-full max-w-lg overflow-y-auto p-6" aria-label="AI 接入设置">
          <div class="flex items-start justify-between gap-4">
            <div>
              <h2 class="text-lg font-semibold text-gray-950">AI 接入设置</h2>
              <p class="mt-1 text-sm text-gray-500">选择分析方式并配置连接</p>
            </div>
            <button class="cursor-pointer rounded-lg p-2 text-gray-500 hover:bg-gray-100" aria-label="关闭" @click="emit('close')">
              <X :size="19" />
            </button>
          </div>

          <div class="mt-6 grid grid-cols-2 rounded-lg border border-gray-300 bg-gray-50 p-1">
            <button
              class="flex h-10 cursor-pointer items-center justify-center gap-2 rounded-md text-sm font-medium transition-colors"
              :class="draft.mode === 'deepseek' ? 'bg-white text-blue-700 shadow-sm' : 'text-gray-600 hover:text-gray-900'"
              @click="draft.mode = 'deepseek'"
            >
              <Cloud :size="17" />
              DeepSeek API
            </button>
            <button
              class="flex h-10 cursor-pointer items-center justify-center gap-2 rounded-md text-sm font-medium transition-colors"
              :class="draft.mode === 'rules' ? 'bg-white text-blue-700 shadow-sm' : 'text-gray-600 hover:text-gray-900'"
              @click="draft.mode = 'rules'"
            >
              <ShieldCheck :size="17" />
              本地规则
            </button>
          </div>

          <div v-if="draft.mode === 'deepseek'" class="mt-6 space-y-5">
            <div class="grid grid-cols-[110px_1fr] gap-y-3 border-y border-gray-200 py-4 text-sm">
              <span class="text-gray-500">服务商</span>
              <span class="font-medium text-gray-900">DeepSeek</span>
              <span class="text-gray-500">Base URL</span>
              <span class="break-all font-mono text-xs text-gray-700">{{ config.base_url }}</span>
              <span class="text-gray-500">模型</span>
              <span class="font-mono text-xs font-semibold text-blue-700">{{ config.model }}</span>
            </div>

            <label class="block">
              <span class="mb-2 flex items-center gap-2 text-sm font-medium text-gray-700">
                <KeyRound :size="16" />
                API 密钥
              </span>
              <div class="relative">
                <input
                  v-model="draft.apiKey"
                  class="form-input pr-11 font-mono"
                  :type="showKey ? 'text' : 'password'"
                  autocomplete="off"
                  spellcheck="false"
                  placeholder="sk-..."
                />
                <button
                  class="absolute right-2 top-1/2 -translate-y-1/2 cursor-pointer rounded p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-700"
                  :aria-label="showKey ? '隐藏密钥' : '显示密钥'"
                  @click="showKey = !showKey"
                >
                  <EyeOff v-if="showKey" :size="17" />
                  <Eye v-else :size="17" />
                </button>
              </div>
              <p class="mt-2 text-xs leading-5 text-gray-500">密钥仅保留在当前页面内存中，刷新后清除。</p>
            </label>

            <div
              v-if="connectionVerified || connectionError"
              class="flex items-start gap-2 rounded-lg border px-3 py-2.5 text-sm"
              :class="connectionVerified ? 'border-emerald-200 bg-emerald-50 text-emerald-800' : 'border-red-200 bg-red-50 text-red-800'"
            >
              <CheckCircle2 v-if="connectionVerified" :size="17" class="mt-0.5 shrink-0" />
              <X v-else :size="17" class="mt-0.5 shrink-0" />
              <span>{{ connectionVerified ? `${config.model} 连接成功` : connectionError }}</span>
            </div>
          </div>

          <div v-else class="mt-6 rounded-lg border border-gray-200 bg-gray-50 px-4 py-4">
            <p class="text-sm font-medium text-gray-800">本地规则分析器</p>
            <p class="mt-1 text-xs leading-5 text-gray-500">无需网络和密钥，使用关键词、结构化提取与风险规则生成结果。</p>
          </div>

          <div class="mt-7 grid grid-cols-2 gap-3 border-t border-gray-200 pt-5 sm:flex sm:flex-wrap sm:justify-end">
            <button
              v-if="draft.mode === 'deepseek'"
              class="btn-secondary col-span-2 w-full sm:mr-auto sm:w-auto"
              :disabled="!keyValid || testing"
              @click="verify"
            >
              <LoaderCircle v-if="testing" :size="16" class="animate-spin" />
              <Cloud v-else :size="16" />
              {{ testing ? '连接中' : '测试连接' }}
            </button>
            <button class="btn-secondary w-full sm:w-auto" :disabled="testing" @click="emit('close')">取消</button>
            <button class="btn-primary w-full sm:w-auto" :disabled="!canSave || testing" @click="save">
              <Save :size="16" />
              保存设置
            </button>
          </div>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>
