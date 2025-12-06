import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import type { RouteLocationNormalized } from 'vue-router'

// Layout Components
import MainLayout from '@/layouts/MainLayout.vue'
import AuthLayout from '@/layouts/AuthLayout.vue'

// View Components
import Dashboard from '@/views/Dashboard.vue'
import Login from '@/views/auth/Login.vue'
import Register from '@/views/auth/Register.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: Login,
      meta: {
        layout: 'auth',
        title: 'Sign In'
      }
    },
    {
      path: '/register',
      name: 'register',
      component: Register,
      meta: {
        layout: 'auth',
        title: 'Create Account'
      }
    },
    {
      path: '/',
      redirect: '/dashboard'
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: Dashboard,
      meta: {
        layout: 'main',
        requiresAuth: true,
        title: 'Dashboard'
      }
    },
    {
      path: '/predictions',
      name: 'predictions',
      component: () => import('@/views/Predictions.vue').catch(() => import('@/views/Dashboard.vue')),
      meta: {
        layout: 'main',
        requiresAuth: true,
        title: 'Predictions'
      }
    },
    {
      path: '/matches',
      name: 'matches',
      component: () => import('@/views/Matches.vue').catch(() => import('@/views/Dashboard.vue')),
      meta: {
        layout: 'main',
        requiresAuth: true,
        title: 'Matches'
      }
    },
    {
      path: '/matches/:id',
      name: 'match-details',
      component: () => import('@/views/match/MatchDetails.vue'),
      meta: {
        layout: 'main',
        requiresAuth: true,
        title: '比赛详情'
      }
    },
    {
      path: '/profile',
      name: 'profile',
      component: () => import('@/views/Profile.vue').catch(() => import('@/views/Dashboard.vue')),
      meta: {
        layout: 'main',
        requiresAuth: true,
        title: 'Profile'
      }
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('@/views/Settings.vue').catch(() => import('@/views/Dashboard.vue')),
      meta: {
        layout: 'main',
        requiresAuth: true,
        title: 'Settings'
      }
    },
    {
      path: '/admin',
      name: 'admin',
      component: () => import('@/views/admin/AdminDashboard.vue').catch(() => import('@/views/Dashboard.vue')),
      meta: {
        layout: 'main',
        requiresAuth: true,
        requiresAdmin: true,
        title: 'Admin Dashboard'
      }
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('@/views/NotFound.vue').catch(() => import('@/views/Dashboard.vue')),
      meta: {
        layout: 'main',
        title: 'Page Not Found'
      }
    }
  ]
})

// Navigation guard for authentication
router.beforeEach(async (
  to: RouteLocationNormalized,
  from: RouteLocationNormalized,
  next: any
) => {
  const authStore = useAuthStore()

  // Check authentication status on route change
  if (!authStore.isAuthenticated && !authStore.checkAuth()) {
    // No authentication data found
  }

  // Set document title
  if (to.meta.title) {
    document.title = `${to.meta.title} - Football Prediction`
  }

  // Handle authentication requirement
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    // Route requires authentication but user is not logged in
    next({
      name: 'login',
      query: { redirect: to.fullPath }
    })
    return
  }

  // Handle admin requirement
  if (to.meta.requiresAdmin && !authStore.isAdmin) {
    // Route requires admin privileges but user is not admin
    next('/dashboard')
    return
  }

  // Redirect authenticated users away from auth pages
  if ((to.name === 'login' || to.name === 'register') && authStore.isAuthenticated) {
    // User is already logged in, redirect to dashboard
    next('/dashboard')
    return
  }

  // Handle redirect from login
  if (to.name === 'login' && to.query.redirect && authStore.isAuthenticated) {
    const redirectPath = to.query.redirect as string
    next(redirectPath)
    return
  }

  next()
})

export default router