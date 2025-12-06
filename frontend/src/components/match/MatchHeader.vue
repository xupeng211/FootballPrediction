<template>
  <div class="match-header">
    <div class="match-info">
      <div class="league">{{ match.league }}</div>
      <div class="datetime">{{ formattedDateTime }}</div>
    </div>

    <div class="teams-container">
      <div class="team home">
        <div class="team-name">{{ match.home_team }}</div>
        <div class="team-score" v-if="match.score">
          {{ match.score.home }}
        </div>
        <div class="team-probability" v-if="prediction">
          {{ (prediction.home_win_prob * 100).toFixed(0) }}%
        </div>
      </div>

      <div class="vs-section">
        <div class="status-badge" :class="statusClass">
          {{ statusText }}
        </div>
        <div class="vs-text">VS</div>
        <div class="confidence" v-if="prediction">
          置信度: {{ (prediction.confidence * 100).toFixed(0) }}%
        </div>
      </div>

      <div class="team away">
        <div class="team-name">{{ match.away_team }}</div>
        <div class="team-score" v-if="match.score">
          {{ match.score.away }}
        </div>
        <div class="team-probability" v-if="prediction">
          {{ (prediction.away_win_prob * 100).toFixed(0) }}%
        </div>
      </div>
    </div>

    <div class="venue-info" v-if="details">
      <div class="venue">
        <span class="icon">🏟️</span>
        {{ details.venue }}
      </div>
      <div class="weather" v-if="details.weather">
        <span class="icon">🌤️</span>
        {{ details.weather }}
      </div>
    </div>

    <div class="odds-section" v-if="match.odds">
      <div class="odds-title">赔率</div>
      <div class="odds-container">
        <div class="odds-item">
          <div class="odds-label">主胜</div>
          <div class="odds-value home">{{ match.odds.home_win }}</div>
        </div>
        <div class="odds-item">
          <div class="odds-label">平局</div>
          <div class="odds-value draw">{{ match.odds.draw }}</div>
        </div>
        <div class="odds-item">
          <div class="odds-label">客胜</div>
          <div class="odds-value away">{{ match.odds.away_win }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, PropType } from 'vue'
import { Match, MatchDetails, Prediction } from '@/types/prediction'

interface Props {
  match: Match
  details?: MatchDetails
  prediction?: Prediction
}

const props = defineProps<Props>()

// 格式化日期时间
const formattedDateTime = computed(() => {
  const date = new Date(props.match.scheduled_at)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'Asia/Shanghai'
  })
})

// 比赛状态文本
const statusText = computed(() => {
  switch (props.match.status) {
    case 'scheduled':
      return '未开始'
    case 'live':
      return '进行中'
    case 'completed':
      return '已结束'
    case 'postponed':
      return '推迟'
    case 'cancelled':
      return '取消'
    default:
      return props.match.status
  }
})

// 状态样式类
const statusClass = computed(() => {
  switch (props.match.status) {
    case 'scheduled':
      return 'scheduled'
    case 'live':
      return 'live'
    case 'completed':
      return 'completed'
    case 'postponed':
      return 'postponed'
    case 'cancelled':
      return 'cancelled'
    default:
      return 'unknown'
  }
})
</script>

<style scoped>
.match-header {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  margin-bottom: 1.5rem;
}

.match-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  font-size: 0.875rem;
  color: #6b7280;
}

.league {
  font-weight: 600;
  color: #374151;
}

.teams-container {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.5rem;
}

.team {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
}

.team-name {
  font-size: 1.25rem;
  font-weight: 700;
  color: #1f2937;
  text-align: center;
  margin-bottom: 0.5rem;
  line-height: 1.2;
}

.team-score {
  font-size: 2.5rem;
  font-weight: 900;
  color: #10b981;
  margin-bottom: 0.25rem;
}

.team-probability {
  font-size: 0.875rem;
  font-weight: 600;
  color: #6b7280;
  background: #f3f4f6;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
}

.vs-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0 1rem;
}

.status-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
}

.status-badge.scheduled {
  background: #dbeafe;
  color: #1e40af;
}

.status-badge.live {
  background: #dcfce7;
  color: #16a34a;
  animation: pulse 2s infinite;
}

.status-badge.completed {
  background: #f3f4f6;
  color: #374151;
}

.status-badge.postponed {
  background: #fef3c7;
  color: #d97706;
}

.status-badge.cancelled {
  background: #fee2e2;
  color: #dc2626;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.vs-text {
  font-size: 1.5rem;
  font-weight: 900;
  color: #9ca3af;
  margin-bottom: 0.5rem;
}

.confidence {
  font-size: 0.75rem;
  color: #6b7280;
  background: #f9fafb;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  border: 1px solid #e5e7eb;
}

.venue-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  padding: 0.75rem;
  background: #f9fafb;
  border-radius: 8px;
  font-size: 0.875rem;
  color: #6b7280;
}

.venue, .weather {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.icon {
  font-size: 1rem;
}

.odds-section {
  border-top: 1px solid #e5e7eb;
  padding-top: 1rem;
}

.odds-title {
  font-size: 0.875rem;
  font-weight: 600;
  color: #374151;
  margin-bottom: 0.5rem;
  text-align: center;
}

.odds-container {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}

.odds-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.odds-label {
  font-size: 0.75rem;
  color: #6b7280;
  margin-bottom: 0.25rem;
}

.odds-value {
  font-size: 1.125rem;
  font-weight: 700;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  min-width: 3rem;
  text-align: center;
}

.odds-value.home {
  background: #dcfce7;
  color: #16a34a;
}

.odds-value.draw {
  background: #f3f4f6;
  color: #374151;
}

.odds-value.away {
  background: #fee2e2;
  color: #dc2626;
}

/* 响应式设计 */
@media (max-width: 640px) {
  .match-header {
    padding: 1rem;
  }

  .team-name {
    font-size: 1rem;
  }

  .team-score {
    font-size: 2rem;
  }

  .vs-text {
    font-size: 1.25rem;
  }

  .teams-container {
    gap: 0.5rem;
  }

  .vs-section {
    padding: 0 0.5rem;
  }

  .odds-container {
    gap: 0.5rem;
  }

  .venue-info {
    flex-direction: column;
    gap: 0.5rem;
    align-items: flex-start;
  }
}
</style>