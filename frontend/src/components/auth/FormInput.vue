<template>
  <div>
    <label v-if="label" :for="name" class="block text-sm font-medium text-gray-700 mb-1">
      {{ label }}
      <span v-if="required" class="text-red-500">*</span>
    </label>
    <div class="relative">
      <input
        :id="name"
        :name="name"
        :type="type"
        :value="modelValue"
        :placeholder="placeholder"
        :required="required"
        :disabled="disabled"
        :class="inputClasses"
        :autocomplete="autocomplete"
        @input="updateValue"
        @blur="validate"
        ref="inputRef"
      />
      <div v-if="type === 'password'" class="absolute inset-y-0 right-0 pr-3 flex items-center">
        <button
          type="button"
          @click="togglePasswordVisibility"
          class="text-gray-400 hover:text-gray-600 focus:outline-none focus:text-gray-600"
        >
          <svg v-if="showPassword" class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
          </svg>
          <svg v-else class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29-3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
          </svg>
        </button>
      </div>
    </div>
    <p v-if="error" class="mt-1 text-sm text-red-600">{{ error }}</p>
    <p v-if="hint" class="mt-1 text-sm text-gray-500">{{ hint }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'

interface Props {
  name: string
  label?: string
  type?: string
  placeholder?: string
  modelValue: string | number
  required?: boolean
  disabled?: boolean
  error?: string
  hint?: string
  autocomplete?: string
  validateOnBlur?: boolean
  validation?: (value: string) => string | null
}

interface Emits {
  (e: 'update:modelValue', value: string): void
  (e: 'blur', value: string): void
}

const props = withDefaults(defineProps<Props>(), {
  type: 'text',
  required: false,
  disabled: false,
  validateOnBlur: true,
  autocomplete: 'off'
})

const emit = defineEmits<Emits>()

const inputRef = ref<HTMLInputElement>()
const showPassword = ref(false)
const internalError = ref('')

const inputClasses = computed(() => {
  const baseClasses = 'block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm'

  if (props.error || internalError.value) {
    return `${baseClasses} border-red-300 text-red-900 placeholder-red-300 focus:ring-red-500 focus:border-red-500`
  }

  if (props.disabled) {
    return `${baseClasses} bg-gray-50 text-gray-500 cursor-not-allowed`
  }

  return baseClasses
})

const updateValue = (event: Event) => {
  const target = event.target as HTMLInputElement
  emit('update:modelValue', target.value)
  internalError.value = ''
}

const validate = () => {
  if (!props.validateOnBlur) return

  const value = (inputRef.value?.value || '').toString().trim()

  if (props.validation) {
    internalError.value = props.validation(value)
  }

  emit('blur', value)
}

const togglePasswordVisibility = () => {
  showPassword.value = !showPassword.value
}

// Expose methods for parent component
defineExpose({
  focus: () => {
    nextTick(() => {
      inputRef.value?.focus()
    })
  },
  blur: () => {
    inputRef.value?.blur()
  }
})
</script>