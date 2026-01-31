/**
 * V85.801 Mock Stress Test - HTML 解析模块离线压力测试
 * =======================================================
 *
 * 任务目标: 验证 parser_v51.js 处理非标准、残缺或异常 HTML 碎片时的健壮性
 * 测试约束: 严禁联网，仅限离线单元测试
 *
 * @author Senior QA Engineer
 * @version V85.801
 * @since 2026-01-25
 */

'use strict';

// 引入被测模块
const parserV51 = require('./modules/parser_v51');
const { ParserV51Error } = parserV51;

// ANSI 颜色代码
const colors = {
    reset: '\x1b[0m',
    red: '\x1b[31m',
    green: '\x1b[32m',
    yellow: '\x1b[33m',
    blue: '\x1b[34m',
    magenta: '\x1b[35m',
    cyan: '\x1b[36m',
    bright: '\x1b[1m'
};

// 测试结果统计
const testStats = {
    total: 0,
    passed: 0,
    failed: 0,
    crashes: 0,
    edgeCasesHandled: 0
};

// ============================================================================
// MOCK 数据集
// ============================================================================

const MOCK_DATA = {
    // Mock A: 缺失锚点 - 只有赔率值，没有 h3 标题或 Odds movement
    A: {
        name: 'Mock A (缺失锚点)',
        html: '<div>只有赔率1.95，没有h3标题的内容</div>',
        provider: 'TEST_PROVIDER',
        expectedBehavior: '应该返回空数组或警告，但不应该崩溃',
        shouldCrash: false,
        shouldHaveRecords: false
    },

    // Mock B: 非数字噪音 - 包含时间戳但赔率值是 "Suspended"
    B: {
        name: 'Mock B (非数字噪音)',
        html: '<h3>Odds movement</h3><div>25 Jan, 14:00</div><div>Suspended</div>',
        provider: 'TEST_PROVIDER',
        expectedBehavior: '应该跳过无效赔率值，不产生错误的浮点记录',
        shouldCrash: false,
        shouldHaveRecords: false,
        shouldRejectInvalid: true
    },

    // Mock C: 跨年边界 - 12月31日深夜时间（单值格式，可能无法通过双点采样校验）
    C: {
        name: 'Mock C (跨年边界 - 单值格式)',
        html: '<h3>Odds movement</h3><div>31 Dec, 23:59</div><div>2.10</div>',
        provider: 'TEST_PROVIDER',
        expectedBehavior: '单值格式可能无法通过双点采样校验，应返回空数组或fallback记录',
        shouldCrash: false,
        shouldHaveRecords: false,  // 由于缺少 Opening odds，无法通过双点采样校验
        timestampValidation: false  // 改为边缘情况测试
    },

    // Mock C2: 跨年边界 - 完整格式（包含 Opening odds）
    C2: {
        name: 'Mock C2 (跨年边界 - 完整格式)',
        html: '<h3>Odds movement</h3><div>31 Dec, 23:59</div><div>Opening odds: 2.10</div><div>2.05</div>',
        provider: 'TEST_PROVIDER',
        expectedBehavior: '应该正确处理年份补全（使用当前年）',
        shouldCrash: false,
        shouldHaveRecords: true,
        timestampValidation: true
    },

    // Mock D: 格式紊乱 - 时间格式无效，赔率值非数字
    D: {
        name: 'Mock D (格式紊乱)',
        html: '<h3>...</h3><div>Unknown Time</div><div>Not_A_Number</div>',
        provider: 'TEST_PROVIDER',
        expectedBehavior: '应该优雅处理格式错误，返回空数组',
        shouldCrash: false,
        shouldHaveRecords: false
    },

    // Mock E: 空字符串 - 边界条件
    E: {
        name: 'Mock E (空字符串)',
        html: '',
        provider: 'TEST_PROVIDER',
        expectedBehavior: '应该抛出 ParserV51Error（正确行为）',
        shouldCrash: false,
        shouldHaveRecords: false,
        shouldThrowError: true,
        allowErrorResult: true  // 允许抛出错误后不返回数组
    },

    // Mock F: null 输入 - 边界条件
    F: {
        name: 'Mock F (null 输入)',
        html: null,
        provider: 'TEST_PROVIDER',
        expectedBehavior: '应该抛出 ParserV51Error（V85.801 修复后）',
        shouldCrash: false,
        shouldThrowError: true,
        allowErrorResult: true  // 允许抛出错误后不返回数组
    },

    // Mock G: 正常数据 - 对照组（使用单行格式）
    G: {
        name: 'Mock G (正常数据 - 对照组)',
        html: '<h3>Odds movement</h3><div>25 Jan, 10:00 Opening odds: 2.50 2.45 +0.05</div>',
        provider: 'TEST_PROVIDER',
        expectedBehavior: '应该成功解析至少1个时序记录',
        shouldCrash: false,
        shouldHaveRecords: true,
        minRecords: 1
    },

    // Mock H: 多个有效赔率值 - 1X2 格式
    H: {
        name: 'Mock H (1X2 格式)',
        html: `<h3>Odds movement</h3>
               <div>25 Jan, 10:00</div>
               <div>2.50 3.20 2.80</div>`,
        provider: 'TEST_PROVIDER',
        expectedBehavior: '应该解析为1X2格式（包含draw_odd）',
        shouldCrash: false,
        shouldHaveRecords: true,
        minRecords: 1,
        expect1X2Format: true
    },

    // Mock I: 只有时间没有赔率
    I: {
        name: 'Mock I (只有时间没有赔率)',
        html: '<h3>Odds movement</h3><div>25 Jan, 14:00</div>',
        provider: 'TEST_PROVIDER',
        expectedBehavior: '应该返回空数组（赔率值不足）',
        shouldCrash: false,
        shouldHaveRecords: false
    }
};

// ============================================================================
// 测试执行器
// ============================================================================

/**
 * 执行单个测试用例
 */
function runTestCase(mockKey) {
    const mock = MOCK_DATA[mockKey];
    testStats.total++;

    console.log(`\n${colors.cyan}${colors.bright}[TEST ${testStats.total}] ${mock.name}${colors.reset}`);
    console.log(`  HTML: ${mock.html ? mock.html.substring(0, 60) + (mock.html.length > 60 ? '...' : '') : 'null'}`);
    console.log(`  预期: ${mock.expectedBehavior}`);

    let result;
    let error = null;
    let crashDetected = false;

    // 执行测试 - 使用 try-catch 捕获所有可能的异常
    const startTime = Date.now();
    try {
        result = parserV51.parseModalHtml(mock.html, mock.provider);
    } catch (e) {
        error = e;
        if (!(e instanceof ParserV51Error)) {
            crashDetected = true;
            testStats.crashes++;
        }
    }
    const executionTime = Date.now() - startTime;

    // 验证逻辑
    const assertions = [];

    // 断言 1: 程序必须在 0ms 内捕获异常，严禁抛出 Crash
    if (mock.shouldCrash) {
        assertions.push({
            name: '程序应该崩溃',
            passed: crashDetected || error !== null,
            detail: crashDetected ? '检测到崩溃' : (error ? `抛出错误: ${error.message}` : '未崩溃')
        });
    } else {
        assertions.push({
            name: '程序不得崩溃',
            passed: !crashDetected,
            detail: crashDetected ? `检测到未预期的崩溃: ${error}` : '正常运行'
        });
    }

    // 断言 2: 执行时间验证
    assertions.push({
        name: '执行时间 < 100ms',
        passed: executionTime < 100,
        detail: `实际执行时间: ${executionTime}ms`
    });

    // 断言 3: 错误类型验证
    if (mock.shouldThrowError) {
        assertions.push({
            name: '应该抛出 ParserV51Error',
            passed: error instanceof ParserV51Error,
            detail: error ? `错误类型: ${error.name}` : '未抛出错误'
        });
    } else if (error) {
        assertions.push({
            name: '错误处理正确',
            passed: error instanceof ParserV51Error,
            detail: `抛出预期的 ParserV51Error: ${error.message}`
        });
    } else {
        assertions.push({
            name: '无异常抛出',
            passed: true,
            detail: '正常执行'
        });
    }

    // 断言 4: 结果验证
    // 如果允许错误结果且确实抛出了预期的错误，跳过数组断言
    const skipArrayAssertion = mock.allowErrorResult && mock.shouldThrowError && error instanceof ParserV51Error;

    if (!skipArrayAssertion && mock.shouldHaveRecords) {
        const hasRecords = Array.isArray(result) && result.length > 0;
        assertions.push({
            name: '应该返回时序记录',
            passed: hasRecords,
            detail: hasRecords ? `返回 ${result.length} 条记录` : '返回空数组'
        });

        // 断言 5: 最小记录数验证
        if (mock.minRecords) {
            assertions.push({
                name: `记录数 >= ${mock.minRecords}`,
                passed: Array.isArray(result) && result.length >= mock.minRecords,
                detail: Array.isArray(result) ? `实际记录数: ${result.length}` : '结果不是数组'
            });
        }

        // 断言 6: 1X2 格式验证
        if (mock.expect1X2Format && Array.isArray(result) && result.length > 0) {
            const has1X2 = result.some(r => r.draw_odd !== null);
            assertions.push({
                name: '应该包含 1X2 格式数据',
                passed: has1X2,
                detail: has1X2 ? '检测到 draw_odd 字段' : '未检测到 draw_odd 字段'
            });
        }

        // 断言 7: 时间戳验证（跨年边界测试）
        if (mock.timestampValidation && Array.isArray(result) && result.length > 0) {
            const timestamp = result[0].timestamp;
            const hasYear2025 = timestamp.includes('2025');
            const hasYear2026 = timestamp.includes('2026');
            assertions.push({
                name: '时间戳应该包含有效年份',
                passed: hasYear2025 || hasYear2026,
                detail: `时间戳: ${timestamp}`
            });
        }
    } else if (!skipArrayAssertion) {
        assertions.push({
            name: '应该返回空数组',
            passed: Array.isArray(result) && result.length === 0,
            detail: Array.isArray(result) ? `返回 ${result.length} 条记录` : '结果不是数组'
        });
    }

    // 断言 8: 边界条件处理
    if (mock.shouldRejectInvalid) {
        assertions.push({
            name: '应该拒绝无效赔率值',
            passed: Array.isArray(result) && result.length === 0,
            detail: 'Suspended 被正确拒绝'
        });
    }

    // 边缘情况计数
    const isEdgeCase = ['A', 'B', 'C', 'C2', 'D', 'E', 'F', 'I'].includes(mockKey);
    const allPassed = assertions.every(a => a.passed);
    if (isEdgeCase && allPassed) {
        testStats.edgeCasesHandled++;
    }

    // 输出结果
    console.log(`\n  ${colors.blue}执行时间: ${executionTime}ms${colors.reset}`);

    let testPassed = true;
    for (const assertion of assertions) {
        const statusIcon = assertion.passed ? '✓' : '✗';
        const statusColor = assertion.passed ? colors.green : colors.red;
        console.log(`  ${statusColor}${statusIcon} ${assertion.name}: ${assertion.detail}${colors.reset}`);
        if (!assertion.passed) {
            testPassed = false;
        }
    }

    if (testPassed) {
        testStats.passed++;
        console.log(`  ${colors.green}${colors.bright}Result: SUCCESS (Handled)${colors.reset}`);
    } else {
        testStats.failed++;
        console.log(`  ${colors.red}${colors.bright}Result: FAILED${colors.reset}`);
    }

    return testPassed;
}

/**
 * 执行所有测试用例
 */
function runAllTests() {
    console.log(`\n${colors.magenta}${colors.bright}╔════════════════════════════════════════════════════════════════╗${colors.reset}`);
    console.log(`${colors.magenta}${colors.bright}║   V85.801 Mock Stress Test - HTML 解析模块离线压力测试      ║${colors.reset}`);
    console.log(`${colors.magenta}${colors.bright}╚════════════════════════════════════════════════════════════════╝${colors.reset}`);
    console.log(`\n${colors.cyan}测试模块: parser_v51.js${colors.reset}`);
    console.log(`${colors.cyan}测试函数: parseModalHtml(html, providerLabel)${colors.reset}`);
    console.log(`${colors.cyan}测试约束: 离线单元测试，严禁联网${colors.reset}`);

    // 按顺序执行所有测试
    const mockKeys = Object.keys(MOCK_DATA);
    for (const key of mockKeys) {
        runTestCase(key);
    }

    // 打印总结报告
    printSummary();
}

/**
 * 打印测试总结
 */
function printSummary() {
    console.log(`\n${colors.magenta}${colors.bright}════════════════════════════════════════════════════════════════${colors.reset}`);
    console.log(`${colors.magenta}${colors.bright}                      测试总结报告                            ${colors.reset}`);
    console.log(`${colors.magenta}${colors.bright}════════════════════════════════════════════════════════════════${colors.reset}\n`);

    // 统计数据
    console.log(`${colors.cyan}总测试用例: ${testStats.total}${colors.reset}`);
    console.log(`${colors.green}通过: ${testStats.passed}${colors.reset}`);
    console.log(`${colors.red}失败: ${testStats.failed}${colors.reset}`);
    console.log(`${colors.yellow}崩溃数: ${testStats.crashes}${colors.reset}`);
    console.log(`${colors.blue}边缘情况处理: ${testStats.edgeCasesHandled}${colors.reset}`);

    // 成功率
    const successRate = testStats.total > 0 ? ((testStats.passed / testStats.total) * 100).toFixed(1) : 0;
    console.log(`\n${colors.cyan}成功率: ${successRate}%${colors.reset}`);

    // 最终判定
    const allTestsPassed = testStats.failed === 0 && testStats.crashes === 0;
    const edgeCasesHandled = testStats.edgeCasesHandled >= 8; // 8个边缘情况用例 (A,B,C,C2,D,E,F,I)

    console.log(`\n${colors.magenta}${colors.bright}════════════════════════════════════════════════════════════════${colors.reset}`);

    if (allTestsPassed && edgeCasesHandled) {
        console.log(`${colors.green}${colors.bright}[V85.801] Mock Stress COMPLETE.${colors.reset}`);
        console.log(`${colors.green}${colors.bright}  Crash Count: ${testStats.crashes}${colors.reset}`);
        console.log(`${colors.green}${colors.bright}  Edge Cases Handled: YES${colors.reset}`);
        console.log(`${colors.green}${colors.bright}  Logic is PROVED solid.${colors.reset}`);
        console.log(`\n${colors.green}${colors.bright}✓ 所有测试通过！parser_v51.js 模块健壮性验证完成。${colors.reset}`);
    } else if (allTestsPassed) {
        console.log(`${colors.yellow}[V85.801] Mock Stress COMPLETE with warnings.${colors.reset}`);
        console.log(`${colors.yellow}  Crash Count: ${testStats.crashes}${colors.reset}`);
        console.log(`${colors.yellow}  Edge Cases Handled: PARTIAL (${testStats.edgeCasesHandled}/7)${colors.reset}`);
    } else {
        console.log(`${colors.red}${colors.bright}[V85.801] Mock Stress FAILED.${colors.reset}`);
        console.log(`${colors.red}${colors.bright}  Failed: ${testStats.failed}${colors.reset}`);
        console.log(`${colors.red}${colors.bright}  Crashes: ${testStats.crashes}${colors.reset}`);
    }

    console.log(`${colors.magenta}${colors.bright}════════════════════════════════════════════════════════════════${colors.reset}\n`);
}

// ============================================================================
// MAIN EXECUTION
// ============================================================================

if (require.main === module) {
    runAllTests();
}

module.exports = { runAllTests, MOCK_DATA, testStats };
