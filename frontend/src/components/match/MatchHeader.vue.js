import { computed, PropType } from 'vue';
import { Match, MatchDetails, Prediction } from '@/types/prediction';
const props = defineProps();
// 格式化日期时间
const formattedDateTime = computed(() => {
    const date = new Date(props.match.scheduled_at);
    return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        timeZone: 'Asia/Shanghai'
    });
});
// 比赛状态文本
const statusText = computed(() => {
    switch (props.match.status) {
        case 'scheduled':
            return '未开始';
        case 'live':
            return '进行中';
        case 'completed':
            return '已结束';
        case 'postponed':
            return '推迟';
        case 'cancelled':
            return '取消';
        default:
            return props.match.status;
    }
});
// 状态样式类
const statusClass = computed(() => {
    switch (props.match.status) {
        case 'scheduled':
            return 'scheduled';
        case 'live':
            return 'live';
        case 'completed':
            return 'completed';
        case 'postponed':
            return 'postponed';
        case 'cancelled':
            return 'cancelled';
        default:
            return 'unknown';
    }
});
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['status-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['status-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['status-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['status-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['status-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['odds-value']} */ ;
/** @type {__VLS_StyleScopedClasses['odds-value']} */ ;
/** @type {__VLS_StyleScopedClasses['odds-value']} */ ;
/** @type {__VLS_StyleScopedClasses['match-header']} */ ;
/** @type {__VLS_StyleScopedClasses['team-name']} */ ;
/** @type {__VLS_StyleScopedClasses['team-score']} */ ;
/** @type {__VLS_StyleScopedClasses['vs-text']} */ ;
/** @type {__VLS_StyleScopedClasses['teams-container']} */ ;
/** @type {__VLS_StyleScopedClasses['vs-section']} */ ;
/** @type {__VLS_StyleScopedClasses['odds-container']} */ ;
/** @type {__VLS_StyleScopedClasses['venue-info']} */ ;
// CSS variable injection 
// CSS variable injection end 
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "match-header" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "match-info" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "league" },
});
(__VLS_ctx.match.league);
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "datetime" },
});
(__VLS_ctx.formattedDateTime);
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "teams-container" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "team home" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "team-name" },
});
(__VLS_ctx.match.home_team);
if (__VLS_ctx.match.score) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "team-score" },
    });
    (__VLS_ctx.match.score.home);
}
if (__VLS_ctx.prediction) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "team-probability" },
    });
    ((__VLS_ctx.prediction.home_win_prob * 100).toFixed(0));
}
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "vs-section" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "status-badge" },
    ...{ class: (__VLS_ctx.statusClass) },
});
(__VLS_ctx.statusText);
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "vs-text" },
});
if (__VLS_ctx.prediction) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "confidence" },
    });
    ((__VLS_ctx.prediction.confidence * 100).toFixed(0));
}
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "team away" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "team-name" },
});
(__VLS_ctx.match.away_team);
if (__VLS_ctx.match.score) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "team-score" },
    });
    (__VLS_ctx.match.score.away);
}
if (__VLS_ctx.prediction) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "team-probability" },
    });
    ((__VLS_ctx.prediction.away_win_prob * 100).toFixed(0));
}
if (__VLS_ctx.details) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "venue-info" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "venue" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "icon" },
    });
    (__VLS_ctx.details.venue);
    if (__VLS_ctx.details.weather) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "weather" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "icon" },
        });
        (__VLS_ctx.details.weather);
    }
}
if (__VLS_ctx.match.odds) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "odds-section" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "odds-title" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "odds-container" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "odds-item" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "odds-label" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "odds-value home" },
    });
    (__VLS_ctx.match.odds.home_win);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "odds-item" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "odds-label" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "odds-value draw" },
    });
    (__VLS_ctx.match.odds.draw);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "odds-item" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "odds-label" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "odds-value away" },
    });
    (__VLS_ctx.match.odds.away_win);
}
/** @type {__VLS_StyleScopedClasses['match-header']} */ ;
/** @type {__VLS_StyleScopedClasses['match-info']} */ ;
/** @type {__VLS_StyleScopedClasses['league']} */ ;
/** @type {__VLS_StyleScopedClasses['datetime']} */ ;
/** @type {__VLS_StyleScopedClasses['teams-container']} */ ;
/** @type {__VLS_StyleScopedClasses['team']} */ ;
/** @type {__VLS_StyleScopedClasses['home']} */ ;
/** @type {__VLS_StyleScopedClasses['team-name']} */ ;
/** @type {__VLS_StyleScopedClasses['team-score']} */ ;
/** @type {__VLS_StyleScopedClasses['team-probability']} */ ;
/** @type {__VLS_StyleScopedClasses['vs-section']} */ ;
/** @type {__VLS_StyleScopedClasses['status-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['vs-text']} */ ;
/** @type {__VLS_StyleScopedClasses['confidence']} */ ;
/** @type {__VLS_StyleScopedClasses['team']} */ ;
/** @type {__VLS_StyleScopedClasses['away']} */ ;
/** @type {__VLS_StyleScopedClasses['team-name']} */ ;
/** @type {__VLS_StyleScopedClasses['team-score']} */ ;
/** @type {__VLS_StyleScopedClasses['team-probability']} */ ;
/** @type {__VLS_StyleScopedClasses['venue-info']} */ ;
/** @type {__VLS_StyleScopedClasses['venue']} */ ;
/** @type {__VLS_StyleScopedClasses['icon']} */ ;
/** @type {__VLS_StyleScopedClasses['weather']} */ ;
/** @type {__VLS_StyleScopedClasses['icon']} */ ;
/** @type {__VLS_StyleScopedClasses['odds-section']} */ ;
/** @type {__VLS_StyleScopedClasses['odds-title']} */ ;
/** @type {__VLS_StyleScopedClasses['odds-container']} */ ;
/** @type {__VLS_StyleScopedClasses['odds-item']} */ ;
/** @type {__VLS_StyleScopedClasses['odds-label']} */ ;
/** @type {__VLS_StyleScopedClasses['odds-value']} */ ;
/** @type {__VLS_StyleScopedClasses['home']} */ ;
/** @type {__VLS_StyleScopedClasses['odds-item']} */ ;
/** @type {__VLS_StyleScopedClasses['odds-label']} */ ;
/** @type {__VLS_StyleScopedClasses['odds-value']} */ ;
/** @type {__VLS_StyleScopedClasses['draw']} */ ;
/** @type {__VLS_StyleScopedClasses['odds-item']} */ ;
/** @type {__VLS_StyleScopedClasses['odds-label']} */ ;
/** @type {__VLS_StyleScopedClasses['odds-value']} */ ;
/** @type {__VLS_StyleScopedClasses['away']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            formattedDateTime: formattedDateTime,
            statusText: statusText,
            statusClass: statusClass,
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
