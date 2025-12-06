<template>
  <div class="stats-summary-container">
    <div class="stats-grid">
      <!-- 银行余额 -->
      <div class="stat-card bankroll-card">
        <div class="stat-icon">💰</div>
        <div class="stat-content">
          <div class="stat-label">银行余额</div>
          <div class="stat-value">¥{{ formatCurrency(profile.bankroll) }}</div>
          <div class="stat-trend" :class="getTrendClass(profile.total_winnings)">
            {{ formatTrend(profile.total_winnings) }}
          </div>
        </div>
      </div>

      <!-- 总盈亏 -->
      <div class="stat-card winnings-card">
        <div class="stat-icon">📈</div>
        <div class="stat-content">
          <div class="stat-label">总盈亏</div>
          <div class="stat-value" :class="getProfitClass(profile.total_winnings)">
            {{ formatProfit(profile.total_winnings) }}
          </div>
          <div class="stat-subtitle">
            累计下注: ¥{{ formatCurrency(profile.total_bets) }}
          </div>
        </div>
      </div>

      <!-- 胜率 -->
      <div class="stat-card winrate-card">
        <div class="stat-icon">🎯</div>
        <div class="stat-content">
          <div class="stat-label">胜率</div>
          <div class="stat-value">{{ profile.win_rate.toFixed(1) }}%</div>
          <div class="stat-subtitle">
            {{ profile.total_bets }} 笔投注
          </div>
        </div>
      </div>

      <!-- ROI -->
      <div class="stat-card roi-card">
        <div class="stat-icon">📊</div>
        <div class="stat-content">
          <div class="stat-label">投资回报率</div>
          <div class="stat-value" :class="getProfitClass(profile.roi)">
            {{ formatPercentage(profile.roi) }}
          </div>
          <div class="stat-subtitle">
            投资收益率
          </div>
        </div>
      </div>
    </div>

    <!-- 详细统计信息 -->
    <div class="detailed-stats" v-if="showDetailed">
      <h4>详细统计</h4>
      <div class="detailed-grid">
        <div class="detail-item">
          <div class="detail-label">注册时间</div>
          <div class="detail-value">{{ formatDate(profile.created_at) }}</div>
        </div>
        <div class="detail-item">
          <div class="detail-label">用户类型</div>
          <div class="detail-value">
            <span class="role-badge" :class="profile.role">
              {{ getRoleText(profile.role) }}
            </span>
          </div>
        </div>
        <div class="detail-item">
          <div class="detail-label">最后登录</div>
          <div class="detail-value">
            {{ profile.last_login ? formatDateTime(profile.last_login) : '未登录' }}
          </div>
        </div>
        <div class="detail-item">
          <div class="detail-label">时区</div>
          <div class="detail-value">{{ profile.timezone || 'UTC' }}</div>
        </div>
      </div>
    </div>

    <!-- 历史统计信息 -->
    <div class="history-stats" v-if="historyStats">
      <h4>历史统计</h4>
      <div class="history-grid">
        <div class="history-item">
          <div class="history-count">{{ historyStats.win_count }}</div>
          <div class="history-label">获胜</div>
        </div>
        <div class="history-item">
          <div class="history-count">{{ historyStats.loss_count }}</div>
          <div class="history-label">失败</div>
        </div>
        <div class="history-item">
          <div class="history-count">{{ historyStats.push_count }}</div>
          <div class="history-label">走水</div>
        </div>
        <div class="history-item">
          <div class="history-count total">{{ historyStats.total_bets }}</div>
          <div class="history-label">总计</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, PropType } from 'vue'
import { UserProfile } from '@/types/prediction'

interface Props {
  profile: UserProfile
  historyStats?: {
    win_count: number
    loss_count: number
    push_count: number
    total_bets: number
  }
  showDetailed?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  showDetailed: false
})

// 格式化货币
const formatCurrency = (amount: number): string => {
  return amount.toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })
}

// 格式化盈亏
const formatProfit = (amount: number): string => {
  const prefix = amount >= 0 ? '+' : ''
  return `${prefix}¥${formatCurrency(Math.abs(amount))}`
}

// 格式化百分比
const formatPercentage = (value: number): string => {
  const prefix = value >= 0 ? '+' : ''
  return `${prefix}${value.toFixed(1)}%`
}

// 格式化趋势
const formatTrend = (amount: number): string => {
  if (amount > 0) return `+¥${formatCurrency(amount)}`
  if (amount < 0) return `-¥${formatCurrency(Math.abs(amount))}`
  return '持平'
}

// 获取盈亏样式类
const getProfitClass = (value: number): string => {
  if (value > 0) return 'profit-positive'
  if (value < 0) return 'profit-negative'
  return 'profit-neutral'
}

// 获取趋势样式类
const getTrendClass = (value: number): string => {
  if (value > 0) return 'trend-up'
  if (value < 0) return 'trend-down'
  return 'trend-neutral'
}

// 格式化日期
const formatDate = (dateString: string): string => {
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
}

// 格式化日期时间
const formatDateTime = (dateString: string): string => {
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 获取角色文本
const getRoleText = (role: string): string => {
  const roleMap: Record<string, string> = {
    'admin': '管理员',
    'user': '普通用户'
  }
  return roleMap[role] || role
}
</script>

<style scoped>
.stats-summary-container {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
}

.stat-card {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  border: 1px solid #e5e7eb;
  transition: transform 0.2s, box-shadow 0.2s;
  display: flex;
  align-items: center;
  gap: 1rem;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.stat-icon {
  font-size: 2.5rem;
  flex-shrink: 0;
}

.stat-content {
  flex: 1;
  min-width: 0;
}

.stat-label {
  font-size: 0.875rem;
  color: #6b7280;
  margin-bottom: 0.25rem;
  font-weight: 500;
}

.stat-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: #1f2937;
  margin-bottom: 0.25rem;
  line-height: 1;
}

.stat-trend {
  font-size: 0.75rem;
  font-weight: 600;
}

.stat-subtitle {
  font-size: 0.75rem;
  color: #9ca3af;
}

/* 特殊卡片样式 */
.bankroll-card .stat-icon {
  color: #3b82f6;
}

.winnings-card .stat-icon {
  color: #10b981;
}

.winrate-card .stat-icon {
  color: #8b5cf6;
}

.roi-card .stat-icon {
  color: #f59e0b;
}

/* 盈亏样式 */
.profit-positive {
  color: #10b981;
}

.profit-negative {
  color: #ef4444;
}

.profit-neutral {
  color: #6b7280;
}

/* 趋势样式 */
.trend-up {
  color: #10b981;
}

.trend-down {
  color: #ef4444;
}

.trend-neutral {
  color: #6b7280;
}

/* 详细统计 */
.detailed-stats {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  border: 1px solid #e5e7eb;
}

.detailed-stats h4 {
  margin: 0 0 1rem 0;
  font-size: 1.125rem;
  font-weight: 700;
  color: #1f2937;
}

.detailed-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem;
  background: #f9fafb;
  border-radius: 6px;
}

.detail-label {
  font-size: 0.875rem;
  color: #6b7280;
  font-weight: 500;
}

.detail-value {
  font-size: 0.875rem;
  font-weight: 600;
  color: #1f2937;
}

.role-badge {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
}

.role-badge.admin {
  background: #fef3c7;
  color: #d97706;
}

.role-badge.user {
  background: #dbeafe;
  color: #1e40af;
}

/* 历史统计 */
.history-stats {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  border: 1px solid #e5e7eb;
}

.history-stats h4 {
  margin: 0 0 1rem 0;
  font-size: 1.125rem;
  font-weight: 700;
  color: #1f2937;
}

.history-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 1rem;
}

.history-item {
  text-align: center;
  padding: 1rem;
  background: #f9fafb;
  border-radius: 8px;
}

.history-count {
  font-size: 1.5rem;
  font-weight: 700;
  color: #1f2937;
  margin-bottom: 0.25rem;
}

.history-count.total {
  color: #3b82f6;
}

.history-label {
  font-size: 0.875rem;
  color: #6b7280;
  font-weight: 500;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }

  .stat-card {
    padding: 1rem;
  }

  .stat-icon {
    font-size: 2rem;
  }

  .stat-value {
    font-size: 1.25rem;
  }

  .detailed-grid,
  .history-grid {
    grid-template-columns: 1fr;
  }

  .detail-item {
    flex-direction: column;
    align-items: stretch;
    gap: 0.5rem;
  }
}

@media (max-width: 480px) {
  .stat-card {
    padding: 0.75rem;
  }

  .stat-icon {
    font-size: 1.75rem;
  }

  .stat-value {
    font-size: 1.125rem;
  }

  .detailed-stats,
  .history-stats {
    padding: 1rem;
  }

  .history-item {
    padding: 0.75rem;
  }

  .history-count {
    font-size: 1.25rem;
  }
}
</style>