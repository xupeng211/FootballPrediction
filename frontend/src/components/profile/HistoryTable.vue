<template>
  <div class="history-table-container">
    <!-- 表格头部 -->
    <div class="table-header">
      <h3>历史记录</h3>
      <div class="table-actions">
        <button
          v-if="hasMore"
          @click="loadMore"
          :disabled="loading"
          class="load-more-button"
        >
          {{ loading ? '加载中...' : '加载更多' }}
        </button>
      </div>
    </div>

    <!-- 表格内容 -->
    <div class="table-responsive">
      <table class="history-table">
        <thead>
          <tr>
            <th>比赛时间</th>
            <th>对阵</th>
            <th>预测</th>
            <th>结果</th>
            <th>赔率</th>
            <th>下注金额</th>
            <th>盈亏</th>
            <th>状态</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="record in records"
            :key="record.id"
            @click="handleRowClick(record)"
            class="table-row"
            :class="getRowClass(record)"
          >
            <td class="date-cell">
              <div class="date-content">
                <div class="date">{{ formatDate(record.scheduled_at) }}</div>
                <div class="time">{{ formatTime(record.scheduled_at) }}</div>
              </div>
            </td>
            <td class="match-cell">
              <div class="match-content">
                <div class="teams">
                  <span class="home-team">{{ record.home_team }}</span>
                  <span class="vs">vs</span>
                  <span class="away-team">{{ record.away_team }}</span>
                </div>
                <div class="league">{{ record.league }}</div>
                <div v-if="record.final_score" class="final-score">
                  {{ record.final_score.home }} : {{ record.final_score.away }}
                </div>
              </div>
            </td>
            <td class="prediction-cell">
              <div class="prediction-badge" :class="getPredictionClass(record.prediction)">
                {{ getPredictionText(record.prediction) }}
              </div>
            </td>
            <td class="result-cell">
              <div v-if="record.actual_outcome" class="result-badge" :class="getResultClass(record)">
                {{ getResultText(record.actual_outcome) }}
              </div>
              <span v-else class="pending">待定</span>
            </td>
            <td class="odds-cell">
              <span class="odds-value">{{ record.odds.toFixed(2) }}</span>
            </td>
            <td class="stake-cell">
              <span class="stake-value">¥{{ record.stake.toFixed(2) }}</span>
            </td>
            <td class="profit-cell">
              <div class="profit-content" :class="getProfitClass(record)">
                <span class="profit-amount">{{ getProfitText(record) }}</span>
                <span class="profit-percentage">{{ getProfitPercentage(record) }}</span>
              </div>
            </td>
            <td class="status-cell">
              <div class="status-badge" :class="record.result">
                {{ getStatusText(record.result) }}
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 空状态 -->
    <div v-if="records.length === 0 && !loading" class="empty-state">
      <div class="empty-icon">📋</div>
      <p>暂无历史记录</p>
      <p class="empty-subtitle">开始下注后这里将显示您的投注历史</p>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading && records.length === 0" class="loading-state">
      <div class="loading-spinner"></div>
      <p>正在加载历史记录...</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, PropType } from 'vue'
import { useRouter } from 'vue-router'
import { HistoryRecord } from '@/types/prediction'

interface Props {
  records: HistoryRecord[]
  loading?: boolean
  hasMore?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  hasMore: false
})

const emit = defineEmits<{
  loadMore: []
}>()

const router = useRouter()

// 加载更多
const loadMore = () => {
  emit('loadMore')
}

// 点击行跳转到比赛详情
const handleRowClick = (record: HistoryRecord) => {
  router.push(`/matches/${record.match_id}`)
}

// 格式化日期
const formatDate = (dateString: string): string => {
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-CN', {
    month: '2-digit',
    day: '2-digit'
  })
}

const formatTime = (dateString: string): string => {
  const date = new Date(dateString)
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 获取预测文本
const getPredictionText = (prediction: string): string => {
  const translations: Record<string, string> = {
    'home_win': '主胜',
    'draw': '平局',
    'away_win': '客胜'
  }
  return translations[prediction] || prediction
}

// 获取预测样式类
const getPredictionClass = (prediction: string): string => {
  const classes: Record<string, string> = {
    'home_win': 'prediction-home',
    'draw': 'prediction-draw',
    'away_win': 'prediction-away'
  }
  return classes[prediction] || ''
}

// 获取结果文本
const getResultText = (outcome: string): string => {
  const translations: Record<string, string> = {
    'home_win': '主胜',
    'draw': '平局',
    'away_win': '客胜'
  }
  return translations[outcome] || outcome
}

// 获取结果样式类
const getResultClass = (record: HistoryRecord): string => {
  if (!record.actual_outcome) return ''
  if (record.result === 'win') return 'result-win'
  if (record.result === 'loss') return 'result-loss'
  return 'result-push'
}

// 获取行样式类
const getRowClass = (record: HistoryRecord): string => {
  const classes = ['clickable']
  if (record.result === 'win') classes.push('win-row')
  if (record.result === 'loss') classes.push('loss-row')
  if (record.result === 'push') classes.push('push-row')
  return classes.join(' ')
}

// 获取盈亏文本
const getProfitText = (record: HistoryRecord): string => {
  const prefix = record.profit >= 0 ? '+' : ''
  return `${prefix}¥${Math.abs(record.profit).toFixed(2)}`
}

// 获取盈亏百分比
const getProfitPercentage = (record: HistoryRecord): string => {
  const percentage = ((record.profit / record.stake) * 100).toFixed(1)
  const prefix = percentage >= '0' ? '+' : ''
  return `${prefix}${percentage}%`
}

// 获取盈亏样式类
const getProfitClass = (record: HistoryRecord): string => {
  if (record.profit > 0) return 'profit-win'
  if (record.profit < 0) return 'profit-loss'
  return 'profit-push'
}

// 获取状态文本
const getStatusText = (result?: string): string => {
  const statusMap: Record<string, string> = {
    'win': '获胜',
    'loss': '失败',
    'push': '走水'
  }
  return statusMap[result || ''] || '待定'
}
</script>

<style scoped>
.history-table-container {
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid #e5e7eb;
}

.table-header h3 {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 700;
  color: #1f2937;
}

.load-more-button {
  padding: 0.5rem 1rem;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  transition: background 0.2s;
}

.load-more-button:hover:not(:disabled) {
  background: #2563eb;
}

.load-more-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.table-responsive {
  overflow-x: auto;
}

.history-table {
  width: 100%;
  border-collapse: collapse;
}

.history-table th,
.history-table td {
  padding: 1rem;
  text-align: left;
  border-bottom: 1px solid #e5e7eb;
}

.history-table th {
  font-weight: 600;
  color: #374151;
  background: #f9fafb;
  font-size: 0.875rem;
  white-space: nowrap;
}

.table-row {
  transition: background-color 0.2s;
}

.table-row:hover {
  background: #f9fafb;
}

.table-row.clickable {
  cursor: pointer;
}

/* 单元格样式 */
.date-cell {
  min-width: 80px;
}

.date-content .date {
  font-weight: 600;
  color: #1f2937;
}

.date-content .time {
  font-size: 0.75rem;
  color: #6b7280;
}

.match-cell {
  min-width: 200px;
}

.match-content .teams {
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 0.25rem;
}

.vs {
  margin: 0 0.5rem;
  color: #6b7280;
  font-size: 0.875rem;
}

.match-content .league {
  font-size: 0.75rem;
  color: #6b7280;
  margin-bottom: 0.25rem;
}

.match-content .final-score {
  font-size: 0.75rem;
  font-weight: 600;
  color: #374151;
}

.prediction-cell,
.result-cell {
  min-width: 80px;
}

.prediction-badge,
.result-badge {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  text-align: center;
}

.prediction-home {
  background: #dcfce7;
  color: #166534;
}

.prediction-draw {
  background: #f3f4f6;
  color: #374151;
}

.prediction-away {
  background: #fee2e2;
  color: #dc2626;
}

.result-win {
  background: #dcfce7;
  color: #166534;
}

.result-loss {
  background: #fee2e2;
  color: #dc2626;
}

.result-push {
  background: #fef3c7;
  color: #d97706;
}

.odds-cell,
.stake-cell {
  min-width: 80px;
  text-align: right;
}

.odds-value,
.stake-value {
  font-weight: 600;
  color: #1f2937;
}

.profit-cell {
  min-width: 120px;
  text-align: right;
}

.profit-content {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.profit-amount {
  font-weight: 700;
  font-size: 0.875rem;
}

.profit-percentage {
  font-size: 0.75rem;
  opacity: 0.8;
}

.profit-win .profit-amount {
  color: #10b981;
}

.profit-loss .profit-amount {
  color: #ef4444;
}

.profit-push .profit-amount {
  color: #6b7280;
}

.status-cell {
  min-width: 80px;
}

.status-badge {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  text-align: center;
}

.status-badge.win {
  background: #dcfce7;
  color: #166534;
}

.status-badge.loss {
  background: #fee2e2;
  color: #dc2626;
}

.status-badge.push {
  background: #fef3c7;
  color: #d97706;
}

/* 行状态样式 */
.win-row {
  border-left: 4px solid #10b981;
}

.loss-row {
  border-left: 4px solid #ef4444;
}

.push-row {
  border-left: 4px solid #d97706;
}

/* 空状态和加载状态 */
.empty-state,
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  text-align: center;
  color: #6b7280;
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.empty-state p,
.loading-state p {
  margin: 0.5rem 0;
}

.empty-subtitle {
  font-size: 0.875rem;
  color: #9ca3af;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #e5e7eb;
  border-top: 3px solid #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 1rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* 响应式设计 */
@media (max-width: 768px) {
  .table-header {
    padding: 1rem;
    flex-direction: column;
    gap: 1rem;
    align-items: stretch;
  }

  .history-table th,
  .history-table td {
    padding: 0.75rem 0.5rem;
    font-size: 0.875rem;
  }

  .match-cell {
    min-width: 150px;
  }

  .teams {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .vs {
    display: none;
  }

  .profit-content {
    align-items: stretch;
    gap: 0.25rem;
  }

  .profit-amount,
  .profit-percentage {
    text-align: left;
  }
}

@media (max-width: 480px) {
  .history-table th,
  .history-table td {
    padding: 0.5rem 0.25rem;
    font-size: 0.75rem;
  }

  .date-cell,
  .prediction-cell,
  .result-cell,
  .odds-cell,
  .stake-cell,
  .profit-cell,
  .status-cell {
    min-width: 60px;
  }

  .match-cell {
    min-width: 120px;
  }

  .loading-spinner {
    width: 32px;
    height: 32px;
  }
}
</style>