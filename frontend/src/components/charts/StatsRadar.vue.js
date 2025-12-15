import { ref, onMounted, watch, PropType } from 'vue';
import { Chart, RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend, Title } from 'chart.js';
import { MatchStats } from '@/types/prediction';
// Register Chart.js components
Chart.register(RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend, Title);
const props = defineProps();
const chartCanvas = ref();
let chartInstance = null;
// 将数据转换为雷达图格式
const transformStatsForRadar = (stats) => {
    // 归一化数据到 0-100 范围
    const normalizeValue = (value, max = 100) => (value / max) * 100;
    return {
        labels: ['xG', '控球率', '射门', '射正', '角球'],
        homeTeam: [
            normalizeValue(stats.home_xg, 3), // xG 最高约3
            normalizeValue(stats.home_possession), // 控球率
            normalizeValue(stats.home_shots, 20), // 射门次数 最高约20
            normalizeValue(stats.home_shots_on_target, 8), // 射正次数 最高约8
            normalizeValue(stats.home_corners, 12) // 角球次数 最高约12
        ],
        awayTeam: [
            normalizeValue(stats.away_xg, 3),
            normalizeValue(stats.away_possession),
            normalizeValue(stats.away_shots, 20),
            normalizeValue(stats.away_shots_on_target, 8),
            normalizeValue(stats.away_corners, 12)
        ]
    };
};
// 创建雷达图
const createRadarChart = () => {
    if (!chartCanvas.value)
        return;
    const ctx = chartCanvas.value.getContext('2d');
    if (!ctx)
        return;
    const radarData = transformStatsForRadar(props.stats);
    // 销毁已存在的图表实例
    if (chartInstance) {
        chartInstance.destroy();
    }
    chartInstance = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: radarData.labels,
            datasets: [
                {
                    label: '主队',
                    data: radarData.homeTeam,
                    borderColor: '#10b981', // green-500
                    backgroundColor: 'rgba(16, 185, 129, 0.2)',
                    borderWidth: 2,
                    pointBackgroundColor: '#10b981',
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: '#10b981'
                },
                {
                    label: '客队',
                    data: radarData.awayTeam,
                    borderColor: '#ef4444', // red-500
                    backgroundColor: 'rgba(239, 68, 68, 0.2)',
                    borderWidth: 2,
                    pointBackgroundColor: '#ef4444',
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: '#ef4444'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            scales: {
                r: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        stepSize: 20,
                        callback: function (value) {
                            return value + '%';
                        }
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.1)'
                    },
                    pointLabels: {
                        font: {
                            size: 12,
                            weight: 'bold'
                        },
                        color: '#374151'
                    }
                }
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        padding: 20,
                        font: {
                            size: 14
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            const value = context.parsed.r;
                            return `${context.dataset.label}: ${value.toFixed(1)}%`;
                        }
                    }
                },
                title: {
                    display: true,
                    text: '攻防对比数据',
                    font: {
                        size: 16,
                        weight: 'bold'
                    },
                    padding: {
                        bottom: 20
                    }
                }
            },
            elements: {
                line: {
                    tension: 0.1 // 曲线平滑度
                }
            }
        }
    });
};
// 监听统计数据变化
watch(() => props.stats, () => {
    createRadarChart();
}, { deep: true });
onMounted(() => {
    createRadarChart();
});
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['chart-wrapper']} */ ;
// CSS variable injection 
// CSS variable injection end 
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "radar-chart-container" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "chart-wrapper" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.canvas, __VLS_intrinsicElements.canvas)({
    ref: "chartCanvas",
});
/** @type {typeof __VLS_ctx.chartCanvas} */ ;
/** @type {__VLS_StyleScopedClasses['radar-chart-container']} */ ;
/** @type {__VLS_StyleScopedClasses['chart-wrapper']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            chartCanvas: chartCanvas,
        };
    },
    __typeProps: {},
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
    __typeProps: {},
});
; /* PartiallyEnd: #4569/main.vue */
