/**
 * FotMob 解析器综合测试
 * @module tests/parsers/fotmob/parsers.test
 */

'use strict';

const assert = require('assert');
const {
    // CloudflareDetector
    detectCloudflareBlock,
    detectFromHtml,
    isBlockedStatus,
    comprehensiveCheck,
    CF_INDICATORS,

    // NextDataParser
    extractFromHtml,
    transformToApiFormat,
    validateNextDataStructure,

    // XGExtractor
    extractXG,
    extractPossession,
    parsePossessionValue,
    extractAllStats,
    validateXG
} = require('../../../src/parsers/fotmob');

// ============================================================================
// Mock 数据
// ============================================================================

// 原始 __NEXT_DATA__ 格式（用于 NextDataParser 测试）
const MOCK_NEXT_DATA = {
    props: {
        pageProps: {
            content: {
                stats: {
                    Periods: {
                        All: {
                            stats: [
                                {
                                    title: 'Expected goals',
                                    stats: [
                                        {
                                            key: 'expected_goals',
                                            stats: ['1.5', '0.8']
                                        }
                                    ]
                                },
                                {
                                    title: 'Ball possession',
                                    stats: [
                                        {
                                            key: 'possession',
                                            stats: ['55%', '45%']
                                        }
                                    ]
                                }
                            ]
                        }
                    }
                },
                lineup: { home: [], away: [] },
                shotmap: []
            },
            general: {
                homeTeam: { name: 'Liverpool' },
                awayTeam: { name: 'Chelsea' }
            },
            header: {}
        }
    }
};

// API 格式（用于 XGExtractor 测试）- 直接传给 extractXG
const MOCK_API_DATA = {
    matchId: 'match-123',
    content: {
        stats: {
            Periods: {
                All: {
                    stats: [
                        {
                            title: 'Expected goals',
                            stats: [
                                {
                                    key: 'expected_goals',
                                    stats: ['1.5', '0.8']
                                }
                            ]
                        },
                        {
                            title: 'Ball possession',
                            stats: [
                                {
                                    key: 'possession',
                                    stats: ['55%', '45%']
                                }
                            ]
                        }
                    ]
                }
            }
        }
    },
    general: {},
    header: {}
};

const CF_BLOCKED_HTML = `
<!DOCTYPE html>
<html>
<head><title>Just a moment...</title></head>
<body>
<div class="cf-browser-verification">Checking your browser</div>
</body>
</html>
`;

const NEXT_DATA_HTML = `
<!DOCTYPE html>
<html>
<head><title>Match</title></head>
<body>
<script id="__NEXT_DATA__" type="application/json">
{"props":{"pageProps":{"content":{"stats":{}},"general":{},"header":{}}}}
</script>
</body>
</html>
`;

// ============================================================================
// CloudflareDetector 测试
// ============================================================================

async function testDetectCloudflareBlock() {
    console.log('测试: detectCloudflareBlock');

    // 被拦截的情况
    const blocked = detectCloudflareBlock(CF_BLOCKED_HTML, 'Just a moment...');
    assert.strictEqual(blocked.blocked, true);
    assert.ok(blocked.indicators.length > 0);

    // 正常页面
    const normal = detectCloudflareBlock('<html><body>Normal page</body></html>', 'Match Result');
    assert.strictEqual(normal.blocked, false);
    assert.strictEqual(normal.indicators.length, 0);

    console.log('✅ detectCloudflareBlock 测试通过');
}

async function testDetectFromHtml() {
    console.log('测试: detectFromHtml');

    const result = detectFromHtml(CF_BLOCKED_HTML);
    assert.strictEqual(result.blocked, true);

    const normal = detectFromHtml('<html><body>Normal</body></html>');
    assert.strictEqual(normal.blocked, false);

    // 空输入
    const empty = detectFromHtml(null);
    assert.strictEqual(empty.blocked, false);

    console.log('✅ detectFromHtml 测试通过');
}

async function testIsBlockedStatus() {
    console.log('测试: isBlockedStatus');

    assert.strictEqual(isBlockedStatus(403), true);
    assert.strictEqual(isBlockedStatus(503), true);
    assert.strictEqual(isBlockedStatus(200), false);
    assert.strictEqual(isBlockedStatus(404), false);

    console.log('✅ isBlockedStatus 测试通过');
}

async function testComprehensiveCheck() {
    console.log('测试: comprehensiveCheck');

    // HTTP 403
    const r1 = comprehensiveCheck({ statusCode: 403 });
    assert.strictEqual(r1.blocked, true);
    assert.strictEqual(r1.reason, 'HTTP_403');

    // CF 挑战
    const r2 = comprehensiveCheck({ content: CF_BLOCKED_HTML, title: 'Checking...', statusCode: 200 });
    assert.strictEqual(r2.blocked, true);
    assert.strictEqual(r2.reason, 'CF_CHALLENGE');

    // 正常
    const r3 = comprehensiveCheck({ content: 'Normal content', title: 'Match', statusCode: 200 });
    assert.strictEqual(r3.blocked, false);

    console.log('✅ comprehensiveCheck 测试通过');
}

// ============================================================================
// NextDataParser 测试
// ============================================================================

async function testExtractFromHtml() {
    console.log('测试: extractFromHtml');

    // 成功提取
    const result = extractFromHtml(NEXT_DATA_HTML);
    assert.strictEqual(result.success, true);
    assert.ok(result.data);
    assert.ok(result.data.props);

    // 无数据
    const noData = extractFromHtml('<html><body>No data</body></html>');
    assert.strictEqual(noData.success, false);
    assert.ok(noData.error.includes('NO_NEXT_DATA'));

    // 空输入
    const empty = extractFromHtml(null);
    assert.strictEqual(empty.success, false);

    console.log('✅ extractFromHtml 测试通过');
}

async function testTransformToApiFormat() {
    console.log('测试: transformToApiFormat');

    const apiData = transformToApiFormat(MOCK_NEXT_DATA, 'match-123');

    assert.strictEqual(apiData.matchId, 'match-123');
    assert.ok(apiData.content);
    assert.ok(apiData.general);
    assert.strictEqual(apiData._meta.source, 'web_infiltration');
    assert.strictEqual(apiData._meta.hasStats, true);

    // 无效数据
    const invalid = transformToApiFormat(null, 'match-456');
    assert.strictEqual(invalid, null);

    const noContent = transformToApiFormat({ props: { pageProps: {} } }, 'match-789');
    assert.strictEqual(noContent, null);

    console.log('✅ transformToApiFormat 测试通过');
}

async function testValidateNextDataStructure() {
    console.log('测试: validateNextDataStructure');

    // 完整结构
    const valid = validateNextDataStructure(MOCK_NEXT_DATA);
    assert.strictEqual(valid.valid, true);
    assert.strictEqual(valid.missing.length, 0);

    // 缺少 props
    const noProps = validateNextDataStructure({});
    assert.strictEqual(noProps.valid, false);
    assert.ok(noProps.missing.includes('props'));

    // 缺少 content
    const noContent = validateNextDataStructure({ props: { pageProps: {} } });
    assert.strictEqual(noContent.valid, false);

    // null
    const nullData = validateNextDataStructure(null);
    assert.strictEqual(nullData.valid, false);

    console.log('✅ validateNextDataStructure 测试通过');
}

// ============================================================================
// XGExtractor 测试
// ============================================================================

async function testExtractXG() {
    console.log('测试: extractXG');

    // 使用 API 格式的 Mock 数据
    const result = extractXG(MOCK_API_DATA);

    assert.strictEqual(result.xg_home, 1.5);
    assert.strictEqual(result.xg_away, 0.8);
    assert.strictEqual(result.hasXG, true);

    // 无数据
    const empty = extractXG({});
    assert.strictEqual(empty.hasXG, false);
    assert.strictEqual(empty.xg_home, null);

    console.log('✅ extractXG 测试通过');
}

async function testExtractPossession() {
    console.log('测试: extractPossession');

    // 使用 API 格式的 Mock 数据
    const result = extractPossession(MOCK_API_DATA);

    assert.strictEqual(result.possession_home, 0.55);
    assert.strictEqual(result.possession_away, 0.45);
    assert.strictEqual(result.hasPossession, true);

    console.log('✅ extractPossession 测试通过');
}

async function testParsePossessionValue() {
    console.log('测试: parsePossessionValue');

    assert.strictEqual(parsePossessionValue('55%'), 0.55);
    assert.strictEqual(parsePossessionValue('45%'), 0.45);
    assert.strictEqual(parsePossessionValue(0.6), 0.6);
    assert.strictEqual(parsePossessionValue(60), 0.6);
    assert.strictEqual(parsePossessionValue(null), null);
    assert.strictEqual(parsePossessionValue('invalid'), null);

    console.log('✅ parsePossessionValue 测试通过');
}

async function testExtractAllStats() {
    console.log('测试: extractAllStats');

    // 使用 API 格式的 Mock 数据
    const result = extractAllStats(MOCK_API_DATA);

    assert.strictEqual(result.xg_home, 1.5);
    assert.strictEqual(result.xg_away, 0.8);
    assert.strictEqual(result.possession_home, 0.55);
    assert.strictEqual(result.hasAnyStats, true);

    console.log('✅ extractAllStats 测试通过');
}

async function testValidateXG() {
    console.log('测试: validateXG');

    // 正常值
    const r1 = validateXG(1.5, 0.8);
    assert.strictEqual(r1.valid, true);
    assert.strictEqual(r1.warnings.length, 0);

    // 缺失值
    const r2 = validateXG(null, null);
    assert.strictEqual(r2.valid, true);  // 缺失不算无效
    assert.ok(r2.warnings.length > 0);

    // 负数
    const r3 = validateXG(-1, 0.5);
    assert.strictEqual(r3.valid, false);

    // 异常高
    const r4 = validateXG(15, 0.5);
    assert.strictEqual(r4.valid, false);

    console.log('✅ validateXG 测试通过');
}

// ============================================================================
// 运行测试
// ============================================================================

async function runTests() {
    console.log('\n========================================');
    console.log('FotMob 解析器综合测试');
    console.log('========================================\n');

    try {
        // CloudflareDetector
        console.log('\n--- CloudflareDetector ---');
        await testDetectCloudflareBlock();
        await testDetectFromHtml();
        await testIsBlockedStatus();
        await testComprehensiveCheck();

        // NextDataParser
        console.log('\n--- NextDataParser ---');
        await testExtractFromHtml();
        await testTransformToApiFormat();
        await testValidateNextDataStructure();

        // XGExtractor
        console.log('\n--- XGExtractor ---');
        await testExtractXG();
        await testExtractPossession();
        await testParsePossessionValue();
        await testExtractAllStats();
        await testValidateXG();

        console.log('\n========================================');
        console.log('✅ 所有 FotMob 解析器测试通过');
        console.log('========================================\n');

    } catch (error) {
        console.error('\n❌ 测试失败:', error.message);
        console.error(error.stack);
        process.exit(1);
    }
}

// 入口
runTests();
