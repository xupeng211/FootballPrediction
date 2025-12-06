<template>
  <div class="space-y-6">
    <div class="bg-white shadow rounded-lg p-6">
      <h1 class="text-2xl font-bold text-gray-900 mb-6">Admin Dashboard</h1>
      <p class="text-gray-600">Admin control panel - Coming soon!</p>

      <div class="mt-8 grid grid-cols-1 md:grid-cols-3 gap-6">
        <!-- Users Stats -->
        <div class="bg-gray-50 rounded-lg p-6">
          <h3 class="text-lg font-medium text-gray-900 mb-2">Users</h3>
          <div class="text-2xl font-bold text-gray-900">1,234</div>
          <p class="text-sm text-gray-500">Total users</p>
        </div>

        <!-- Predictions Stats -->
        <div class="bg-gray-50 rounded-lg p-6">
          <h3 class="text-lg font-medium text-gray-900 mb-2">Predictions</h3>
          <div class="text-2xl font-bold text-gray-900">45,678</div>
          <p class="text-sm text-gray-500">Total predictions</p>
        </div>

        <!-- System Health -->
        <div class="bg-gray-50 rounded-lg p-6">
          <h3 class="text-lg font-medium text-gray-900 mb-2">System Health</h3>
          <div class="text-2xl font-bold text-green-600">98.5%</div>
          <p class="text-sm text-gray-500">System status</p>
        </div>
      </div>

      <div class="mt-8">
        <h3 class="text-lg font-medium text-gray-900 mb-4">Admin Actions</h3>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <button class="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50">
            Manage Users
          </button>
          <button class="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50">
            System Settings
          </button>
          <button class="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50">
            View Logs
          </button>
          <button class="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50">
            Database Backup
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
</script>