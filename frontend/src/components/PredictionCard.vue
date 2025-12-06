<template>
  <div class="prediction-card bg-white border border-gray-200 rounded-lg p-6 hover:shadow-lg transition-shadow">
    <!-- Match Header -->
    <div class="flex justify-between items-center mb-4">
      <div class="text-sm text-gray-500">
        {{ formatDateTime(match.scheduled_at) }}
      </div>
      <div class="px-2 py-1 text-xs font-medium rounded-full"
           :class="statusClass">
        {{ match.status.toUpperCase() }}
      </div>
    </div>

    <!-- Teams -->
    <div class="flex justify-between items-center mb-6">
      <div class="text-center flex-1">
        <div class="text-lg font-bold text-gray-900">{{ match.home_team }}</div>
        <div class="text-3xl font-bold text-primary-600" v-if="match.score">
          {{ match.score.home }}
        </div>
      </div>

      <div class="px-4 text-center">
        <div class="text-gray-400 text-sm">VS</div>
        <div class="text-xs text-gray-500 mt-1">{{ match.league }}</div>
      </div>

      <div class="text-center flex-1">
        <div class="text-lg font-bold text-gray-900">{{ match.away_team }}</div>
        <div class="text-3xl font-bold text-primary-600" v-if="match.score">
          {{ match.score.away }}
        </div>
      </div>
    </div>

    <!-- Prediction -->
    <div class="border-t border-gray-100 pt-4">
      <div class="flex justify-between items-center mb-3">
        <span class="text-sm font-medium text-gray-700">Prediction</span>
        <span class="text-sm text-gray-500">Confidence: {{ (prediction.confidence * 100).toFixed(1) }}%</span>
      </div>

      <div class="mb-4">
        <div class="text-lg font-bold text-primary-600 mb-2">
          {{ formatPrediction(prediction.prediction) }}
        </div>

        <!-- Probability Bars -->
        <div class="space-y-2">
          <div class="flex justify-between items-center">
            <span class="text-sm text-gray-600 w-20">{{ match.home_team }}</span>
            <div class="flex-1 mx-3">
              <div class="bg-gray-200 rounded-full h-2">
                <div class="bg-green-500 h-2 rounded-full"
                     :style="{ width: `${prediction.home_win_prob * 100}%` }">
                </div>
              </div>
            </div>
            <span class="text-sm text-gray-600 w-12 text-right">
              {{ (prediction.home_win_prob * 100).toFixed(1) }}%
            </span>
          </div>

          <div class="flex justify-between items-center">
            <span class="text-sm text-gray-600 w-20">Draw</span>
            <div class="flex-1 mx-3">
              <div class="bg-gray-200 rounded-full h-2">
                <div class="bg-yellow-500 h-2 rounded-full"
                     :style="{ width: `${prediction.draw_prob * 100}%` }">
                </div>
              </div>
            </div>
            <span class="text-sm text-gray-600 w-12 text-right">
              {{ (prediction.draw_prob * 100).toFixed(1) }}%
            </span>
          </div>

          <div class="flex justify-between items-center">
            <span class="text-sm text-gray-600 w-20">{{ match.away_team }}</span>
            <div class="flex-1 mx-3">
              <div class="bg-gray-200 rounded-full h-2">
                <div class="bg-red-500 h-2 rounded-full"
                     :style="{ width: `${prediction.away_win_prob * 100}%` }">
                </div>
              </div>
            </div>
            <span class="text-sm text-gray-600 w-12 text-right">
              {{ (prediction.away_win_prob * 100).toFixed(1) }}%
            </span>
          </div>
        </div>
      </div>

      <!-- Odds and Additional Info -->
      <div class="flex justify-between items-center text-sm text-gray-500">
        <div v-if="match.odds">
          <span>Odds: {{ match.odds.home_win }} / {{ match.odds.draw }} / {{ match.odds.away_win }}</span>
        </div>
        <div class="flex items-center space-x-2">
          <div class="w-2 h-2 rounded-full"
               :class="prediction.mode === 'real' ? 'bg-green-500' : 'bg-yellow-500'"
               :title="`Mode: ${prediction.mode}`">
          </div>
          <span>{{ prediction.mode === 'real' ? 'Real' : 'Mock' }}</span>
        </div>
      </div>
    </div>

    <!-- Mock Reason (if applicable) -->
    <div v-if="prediction.mock_reason"
         class="mt-3 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs text-yellow-800">
      <strong>Mock Mode:</strong> {{ prediction.mock_reason }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Prediction, Match } from '@/types/prediction'

interface Props {
  prediction: Prediction
  match: Match
}

const props = defineProps<Props>()

const statusClass = computed(() => {
  switch (props.match.status) {
    case 'live':
      return 'bg-red-100 text-red-800'
    case 'completed':
      return 'bg-green-100 text-green-800'
    case 'scheduled':
      return 'bg-blue-100 text-blue-800'
    default:
      return 'bg-gray-100 text-gray-800'
  }
})

const formatDateTime = (dateString: string) => {
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const formatPrediction = (prediction: string) => {
  return prediction.split('_').map(word =>
    word.charAt(0).toUpperCase() + word.slice(1)
  ).join(' ')
}
</script>