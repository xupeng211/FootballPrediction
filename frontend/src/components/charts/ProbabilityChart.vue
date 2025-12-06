<template>
  <div class="probability-chart-container">
    <div class="chart-wrapper">
      <canvas ref="chartCanvas"></canvas>
    </div>
    <div class="legend">
      <div class="legend-item home">
        <span class="color-box" style="background-color: #10b981"></span>
        <span>主队胜: {{ (homeWinProb * 100).toFixed(1) }}%</span>
      </div>
      <div class="legend-item draw">
        <span class="color-box" style="background-color: #6b7280"></span>
        <span>平局: {{ (drawProb * 100).toFixed(1) }}%</span>
      </div>
      <div class="legend-item away">
        <span class="color-box" style="background-color: #ef4444"></span>
        <span>客队胜: {{ (awayWinProb * 100).toFixed(1) }}%</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, PropType } from 'vue'
import {
  Chart,
  PieController,
  Title,
  Tooltip,
  Legend,
  ArcElement
} from 'chart.js'

// Register Chart.js components
Chart.register(PieController, Title, Tooltip, Legend, ArcElement)

interface Props {
  homeWinProb: number
  drawProb: number
  awayWinProb: number
  confidence?: number
}

const props = defineProps<Props>()

const chartCanvas = ref<HTMLCanvasElement>()
let chartInstance: Chart | null = null

// 创建图表
const createChart = () => {
  if (!chartCanvas.value) return

  const ctx = chartCanvas.value.getContext('2d')
  if (!ctx) return

  // 销毁已存在的图表实例
  if (chartInstance) {
    chartInstance.destroy()
  }

  chartInstance = new Chart(ctx, {
    type: 'pie',
    data: {
      labels: ['主队胜', '平局', '客队胜'],
      datasets: [
        {
          data: [
            props.homeWinProb * 100,
            props.drawProb * 100,
            props.awayWinProb * 100
          ],
          backgroundColor: [
            '#10b981', // green-500
            '#6b7280', // gray-500
            '#ef4444'  // red-500
          ],
          borderColor: '#ffffff',
          borderWidth: 2
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: {
          display: false // 使用自定义图例
        },
        tooltip: {
          callbacks: {
            label: function (context) {
              return context.label + ': ' + context.parsed.toFixed(1) + '%'
            }
          }
        },
        title: {
          display: true,
          text: '胜率分布',
          font: {
            size: 16,
            weight: 'bold'
          }
        }
      }
    }
  })
}

// 监听概率数据变化
watch(
  () => [props.homeWinProb, props.drawProb, props.awayWinProb],
  () => {
    createChart()
  },
  { deep: true }
)

onMounted(() => {
  createChart()
})
</script>

<style scoped>
.probability-chart-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 1rem;
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
}

.chart-wrapper {
  width: 280px;
  height: 280px;
  position: relative;
}

.legend {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-top: 1rem;
  width: 100%;
  max-width: 200px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
}

.color-box {
  width: 12px;
  height: 12px;
  border-radius: 2px;
}

.legend-item.home {
  color: #10b981;
}

.legend-item.draw {
  color: #6b7280;
}

.legend-item.away {
  color: #ef4444;
}

/* 响应式设计 */
@media (max-width: 640px) {
  .chart-wrapper {
    width: 240px;
    height: 240px;
  }

  .legend {
    flex-direction: row;
    flex-wrap: wrap;
    justify-content: center;
    max-width: none;
  }
}
</style>