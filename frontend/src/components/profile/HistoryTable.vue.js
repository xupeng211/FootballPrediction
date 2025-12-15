import { ref, computed, PropType } from 'vue';
import { useRouter } from 'vue-router';
import { HistoryRecord } from '@/types/prediction';
const props = withDefaults(defineProps(), {
    loading: false,
    hasMore: false
});
const emit = defineEmits();
const router = useRouter();
// 加载更多
const loadMore = () => {
    emit('loadMore');
};
// 点击行跳转到比赛详情
const handleRowClick = (record) => {
    router.push(`/matches/${record.match_id}`);
};
// 格式化日期
const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-CN', {
        month: '2-digit',
        day: '2-digit'
    });
};
const formatTime = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit'
    });
};
// 获取预测文本
const getPredictionText = (prediction) => {
    const translations = {
        'home_win': '主胜',
        'draw': '平局',
        'away_win': '客胜'
    };
    return translations[prediction] || prediction;
};
// 获取预测样式类
const getPredictionClass = (prediction) => {
    const classes = {
        'home_win': 'prediction-home',
        'draw': 'prediction-draw',
        'away_win': 'prediction-away'
    };
    return classes[prediction] || '';
};
// 获取结果文本
const getResultText = (outcome) => {
    const translations = {
        'home_win': '主胜',
        'draw': '平局',
        'away_win': '客胜'
    };
    return translations[outcome] || outcome;
};
// 获取结果样式类
const getResultClass = (record) => {
    if (!record.actual_outcome)
        return '';
    if (record.result === 'win')
        return 'result-win';
    if (record.result === 'loss')
        return 'result-loss';
    return 'result-push';
};
// 获取行样式类
const getRowClass = (record) => {
    const classes = ['clickable'];
    if (record.result === 'win')
        classes.push('win-row');
    if (record.result === 'loss')
        classes.push('loss-row');
    if (record.result === 'push')
        classes.push('push-row');
    return classes.join(' ');
};
// 获取盈亏文本
const getProfitText = (record) => {
    const prefix = record.profit >= 0 ? '+' : '';
    return `${prefix}¥${Math.abs(record.profit).toFixed(2)}`;
};
// 获取盈亏百分比
const getProfitPercentage = (record) => {
    const percentage = ((record.profit / record.stake) * 100).toFixed(1);
    const prefix = percentage >= '0' ? '+' : '';
    return `${prefix}${percentage}%`;
};
// 获取盈亏样式类
const getProfitClass = (record) => {
    if (record.profit > 0)
        return 'profit-win';
    if (record.profit < 0)
        return 'profit-loss';
    return 'profit-push';
};
// 获取状态文本
const getStatusText = (result) => {
    const statusMap = {
        'win': '获胜',
        'loss': '失败',
        'push': '走水'
    };
    return statusMap[result || ''] || '待定';
};
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_withDefaultsArg = (function (t) { return t; })({
    loading: false,
    hasMore: false
});
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['table-header']} */ ;
/** @type {__VLS_StyleScopedClasses['load-more-button']} */ ;
/** @type {__VLS_StyleScopedClasses['load-more-button']} */ ;
/** @type {__VLS_StyleScopedClasses['history-table']} */ ;
/** @type {__VLS_StyleScopedClasses['history-table']} */ ;
/** @type {__VLS_StyleScopedClasses['history-table']} */ ;
/** @type {__VLS_StyleScopedClasses['table-row']} */ ;
/** @type {__VLS_StyleScopedClasses['table-row']} */ ;
/** @type {__VLS_StyleScopedClasses['date-content']} */ ;
/** @type {__VLS_StyleScopedClasses['match-content']} */ ;
/** @type {__VLS_StyleScopedClasses['match-content']} */ ;
/** @type {__VLS_StyleScopedClasses['profit-amount']} */ ;
/** @type {__VLS_StyleScopedClasses['profit-amount']} */ ;
/** @type {__VLS_StyleScopedClasses['profit-amount']} */ ;
/** @type {__VLS_StyleScopedClasses['status-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['status-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['status-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['empty-state']} */ ;
/** @type {__VLS_StyleScopedClasses['loading-state']} */ ;
/** @type {__VLS_StyleScopedClasses['table-header']} */ ;
/** @type {__VLS_StyleScopedClasses['history-table']} */ ;
/** @type {__VLS_StyleScopedClasses['history-table']} */ ;
/** @type {__VLS_StyleScopedClasses['match-cell']} */ ;
/** @type {__VLS_StyleScopedClasses['teams']} */ ;
/** @type {__VLS_StyleScopedClasses['vs']} */ ;
/** @type {__VLS_StyleScopedClasses['profit-content']} */ ;
/** @type {__VLS_StyleScopedClasses['profit-amount']} */ ;
/** @type {__VLS_StyleScopedClasses['profit-percentage']} */ ;
/** @type {__VLS_StyleScopedClasses['history-table']} */ ;
/** @type {__VLS_StyleScopedClasses['history-table']} */ ;
/** @type {__VLS_StyleScopedClasses['date-cell']} */ ;
/** @type {__VLS_StyleScopedClasses['prediction-cell']} */ ;
/** @type {__VLS_StyleScopedClasses['result-cell']} */ ;
/** @type {__VLS_StyleScopedClasses['odds-cell']} */ ;
/** @type {__VLS_StyleScopedClasses['stake-cell']} */ ;
/** @type {__VLS_StyleScopedClasses['profit-cell']} */ ;
/** @type {__VLS_StyleScopedClasses['status-cell']} */ ;
/** @type {__VLS_StyleScopedClasses['match-cell']} */ ;
/** @type {__VLS_StyleScopedClasses['loading-spinner']} */ ;
// CSS variable injection 
// CSS variable injection end 
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "history-table-container" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "table-header" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.h3, __VLS_intrinsicElements.h3)({});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "table-actions" },
});
if (__VLS_ctx.hasMore) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ onClick: (__VLS_ctx.loadMore) },
        disabled: (__VLS_ctx.loading),
        ...{ class: "load-more-button" },
    });
    (__VLS_ctx.loading ? '加载中...' : '加载更多');
}
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "table-responsive" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.table, __VLS_intrinsicElements.table)({
    ...{ class: "history-table" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.thead, __VLS_intrinsicElements.thead)({});
__VLS_asFunctionalElement(__VLS_intrinsicElements.tr, __VLS_intrinsicElements.tr)({});
__VLS_asFunctionalElement(__VLS_intrinsicElements.th, __VLS_intrinsicElements.th)({});
__VLS_asFunctionalElement(__VLS_intrinsicElements.th, __VLS_intrinsicElements.th)({});
__VLS_asFunctionalElement(__VLS_intrinsicElements.th, __VLS_intrinsicElements.th)({});
__VLS_asFunctionalElement(__VLS_intrinsicElements.th, __VLS_intrinsicElements.th)({});
__VLS_asFunctionalElement(__VLS_intrinsicElements.th, __VLS_intrinsicElements.th)({});
__VLS_asFunctionalElement(__VLS_intrinsicElements.th, __VLS_intrinsicElements.th)({});
__VLS_asFunctionalElement(__VLS_intrinsicElements.th, __VLS_intrinsicElements.th)({});
__VLS_asFunctionalElement(__VLS_intrinsicElements.th, __VLS_intrinsicElements.th)({});
__VLS_asFunctionalElement(__VLS_intrinsicElements.tbody, __VLS_intrinsicElements.tbody)({});
for (const [record] of __VLS_getVForSourceType((__VLS_ctx.records))) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.tr, __VLS_intrinsicElements.tr)({
        ...{ onClick: (...[$event]) => {
                __VLS_ctx.handleRowClick(record);
            } },
        key: (record.id),
        ...{ class: "table-row" },
        ...{ class: (__VLS_ctx.getRowClass(record)) },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.td, __VLS_intrinsicElements.td)({
        ...{ class: "date-cell" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "date-content" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "date" },
    });
    (__VLS_ctx.formatDate(record.scheduled_at));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "time" },
    });
    (__VLS_ctx.formatTime(record.scheduled_at));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.td, __VLS_intrinsicElements.td)({
        ...{ class: "match-cell" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "match-content" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "teams" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "home-team" },
    });
    (record.home_team);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "vs" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "away-team" },
    });
    (record.away_team);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "league" },
    });
    (record.league);
    if (record.final_score) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "final-score" },
        });
        (record.final_score.home);
        (record.final_score.away);
    }
    __VLS_asFunctionalElement(__VLS_intrinsicElements.td, __VLS_intrinsicElements.td)({
        ...{ class: "prediction-cell" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "prediction-badge" },
        ...{ class: (__VLS_ctx.getPredictionClass(record.prediction)) },
    });
    (__VLS_ctx.getPredictionText(record.prediction));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.td, __VLS_intrinsicElements.td)({
        ...{ class: "result-cell" },
    });
    if (record.actual_outcome) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "result-badge" },
            ...{ class: (__VLS_ctx.getResultClass(record)) },
        });
        (__VLS_ctx.getResultText(record.actual_outcome));
    }
    else {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "pending" },
        });
    }
    __VLS_asFunctionalElement(__VLS_intrinsicElements.td, __VLS_intrinsicElements.td)({
        ...{ class: "odds-cell" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "odds-value" },
    });
    (record.odds.toFixed(2));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.td, __VLS_intrinsicElements.td)({
        ...{ class: "stake-cell" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "stake-value" },
    });
    (record.stake.toFixed(2));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.td, __VLS_intrinsicElements.td)({
        ...{ class: "profit-cell" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "profit-content" },
        ...{ class: (__VLS_ctx.getProfitClass(record)) },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "profit-amount" },
    });
    (__VLS_ctx.getProfitText(record));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "profit-percentage" },
    });
    (__VLS_ctx.getProfitPercentage(record));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.td, __VLS_intrinsicElements.td)({
        ...{ class: "status-cell" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "status-badge" },
        ...{ class: (record.result) },
    });
    (__VLS_ctx.getStatusText(record.result));
}
if (__VLS_ctx.records.length === 0 && !__VLS_ctx.loading) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "empty-state" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "empty-icon" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({
        ...{ class: "empty-subtitle" },
    });
}
if (__VLS_ctx.loading && __VLS_ctx.records.length === 0) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "loading-state" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "loading-spinner" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({});
}
/** @type {__VLS_StyleScopedClasses['history-table-container']} */ ;
/** @type {__VLS_StyleScopedClasses['table-header']} */ ;
/** @type {__VLS_StyleScopedClasses['table-actions']} */ ;
/** @type {__VLS_StyleScopedClasses['load-more-button']} */ ;
/** @type {__VLS_StyleScopedClasses['table-responsive']} */ ;
/** @type {__VLS_StyleScopedClasses['history-table']} */ ;
/** @type {__VLS_StyleScopedClasses['table-row']} */ ;
/** @type {__VLS_StyleScopedClasses['date-cell']} */ ;
/** @type {__VLS_StyleScopedClasses['date-content']} */ ;
/** @type {__VLS_StyleScopedClasses['date']} */ ;
/** @type {__VLS_StyleScopedClasses['time']} */ ;
/** @type {__VLS_StyleScopedClasses['match-cell']} */ ;
/** @type {__VLS_StyleScopedClasses['match-content']} */ ;
/** @type {__VLS_StyleScopedClasses['teams']} */ ;
/** @type {__VLS_StyleScopedClasses['home-team']} */ ;
/** @type {__VLS_StyleScopedClasses['vs']} */ ;
/** @type {__VLS_StyleScopedClasses['away-team']} */ ;
/** @type {__VLS_StyleScopedClasses['league']} */ ;
/** @type {__VLS_StyleScopedClasses['final-score']} */ ;
/** @type {__VLS_StyleScopedClasses['prediction-cell']} */ ;
/** @type {__VLS_StyleScopedClasses['prediction-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['result-cell']} */ ;
/** @type {__VLS_StyleScopedClasses['result-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['pending']} */ ;
/** @type {__VLS_StyleScopedClasses['odds-cell']} */ ;
/** @type {__VLS_StyleScopedClasses['odds-value']} */ ;
/** @type {__VLS_StyleScopedClasses['stake-cell']} */ ;
/** @type {__VLS_StyleScopedClasses['stake-value']} */ ;
/** @type {__VLS_StyleScopedClasses['profit-cell']} */ ;
/** @type {__VLS_StyleScopedClasses['profit-content']} */ ;
/** @type {__VLS_StyleScopedClasses['profit-amount']} */ ;
/** @type {__VLS_StyleScopedClasses['profit-percentage']} */ ;
/** @type {__VLS_StyleScopedClasses['status-cell']} */ ;
/** @type {__VLS_StyleScopedClasses['status-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['empty-state']} */ ;
/** @type {__VLS_StyleScopedClasses['empty-icon']} */ ;
/** @type {__VLS_StyleScopedClasses['empty-subtitle']} */ ;
/** @type {__VLS_StyleScopedClasses['loading-state']} */ ;
/** @type {__VLS_StyleScopedClasses['loading-spinner']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            loadMore: loadMore,
            handleRowClick: handleRowClick,
            formatDate: formatDate,
            formatTime: formatTime,
            getPredictionText: getPredictionText,
            getPredictionClass: getPredictionClass,
            getResultText: getResultText,
            getResultClass: getResultClass,
            getRowClass: getRowClass,
            getProfitText: getProfitText,
            getProfitPercentage: getProfitPercentage,
            getProfitClass: getProfitClass,
            getStatusText: getStatusText,
        };
    },
    __typeEmits: {},
    __typeProps: {},
    props: {},
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
    __typeEmits: {},
    __typeProps: {},
    props: {},
});
; /* PartiallyEnd: #4569/main.vue */
