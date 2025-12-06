<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
    <div class="max-w-md w-full space-y-8">
      <div>
        <div class="flex justify-center">
          <div class="flex items-center">
            <div class="w-12 h-12 bg-primary-600 rounded-lg flex items-center justify-center">
              <svg class="h-8 w-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
          </div>
        </div>
        <h2 class="mt-6 text-center text-3xl font-extrabold text-gray-900">
          Sign in to your account
        </h2>
        <p class="mt-2 text-center text-sm text-gray-600">
          Or
          <router-link to="/register" class="font-medium text-primary-600 hover:text-primary-500">
            create a new account
          </router-link>
        </p>
      </div>

      <form class="mt-8 space-y-6" @submit.prevent="handleLogin">
        <div class="space-y-4">
          <!-- Email Input -->
          <FormInput
            ref="emailInput"
            name="email"
            label="Email address"
            type="email"
            placeholder="Enter your email"
            v-model="form.email"
            :error="authStore.error?.field === 'email' ? authStore.error?.message : null"
            required
            autocomplete="email"
            :validation="validateEmail"
          />

          <!-- Password Input -->
          <FormInput
            name="password"
            label="Password"
            type="password"
            placeholder="Enter your password"
            v-model="form.password"
            :error="authStore.error?.field === 'password' ? authStore.error?.message : null"
            required
            autocomplete="current-password"
            :validation="validatePassword"
          />
        </div>

        <div class="flex items-center justify-between">
          <div class="flex items-center">
            <input
              id="remember-me"
              name="remember-me"
              type="checkbox"
              v-model="form.rememberMe"
              class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
            />
            <label for="remember-me" class="ml-2 block text-sm text-gray-900">
              Remember me
            </label>
          </div>

          <div class="text-sm">
            <a href="#" class="font-medium text-primary-600 hover:text-primary-500">
              Forgot your password?
            </a>
          </div>
        </div>

        <!-- Error Alert -->
        <div v-if="authStore.error && !authStore.error?.field"
             class="rounded-md bg-red-50 p-4">
          <div class="flex">
            <div class="flex-shrink-0">
              <svg class="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
              </svg>
            </div>
            <div class="ml-3">
              <h3 class="text-sm font-medium text-red-800">
                Login failed
              </h3>
              <div class="mt-2 text-sm text-red-700">
                {{ authStore.error.message }}
              </div>
            </div>
          </div>
        </div>

        <div>
          <LoadingButton
            text="Sign in"
            :loading="authStore.loading"
            loading-text="Signing in..."
            type="submit"
            variant="primary"
            size="md"
            full-width
          />
        </div>

        <!-- Demo Credentials -->
        <div class="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <p class="text-sm text-blue-800">
            <strong>Demo Credentials:</strong>
          </p>
          <div class="mt-2 space-y-1 text-xs text-blue-700">
            <p>Admin: admin@football.com / admin123</p>
            <p>User: user@football.com / user123</p>
          </div>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import FormInput from '@/components/auth/FormInput.vue'
import LoadingButton from '@/components/auth/LoadingButton.vue'
import type { LoginCredentials } from '@/types/auth'

const router = useRouter()
const authStore = useAuthStore()

const emailInput = ref()

const form = reactive<LoginCredentials & { rememberMe: boolean }>({
  email: '',
  password: '',
  rememberMe: false
})

const validateEmail = (value: string): string | null => {
  if (!value) return 'Email is required'
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  if (!emailRegex.test(value)) return 'Please enter a valid email address'
  return null
}

const validatePassword = (value: string): string | null => {
  if (!value) return 'Password is required'
  if (value.length < 6) return 'Password must be at least 6 characters'
  return null
}

const handleLogin = async () => {
  // Validate all fields
  if (validateEmail(form.email) || validatePassword(form.password)) {
    return
  }

  const success = await authStore.login({
    email: form.email,
    password: form.password
  })

  if (success) {
    router.push('/dashboard')
  }
}

// Auto-fill demo credentials on mount
onMounted(() => {
  // Focus on email input
  emailInput.value?.focus()

  // Auto-fill demo credentials for quick testing
  setTimeout(() => {
    form.email = 'admin@football.com'
    form.password = 'admin123'
  }, 100)
})
</script>