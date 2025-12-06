<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="bg-white rounded-lg shadow p-6">
      <div class="flex justify-between items-center">
        <div>
          <h1 class="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p class="text-gray-600 mt-1">Real-time football predictions and analysis</p>
        </div>
        <div class="flex items-center space-x-4">
          <!-- Health Status -->
          <div class="flex items-center space-x-2">
            <div class="w-2 h-2 rounded-full"
                 :class="isHealthy ? 'bg-green-500' : 'bg-red-500'">
            </div>
            <span class="text-sm text-gray-600">
              {{ isHealthy ? 'API Connected' : 'API Disconnected' }}
            </span>
          </div>

          <!-- Refresh Button -->
          <button @click="refreshData"
                  :disabled="loading"
                  class="btn-primary disabled:opacity-50">
            <svg v-if="loading" class="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            {{ loading ? 'Loading...' : 'Refresh' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Stats Overview -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
      <div class="bg-white rounded-lg shadow p-6">
        <div class="flex items-center">
          <div class="flex-shrink-0 bg-primary-100 rounded-full p-3">
            <svg class="h-6 w-6 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
          <div class="ml-4">
            <p class="text-sm font-medium text-gray-600">Total Predictions</p>
            <p class="text-2xl font-bold text-gray-900">{{ predictions.length }}</p>
          </div>
        </div>
      </div>

      <div class="bg-white rounded-lg shadow p-6">
        <div class="flex items-center">
          <div class="flex-shrink-0 bg-green-100 rounded-full p-3">
            <svg class="h-6 w-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div class="ml-4">
            <p class="text-sm font-medium text-gray-600">Success Rate</p>
            <p class="text-2xl font-bold text-gray-900">{{ successRate }}%</p>
          </div>
        </div>
      </div>

      <div class="bg-white rounded-lg shadow p-6">
        <div class="flex items-center">
          <div class="flex-shrink-0 bg-yellow-100 rounded-full p-3">
            <svg class="h-6 w-6 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <div class="ml-4">
            <p class="text-sm font-medium text-gray-600">High Confidence</p>
            <p class="text-2xl font-bold text-gray-900">{{ highConfidenceCount }}</p>
          </div>
        </div>
      </div>

      <div class="bg-white rounded-lg shadow p-6">
        <div class="flex items-center">
          <div class="flex-shrink-0 bg-blue-100 rounded-full p-3">
            <svg class="h-6 w-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div class="ml-4">
            <p class="text-sm font-medium text-gray-600">Live Matches</p>
            <p class="text-2xl font-bold text-gray-900">{{ liveMatches.length }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Error Message -->
    <ErrorMessage v-if="error"
                 :message="error"
                 title="Failed to load data"
                 @retry="refreshData" />

    <!-- Loading State -->
    <LoadingSpinner v-if="loading && predictions.length === 0"
                    message="Loading predictions..." />

    <!-- Predictions Grid -->
    <div v-if="!loading || predictions.length > 0">
      <div class="bg-white rounded-lg shadow p-6 mb-6">
        <div class="flex justify-between items-center mb-4">
          <h2 class="text-lg font-semibold text-gray-900">Recent Predictions</h2>
          <div class="flex items-center space-x-4">
            <label class="flex items-center space-x-2">
              <input type="checkbox" v-model="showHighConfidenceOnly"
                     class="rounded border-gray-300 text-primary-600 focus:ring-primary-500">
              <span class="text-sm text-gray-700">High confidence only</span>
            </label>
          </div>
        </div>

        <!-- Empty State -->
        <div v-if="filteredPredictions.length === 0"
             class="text-center py-8 text-gray-500">
          <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
          </svg>
          <p class="mt-2">No predictions available</p>
        </div>

        <!-- Predictions List -->
        <div v-else class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <PredictionCard v-for="prediction in filteredPredictions"
                         :key="prediction.match_id"
                         :prediction="prediction"
                         :match="getMatchForPrediction(prediction)" />
        </div>
      </div>
    </div>

    <!-- Recent Matches Section -->
    <div class="bg-white rounded-lg shadow p-6">
      <h2 class="text-lg font-semibold text-gray-900 mb-4">Recent Matches</h2>
      <LoadingSpinner v-if="matchesLoading" message="Loading matches..." />
      <div v-else-if="upcomingMatches.length > 0" class="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div v-for="match in upcomingMatches.slice(0, 6)"
             :key="match.id"
             class="border border-gray-200 rounded-lg p-4">
          <div class="flex justify-between items-center mb-2">
            <span class="text-sm font-medium text-gray-900">{{ match.league }}</span>
            <span class="text-xs text-gray-500">{{ formatDateTime(match.scheduled_at) }}</span>
          </div>
          <div class="text-center">
            <div class="text-sm font-medium text-gray-900">
              {{ match.home_team }} vs {{ match.away_team }}
            </div>
            <div v-if="match.odds" class="text-xs text-gray-500 mt-1">
              Odds: {{ match.odds.home_win }} / {{ match.odds.draw }} / {{ match.odds.away_win }}
            </div>
          </div>
        </div>
      </div>
      <div v-else class="text-center py-8 text-gray-500">
        No upcoming matches
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { usePredictions, useMatches, useHealthCheck } from '@/composables/useApi'
import PredictionCard from '@/components/PredictionCard.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import ErrorMessage from '@/components/ErrorMessage.vue'
import type { Prediction, Match } from '@/types/prediction'

// API Hooks
const { predictions, loading, error, fetchPredictions, successfulPredictions, highConfidencePredictions } = usePredictions()
const { matches, loading: matchesLoading, fetchRecentMatches, upcomingMatches, liveMatches } = useMatches()
const { isHealthy, checkHealth, startAutoCheck } = useHealthCheck()

// Local State
const showHighConfidenceOnly = ref(false)

// Computed
const successRate = computed(() => {
  if (predictions.value.length === 0) return 0
  return Math.round((successfulPredictions.value.length / predictions.value.length) * 100)
})

const highConfidenceCount = computed(() => highConfidencePredictions.value.length)

const filteredPredictions = computed(() => {
  let filtered = predictions.value

  if (showHighConfidenceOnly.value) {
    filtered = highConfidencePredictions.value
  }

  return filtered.slice(0, 10) // Show max 10 predictions
})

// Methods
const refreshData = async () => {
  await Promise.all([
    fetchPredictions(),
    fetchRecentMatches(),
    checkHealth()
  ])
}

const getMatchForPrediction = (prediction: Prediction): Match => {
  // Find matching match or create a mock match
  const match = upcomingMatches.value.find(m => m.id === prediction.match_id)
  if (match) return match

  // Return mock match for development
  return {
    id: prediction.match_id,
    home_team: 'Home Team',
    away_team: 'Away Team',
    scheduled_at: prediction.created_at || new Date().toISOString(),
    league: 'Mock League',
    status: 'scheduled',
    odds: {
      home_win: 2.0,
      draw: 3.0,
      away_win: 4.0,
    },
  }
}

const formatDateTime = (dateString: string) => {
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

// Lifecycle
onMounted(() => {
  startAutoCheck()
  refreshData()
})
</script>