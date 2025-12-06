<template>
  <button
    :type="type"
    :disabled="disabled || loading"
    :class="buttonClasses"
    @click="handleClick"
  >
    <span v-if="loading" class="flex items-center">
      <svg class="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
      {{ loadingText }}
    </span>
    <span v-else>
      {{ text }}
    </span>
  </button>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  text: string
  loading?: boolean
  loadingText?: string
  disabled?: boolean
  type?: 'button' | 'submit' | 'reset'
  variant?: 'primary' | 'secondary' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  fullWidth?: boolean
}

interface Emits {
  (e: 'click', event: MouseEvent): void
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  loadingText: 'Loading...',
  disabled: false,
  type: 'button',
  variant: 'primary',
  size: 'md',
  fullWidth: false
})

const emit = defineEmits<Emits>()

const buttonClasses = computed(() => {
  const baseClasses = 'inline-flex justify-center items-center font-medium rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2'

  // Size classes
  const sizeClasses = {
    sm: 'px-3 py-1.5 text-xs',
    md: 'px-4 py-2 text-sm',
    lg: 'px-6 py-3 text-base'
  }

  // Variant classes
  const variantClasses = {
    primary: 'bg-primary-600 border border-transparent text-white hover:bg-primary-700 focus:ring-primary-500',
    secondary: 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 focus:ring-primary-500',
    danger: 'bg-red-600 border border-transparent text-white hover:bg-red-700 focus:ring-red-500'
  }

  // Disabled classes
  const disabledClasses = props.disabled || props.loading
    ? 'opacity-50 cursor-not-allowed'
    : ''

  // Full width classes
  const fullWidthClasses = props.fullWidth ? 'w-full' : ''

  return [
    baseClasses,
    sizeClasses[props.size],
    variantClasses[props.variant],
    disabledClasses,
    fullWidthClasses
  ].filter(Boolean).join(' ')
})

const handleClick = (event: MouseEvent) => {
  if (!props.disabled && !props.loading) {
    emit('click', event)
  }
}
</script>