<template>
  <div class="match-details-page">
    <div class="container">
      <!-- 加载状态 -->
      <div v-if="loading" class="loading-state">
        <div class="loading-spinner"></div>
        <p>正在加载比赛详情...</p>
      </div>

      <!-- 错误状态 -->
      <div v-else-if="error" class="error-state">
        <h2>加载失败</h2>
        <p>{{ error }}</p>
        <button @click="loadData" class="retry-button">重试</button>
      </div>

      <!-- 比赛详情内容 -->
      <div v-else class="match-content">
        <!-- 比赛头部信息 -->
        <MatchHeader
          :match="match"
          :details="matchDetails"
          :prediction="prediction"
        />

        <!-- 标签页导航 -->
        <div class="tabs-container">
          <div class="tabs">
            <button
              v-for="tab in tabs"
              :key="tab.key"
              @click="activeTab = tab.key"
              :class="['tab-button', { active: activeTab === tab.key }]"
            >
              {{ tab.label }}
            </button>
          </div>
        </div>

        <!-- 标签页内容 -->
        <div class="tab-content">
          <!-- 概览标签页 -->
          <div v-if="activeTab === 'overview'" class="overview-content">
            <div class="overview-grid">
              <!-- 预测结果 -->
              <div class="prediction-section">
                <h3>预测分析</h3>
                <ProbabilityChart
                  :home-win-prob="prediction.home_win_prob"
                  :draw-prob="prediction.draw_prob"
                  :away-win-prob="prediction.away_win_prob"
                  :confidence="prediction.confidence"
                />
              </div>

              <!-- 模型信息 -->
              <div class="model-info">
                <h3>模型信息</h3>
                <div class="model-details">
                  <div class="model-item">
                    <span class="label">预测结果:</span>
                    <span class="value" :class="predictionResultClass">
                      {{ predictionResultText }}
                    </span>
                  </div>
                  <div class="model-item">
                    <span class="label">置信度:</span>
                    <span class="value">
                      {{ (prediction.confidence * 100).toFixed(1) }}%
                    </span>
                  </div>
                  <div class="model-item">
                    <span class="label">模式:</span>
                    <span class="value">{{ prediction.mode || 'mock' }}</span>
                  </div>
                  <div class="model-item">
                    <span class="label">使用特征:</span>
                    <span class="value">
                      {{ (prediction.features_used || []).length }} 项
                    </span>
                  </div>
                </div>
                <div v-if="prediction.features_used" class="features-list">
                  <div class="features-title">使用特征:</div>
                  <div class="feature-tags">
                    <span
                      v-for="feature in prediction.features_used"
                      :key="feature"
                      class="feature-tag"
                    >
                      {{ translateFeature(feature) }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 统计数据标签页 -->
          <div v-if="activeTab === 'stats'" class="stats-content">
            <div class="stats-grid">
              <!-- 雷达图 -->
              <div class="radar-section">
                <h3>攻防对比</h3>
                <StatsRadar :stats="matchStats" />
              </div>

              <!-- 详细统计 -->
              <div class="detailed-stats">
                <h3>技术统计</h3>
                <div class="stats-table">
                  <div class="stat-row" v-for="stat in detailedStats" :key="stat.key">
                    <span class="stat-label">{{ stat.label }}</span>
                    <div class="stat-values">
                      <span class="home-value">{{ stat.home }}</span>
                      <div class="stat-bar">
                        <div
                          class="home-bar"
                          :style="{ width: stat.homePercentage + '%' }"
                        ></div>
                        <div
                          class="away-bar"
                          :style="{ width: stat.awayPercentage + '%' }"
                        ></div>
                      </div>
                      <span class="away-value">{{ stat.away }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 赔率标签页 -->
          <div v-if="activeTab === 'odds'" class="odds-content">
            <div class="odds-analysis">
              <h3>赔率分析</h3>
              <div class="odds-cards">
                <div class="odds-card home">
                  <div class="card-header">主胜</div>
                  <div class="card-odds">{{ match.odds.home_win }}</div>
                  <div class="card-probability">
                    {{ ((1 / match.odds.home_win) * 100).toFixed(1) }}% 隐含概率
                  </div>
                </div>
                <div class="odds-card draw">
                  <div class="card-header">平局</div>
                  <div class="card-odds">{{ match.odds.draw }}</div>
                  <div class="card-probability">
                    {{ ((1 / match.odds.draw) * 100).toFixed(1) }}% 隐含概率
                  </div>
                </div>
                <div class="odds-card away">
                  <div class="card-header">客胜</div>
                  <div class="card-odds">{{ match.odds.away_win }}</div>
                  <div class="card-probability">
                    {{ ((1 / match.odds.away_win) * 100).toFixed(1) }}% 隐含概率
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import apiClient from '@/api/client'
import { Match, MatchDetails, MatchStats, Prediction } from '@/types/prediction'
import MatchHeader from '@/components/match/MatchHeader.vue'
import ProbabilityChart from '@/components/charts/ProbabilityChart.vue'
import StatsRadar from '@/components/charts/StatsRadar.vue'

const route = useRoute()
const router = useRouter()

// 响应式数据
const loading = ref(true)
const error = ref<string>('')
const match = ref<Match | null>(null)
const matchDetails = ref<MatchDetails | null>(null)
const matchStats = ref<MatchStats | null>(null)
const prediction = ref<Prediction | null>(null)
const activeTab = ref('overview')

// 标签页配置
const tabs = [
  { key: 'overview', label: '预测分析' },
  { key: 'stats', label: '技术统计' },
  { key: 'odds', label: '赔率分析' }
]

// 加载数据
const loadData = async () => {
  try {
    loading.value = true
    error.value = ''

    const matchId = parseInt(route.params.id as string)
    if (isNaN(matchId)) {
      throw new Error('无效的比赛ID')
    }

    // 并行加载所有数据
    const [matchData, detailsData, statsData, predictionsData] = await Promise.all([
      apiClient.getMatch(matchId),
      apiClient.getMatchDetails(matchId),
      apiClient.getMatchStats(matchId),
      apiClient.getPredictions(matchId)
    ])

    match.value = matchData
    matchDetails.value = detailsData
    matchStats.value = statsData

    // 找到匹配的预测数据
    prediction.value = predictionsData.predictions.find(
      p => p.match_id === matchId
    ) || predictionsData.predictions[0]

  } catch (err) {
    console.error('Failed to load match details:', err)
    error.value = err instanceof Error ? err.message : '加载失败，请重试'
  } finally {
    loading.value = false
  }
}

// 计算属性
const predictionResultText = computed(() => {
  if (!prediction.value) return '未知'

  switch (prediction.value.prediction) {
    case 'home_win':
      return '主队胜'
    case 'draw':
      return '平局'
    case 'away_win':
      return '客队胜'
    default:
      return prediction.value.prediction
  }
})

const predictionResultClass = computed(() => {
  if (!prediction.value) return ''

  return `prediction-${prediction.value.prediction}`
})

// 详细统计数据
const detailedStats = computed(() => {
  if (!matchStats.value) return []

  const stats = matchStats.value
  return [
    {
      key: 'xg',
      label: '期望进球 (xG)',
      home: stats.home_xg.toFixed(2),
      away: stats.away_xg.toFixed(2),
      homePercentage: (stats.home_xg / Math.max(stats.home_xg + stats.away_xg, 0.01)) * 100,
      awayPercentage: (stats.away_xg / Math.max(stats.home_xg + stats.away_xg, 0.01)) * 100
    },
    {
      key: 'possession',
      label: '控球率',
      home: stats.home_possession + '%',
      away: stats.away_possession + '%',
      homePercentage: stats.home_possession,
      awayPercentage: stats.away_possession
    },
    {
      key: 'shots',
      label: '射门次数',
      home: stats.home_shots,
      away: stats.away_shots,
      homePercentage: (stats.home_shots / Math.max(stats.home_shots + stats.away_shots, 1)) * 100,
      awayPercentage: (stats.away_shots / Math.max(stats.home_shots + stats.away_shots, 1)) * 100
    },
    {
      key: 'shots_on_target',
      label: '射正次数',
      home: stats.home_shots_on_target,
      away: stats.away_shots_on_target,
      homePercentage: (stats.home_shots_on_target / Math.max(stats.home_shots_on_target + stats.away_shots_on_target, 1)) * 100,
      awayPercentage: (stats.away_shots_on_target / Math.max(stats.home_shots_on_target + stats.away_shots_on_target, 1)) * 100
    }
  ]
})

// 翻译特征名称
const translateFeature = (feature: string): string => {
  const translations: Record<string, string> = {
    'home_xg': '主队期望进球',
    'away_xg': '客队期望进球',
    'home_possession': '主队控球率',
    'away_possession': '客队控球率',
    'shots_difference': '射门次数差',
    'home_form': '主队近期状态',
    'away_form': '客队近期状态',
    'head_to_head': '历史交锋',
    'home_advantage': '主场优势'
  }
  return translations[feature] || feature
}

// 页面加载时获取数据
onMounted(() => {
  loadData()
})
</script>

<style scoped>
.match-details-page {
  min-height: 100vh;
  background: #f9fafb;
  padding: 1rem 0;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
}

/* 加载和错误状态 */
.loading-state, .error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  text-align: center;
}

.loading-spinner {
  width: 48px;
  height: 48px;
  border: 4px solid #e5e7eb;
  border-top: 4px solid #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 1rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-state h2 {
  color: #dc2626;
  margin-bottom: 0.5rem;
}

.retry-button {
  margin-top: 1rem;
  padding: 0.75rem 1.5rem;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
}

.retry-button:hover {
  background: #2563eb;
}

/* 标签页 */
.tabs-container {
  background: white;
  border-radius: 8px;
  padding: 0;
  margin-bottom: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.tabs {
  display: flex;
  border-bottom: 1px solid #e5e7eb;
}

.tab-button {
  flex: 1;
  padding: 1rem;
  background: none;
  border: none;
  cursor: pointer;
  font-weight: 600;
  color: #6b7280;
  transition: all 0.2s;
}

.tab-button:hover {
  background: #f9fafb;
}

.tab-button.active {
  color: #3b82f6;
  border-bottom: 2px solid #3b82f6;
}

/* 标签页内容 */
.tab-content {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

/* 概览页面 */
.overview-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
}

.prediction-section, .model-info {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.model-details {
  background: #f9fafb;
  padding: 1rem;
  border-radius: 8px;
}

.model-item {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.model-item .label {
  color: #6b7280;
  font-weight: 500;
}

.model-item .value {
  color: #1f2937;
  font-weight: 600;
}

.prediction-home_win {
  color: #10b981;
}

.prediction-draw {
  color: #6b7280;
}

.prediction-away_win {
  color: #ef4444;
}

.features-list {
  margin-top: 1rem;
}

.features-title {
  font-weight: 600;
  color: #374151;
  margin-bottom: 0.5rem;
}

.feature-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.feature-tag {
  background: #e0f2fe;
  color: #0c4a6e;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 500;
}

/* 统计页面 */
.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
}

.radar-section, .detailed-stats {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.stats-table {
  background: #f9fafb;
  padding: 1rem;
  border-radius: 8px;
}

.stat-row {
  margin-bottom: 1rem;
}

.stat-row:last-child {
  margin-bottom: 0;
}

.stat-label {
  display: block;
  font-weight: 600;
  color: #374151;
  margin-bottom: 0.5rem;
}

.stat-values {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.home-value, .away-value {
  font-weight: 600;
  min-width: 3rem;
  text-align: center;
}

.home-value {
  color: #10b981;
}

.away-value {
  color: #ef4444;
}

.stat-bar {
  flex: 1;
  height: 8px;
  background: #e5e7eb;
  border-radius: 4px;
  overflow: hidden;
  position: relative;
}

.home-bar {
  height: 100%;
  background: #10b981;
  border-radius: 4px 0 0 4px;
  position: absolute;
  left: 0;
  transform-origin: left;
}

.away-bar {
  height: 100%;
  background: #ef4444;
  border-radius: 0 4px 4px 0;
  position: absolute;
  right: 0;
  transform-origin: right;
}

/* 赔率页面 */
.odds-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
}

.odds-card {
  background: #f9fafb;
  padding: 1.5rem;
  border-radius: 8px;
  text-align: center;
  border-top: 4px solid #6b7280;
}

.odds-card.home {
  border-top-color: #10b981;
}

.odds-card.draw {
  border-top-color: #6b7280;
}

.odds-card.away {
  border-top-color: #ef4444;
}

.card-header {
  font-weight: 600;
  color: #374151;
  margin-bottom: 1rem;
}

.card-odds {
  font-size: 2rem;
  font-weight: 900;
  margin-bottom: 0.5rem;
}

.card-probability {
  font-size: 0.875rem;
  color: #6b7280;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .overview-grid,
  .stats-grid {
    grid-template-columns: 1fr;
    gap: 1rem;
  }

  .tabs {
    flex-direction: column;
  }

  .odds-cards {
    grid-template-columns: 1fr;
  }

  .stat-values {
    align-items: stretch;
    gap: 0.5rem;
  }

  .stat-bar {
    order: -1;
  }
}

@media (max-width: 480px) {
  .container {
    padding: 0 0.5rem;
  }

  .tab-content {
    padding: 1rem;
  }

  .odds-card {
    padding: 1rem;
  }

  .card-odds {
    font-size: 1.5rem;
  }
}
</style>