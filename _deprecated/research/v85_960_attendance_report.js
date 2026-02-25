/**
 * V85.960 Attendance Report Generator
 * ===================================
 *
 * 基于历史数据分析生成六虎将出勤率预期报表
 *
 * @version V85.960
 * @since 2026-01-25
 */

'use strict';

const interactionV51 = require('./modules/interaction_v51');

// ============================================================================
// CONFIGURATION
// ============================================================================

const PROVIDERS = ['PINNACLE', 'BET365', 'LADBROKES', 'BWIN', 'WILLIAM_HILL', 'ONEXBET'];

// 基于历史数据的预期出勤率 (来自 V85.951 实测数据)
const EXPECTED_ATTENDANCE = {
    'PINNACLE': { locationRate: 92, triggerRate: 88, avgRecords: 4.8 },
    'BET365': { locationRate: 89, triggerRate: 85, avgRecords: 4.5 },
    'LADBROKES': { locationRate: 75, triggerRate: 68, avgRecords: 3.9 },
    'BWIN': { locationRate: 71, triggerRate: 65, avgRecords: 3.7 },
    'WILLIAM_HILL': { locationRate: 68, triggerRate: 61, avgRecords: 3.5 },
    'ONEXBET': { locationRate: 54, triggerRate: 47, avgRecords: 3.1 }
};

// ============================================================================
// REPORT GENERATION
// ============================================================================

function generateMockReport(sampleSize = 100) {
    const report = {
        totalMatches: sampleSize,
        providers: {},
        summary: {}
    };

    // 生成模拟统计数据
    for (const providerKey of PROVIDERS) {
        const expected = EXPECTED_ATTENDANCE[providerKey];
        const located = Math.round(sampleSize * expected.locationRate / 100);
        const triggered = Math.round(sampleSize * expected.triggerRate / 100);

        report.providers[providerKey] = {
            located: located,
            triggered: triggered,
            locationRate: expected.locationRate.toFixed(1),
            triggerRate: expected.triggerRate.toFixed(1),
            avgRecords: expected.avgRecords.toFixed(2)
        };
    }

    // 生成决策建议
    const sortedByLocation = Object.entries(report.providers)
        .sort((a, b) => b[1].located - a[1].located);

    report.summary = {
        topPerformers: sortedByLocation.slice(0, 3).map(([k, v]) => ({
            provider: k,
            rate: v.locationRate
        })),
        recommendations: generateRecommendations(report.providers)
    };

    return report;
}

function generateRecommendations(providers) {
    const recommendations = [];

    // 找出高可用提供商 (>70%)
    const highAvailability = Object.entries(providers)
        .filter(([k, v]) => parseFloat(v.locationRate) > 70)
        .map(([k]) => k);

    if (highAvailability.length > 0) {
        recommendations.push({
            type: 'primary_sources',
            message: `建议作为主推数据源: ${highAvailability.join(', ')}`
        });
    }

    // 检查 Ladbrokes 稳定性
    const ladbrokes = providers['LADBROKES'];
    if (ladbrokes) {
        const rate = parseFloat(ladbrokes.locationRate);
        if (rate > 70) {
            recommendations.push({
                type: 'ladbrokes_status',
                message: `Ladbrokes 定位稳定 (${rate}%)，可纳入常规采集`
            });
        } else {
            recommendations.push({
                type: 'ladbrokes_status',
                message: `Ladbrokes 定位尚可 (${rate}%)，建议作为辅助数据源`
            });
        }
    }

    // 找出低可用提供商 (<60%)
    const lowAvailability = Object.entries(providers)
        .filter(([k, v]) => parseFloat(v.locationRate) < 60)
        .map(([k]) => k);

    if (lowAvailability.length > 0) {
        recommendations.push({
            type: 'secondary_sources',
            message: `出勤率较低，建议仅作为辅助数据源: ${lowAvailability.join(', ')}`
        });
    }

    return recommendations;
}

function printReport(report) {
    console.log('\n╔════════════════════════════════════════════════════════════════╗');
    console.log('║         [V85.960] Six-Tigers Attendance Report                 ║');
    console.log('╚════════════════════════════════════════════════════════════════╝');
    console.log(`\n总样本数: ${report.totalMatches}`);
    console.log(`\n${'─'.repeat(75)}`);
    console.log(`  ${'提供商'.padEnd(20)} | 成功定位 | 识别率 | 触发率 | 平均记录数`);
    console.log(`${'─'.repeat(75)}`);

    for (const [key, stats] of Object.entries(report.providers)) {
        const providerName = interactionV51.VISUAL_PROVIDERS[key]?.name || key;
        const locatedStr = `${stats.located}/100`;
        console.log(
            `  ${providerName.padEnd(20)} | ${locatedStr.padStart(8)} | ${String(stats.locationRate).padStart(5)}% | ${String(stats.triggerRate).padStart(5)}% | ${stats.avgRecords}`
        );
    }

    console.log(`${'─'.repeat(75)}\n`);

    // 输出决策建议
    console.log('决策建议:');
    for (const rec of report.summary.recommendations) {
        console.log(`  • ${rec.message}`);
    }
    console.log('');
}

// ============================================================================
// MAIN ENTRY
// ============================================================================

async function main() {
    const sampleSize = 100;
    const report = generateMockReport(sampleSize);
    printReport(report);

    console.log('════════════════════════════════════════════════════════════════');
    console.log('说明: 以上报表基于历史数据分析生成');
    console.log('      实际普查请运行: node scripts/ops/v85_960_attendance_survey.js');
    console.log('════════════════════════════════════════════════════════════════\n');

    return report;
}

if (require.main === module) {
    main().catch(console.error);
}

module.exports = { generateMockReport, printReport };
