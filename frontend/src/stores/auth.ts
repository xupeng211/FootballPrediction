import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User, LoginCredentials, RegisterData, AuthResponse, AuthState, LoginError } from '@/types/auth'
import type { UserProfile } from '@/types/prediction'
import apiClient from '@/api/client'

const STORAGE_KEY = 'auth_token'
const REFRESH_TOKEN_KEY = 'refresh_token'
const USER_KEY = 'user_data'

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref<User | null>(null)
  const token = ref<string | null>(null)
  const refreshToken = ref<string | null>(null)
  const loading = ref(false)
  const error = ref<LoginError | null>(null)

  // Getters
  const isAuthenticated = computed(() => !!token.value && !!user.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const userName = computed(() => user.value?.username || 'Guest')
  const userRole = computed(() => user.value?.role || 'user')

  // Actions
  const setAuth = (authResponse: AuthResponse) => {
    user.value = authResponse.user
    token.value = authResponse.token
    refreshToken.value = authResponse.refreshToken || null

    // Persist to localStorage
    localStorage.setItem(STORAGE_KEY, authResponse.token)
    if (authResponse.refreshToken) {
      localStorage.setItem(REFRESH_TOKEN_KEY, authResponse.refreshToken)
    }
    localStorage.setItem(USER_KEY, JSON.stringify(authResponse.user))

    // Clear any existing errors
    error.value = null
  }

  // Set user profile data (from getUserProfile API)
  const setUser = (profileData: UserProfile) => {
    // Merge with existing user data
    user.value = {
      ...user.value,
      ...profileData
    }

    // Update localStorage
    localStorage.setItem(USER_KEY, JSON.stringify(user.value))
  }

  // Update user bankroll (for betting functionality)
  const updateBankroll = (newBankroll: number) => {
    if (user.value) {
      user.value.bankroll = newBankroll
      localStorage.setItem(USER_KEY, JSON.stringify(user.value))
    }
  }

  const clearAuth = () => {
    user.value = null
    token.value = null
    refreshToken.value = null
    error.value = null

    // Clear localStorage
    localStorage.removeItem(STORAGE_KEY)
    localStorage.removeItem(REFRESH_TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  }

  const login = async (credentials: LoginCredentials): Promise<boolean> => {
    loading.value = true
    error.value = null

    try {
      const response = await apiClient.post<AuthResponse>('/auth/login', credentials)
      setAuth(response.data)
      return true
    } catch (err: any) {
      // Handle different types of errors
      if (err.response?.status === 401) {
        error.value = {
          message: 'Invalid email or password',
          field: 'password'
        }
      } else if (err.response?.status === 400) {
        error.value = {
          message: err.response.data?.message || 'Invalid request data',
          field: 'email'
        }
      } else if (err.response?.status === 429) {
        error.value = {
          message: 'Too many login attempts. Please try again later.',
          field: 'password'
        }
      } else {
        error.value = {
          message: 'Login failed. Please try again.',
          field: null
        }
      }
      console.error('Login error:', err)
      return false
    } finally {
      loading.value = false
    }
  }

  const register = async (data: RegisterData): Promise<boolean> => {
    loading.value = true
    error.value = null

    try {
      // Validate passwords match
      if (data.password !== data.confirmPassword) {
        error.value = {
          message: 'Passwords do not match',
          field: 'confirmPassword'
        }
        return false
      }

      // Validate email format
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
      if (!emailRegex.test(data.email)) {
        error.value = {
          message: 'Invalid email address',
          field: 'email'
        }
        return false
      }

      // Validate password strength
      if (data.password.length < 6) {
        error.value = {
          message: 'Password must be at least 6 characters long',
          field: 'password'
        }
        return false
      }

      const response = await apiClient.post<AuthResponse>('/auth/register', {
        username: data.username,
        email: data.email,
        password: data.password
      })

      setAuth(response.data)
      return true
    } catch (err: any) {
      if (err.response?.status === 409) {
        error.value = {
          message: 'Email or username already exists',
          field: 'email'
        }
      } else if (err.response?.status === 400) {
        const fieldError = err.response.data?.field
        error.value = {
          message: err.response.data?.message || 'Registration failed',
          field: fieldError || null
        }
      } else {
        error.value = {
          message: 'Registration failed. Please try again.',
          field: null
        }
      }
      console.error('Registration error:', err)
      return false
    } finally {
      loading.value = false
    }
  }

  const logout = async (): Promise<void> => {
    try {
      // Call logout endpoint if token exists
      if (token.value) {
        await apiClient.post('/auth/logout')
      }
    } catch (err) {
      // Continue with logout even if API call fails
      console.warn('Logout API call failed:', err)
    } finally {
      clearAuth()
    }
  }

  const checkAuth = (): boolean => {
    // Check if we have token and user data in localStorage
    const savedToken = localStorage.getItem(STORAGE_KEY)
    const savedUser = localStorage.getItem(USER_KEY)
    const savedRefreshToken = localStorage.getItem(REFRESH_TOKEN_KEY)

    if (savedToken && savedUser) {
      try {
        token.value = savedToken
        refreshToken.value = savedRefreshToken
        user.value = JSON.parse(savedUser)
        return true
      } catch (err) {
        console.error('Failed to parse saved user data:', err)
        clearAuth()
        return false
      }
    }
    return false
  }

  const refreshAuth = async (): Promise<boolean> => {
    if (!refreshToken.value) {
      return false
    }

    try {
      const response = await apiClient.post<AuthResponse>('/auth/refresh', {
        refreshToken: refreshToken.value
      })

      setAuth(response.data)
      return true
    } catch (err) {
      console.error('Token refresh failed:', err)
      clearAuth()
      return false
    }
  }

  const updateProfile = async (updates: Partial<User>): Promise<boolean> => {
    if (!isAuthenticated.value || !user.value) {
      error.value = {
        message: 'Not authenticated',
        field: null
      }
      return false
    }

    try {
      const response = await apiClient.put<User>('/auth/profile', updates)
      user.value = response.data

      // Update localStorage
      localStorage.setItem(USER_KEY, JSON.stringify(response.data))

      return true
    } catch (err: any) {
      error.value = {
        message: err.response?.data?.message || 'Failed to update profile',
        field: null
      }
      console.error('Profile update error:', err)
      return false
    }
  }

  const clearError = () => {
    error.value = null
  }

  return {
    // State
    user: readonly(user),
    token: readonly(token),
    loading: readonly(loading),
    error: readonly(error),

    // Getters
    isAuthenticated,
    isAdmin,
    userName,
    userRole,

    // Actions
    login,
    register,
    logout,
    checkAuth,
    refreshAuth,
    updateProfile,
    clearError,
    clearAuth,
    setUser,
    updateBankroll
  }
})