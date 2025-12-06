export interface User {
  id: number
  username: string
  email: string
  role: 'user' | 'admin'
  created_at: string
  updated_at?: string
}

export interface LoginCredentials {
  email: string
  password: string
}

export interface RegisterData {
  username: string
  email: string
  password: string
  confirmPassword: string
}

export interface AuthResponse {
  user: User
  token: string
  refreshToken?: string
  expiresIn?: number
}

export interface LoginError {
  message: string
  field?: string
}

export interface AuthState {
  user: User | null
  token: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  loading: boolean
  error: LoginError | null
}