<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50">
    <div class="text-center">
      <div class="mb-4">
        <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.172 16.172a4 4 0 015.656 0M9 12h6m-6 4h.01M9 5h.01" />
        </svg>
      </div>
      <h1 class="text-2xl font-bold text-gray-900 mb-2">404 - Page Not Found</h1>
      <p class="text-gray-600 mb-6">The page you're looking for doesn't exist.</p>
      <router-link
        to="/dashboard"
        class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
      >
        Go back home
      </router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
// 404 page component
</script>