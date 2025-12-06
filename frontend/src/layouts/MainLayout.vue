<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Navigation Header -->
    <nav class="bg-white shadow-sm border-b border-gray-200">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between h-16">
          <!-- Logo and Title -->
          <div class="flex items-center">
            <router-link to="/dashboard" class="flex items-center space-x-3">
              <div class="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
                <svg class="h-5 w-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <span class="text-xl font-bold text-gray-900">Football Prediction</span>
            </router-link>
          </div>

          <!-- Navigation Links -->
          <div class="hidden md:flex md:items-center md:space-x-8">
            <router-link
              to="/dashboard"
              class="text-gray-500 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium transition-colors"
              active-class="text-primary-600 bg-primary-50"
            >
              Dashboard
            </router-link>
            <router-link
              to="/predictions"
              class="text-gray-500 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium transition-colors"
              active-class="text-primary-600 bg-primary-50"
            >
              Predictions
            </router-link>
            <router-link
              to="/matches"
              class="text-gray-500 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium transition-colors"
              active-class="text-primary-600 bg-primary-50"
            >
              Matches
            </router-link>
            <router-link
              v-if="authStore.isAdmin"
              to="/admin"
              class="text-gray-500 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium transition-colors"
              active-class="text-primary-600 bg-primary-50"
            >
              Admin
            </router-link>
          </div>

          <!-- User Menu -->
          <div class="flex items-center space-x-4">
            <!-- Health Status -->
            <div class="flex items-center space-x-2">
              <div class="w-2 h-2 rounded-full"
                   :class="isHealthy ? 'bg-green-500' : 'bg-red-500'">
              </div>
              <span class="text-sm text-gray-600 hidden sm:block">
                {{ isHealthy ? 'Online' : 'Offline' }}
              </span>
            </div>

            <!-- User Dropdown -->
            <div class="relative" ref="userMenuRef">
              <button
                @click="toggleUserMenu"
                class="flex items-center text-sm rounded-full focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
              >
                <div class="h-8 w-8 rounded-full bg-primary-600 flex items-center justify-center">
                  <span class="text-white font-medium text-sm">
                    {{ userInitials }}
                  </span>
                </div>
              </button>

              <!-- Dropdown Menu -->
              <div
                v-if="showUserMenu"
                class="origin-top-right absolute right-0 mt-2 w-48 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 focus:outline-none z-50"
              >
                <div class="py-1">
                  <div class="px-4 py-2 border-b border-gray-100">
                    <p class="text-sm font-medium text-gray-900">{{ authStore.userName }}</p>
                    <p class="text-xs text-gray-500">{{ authStore.user?.email }}</p>
                  </div>
                  <router-link
                    to="/profile"
                    class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    @click="closeUserMenu"
                  >
                    Profile
                  </router-link>
                  <router-link
                    to="/settings"
                    class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    @click="closeUserMenu"
                  >
                    Settings
                  </router-link>
                  <div class="border-t border-gray-100"></div>
                  <button
                    @click="handleLogout"
                    class="block w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-gray-100"
                  >
                    Sign out
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Mobile menu button -->
          <div class="md:hidden flex items-center">
            <button
              @click="toggleMobileMenu"
              class="inline-flex items-center justify-center p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-primary-500"
            >
              <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      <!-- Mobile menu -->
      <div v-if="showMobileMenu" class="md:hidden">
        <div class="px-2 pt-2 pb-3 space-y-1">
          <router-link
            to="/dashboard"
            class="block px-3 py-2 rounded-md text-base font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-50"
            @click="toggleMobileMenu"
          >
            Dashboard
          </router-link>
          <router-link
            to="/predictions"
            class="block px-3 py-2 rounded-md text-base font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-50"
            @click="toggleMobileMenu"
          >
            Predictions
          </router-link>
          <router-link
            to="/matches"
            class="block px-3 py-2 rounded-md text-base font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-50"
            @click="toggleMobileMenu"
          >
            Matches
          </router-link>
          <router-link
            v-if="authStore.isAdmin"
            to="/admin"
            class="block px-3 py-2 rounded-md text-base font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-50"
            @click="toggleMobileMenu"
          >
            Admin
          </router-link>
        </div>
        <div class="pt-4 pb-3 border-t border-gray-200">
          <div class="px-4 py-2">
            <div class="text-base font-medium text-gray-800">{{ authStore.userName }}</div>
            <div class="text-sm text-gray-500">{{ authStore.user?.email }}</div>
          </div>
          <div class="mt-3 px-2">
            <button
              @click="handleLogout"
              class="block w-full text-left px-3 py-2 rounded-md text-base font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-50"
            >
              Sign out
            </button>
          </div>
        </div>
      </div>
    </nav>

    <!-- Main Content -->
    <main>
      <slot />
    </main>

    <!-- Global Loading Overlay -->
    <div v-if="authStore.loading" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-lg p-6 flex flex-col items-center">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mb-4"></div>
        <p class="text-gray-700">Loading...</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useHealthCheck } from '@/composables/useApi'

const router = useRouter()
const authStore = useAuthStore()
const { isHealthy } = useHealthCheck()

const showUserMenu = ref(false)
const showMobileMenu = ref(false)
const userMenuRef = ref<HTMLElement>()

const userInitials = computed(() => {
  if (!authStore.user?.username) return 'U'
  return authStore.user.username.slice(0, 2).toUpperCase()
})

const toggleUserMenu = () => {
  showUserMenu.value = !showUserMenu.value
}

const closeUserMenu = () => {
  showUserMenu.value = false
}

const toggleMobileMenu = () => {
  showMobileMenu.value = !showMobileMenu.value
}

const handleLogout = async () => {
  showUserMenu.value = false
  showMobileMenu.value = false
  await authStore.logout()
  router.push('/login')
}

// Close dropdown when clicking outside
const handleClickOutside = (event: MouseEvent) => {
  if (userMenuRef.value && !userMenuRef.value.contains(event.target as Node)) {
    showUserMenu.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>