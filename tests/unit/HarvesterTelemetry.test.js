'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');

const { HarvesterTelemetry } = require('../../src/infrastructure/harvesters/components/HarvesterTelemetry');

describe('HarvesterTelemetry 单元测试', () => {
    it('应在多 Worker 并发下准确累计统计', async () => {
        const telemetry = new HarvesterTelemetry();

        await Promise.all([
            Promise.resolve().then(() => telemetry.recordSuccess()),
            Promise.resolve().then(() => telemetry.recordSuccess()),
            Promise.resolve().then(() => telemetry.recordFailure()),
            Promise.resolve().then(() => telemetry.recordRetry()),
            Promise.resolve().then(() => telemetry.recordRetry())
        ]);

        const stats = telemetry.getStats();
        assert.strictEqual(stats.processed, 3);
        assert.strictEqual(stats.success, 2);
        assert.strictEqual(stats.failed, 1);
        assert.strictEqual(stats.retries, 2);
    });

    it('应正确上报 metrics', () => {
        const calls = [];
        const telemetry = new HarvesterTelemetry({
            metricsClient: {
                recordHarvestStart: (...args) => calls.push(['start', ...args]),
                recordHarvestSuccess: (...args) => calls.push(['success', ...args]),
                recordHarvestFailure: (...args) => calls.push(['failure', ...args]),
            }
        });

        telemetry.recordHarvestStart('m1', 1);
        telemetry.recordHarvestSuccess('m1', 1, 1200, 2048, 7890);
        telemetry.recordHarvestFailure('m2', 2, 'TIMEOUT', 'timeout', 7891);

        assert.deepStrictEqual(calls, [
            ['start', 'm1', 1],
            ['success', 'm1', 1, 1200, 2048, 7890],
            ['failure', 'm2', 2, 'TIMEOUT', 'timeout', 7891]
        ]);
    });

    it('应生成符合预期格式的摘要报告', () => {
        const telemetry = new HarvesterTelemetry();
        telemetry.replaceStats({
            total: 100,
            processed: 95,
            success: 90,
            failed: 5,
            retries: 10,
            sweepRounds: 2
        });
        telemetry.setStartTime(Date.now() - 60000);

        const workerIdentities = new Map([
            [1, {
                proxy: { port: 7890 },
                requestCount: 20,
                getSuccessRate: () => 0.95
            }]
        ]);

        const lines = telemetry.generateHarvestSummary({
            harvesterName: 'AbstractHarvester',
            maxWorkers: 4,
            now: telemetry.startTime + 60000,
            contextStats: {
                totalCreations: 5,
                totalReuses: 10,
                totalEvictions: 1
            },
            workerIdentities
        });

        assert.ok(lines[0].includes('═'));
        assert.ok(lines.some(line => line.includes('AbstractHarvester 收割完成报告')));
        assert.ok(lines.some(line => line.includes('总计: 100 场')));
        assert.ok(lines.some(line => line.includes('成功率: 90.0%')));
        assert.ok(lines.some(line => line.includes('重试次数: 10')));
        assert.ok(lines.some(line => line.includes('Context 池: 创建=5 复用=10')));
        assert.ok(lines.some(line => line.includes('W1: Port 7890 | 20 请求 | 95% 成功率')));
    });
});
