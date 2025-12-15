import { ref, onMounted, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import apiClient from '@/api/client';
import { Match, MatchDetails, MatchStats, Prediction } from '@/types/prediction';
import MatchHeader from '@/components/match/MatchHeader.vue';
import ProbabilityChart from '@/components/charts/ProbabilityChart.vue';
import StatsRadar from '@/components/charts/StatsRadar.vue';
const route = useRoute();
const router = useRouter();
// 响应式数据
const loading = ref(true);
const error = ref('');
const match = ref(null);
const matchDetails = ref(null);
const matchStats = ref(null);
const prediction = ref(null);
const activeTab = ref('overview');
// 标签页配置
const tabs = [
    { key: 'overview', label: '预测分析' },
    { key: 'stats', label: '技术统计' },
    { key: 'odds', label: '赔率分析' }
];
// 加载数据
const loadData = async () => {
    try {
        loading.value = true;
        error.value = '';
        const matchId = parseInt(route.params.id);
        if (isNaN(matchId)) {
            throw new Error('无效的比赛ID');
        }
        // 并行加载所有数据
        const [matchData, detailsData, statsData, predictionsData] = await Promise.all([
            apiClient.getMatch(matchId),
            apiClient.getMatchDetails(matchId),
            apiClient.getMatchStats(matchId),
            apiClient.getPredictions(matchId)
        ]);
        match.value = matchData;
        matchDetails.value = detailsData;
        matchStats.value = statsData;
        // 找到匹配的预测数据
        prediction.value = predictionsData.predictions.find(p => p.match_id === matchId) || predictionsData.predictions[0];
    }
    catch (err) {
        console.error('Failed to load match details:', err);
        error.value = err instanceof Error ? err.message : '加载失败，请重试';
    }
    finally {
        loading.value = false;
    }
};
// 计算属性
const predictionResultText = computed(() => {
    if (!prediction.value)
        return '未知';
    switch (prediction.value.prediction) {
        case 'home_win':
            return '主队胜';
        case 'draw':
            return '平局';
        case 'away_win':
            return '客队胜';
        default:
            return prediction.value.prediction;
    }
});
const predictionResultClass = computed(() => {
    if (!prediction.value)
        return '';
    return `prediction-${prediction.value.prediction}`;
});
// 详细统计数据
const detailedStats = computed(() => {
    if (!matchStats.value)
        return [];
    const stats = matchStats.value;
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
    ];
});
// 翻译特征名称
const translateFeature = (feature) => {
    const translations = {
        'home_xg': '主队期望进球',
        'away_xg': '客队期望进球',
        'home_possession': '主队控球率',
        'away_possession': '客队控球率',
        'shots_difference': '射门次数差',
        'home_form': '主队近期状态',
        'away_form': '客队近期状态',
        'head_to_head': '历史交锋',
        'home_advantage': '主场优势'
    };
    return translations[feature] || feature;
};
// 页面加载时获取数据
onMounted(() => {
    loadData();
});
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['error-state']} */ ;
/** @type {__VLS_StyleScopedClasses['retry-button']} */ ;
/** @type {__VLS_StyleScopedClasses['tab-button']} */ ;
/** @type {__VLS_StyleScopedClasses['tab-button']} */ ;
/** @type {__VLS_StyleScopedClasses['model-item']} */ ;
/** @type {__VLS_StyleScopedClasses['model-item']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-row']} */ ;
/** @type {__VLS_StyleScopedClasses['home-value']} */ ;
/** @type {__VLS_StyleScopedClasses['away-value']} */ ;
/** @type {__VLS_StyleScopedClasses['odds-card']} */ ;
/** @type {__VLS_StyleScopedClasses['odds-card']} */ ;
/** @type {__VLS_StyleScopedClasses['odds-card']} */ ;
/** @type {__VLS_StyleScopedClasses['overview-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['stats-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['tabs']} */ ;
/** @type {__VLS_StyleScopedClasses['odds-cards']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-values']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-bar']} */ ;
/** @type {__VLS_StyleScopedClasses['container']} */ ;
/** @type {__VLS_StyleScopedClasses['tab-content']} */ ;
/** @type {__VLS_StyleScopedClasses['odds-card']} */ ;
/** @type {__VLS_StyleScopedClasses['card-odds']} */ ;
// CSS variable injection 
// CSS variable injection end 
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "match-details-page" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "container" },
});
if (__VLS_ctx.loading) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "loading-state" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "loading-spinner" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({});
}
else if (__VLS_ctx.error) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "error-state" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.h2, __VLS_intrinsicElements.h2)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({});
    (__VLS_ctx.error);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ onClick: (__VLS_ctx.loadData) },
        ...{ class: "retry-button" },
    });
}
else {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "match-content" },
    });
    /** @type {[typeof MatchHeader, ]} */ ;
    // @ts-ignore
    const __VLS_0 = __VLS_asFunctionalComponent(MatchHeader, new MatchHeader({
        match: (__VLS_ctx.match),
        details: (__VLS_ctx.matchDetails),
        prediction: (__VLS_ctx.prediction),
    }));
    const __VLS_1 = __VLS_0({
        match: (__VLS_ctx.match),
        details: (__VLS_ctx.matchDetails),
        prediction: (__VLS_ctx.prediction),
    }, ...__VLS_functionalComponentArgsRest(__VLS_0));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "tabs-container" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "tabs" },
    });
    for (const [tab] of __VLS_getVForSourceType((__VLS_ctx.tabs))) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (...[$event]) => {
                    if (!!(__VLS_ctx.loading))
                        return;
                    if (!!(__VLS_ctx.error))
                        return;
                    __VLS_ctx.activeTab = tab.key;
                } },
            key: (tab.key),
            ...{ class: (['tab-button', { active: __VLS_ctx.activeTab === tab.key }]) },
        });
        (tab.label);
    }
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "tab-content" },
    });
    if (__VLS_ctx.activeTab === 'overview') {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "overview-content" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "overview-grid" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "prediction-section" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.h3, __VLS_intrinsicElements.h3)({});
        /** @type {[typeof ProbabilityChart, ]} */ ;
        // @ts-ignore
        const __VLS_3 = __VLS_asFunctionalComponent(ProbabilityChart, new ProbabilityChart({
            homeWinProb: (__VLS_ctx.prediction.home_win_prob),
            drawProb: (__VLS_ctx.prediction.draw_prob),
            awayWinProb: (__VLS_ctx.prediction.away_win_prob),
            confidence: (__VLS_ctx.prediction.confidence),
        }));
        const __VLS_4 = __VLS_3({
            homeWinProb: (__VLS_ctx.prediction.home_win_prob),
            drawProb: (__VLS_ctx.prediction.draw_prob),
            awayWinProb: (__VLS_ctx.prediction.away_win_prob),
            confidence: (__VLS_ctx.prediction.confidence),
        }, ...__VLS_functionalComponentArgsRest(__VLS_3));
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "model-info" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.h3, __VLS_intrinsicElements.h3)({});
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "model-details" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "model-item" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "label" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "value" },
            ...{ class: (__VLS_ctx.predictionResultClass) },
        });
        (__VLS_ctx.predictionResultText);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "model-item" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "label" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "value" },
        });
        ((__VLS_ctx.prediction.confidence * 100).toFixed(1));
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "model-item" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "label" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "value" },
        });
        (__VLS_ctx.prediction.mode || 'mock');
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "model-item" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "label" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "value" },
        });
        ((__VLS_ctx.prediction.features_used || []).length);
        if (__VLS_ctx.prediction.features_used) {
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                ...{ class: "features-list" },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                ...{ class: "features-title" },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                ...{ class: "feature-tags" },
            });
            for (const [feature] of __VLS_getVForSourceType((__VLS_ctx.prediction.features_used))) {
                __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                    key: (feature),
                    ...{ class: "feature-tag" },
                });
                (__VLS_ctx.translateFeature(feature));
            }
        }
    }
    if (__VLS_ctx.activeTab === 'stats') {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "stats-content" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "stats-grid" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "radar-section" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.h3, __VLS_intrinsicElements.h3)({});
        /** @type {[typeof StatsRadar, ]} */ ;
        // @ts-ignore
        const __VLS_6 = __VLS_asFunctionalComponent(StatsRadar, new StatsRadar({
            stats: (__VLS_ctx.matchStats),
        }));
        const __VLS_7 = __VLS_6({
            stats: (__VLS_ctx.matchStats),
        }, ...__VLS_functionalComponentArgsRest(__VLS_6));
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "detailed-stats" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.h3, __VLS_intrinsicElements.h3)({});
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "stats-table" },
        });
        for (const [stat] of __VLS_getVForSourceType((__VLS_ctx.detailedStats))) {
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                ...{ class: "stat-row" },
                key: (stat.key),
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                ...{ class: "stat-label" },
            });
            (stat.label);
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                ...{ class: "stat-values" },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                ...{ class: "home-value" },
            });
            (stat.home);
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                ...{ class: "stat-bar" },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                ...{ class: "home-bar" },
                ...{ style: ({ width: stat.homePercentage + '%' }) },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                ...{ class: "away-bar" },
                ...{ style: ({ width: stat.awayPercentage + '%' }) },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                ...{ class: "away-value" },
            });
            (stat.away);
        }
    }
    if (__VLS_ctx.activeTab === 'odds') {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "odds-content" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "odds-analysis" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.h3, __VLS_intrinsicElements.h3)({});
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "odds-cards" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "odds-card home" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "card-header" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "card-odds" },
        });
        (__VLS_ctx.match.odds.home_win);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "card-probability" },
        });
        (((1 / __VLS_ctx.match.odds.home_win) * 100).toFixed(1));
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "odds-card draw" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "card-header" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "card-odds" },
        });
        (__VLS_ctx.match.odds.draw);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "card-probability" },
        });
        (((1 / __VLS_ctx.match.odds.draw) * 100).toFixed(1));
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "odds-card away" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "card-header" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "card-odds" },
        });
        (__VLS_ctx.match.odds.away_win);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "card-probability" },
        });
        (((1 / __VLS_ctx.match.odds.away_win) * 100).toFixed(1));
    }
}
/** @type {__VLS_StyleScopedClasses['match-details-page']} */ ;
/** @type {__VLS_StyleScopedClasses['container']} */ ;
/** @type {__VLS_StyleScopedClasses['loading-state']} */ ;
/** @type {__VLS_StyleScopedClasses['loading-spinner']} */ ;
/** @type {__VLS_StyleScopedClasses['error-state']} */ ;
/** @type {__VLS_StyleScopedClasses['retry-button']} */ ;
/** @type {__VLS_StyleScopedClasses['match-content']} */ ;
/** @type {__VLS_StyleScopedClasses['tabs-container']} */ ;
/** @type {__VLS_StyleScopedClasses['tabs']} */ ;
/** @type {__VLS_StyleScopedClasses['tab-content']} */ ;
/** @type {__VLS_StyleScopedClasses['overview-content']} */ ;
/** @type {__VLS_StyleScopedClasses['overview-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['prediction-section']} */ ;
/** @type {__VLS_StyleScopedClasses['model-info']} */ ;
/** @type {__VLS_StyleScopedClasses['model-details']} */ ;
/** @type {__VLS_StyleScopedClasses['model-item']} */ ;
/** @type {__VLS_StyleScopedClasses['label']} */ ;
/** @type {__VLS_StyleScopedClasses['value']} */ ;
/** @type {__VLS_StyleScopedClasses['model-item']} */ ;
/** @type {__VLS_StyleScopedClasses['label']} */ ;
/** @type {__VLS_StyleScopedClasses['value']} */ ;
/** @type {__VLS_StyleScopedClasses['model-item']} */ ;
/** @type {__VLS_StyleScopedClasses['label']} */ ;
/** @type {__VLS_StyleScopedClasses['value']} */ ;
/** @type {__VLS_StyleScopedClasses['model-item']} */ ;
/** @type {__VLS_StyleScopedClasses['label']} */ ;
/** @type {__VLS_StyleScopedClasses['value']} */ ;
/** @type {__VLS_StyleScopedClasses['features-list']} */ ;
/** @type {__VLS_StyleScopedClasses['features-title']} */ ;
/** @type {__VLS_StyleScopedClasses['feature-tags']} */ ;
/** @type {__VLS_StyleScopedClasses['feature-tag']} */ ;
/** @type {__VLS_StyleScopedClasses['stats-content']} */ ;
/** @type {__VLS_StyleScopedClasses['stats-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['radar-section']} */ ;
/** @type {__VLS_StyleScopedClasses['detailed-stats']} */ ;
/** @type {__VLS_StyleScopedClasses['stats-table']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-row']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-values']} */ ;
/** @type {__VLS_StyleScopedClasses['home-value']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-bar']} */ ;
/** @type {__VLS_StyleScopedClasses['home-bar']} */ ;
/** @type {__VLS_StyleScopedClasses['away-bar']} */ ;
/** @type {__VLS_StyleScopedClasses['away-value']} */ ;
/** @type {__VLS_StyleScopedClasses['odds-content']} */ ;
/** @type {__VLS_StyleScopedClasses['odds-analysis']} */ ;
/** @type {__VLS_StyleScopedClasses['odds-cards']} */ ;
/** @type {__VLS_StyleScopedClasses['odds-card']} */ ;
/** @type {__VLS_StyleScopedClasses['home']} */ ;
/** @type {__VLS_StyleScopedClasses['card-header']} */ ;
/** @type {__VLS_StyleScopedClasses['card-odds']} */ ;
/** @type {__VLS_StyleScopedClasses['card-probability']} */ ;
/** @type {__VLS_StyleScopedClasses['odds-card']} */ ;
/** @type {__VLS_StyleScopedClasses['draw']} */ ;
/** @type {__VLS_StyleScopedClasses['card-header']} */ ;
/** @type {__VLS_StyleScopedClasses['card-odds']} */ ;
/** @type {__VLS_StyleScopedClasses['card-probability']} */ ;
/** @type {__VLS_StyleScopedClasses['odds-card']} */ ;
/** @type {__VLS_StyleScopedClasses['away']} */ ;
/** @type {__VLS_StyleScopedClasses['card-header']} */ ;
/** @type {__VLS_StyleScopedClasses['card-odds']} */ ;
/** @type {__VLS_StyleScopedClasses['card-probability']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            MatchHeader: MatchHeader,
            ProbabilityChart: ProbabilityChart,
            StatsRadar: StatsRadar,
            loading: loading,
            error: error,
            match: match,
            matchDetails: matchDetails,
            matchStats: matchStats,
            prediction: prediction,
            activeTab: activeTab,
            tabs: tabs,
            loadData: loadData,
            predictionResultText: predictionResultText,
            predictionResultClass: predictionResultClass,
            detailedStats: detailedStats,
            translateFeature: translateFeature,
        };
    },
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
});
; /* PartiallyEnd: #4569/main.vue */
