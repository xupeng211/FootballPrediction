import { ref, onMounted, watch, PropType } from 'vue';
import { Chart, PieController, Title, Tooltip, Legend, ArcElement } from 'chart.js';
// Register Chart.js components
Chart.register(PieController, Title, Tooltip, Legend, ArcElement);
const props = defineProps();
const chartCanvas = ref();
let chartInstance = null;
// 创建图表
const createChart = () => {
    if (!chartCanvas.value)
        return;
    const ctx = chartCanvas.value.getContext('2d');
    if (!ctx)
        return;
    // 销毁已存在的图表实例
    if (chartInstance) {
        chartInstance.destroy();
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
                        '#ef4444' // red-500
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
                            return context.label + ': ' + context.parsed.toFixed(1) + '%';
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
    });
};
// 监听概率数据变化
watch(() => [props.homeWinProb, props.drawProb, props.awayWinProb], () => {
    createChart();
}, { deep: true });
onMounted(() => {
    createChart();
});
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['legend-item']} */ ;
/** @type {__VLS_StyleScopedClasses['legend-item']} */ ;
/** @type {__VLS_StyleScopedClasses['legend-item']} */ ;
/** @type {__VLS_StyleScopedClasses['chart-wrapper']} */ ;
/** @type {__VLS_StyleScopedClasses['legend']} */ ;
// CSS variable injection 
// CSS variable injection end 
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "probability-chart-container" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "chart-wrapper" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.canvas, __VLS_intrinsicElements.canvas)({
    ref: "chartCanvas",
});
/** @type {typeof __VLS_ctx.chartCanvas} */ ;
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "legend" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "legend-item home" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: "color-box" },
    ...{ style: {} },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
((__VLS_ctx.homeWinProb * 100).toFixed(1));
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "legend-item draw" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: "color-box" },
    ...{ style: {} },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
((__VLS_ctx.drawProb * 100).toFixed(1));
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "legend-item away" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: "color-box" },
    ...{ style: {} },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
((__VLS_ctx.awayWinProb * 100).toFixed(1));
/** @type {__VLS_StyleScopedClasses['probability-chart-container']} */ ;
/** @type {__VLS_StyleScopedClasses['chart-wrapper']} */ ;
/** @type {__VLS_StyleScopedClasses['legend']} */ ;
/** @type {__VLS_StyleScopedClasses['legend-item']} */ ;
/** @type {__VLS_StyleScopedClasses['home']} */ ;
/** @type {__VLS_StyleScopedClasses['color-box']} */ ;
/** @type {__VLS_StyleScopedClasses['legend-item']} */ ;
/** @type {__VLS_StyleScopedClasses['draw']} */ ;
/** @type {__VLS_StyleScopedClasses['color-box']} */ ;
/** @type {__VLS_StyleScopedClasses['legend-item']} */ ;
/** @type {__VLS_StyleScopedClasses['away']} */ ;
/** @type {__VLS_StyleScopedClasses['color-box']} */ ;
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
