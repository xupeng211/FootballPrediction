/**
 * V171-Standard-06 实时监控演示
 * =============================
 *
 * 展示实时监控看板效果
 */

'use strict';

const { MetricsCollector, TelemetryDashboard, StructuredLogger } = require('./lib/telemetry');

console.log('═══════════════════════════════════════════════════════════════');
console.log('  V171-Standard-06 性能监控演示');
console.log('═══════════════════════════════════════════════════════════════');
console.log('');

// ============================================================================
// 初始化
// ============================================================================

const metrics = new MetricsCollector();
const dashboard = new TelemetryDashboard(metrics);
const logger = new StructuredLogger();

// 模拟代理池状态
metrics.updateGauge('activeProxies', 18);
metrics.updateGauge('trippedProxies', 4);
metrics.updateGauge('pendingMatches', 47);

// ============================================================================
// 模拟性能数据
// ============================================================================

console.log('📋 模拟性能数据采集...');
console.log('');

// 模拟 C++ 桥接耗时
const cppTimings = [125, 89, 156, 102, 178, 95, 134, 88, 145, 110];
cppTimings.forEach(ms => metrics.recordTiming('cppBridgeMs', ms));

// 模拟收割耗时
const harvestTimings = [3500, 4200, 3100, 5600, 2800, 4100, 3200, 4500, 2900, 3800];
harvestTimings.forEach(ms => metrics.recordTiming('harvestMs', ms));

// 模拟预测耗时
const predictTimings = [45, 52, 38, 61, 42, 55, 48, 39, 58, 44];
predictTimings.forEach(ms => metrics.recordTiming('predictMs', ms));

// 模拟全流程耗时
const totalTimings = [4500, 5200, 4100, 6800, 3800, 5100, 4200, 5500, 3900, 4800];
totalTimings.forEach(ms => metrics.recordTiming('totalFlowMs', ms));

// 模拟计数器
for (let i = 0; i < 50; i++) {
    metrics.incrementCounter('harvested');
    metrics.incrementCounter('predicted');
}

metrics.incrementCounter('ssrAlerts', 3);
metrics.incrementCounter('errors', 2);
metrics.incrementCounter('skipped', 1);

console.log('✅ 模拟数据已注入');
console.log('');

// ============================================================================
// 启动看板
// ============================================================================

console.log('🚀 启动实时监控看板 (10秒后自动停止)...');
console.log('');

metrics.start();
dashboard.start();

// ============================================================================
// 模拟实时更新
// ============================================================================

let updateCount = 0;

const updateInterval = setInterval(() => {
    updateCount++;

    // 模拟新的收割
    metrics.incrementCounter('harvested');
    metrics.incrementCounter('predicted');

    // 模拟耗时
    metrics.recordTiming('harvestMs', 3000 + Math.random() * 2000);
    metrics.recordTiming('predictMs', 40 + Math.random() * 20);
    metrics.recordTiming('totalFlowMs', 4000 + Math.random() * 3000);

    // 随机更新代理状态
    const active = 15 + Math.floor(Math.random() * 7);
    const tripped = 22 - active;
    metrics.updateGauge('activeProxies', active);
    metrics.updateGauge('trippedProxies', tripped);

    // 偶尔记录错误
    if (updateCount % 5 === 0) {
        metrics.incrementCounter('errors');
        logger.error('模拟错误: 代理连接超时', { proxy: '7891', attempt: updateCount });
    }

}, 3000);

// ============================================================================
// 停止演示
// ============================================================================

setTimeout(() => {
    clearInterval(updateInterval);
    metrics.stop();
    dashboard.stop();

    console.log('');
    console.log('═══════════════════════════════════════════════════════════════');
    console.log('  演示结束 - 最终性能报告');
    console.log('═══════════════════════════════════════════════════════════════');
    console.log('');

    dashboard.printSummary();

    console.log('');
    console.log('📋 日志文件:');
    console.log('   - logs/app.log (全量日志)');
    console.log('   - logs/critical.log (仅 ERROR/CRITICAL)');
    console.log('');

    process.exit(0);
}, 10000);
