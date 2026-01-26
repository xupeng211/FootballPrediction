/**
 * V51.000 Integration Tests
 * =========================
 *
 * 综合攻坚逻辑测试：
 *   - 动作 A: 穿透加载
 *   - 动作 B: 契约校验
 *   - 动作 C: DOM 审计
 *   - 输出协议: [JSON_RESULT]
 *
 * @module test_v51_integration
 * @version V51.000
 * @since 2026-01-25
 */

'use strict';

const assert = require('assert');
const parserV51 = require('../modules/parser_v51');
const logger = require('../modules/logger');

const log = logger.createLogger('test_v51');

// ============================================================================
// TEST FIXTURES
// ============================================================================

const FIXTURES = {
    // 完整双点采样 HTML
    fullDualPointHTML: `
        <div class="height-content absolute bottom-[30px] z-10 flex w-max flex-col gap-2 bg-gray-med_light pb-2 pl-2 pr-2 pt-2 text-[10px] text-black-main shadow-xl">
            <h3 class="text-sm font-semibold uppercase leading-4 text-[#2F2F2F]">Odds movement</h3>
            <div class="flex flex-row gap-3">
                <div class="flex flex-col gap-1">
                    <div class="flex gap-3">
                        <div class="text-[10px] font-normal">24 Jan, 10:00</div>
                    </div>
                </div>
                <div class="flex flex-col gap-1">
                    <div class="text-[10px] font-bold">1.95</div>
                </div>
                <div class="flex flex-col gap-1">
                    <div class="text-[10px] font-bold text-green-dark">+0.05</div>
                </div>
            </div>
            <div class="mt-2 gap-1">
                <div class="text-[10px] font-bold">Opening odds: 1.90</div>
            </div>
        </div>
    `,

    // 单点采样 HTML (需要回退)
    singlePointHTML: `
        <div class="height-content absolute bottom-[30px] z-10 flex w-max flex-col gap-2">
            <h3 class="text-sm font-semibold uppercase leading-4">Odds movement</h3>
            <div class="flex flex-row gap-3">
                <div class="flex flex-col gap-1">
                    <div class="text-[10px] font-normal">24 Jan, 10:00</div>
                </div>
                <div class="flex flex-col gap-1">
                    <div class="text-[10px] font-bold">1.95</div>
                </div>
            </div>
        </div>
    `,

    // 无效 HTML (无锚点)
    invalidHTML: `
        <div class="some-class">
            <p>No odds movement here</p>
        </div>
    `
};

// ============================================================================
// TEST SUITES
// ============================================================================

/**
 * 测试套件 1: 动作 B - 契约校验
 */
function testContractValidation() {
    log.info('=== 测试套件 1: 契约校验 ===');

    let passed = 0;
    let failed = 0;

    // 测试 1.1: 有效双点采样
    try {
        const samples = [
            { type: 'Initial', value: 1.90, timestamp: Date.now() },
            { type: 'Current', value: 1.95, timestamp: Date.now() }
        ];
        const result = parserV51.validateContract(samples);
        assert.strictEqual(result.valid, true, '有效双点采样应通过校验');
        log.info('  [PASS] 1.1: 有效双点采样校验');
        passed++;
    } catch (e) {
        log.error(`  [FAIL] 1.1: ${e.message}`);
        failed++;
    }

    // 测试 1.2: 采样密度不足 (单点采样)
    try {
        const samples = [
            { type: 'Initial', value: 1.90, timestamp: Date.now() }
        ];
        const result = parserV51.validateContract(samples);
        assert.strictEqual(result.valid, false, '单点采样应失败');
        // 由于先检查完整性，单点采样会返回 "双点采样不完整" 错误
        assert.ok(result.error.includes('采样密度不足') || result.error.includes('不完整'), '应返回密度不足或不完整错误');
        log.info('  [PASS] 1.2: 采样密度不足校验');
        passed++;
    } catch (e) {
        log.error(`  [FAIL] 1.2: ${e.message}`);
        failed++;
    }

    // 测试 1.3: 缺少 Initial
    try {
        const samples = [
            { type: 'Current', value: 1.95, timestamp: Date.now() }
        ];
        const result = parserV51.validateContract(samples);
        assert.strictEqual(result.valid, false, '缺少 Initial 应失败');
        assert.ok(result.error.includes('Initial') || result.error.includes('不完整'), '应返回 Initial 缺失错误');
        log.info('  [PASS] 1.3: 缺少 Initial 校验');
        passed++;
    } catch (e) {
        log.error(`  [FAIL] 1.3: ${e.message}`);
        failed++;
    }

    // 测试 1.4: 无效格式
    try {
        const samples = 'invalid';
        const result = parserV51.validateContract(samples);
        assert.strictEqual(result.valid, false, '无效格式应失败');
        log.info('  [PASS] 1.4: 无效格式校验');
        passed++;
    } catch (e) {
        log.error(`  [FAIL] 1.4: ${e.message}`);
        failed++;
    }

    log.info(`契约校验测试: ${passed}/${passed + failed} 通过\n`);
    return { passed, failed };
}

/**
 * 测试套件 2: 双点采样提取
 */
function testDualPointExtraction() {
    log.info('=== 测试套件 2: 双点采样提取 ===');

    let passed = 0;
    let failed = 0;

    // 测试 2.1: 完整双点采样
    try {
        const result = parserV51.extractDualPointFromRow(FIXTURES.fullDualPointHTML);
        assert.strictEqual(result.initial, 1.90, '应提取 Initial = 1.90');
        assert.strictEqual(result.current, 1.95, '应提取 Current = 1.95');
        assert.strictEqual(result.delta, 0.05, '应计算 Delta = 0.05');
        log.info('  [PASS] 2.1: 完整双点采样提取');
        passed++;
    } catch (e) {
        log.error(`  [FAIL] 2.1: ${e.message}`);
        failed++;
    }

    // 测试 2.2: 单点采样
    try {
        const result = parserV51.extractDualPointFromRow(FIXTURES.singlePointHTML);
        assert.strictEqual(result.initial, null, 'Initial 应为 null');
        assert.strictEqual(result.current, 1.95, '应提取 Current = 1.95');
        log.info('  [PASS] 2.2: 单点采样提取');
        passed++;
    } catch (e) {
        log.error(`  [FAIL] 2.2: ${e.message}`);
        failed++;
    }

    log.info(`双点采样提取测试: ${passed}/${passed + failed} 通过\n`);
    return { passed, failed };
}

/**
 * 测试套件 3: HTML 解析
 */
function testHTMLParsing() {
    log.info('=== 测试套件 3: HTML 解析 ===');

    let passed = 0;
    let failed = 0;

    // 测试 3.1: 完整双点采样 HTML 解析
    try {
        const records = parserV51.parseFullTooltipHTMLWithContract(FIXTURES.fullDualPointHTML, 'test_provider');
        assert.ok(records.length >= 1, '应至少解析 1 条记录');
        const record = records[0];
        assert.ok(record.dual_point_sampling.valid, '双点采样应有效');
        assert.strictEqual(record.dual_point_sampling.initial, 1.90, 'Initial 应为 1.90');
        assert.strictEqual(record.dual_point_sampling.current, 1.95, 'Current 应为 1.95');
        log.info('  [PASS] 3.1: 完整 HTML 解析');
        passed++;
    } catch (e) {
        log.error(`  [FAIL] 3.1: ${e.message}`);
        failed++;
    }

    // 测试 3.2: 单点采样 HTML 解析 (应使用回退)
    try {
        const records = parserV51.parseFullTooltipHTMLWithContract(FIXTURES.singlePointHTML, 'test_provider');
        assert.ok(records.length >= 1, '应至少解析 1 条记录');
        const record = records[0];
        assert.strictEqual(record.dual_point_sampling.valid, false, '双点采样应无效');
        assert.strictEqual(record.dual_point_sampling.fallback, true, '应使用回退模式');
        log.info('  [PASS] 3.2: 单点 HTML 回退解析');
        passed++;
    } catch (e) {
        log.error(`  [FAIL] 3.2: ${e.message}`);
        failed++;
    }

    // 测试 3.3: 无效 HTML 解析 (应抛出错误)
    try {
        assert.throws(() => {
            parserV51.parseFullTooltipHTMLWithContract(FIXTURES.invalidHTML, 'test_provider');
        }, /ANCHOR_NOT_FOUND/);
        log.info('  [PASS] 3.3: 无效 HTML 错误处理');
        passed++;
    } catch (e) {
        log.error(`  [FAIL] 3.3: ${e.message}`);
        failed++;
    }

    // 测试 3.4: 空输入
    try {
        assert.throws(() => {
            parserV51.parseFullTooltipHTMLWithContract('', 'test_provider');
        }, /INVALID_INPUT/);
        log.info('  [PASS] 3.4: 空输入错误处理');
        passed++;
    } catch (e) {
        log.error(`  [FAIL] 3.4: ${e.message}`);
        failed++;
    }

    log.info(`HTML 解析测试: ${passed}/${passed + failed} 通过\n`);
    return { passed, failed };
}

/**
 * 测试套件 4: JSON_RESULT 协议
 */
function testJsonResultProtocol() {
    log.info('=== 测试套件 4: JSON_RESULT 协议 ===');

    let passed = 0;
    let failed = 0;

    // 测试 4.1: 格式化输出
    try {
        const records = parserV51.parseFullTooltipHTMLWithContract(FIXTURES.fullDualPointHTML, 'test_provider');
        const jsonResult = parserV51.formatJsonResult(records, { provider: 'test_provider' });

        assert.ok(jsonResult.startsWith('[JSON_RESULT]'), '应以 [JSON_RESULT] 开头');
        assert.ok(jsonResult.endsWith('[JSON_RESULT]'), '应以 [JSON_RESULT] 结尾');
        log.info('  [PASS] 4.1: JSON_RESULT 格式化');
        passed++;
    } catch (e) {
        log.error(`  [FAIL] 4.1: ${e.message}`);
        failed++;
    }

    // 测试 4.2: 解析 JSON_RESULT
    try {
        const records = parserV51.parseFullTooltipHTMLWithContract(FIXTURES.fullDualPointHTML, 'test_provider');
        const jsonResult = parserV51.formatJsonResult(records);
        const parsed = parserV51.parseJsonResult(jsonResult);

        assert.ok(parsed, '应成功解析 JSON_RESULT');
        assert.strictEqual(parsed.version, 'V51.000', '版本应为 V51.000');
        assert.ok(parsed.data, '应包含 data 字段');
        assert.ok(parsed.stats, '应包含 stats 字段');
        assert.strictEqual(parsed.stats.totalRecords, records.length, '记录数应匹配');
        log.info('  [PASS] 4.2: JSON_RESULT 解析');
        passed++;
    } catch (e) {
        log.error(`  [FAIL] 4.2: ${e.message}`);
        failed++;
    }

    // 测试 4.3: 无效 JSON_RESULT 解析
    try {
        const parsed = parserV51.parseJsonResult('invalid format');
        assert.strictEqual(parsed, null, '无效格式应返回 null');
        log.info('  [PASS] 4.3: 无效 JSON_RESULT 处理');
        passed++;
    } catch (e) {
        log.error(`  [FAIL] 4.3: ${e.message}`);
        failed++;
    }

    // 测试 4.4: 完整流程 (解析 + 格式化)
    try {
        const jsonResult = parserV51.parseAndFormat(FIXTURES.fullDualPointHTML, 'test_provider');
        const parsed = parserV51.parseJsonResult(jsonResult);

        assert.ok(parsed, '应成功解析');
        assert.ok(parsed.stats.contractValidated > 0, '应有契约验证通过的记录');
        log.info('  [PASS] 4.4: 完整流程');
        passed++;
    } catch (e) {
        log.error(`  [FAIL] 4.4: ${e.message}`);
        failed++;
    }

    log.info(`JSON_RESULT 协议测试: ${passed}/${passed + failed} 通过\n`);
    return { passed, failed };
}

/**
 * 测试套件 5: 时间校准
 */
function testTimestampCalibration() {
    log.info('=== 测试套件 5: 时间校准 ===');

    let passed = 0;
    let failed = 0;

    // 测试 5.1: 标准格式
    try {
        const timestamp = parserV51.calibrateTimestamp('24 Jan, 10:00');
        assert.ok(timestamp, '应成功解析时间');
        assert.ok(timestamp.includes('T'), '应返回 ISO 格式');
        log.info('  [PASS] 5.1: 标准时间格式解析');
        passed++;
    } catch (e) {
        log.error(`  [FAIL] 5.1: ${e.message}`);
        failed++;
    }

    // 测试 5.2: 空输入
    try {
        const timestamp = parserV51.calibrateTimestamp('');
        assert.strictEqual(timestamp, null, '空输入应返回 null');
        log.info('  [PASS] 5.2: 空输入处理');
        passed++;
    } catch (e) {
        log.error(`  [FAIL] 5.2: ${e.message}`);
        failed++;
    }

    // 测试 5.3: 无效格式
    try {
        const timestamp = parserV51.calibrateTimestamp('invalid time');
        assert.strictEqual(timestamp, null, '无效格式应返回 null');
        log.info('  [PASS] 5.3: 无效格式处理');
        passed++;
    } catch (e) {
        log.error(`  [FAIL] 5.3: ${e.message}`);
        failed++;
    }

    log.info(`时间校准测试: ${passed}/${passed + failed} 通过\n`);
    return { passed, failed };
}

// ============================================================================
// MAIN TEST RUNNER
// ============================================================================

/**
 * 运行所有测试套件
 */
function runAllTests() {
    log.info('========================================');
    log.info('V51.000 综合攻坚逻辑测试');
    log.info('========================================\n');

    const startTime = Date.now();

    const results = {
        contractValidation: testContractValidation(),
        dualPointExtraction: testDualPointExtraction(),
        htmlParsing: testHTMLParsing(),
        jsonResultProtocol: testJsonResultProtocol(),
        timestampCalibration: testTimestampCalibration()
    };

    const duration = Date.now() - startTime;

    // 汇总结果
    let totalPassed = 0;
    let totalFailed = 0;

    for (const [suite, result] of Object.entries(results)) {
        totalPassed += result.passed;
        totalFailed += result.failed;
    }

    // 最终报告
    log.info('========================================');
    log.info('最终测试报告');
    log.info('========================================');
    log.info(`契约校验: ${results.contractValidation.passed}/${results.contractValidation.passed + results.contractValidation.failed}`);
    log.info(`双点采样提取: ${results.dualPointExtraction.passed}/${results.dualPointExtraction.passed + results.dualPointExtraction.failed}`);
    log.info(`HTML 解析: ${results.htmlParsing.passed}/${results.htmlParsing.passed + results.htmlParsing.failed}`);
    log.info(`JSON_RESULT 协议: ${results.jsonResultProtocol.passed}/${results.jsonResultProtocol.passed + results.jsonResultProtocol.failed}`);
    log.info(`时间校准: ${results.timestampCalibration.passed}/${results.timestampCalibration.passed + results.timestampCalibration.failed}`);
    log.info('========================================');
    log.info(`总计: ${totalPassed}/${totalPassed + totalFailed} 通过`);
    log.info(`耗时: ${duration}ms`);
    log.info('========================================\n');

    // 退出标准
    const allPassed = totalFailed === 0;
    if (allPassed) {
        log.info('✓ 所有测试通过 - V51.000 模块就绪');
    } else {
        log.warn(`✗ ${totalFailed} 个测试失败`);
    }

    return {
        success: allPassed,
        totalPassed,
        totalFailed,
        duration,
        results
    };
}

// ============================================================================
// CLI ENTRY POINT
// ============================================================================

if (require.main === module) {
    const result = runAllTests();
    process.exit(result.success ? 0 : 1);
}

module.exports = {
    runAllTests,
    testContractValidation,
    testDualPointExtraction,
    testHTMLParsing,
    testJsonResultProtocol,
    testTimestampCalibration,
    FIXTURES
};
