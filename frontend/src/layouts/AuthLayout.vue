<template>
  <div class="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
    <div class="sm:mx-auto sm:w-full sm:max-w-md">
      <!-- Logo/Header -->
      <div class="flex justify-center mb-8">
        <router-link to="/" class="flex items-center space-x-3">
          <div class="w-10 h-10 bg-primary-600 rounded-lg flex items-center justify-center">
            <svg class="h-6 w-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <span class="text-xl font-bold text-gray-900">Football Prediction</span>
        </router-link>
      </div>

      <!-- Main Content -->
      <div class="bg-white shadow sm:rounded-lg">
        <div v-if="title" class="px-6 py-4 border-b border-gray-200">
          <h2 class="text-lg font-medium text-gray-900">{{ title }}</h2>
          <p v-if="subtitle" class="mt-1 text-sm text-gray-600">{{ subtitle }}</p>
        </div>

        <div class="px-6 py-6">
          <slot />
        </div>

        <!-- Footer -->
        <div class="px-6 py-4 border-t border-gray-200">
          <div class="text-center text-sm text-gray-600">
            <p>&copy; 2024 Football Prediction. All rights reserved.</p>
            <div class="mt-2 space-x-4">
              <a href="#" class="text-gray-500 hover:text-gray-700">Terms</a>
              <a href="#" class="text-gray-500 hover:text-gray-700">Privacy</a>
              <a href="#" class="text-gray-500 hover:text-gray-700">Support</a>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  title?: string
  subtitle?: string
}

defineProps<Props>()
</script>