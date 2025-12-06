<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
    <div class="max-w-md w-full space-y-8">
      <div>
        <div class="flex justify-center">
          <div class="flex items-center">
            <div class="w-12 h-12 bg-primary-600 rounded-lg flex items-center justify-center">
              <svg class="h-8 w-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
              </svg>
            </div>
          </div>
        </div>
        <h2 class="mt-6 text-center text-3xl font-extrabold text-gray-900">
          Create your account
        </h2>
        <p class="mt-2 text-center text-sm text-gray-600">
          Or
          <router-link to="/login" class="font-medium text-primary-600 hover:text-primary-500">
            sign in to your existing account
          </router-link>
        </p>
      </div>

      <form class="mt-8 space-y-6" @submit.prevent="handleRegister">
        <div class="space-y-4">
          <!-- Username Input -->
          <FormInput
            ref="usernameInput"
            name="username"
            label="Username"
            type="text"
            placeholder="Choose a username"
            v-model="form.username"
            :error="authStore.error?.field === 'username' ? authStore.error?.message : null"
            required
            autocomplete="username"
            :validation="validateUsername"
          />

          <!-- Email Input -->
          <FormInput
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
            placeholder="Create a password"
            v-model="form.password"
            :error="authStore.error?.field === 'password' ? authStore.error?.message : null"
            required
            autocomplete="new-password"
            :validation="validatePassword"
            hint="Must be at least 6 characters"
          />

          <!-- Confirm Password Input -->
          <FormInput
            name="confirmPassword"
            label="Confirm password"
            type="password"
            placeholder="Confirm your password"
            v-model="form.confirmPassword"
            :error="confirmPasswordError"
            required
            autocomplete="new-password"
            :validation="validateConfirmPassword"
          />
        </div>

        <!-- Terms and Conditions -->
        <div class="flex items-center">
          <input
            id="agree-terms"
            name="agree-terms"
            type="checkbox"
            v-model="form.agreeTerms"
            class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
            :class="{ 'border-red-300': termsError }"
          />
          <label for="agree-terms" class="ml-2 block text-sm text-gray-900">
            I agree to the
            <a href="#" class="text-primary-600 hover:text-primary-500">Terms and Conditions</a>
            and
            <a href="#" class="text-primary-600 hover:text-primary-500">Privacy Policy</a>
          </label>
        </div>
        <p v-if="termsError" class="mt-1 text-sm text-red-600">
          You must agree to the terms and conditions
        </p>

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
                Registration failed
              </h3>
              <div class="mt-2 text-sm text-red-700">
                {{ authStore.error.message }}
              </div>
            </div>
          </div>
        </div>

        <div>
          <LoadingButton
            text="Create account"
            :loading="authStore.loading"
            loading-text="Creating account..."
            type="submit"
            variant="primary"
            size="md"
            full-width
          />
        </div>

        <!-- Password Requirements -->
        <div class="mt-6 p-4 bg-gray-50 border border-gray-200 rounded-lg">
          <p class="text-sm font-medium text-gray-900 mb-2">Password Requirements:</p>
          <ul class="text-xs text-gray-600 space-y-1">
            <li>• At least 6 characters</li>
            <li>• Contains uppercase and lowercase letters</li>
            <li>• Contains at least one number</li>
            <li>• Contains at least one special character</li>
          </ul>
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
import type { RegisterData } from '@/types/auth'

const router = useRouter()
const authStore = useAuthStore()

const usernameInput = ref()
const confirmPasswordError = ref('')
const termsError = ref(false)

const form = reactive<RegisterData & { agreeTerms: boolean }>({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
  agreeTerms: false
})

const validateUsername = (value: string): string | null => {
  if (!value) return 'Username is required'
  if (value.length < 3) return 'Username must be at least 3 characters'
  if (value.length > 20) return 'Username must be less than 20 characters'
  if (!/^[a-zA-Z0-9_]+$/.test(value)) return 'Username can only contain letters, numbers, and underscores'
  return null
}

const validateEmail = (value: string): string | null => {
  if (!value) return 'Email is required'
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  if (!emailRegex.test(value)) return 'Please enter a valid email address'
  return null
}

const validatePassword = (value: string): string | null => {
  if (!value) return 'Password is required'
  if (value.length < 6) return 'Password must be at least 6 characters'

  // Check for stronger password requirements
  const hasUpperCase = /[A-Z]/.test(value)
  const hasLowerCase = /[a-z]/.test(value)
  const hasNumbers = /\d/.test(value)
  const hasSpecialChar = /[!@#$%^&*(),.?":{}|<>]/.test(value)

  const strengthScore = [hasUpperCase, hasLowerCase, hasNumbers, hasSpecialChar].filter(Boolean).length

  if (strengthScore < 3) {
    return 'Password should include uppercase, lowercase, numbers, and special characters'
  }

  return null
}

const validateConfirmPassword = (value: string): string | null => {
  if (!value) return 'Please confirm your password'
  if (value !== form.password) return 'Passwords do not match'
  return null
}

const handleRegister = async () => {
  // Reset errors
  confirmPasswordError.value = ''
  termsError.value = false

  // Validate all fields
  const usernameError = validateUsername(form.username)
  const emailError = validateEmail(form.email)
  const passwordError = validatePassword(form.password)
  const confirmError = validateConfirmPassword(form.confirmPassword)

  if (usernameError || emailError || passwordError || confirmError) {
    if (confirmError) confirmPasswordError.value = confirmError
    return
  }

  // Check terms agreement
  if (!form.agreeTerms) {
    termsError.value = true
    return
  }

  const success = await authStore.register({
    username: form.username,
    email: form.email,
    password: form.password,
    confirmPassword: form.confirmPassword
  })

  if (success) {
    router.push('/dashboard')
  }
}

// Focus on username input on mount
onMounted(() => {
  usernameInput.value?.focus()
})
</script>