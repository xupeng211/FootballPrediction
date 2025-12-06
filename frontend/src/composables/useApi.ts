import { ref, computed } from 'vue'
import type { Prediction, Match, PredictionResponse } from '@/types/prediction'
import apiClient from '@/api/client'

export function usePredictions() {
  const predictions = ref<Prediction[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const fetchPredictions = async (matchId?: number) => {
    loading.value = true
    error.value = null

    try {
      const response = await apiClient.getPredictions(matchId)
      predictions.value = response.predictions
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch predictions'
      console.error('Error fetching predictions:', err)
    } finally {
      loading.value = false
    }
  }

  const successfulPredictions = computed(() =>
    predictions.value.filter(p => p.success)
  )

  const highConfidencePredictions = computed(() =>
    predictions.value.filter(p => p.confidence > 0.8)
  )

  return {
    predictions,
    loading,
    error,
    fetchPredictions,
    successfulPredictions,
    highConfidencePredictions,
  }
}

export function useMatches() {
  const matches = ref<Match[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const fetchRecentMatches = async (limit = 20) => {
    loading.value = true
    error.value = null

    try {
      const response = await apiClient.getRecentMatches(limit)
      matches.value = response
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch matches'
      console.error('Error fetching matches:', err)
    } finally {
      loading.value = false
    }
  }

  const upcomingMatches = computed(() =>
    matches.value.filter(m => m.status === 'scheduled')
  )

  const liveMatches = computed(() =>
    matches.value.filter(m => m.status === 'live')
  )

  return {
    matches,
    loading,
    error,
    fetchRecentMatches,
    upcomingMatches,
    liveMatches,
  }
}

export function useHealthCheck() {
  const isHealthy = ref(true)
  const lastCheck = ref<Date | null>(null)
  const checking = ref(false)

  const checkHealth = async () => {
    checking.value = true
    try {
      await apiClient.healthCheck()
      isHealthy.value = true
      lastCheck.value = new Date()
    } catch (err) {
      isHealthy.value = false
      console.error('Health check failed:', err)
    } finally {
      checking.value = false
    }
  }

  // Auto-check every 30 seconds
  const startAutoCheck = () => {
    checkHealth()
    setInterval(checkHealth, 30000)
  }

  return {
    isHealthy,
    lastCheck,
    checking,
    checkHealth,
    startAutoCheck,
  }
}