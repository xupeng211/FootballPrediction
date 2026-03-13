/**
 * Stress Test - 意甲 10 场压力测试 (重构后版本)
 * ============================================
 *
 * 使用重构后的 ProductionHarvester + FotMobStrategy
 * 测试 MatchID: 4803301 - 4803311
 *
 * @module scripts/ops/stress_test_seriea
 * @version V4.46-TITAN
 */

'use strict';

const { ProductionHarvester } = require('../../src/infrastructure/harvesters/ProductionHarvester');

// 10 场意甲比赛 ID (Serie A)
const SERIE_A_MATCH_IDS = [
    '4803301', '4803302', '4803303', '4803304', '4803305',
    '4803306', '4803307', '4803308', '4803309', '4803310', '4803311'
];

/**
 * 执行单场收割测试
 * @param {ProductionHarvester} harvester - 收割器实例
 * @param {string} matchId - 比赛 ID
 * @param {number} index - 索引
 * @returns {Promise<Object>} 测试结果
 */
async function testSingleMatch(harvester, matchId, index) {
    const startTime = Date.now();
    console.log(`\n[${index + 1}/10] 🎯 测试 MatchID: ${matchId}`);
    console.log('─────────────────────────────────────────────────────────────');

    try {
        const result = await harvester.run({ matchId, force: true });
        const elapsed = Date.now() - startTime;

        console.log(`✅ 完成 | 耗时: ${(elapsed / 1000).toFixed(1)}s | 成功: ${result.success}`);

        return {
            matchId,
            success: result.success > 0 || result.success === true,
            error: result.error,
            elapsed,
            timestamp: new Date().toISOString()
        };
    } catch (error) {
        const elapsed = Date.now() - startTime;
        console.error(`❌ 失败 | 耗时: ${(elapsed / 1000).toFixed(1)}s | 错误: ${error.message}`);

        return {
            matchId,
            success: false,
            error: error.message,
            elapsed,
            timestamp: new Date().toISOString()
        };
    }
}

/**
 * 打印测试报告
 * @param {Array<Object>} results - 测试结果数组
 */
function printStressTestReport(results) {
    const total = results.length;
    const success = results.filter(r => r.success).length;
    const failed = total - success;
    const successRate = ((success / total) * 100).toFixed(1);
    const totalTime = results.reduce((sum, r) => sum + r.elapsed, 0);
    const avgTime = (totalTime / total / 1000).toFixed(1);

    console.log('\n');
    console.log('╔══════════════════════════════════════════════════════════════════╗');
    console.log('║          TITAN 重构后压力测试报告 (Serie A 10场)                 ║');
    console.log('╠══════════════════════════════════════════════════════════════════╣');
    console.log(`║  架构版本: V4.46-TITAN (三层架构)                                 ║`);
    console.log(`║  测试场次: ${String(total).padEnd(3)}                                             ║`);
    console.log(`║  成功: ${String(success).padEnd(3)} | 失败: ${String(failed).padEnd(3)} | 成功率: ${String(successRate + '%').padEnd(6)}          ║`);
    console.log(`║  总耗时: ${String((totalTime / 1000).toFixed(1) + 's').padEnd(6)} | 平均: ${String(avgTime + 's/场').padEnd(10)}            ║`);
    console.log('╠══════════════════════════════════════════════════════════════════╣');

    results.forEach((r, i) => {
        const status = r.success ? '✅' : '❌';
        const timeStr = `${(r.elapsed / 1000).toFixed(1)}s`.padStart(5);
        const idStr = r.matchId.padStart(8);
        console.log(`║  ${String(i + 1).padStart(2)}. ${status} MatchID ${idStr} | ${timeStr} | ${r.success ? 'SUCCESS' : (r.error || 'FAILED').substring(0, 20).padEnd(20)} ║`);
    });

    console.log('╚══════════════════════════════════════════════════════════════════╝');

    // 关键指标
    if (successRate === '100.0') {
        console.log('\n🎉 重构验证通过！三层架构保持 100% 成功率！');
    } else {
        console.log('\n⚠️  成功率未达 100%，建议检查失败场次日志');
    }

    return { total, success, failed, successRate };
}

/**
 * 主函数
 */
async function main() {
    console.log('\n');
    console.log('╔══════════════════════════════════════════════════════════════════╗');
    console.log('║     TITAN-DECOUPLING 压力测试 - Serie A (4803301-4803311)       ║');
    console.log('╠══════════════════════════════════════════════════════════════════╣');
    console.log('║  组件: ProductionHarvester + FotMobStrategy                      ║');
    console.log('║  模式: 单场比赛独立收割                                           ║');
    console.log('╚══════════════════════════════════════════════════════════════════╝');

    const harvester = new ProductionHarvester({
        maxWorkers: 3,  // 并发 Worker 数
        minDelayMs: 5000,
        maxDelayMs: 8000,
        dryRun: false,
        verboseLogging: true
    });

    const results = [];

    try {
        // 初始化
        console.log('\n🔧 初始化收割器...');
        await harvester.init();
        console.log('✅ 初始化完成\n');

        // 顺序执行 10 场测试
        for (let i = 0; i < SERIE_A_MATCH_IDS.length; i++) {
            const matchId = SERIE_A_MATCH_IDS[i];
            const result = await testSingleMatch(harvester, matchId, i);
            results.push(result);

            // 场次间延时，避免过快请求
            if (i < SERIE_A_MATCH_IDS.length - 1) {
                const delay = 3000 + Math.random() * 2000;
                console.log(`⏳ 等待 ${(delay / 1000).toFixed(1)}s 后继续...`);
                await new Promise(resolve => { setTimeout(resolve, delay); });
            }
        }

        // 清理
        await harvester.cleanup();

        // 打印报告
        const report = printStressTestReport(results);

        // 返回退出码
        process.exit(report.successRate === '100.0' ? 0 : 1);

    } catch (error) {
        console.error('\n💥 致命错误:', error);
        await harvester.cleanup().catch(() => {});
        process.exit(1);
    }
}

// 执行
if (require.main === module) {
    main();
}

module.exports = { SERIE_A_MATCH_IDS, testSingleMatch, printStressTestReport };
