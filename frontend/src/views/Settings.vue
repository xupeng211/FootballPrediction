<template>
  <div class="space-y-6">
    <div class="bg-white shadow rounded-lg p-6">
      <h1 class="text-2xl font-bold text-gray-900 mb-6">Settings</h1>
      <p class="text-gray-600">Application settings page - Coming soon!</p>

      <div class="mt-8 space-y-8">
        <!-- Theme Settings -->
        <div>
          <h3 class="text-lg font-medium text-gray-900 mb-4">Appearance</h3>
          <div class="space-y-4">
            <div class="flex items-center justify-between">
              <div>
                <label class="text-sm font-medium text-gray-700">Dark Mode</label>
                <p class="text-sm text-gray-500">Toggle dark theme (coming soon)</p>
              </div>
              <button class="relative inline-flex h-6 w-11 items-center rounded-full bg-gray-200 transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2">
                <span class="sr-only">Use setting</span>
                <span class="translate-x-0 inline-block h-4 w-4 transform rounded-full bg-white transition-transform"></span>
              </button>
            </div>
          </div>
        </div>

        <!-- Notification Settings -->
        <div>
          <h3 class="text-lg font-medium text-gray-900 mb-4">Notifications</h3>
          <div class="space-y-4">
            <div class="flex items-center justify-between">
              <div>
                <label class="text-sm font-medium text-gray-700">Email Notifications</label>
                <p class="text-sm text-gray-500">Receive prediction results via email</p>
              </div>
              <input type="checkbox" class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded">
            </div>
            <div class="flex items-center justify-between">
              <div>
                <label class="text-sm font-medium text-gray-700">Push Notifications</label>
                <p class="text-sm text-gray-500">Browser push notifications</p>
              </div>
              <input type="checkbox" class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded">
            </div>
          </div>
        </div>

        <!-- Data Settings -->
        <div>
          <h3 class="text-lg font-medium text-gray-900 mb-4">Data & Privacy</h3>
          <div class="space-y-4">
            <button class="text-sm text-red-600 hover:text-red-800 underline">
              Clear Cache
            </button>
            <button class="text-sm text-red-600 hover:text-red-800 underline">
              Export My Data
            </button>
            <button class="text-sm text-red-600 hover:text-red-800 underline">
              Delete Account
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// Settings page component
</script>