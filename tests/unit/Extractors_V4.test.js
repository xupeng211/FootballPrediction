/**
 * Extractors_V4.test.js - V4.0 提取器高压测试套件
 * ==================================================
 *
 * 目标：行覆盖率 90%+
 * 重点：字段缺失、非法数值、深层嵌套 JSON 等极端破坏性场景
 *
 * @module tests/unit/Extractors_V4
 * @version V4.0.0
 * @since 2026-03-14
 */

'use strict';

const assert = require('assert');
const {
    BaseExtractor,
    GoldenExtractor,
    TacticalExtractor,
    ExtractorError,
    ValidationError,
    ExtractionError,
    FEATURE_NAMES
} = require('../../src/feature_engine/smelter/components');

// ============================================================================
// 测试辅助函数
// ============================================================================

/**
 * 创建完整有效的原始数据
 */
function createValidRawData() {
    return {
        content: {
            lineup: {
                homeTeam: {
                    totalStarterMarketValue: 500,  // 500M 欧元
                    starters: [
                        { marketValue: 80, performance: { rating: 7.5 }, age: 25 },
                        { marketValue: 60, performance: { rating: 6.8 }, age: 28 },
                        { marketValue: 45, performance: { rating: 7.2 }, age: 22 }
                    ],
                    unavailable: [
                        { unavailability: { type: 'injury', expectedReturn: 'doubtful' } },
                        { unavailability: { type: 'suspension' } }
                    ]
                },
                awayTeam: {
                    totalStarterMarketValue: 350,
                    starters: [
                        { marketValue: 50, performance: { rating: 6.5 }, age: 30 },
                        { marketValue: 40, performance: { rating: 6.2 }, age: 27 }
                    ],
                    unavailable: [
                        { unavailability: { type: 'injury' } }
                    ]
                }
            },
            stats: {
                Periods: {
                    All: {
                        stats: [
                            { title: 'Expected goals', stats: [1.5, 0.8] },
                            { title: 'Ball possession', stats: ['55%', '45%'] },
                            { title: 'Total shots', stats: [12, 8] },
                            { title: 'Corners', stats: [6, 4] },
                            { title: 'Fouls', stats: [10, 12] },
                            { title: 'Yellow cards', stats: [2, 3] }
                        ]
                    }
                }
            },
            momentum: {
                main: {
                    data: [
                        { value: 20 }, { value: 30 }, { value: 25 },
                        { value: 40 }, { value: 35 }, { value: 45 }
                    ]
                }
            }
        },
        header: {
            homeMarketValue: 500,
            awayMarketValue: 350
        }
    };
}

/**
 * 创建损坏/缺失字段的数据
 */
function createCorruptedData(type) {
    const base = createValidRawData();

    switch (type) {
        case 'missing_lineup':
            delete base.content.lineup;
            return base;

        case 'missing_stats':
            delete base.content.stats;
            return base;

        case 'missing_momentum':
            delete base.content.momentum;
            return base;

        case 'null_values':
            base.content.lineup.homeTeam = null;
            return base;

        case 'empty_arrays':
            base.content.lineup.homeTeam.starters = [];
            base.content.lineup.awayTeam.starters = [];
            return base;

        case 'deep_nesting':
            // 深层嵌套测试
            base.content.deep = { nested: { data: { value: 42 } } };
            return base;

        default:
            return base;
    }
}

/**
 * 创建非法数值数据
 */
function createInvalidNumericData() {
    return {
        content: {
            lineup: {
                homeTeam: {
                    totalStarterMarketValue: NaN,
                    starters: [
                        { marketValue: Infinity, performance: { rating: -5 }, age: 'invalid' },
                        { marketValue: -100, performance: { rating: NaN }, age: null }
                    ],
                    unavailable: null
                },
                awayTeam: {
                    totalStarterMarketValue: undefined,
                    starters: 'not_an_array',
                    unavailable: undefined
                }
            },
            stats: {
                Periods: {
                    All: {
                        stats: [
                            { title: 'Expected goals', stats: [NaN, Infinity] },
                            { title: 'Ball possession', stats: ['invalid', null] }
                        ]
                    }
                }
            }
        }
    };
}

// ============================================================================
// BaseExtractor 测试
// ============================================================================

console.log('\n🔧 BaseExtractor 基础协议测试\n');

// 测试 1: 抽象类实例化
{
    console.log('  Test 1.1: 抽象类必须提供名称');
    assert.throws(() => {
        new BaseExtractor({});
    }, /提取器名称必填/, '应抛出名称缺失错误');

    console.log('  ✅ 抽象类名称验证通过');
}

// 测试 2: 抽象方法调用
{
    console.log('  Test 1.2: 抽象方法必须被子类实现');
    const extractor = new BaseExtractor({ name: 'TestExtractor' });

    assert.throws(() => {
        extractor.extract({});
    }, /必须实现 extract 方法/, '应抛出抽象方法错误');

    assert.throws(() => {
        extractor.getFeatureNames();
    }, /必须实现 getFeatureNames 方法/, '应抛出抽象方法错误');

    console.log('  ✅ 抽象方法验证通过');
}

// 测试 3: 数据验证
{
    console.log('  Test 1.3: 数据验证逻辑');
    class TestExtractor extends BaseExtractor {
        constructor() {
            super({
                name: 'TestExtractor',
                requiredFields: ['content.data', 'header.id']
            });
        }
        extract(rawData) { return {}; }
        getFeatureNames() { return ['test_feature']; }
    }

    const extractor = new TestExtractor();

    // 完整数据验证
    const validData = {
        content: { data: 'value' },
        header: { id: 123 }
    };
    const validResult = extractor.validate(validData);
    assert.strictEqual(validResult.valid, true, '应验证通过');
    assert.strictEqual(validResult.completeness, 1.0, '完整度应为 100%');

    // 缺失字段验证
    const invalidData = { content: {} };
    const invalidResult = extractor.validate(invalidData);
    assert.strictEqual(invalidResult.valid, false, '应验证失败');
    assert.ok(invalidResult.missing.includes('content.data'), '应报告缺失字段');

    console.log('  ✅ 数据验证逻辑通过');
}

// 测试 4: 严格验证模式
{
    console.log('  Test 1.4: 严格验证抛出异常');
    class StrictExtractor extends BaseExtractor {
        constructor() {
            super({
                name: 'StrictExtractor',
                requiredFields: ['mandatory.field'],
                config: { strictMode: true }
            });
        }
        extract(rawData) { return {}; }
        getFeatureNames() { return ['feature']; }
    }

    const extractor = new StrictExtractor();

    assert.throws(() => {
        extractor.extractSync({});
    }, ValidationError, '应抛出 ValidationError');

    console.log('  ✅ 严格验证模式通过');
}

// 测试 5: 工具方法
{
    console.log('  Test 1.5: 工具方法');
    const extractor = new BaseExtractor({ name: 'ToolTest' });

    // safeGet
    const obj = { a: { b: { c: 'value' } } };
    assert.strictEqual(extractor.safeGet(obj, 'a.b.c'), 'value');
    assert.strictEqual(extractor.safeGet(obj, 'a.b.x', 'default'), 'default');
    assert.strictEqual(extractor.safeGet(null, 'a'), undefined);

    // isValidNumber
    assert.strictEqual(extractor.isValidNumber(42), true);
    assert.strictEqual(extractor.isValidNumber(NaN), false);
    assert.strictEqual(extractor.isValidNumber(Infinity), false);
    assert.strictEqual(extractor.isValidNumber('42'), false);

    // isValidObject
    assert.strictEqual(extractor.isValidObject({}), true);
    assert.strictEqual(extractor.isValidObject([]), false);
    assert.strictEqual(extractor.isValidObject(null), false);

    console.log('  ✅ 工具方法通过');
}

// 测试 6: 统计功能
{
    console.log('  Test 1.6: 统计信息收集');
    class CountingExtractor extends BaseExtractor {
        constructor() {
            super({ name: 'CountingExtractor' });
        }
        extract(rawData) {
            return { value: 42 };
        }
        getFeatureNames() { return ['value']; }
    }

    const extractor = new CountingExtractor();

    // 多次调用
    extractor.extractSync({});
    extractor.extractSync({});
    extractor.extractSync({ invalid: true }); // 可能失败

    const stats = extractor.getStats();
    assert.strictEqual(stats.name, 'CountingExtractor');
    assert.ok(stats.totalCalls >= 2, '应有调用记录');
    assert.ok(stats.successRate.includes('%'), '应有成功率');

    console.log('  ✅ 统计功能通过');
}

// ============================================================================
// GoldenExtractor 测试
// ============================================================================

console.log('\n🏆 GoldenExtractor 黄金特征提取测试\n');

// 测试 7: 正常提取流程
{
    console.log('  Test 2.1: 正常提取流程');
    const extractor = new GoldenExtractor();
    const rawData = createValidRawData();
    const features = extractor.extract(rawData);

    // 验证关键特征
    assert.ok(features.home_market_value_total > 0, '主队身价应大于 0');
    assert.ok(features.away_market_value_total > 0, '客队身价应大于 0');
    assert.ok(features.home_rating_avg > 0, '主队评分应大于 0');
    assert.ok(features.away_rating_avg > 0, '客队评分应大于 0');
    assert.ok(features.home_injury_count >= 0, '伤病数应 >= 0');

    // 验证对比特征
    assert.ok(typeof features.market_value_gap === 'number', '应有身价差距');
    assert.ok(typeof features.market_value_ratio === 'number', '应有身价比例');

    console.log('  ✅ 正常提取流程通过');
}

// 测试 8: 字段缺失场景
{
    console.log('  Test 2.2: 字段缺失降级处理');
    const extractor = new GoldenExtractor();

    // 缺少 lineup
    const noLineup = createCorruptedData('missing_lineup');
    const features1 = extractor.extract(noLineup);
    // 验证应返回有效对象（可能包含错误或默认值）
    assert.ok(typeof features1 === 'object', '应返回对象');
    assert.ok(typeof features1.home_market_value_total === 'number', '应返回数值');

    // 空数组
    const emptyArrays = createCorruptedData('empty_arrays');
    const features2 = extractor.extract(emptyArrays);
    assert.ok(typeof features2.home_market_value_total === 'number', '应返回数值');

    console.log('  ✅ 字段缺失降级处理通过');
}

// 测试 9: 非法数值处理
{
    console.log('  Test 2.3: 非法数值处理');
    const extractor = new GoldenExtractor();
    const invalidData = createInvalidNumericData();
    const features = extractor.extract(invalidData);

    // 应返回默认值而不是 NaN/Infinity
    assert.ok(!isNaN(features.home_market_value_total), '身价不应为 NaN');
    assert.ok(features.home_market_value_total !== Infinity, '身价不应为 Infinity');

    console.log('  ✅ 非法数值处理通过');
}

// 测试 10: 多路径身价搜索
{
    console.log('  Test 2.4: 多路径身价搜索');
    const extractor = new GoldenExtractor();

    // 策略 1: totalStarterMarketValue
    const data1 = createValidRawData();
    const features1 = extractor.extract(data1);
    assert.strictEqual(features1.home_market_value_source, 'totalStarterMarketValue');

    // 策略 2: starters 数组
    const data2 = createValidRawData();
    delete data2.content.lineup.homeTeam.totalStarterMarketValue;
    const features2 = extractor.extract(data2);
    assert.ok(features2.home_market_value_total > 0, '应能从 starters 提取');

    // 策略 3: header
    const data3 = createValidRawData();
    delete data3.content.lineup.homeTeam.totalStarterMarketValue;
    delete data3.content.lineup.homeTeam.starters;
    const features3 = extractor.extract(data3);
    assert.ok(features3.home_market_value_total > 0, '应能从 header 提取');

    console.log('  ✅ 多路径身价搜索通过');
}

// 测试 11: 特征字段清单
{
    console.log('  Test 2.5: 特征字段清单完整性');
    const extractor = new GoldenExtractor();
    const featureNames = extractor.getFeatureNames();

    assert.ok(featureNames.length > 20, '应有 20+ 个特征字段');
    assert.ok(featureNames.includes('home_market_value_total'), '应包含主队身价');
    assert.ok(featureNames.includes('away_market_value_total'), '应包含客队身价');
    assert.ok(featureNames.includes('market_value_gap'), '应包含身价差距');

    // 验证 FEATURE_NAMES 导出
    assert.ok(FEATURE_NAMES.golden.length > 20, '导出清单应有 20+ 字段');

    console.log('  ✅ 特征字段清单完整性通过');
}

// 测试 12: 元数据
{
    console.log('  Test 2.6: 元数据完整性');
    const extractor = new GoldenExtractor();
    const features = extractor.extractSync(createValidRawData());

    assert.strictEqual(features._extractor, 'GoldenExtractor');
    assert.match(features._version, /^V\d+\./, '版本号应为当前主版本格式');
    assert.ok(features._extractedAt, '应有提取时间戳');

    console.log('  ✅ 元数据完整性通过');
}

// ============================================================================
// TacticalExtractor 测试
// ============================================================================

console.log('\n⚔️ TacticalExtractor 战术动量特征测试\n');

// 测试 13: 正常提取流程
{
    console.log('  Test 3.1: 正常提取流程');
    const extractor = new TacticalExtractor();
    const rawData = createValidRawData();
    const features = extractor.extract(rawData);

    // 验证战术统计
    assert.ok(features.home_xg >= 0, '主队 xG 应 >= 0');
    assert.ok(features.away_xg >= 0, '客队 xG 应 >= 0');
    assert.ok(features.home_shots >= 0, '主队射门应 >= 0');
    assert.ok(features.away_shots >= 0, '客队射门应 >= 0');

    // 验证控球率
    assert.ok(features.home_possession_pct >= 0 && features.home_possession_pct <= 100, '控球率应在 0-100 之间');

    // 验证动量
    assert.ok(features.has_momentum_data, '应有动量数据');
    assert.ok(features.momentum_samples_count > 0, '应有动量样本');

    console.log('  ✅ 正常提取流程通过');
}

// 测试 14: 统计解析
{
    console.log('  Test 3.2: 统计解析（多种格式）');
    const extractor = new TacticalExtractor();

    // 百分比格式
    const data1 = createValidRawData();
    data1.content.stats.Periods.All.stats[1].stats = ['60%', '40%'];
    const features1 = extractor.extract(data1);
    assert.strictEqual(features1.home_possession_pct, 60, '应解析百分比');

    // 数字格式
    const data2 = createValidRawData();
    data2.content.stats.Periods.All.stats[1].stats = [0.6, 0.4];
    const features2 = extractor.extract(data2);
    assert.ok(features2.home_possession_pct === 60 || features2.home_possession_pct === 0.6, '应解析数字');

    console.log('  ✅ 统计解析通过');
}

// 测试 15: 动量分析
{
    console.log('  Test 3.3: 动量时间序列分析');
    const extractor = new TacticalExtractor();
    const features = extractor.extract(createValidRawData());

    // 6 个时段
    assert.ok(typeof features.momentum_seg1_dominance === 'number', '应有时段 1 支配度');
    assert.ok(typeof features.momentum_seg6_dominance === 'number', '应有时段 6 支配度');

    // 方向判断
    assert.ok(['home_dominant', 'away_dominant', 'balanced', 'unknown'].includes(features.momentum_direction), '应有有效方向');

    console.log('  ✅ 动量时间序列分析通过');
}

// 测试 16: 动量降级
{
    console.log('  Test 3.4: 动量数据缺失降级');
    const extractor = new TacticalExtractor();
    const data = createCorruptedData('missing_momentum');
    const features = extractor.extract(data);

    assert.strictEqual(features.has_momentum_data, false, '应标记无动量数据');
    assert.strictEqual(features.momentum_direction, 'unknown', '方向应为 unknown');
    assert.ok(features.momentum_seg1_dominance >= 0, '时段支配度应有默认值');

    console.log('  ✅ 动量降级通过');
}

// 测试 17: 高级特征计算
{
    console.log('  Test 3.5: 高级特征计算');
    const extractor = new TacticalExtractor();
    const features = extractor.extract(createValidRawData());

    // xG 相关
    assert.ok(typeof features.xg_diff === 'number', '应有 xG 差距');
    assert.ok(typeof features.xg_ratio === 'number', '应有 xG 比例');

    // 效率
    assert.ok(typeof features.home_xg_per_shot === 'number', '应有 xG/射门');

    // 综合实力
    assert.ok(typeof features.home_strength_index === 'number', '应有实力指数');
    assert.ok(typeof features.strength_diff === 'number', '应有实力差距');

    // 纪律性
    assert.ok(typeof features.home_discipline_score === 'number', '应有纪律评分');

    console.log('  ✅ 高级特征计算通过');
}

// ============================================================================
// 极端场景测试
// ============================================================================

console.log('\n💥 极端破坏性场景测试\n');

// 测试 18: null/undefined 输入
{
    console.log('  Test 4.1: null/undefined 输入');
    const golden = new GoldenExtractor();
    const tactical = new TacticalExtractor();

    const nullResult = golden.extract(null);
    assert.ok(nullResult._error || nullResult.home_market_value_total === 0, '应处理 null');

    const undefinedResult = tactical.extract(undefined);
    assert.ok(undefinedResult._error || undefinedResult.home_xg === 0, '应处理 undefined');

    console.log('  ✅ null/undefined 处理通过');
}

// 测试 19: 循环引用防护
{
    console.log('  Test 4.2: 深层嵌套 JSON');
    const extractor = new GoldenExtractor();
    const data = createCorruptedData('deep_nesting');
    const features = extractor.extract(data);

    assert.ok(typeof features === 'object', '应能处理深层嵌套');

    console.log('  ✅ 深层嵌套处理通过');
}

// 测试 20: 超大数组
{
    console.log('  Test 4.3: 大规模数据处理');
    const extractor = new GoldenExtractor();
    const data = createValidRawData();

    // 创建大量球员
    data.content.lineup.homeTeam.starters = Array(100).fill({
        marketValue: 50,
        performance: { rating: 6.5 },
        age: 25
    });

    const features = extractor.extract(data);
    assert.ok(features.home_market_value_total > 0, '应能处理大数组');

    console.log('  ✅ 大规模数据处理通过');
}

// 测试 21: 特殊字符和编码
{
    console.log('  Test 4.4: 特殊字符处理');
    const extractor = new GoldenExtractor();
    const data = createValidRawData();

    data.content.lineup.homeTeam.starters[0].name = '球员👍\n\t特殊字符';
    const features = extractor.extract(data);

    assert.ok(typeof features.home_market_value_total === 'number', '应能处理特殊字符');

    console.log('  ✅ 特殊字符处理通过');
}

// ============================================================================
// 性能测试
// ============================================================================

console.log('\n⚡ 性能测试\n');

// 测试 22: 执行时间
{
    console.log('  Test 5.1: 执行时间 < 10ms');
    const extractor = new GoldenExtractor();
    const data = createValidRawData();

    const start = Date.now();
    for (let i = 0; i < 100; i++) {
        extractor.extract(data);
    }
    const elapsed = Date.now() - start;

    assert.ok(elapsed < 1000, `100 次提取应在 1000ms 内完成 (实际: ${elapsed}ms)`);
    console.log(`    实际耗时: ${elapsed}ms (平均: ${elapsed / 100}ms/次)`);

    console.log('  ✅ 执行时间通过');
}

// 测试 23: 内存效率
{
    console.log('  Test 5.2: 内存效率检查');
    const extractor = new GoldenExtractor();

    // 大量特征提取，检查内存增长
    const initialMemory = process.memoryUsage().heapUsed;

    for (let i = 0; i < 1000; i++) {
        extractor.extract(createValidRawData());
    }

    // 触发垃圾回收（如果在 --expose-gc 模式下）
    if (global.gc) {
        global.gc();
    }

    const finalMemory = process.memoryUsage().heapUsed;
    const growth = (finalMemory - initialMemory) / 1024 / 1024;

    console.log(`    内存增长: ${growth.toFixed(2)} MB`);
    assert.ok(growth < 50, '内存增长应小于 50MB');

    console.log('  ✅ 内存效率通过');
}

// ============================================================================
// 覆盖统计
// ============================================================================

console.log('\n📊 测试覆盖统计\n');

// 收集所有提取器的统计
const golden = new GoldenExtractor();
const tactical = new TacticalExtractor();

// 执行各种操作以触发代码路径
golden.extract(createValidRawData());
golden.extract(createCorruptedData('missing_lineup'));
golden.extract(createInvalidNumericData());

tactical.extract(createValidRawData());
tactical.extract(createCorruptedData('missing_momentum'));

console.log(`  GoldenExtractor 统计:`);
console.log(`    - 总调用: ${golden.getStats().totalCalls}`);
console.log(`    - 成功率: ${golden.getStats().successRate}`);
console.log(`    - 平均耗时: ${golden.getStats().avgExecutionTimeMs.toFixed(2)}ms`);

console.log(`\n  TacticalExtractor 统计:`);
console.log(`    - 总调用: ${tactical.getStats().totalCalls}`);
console.log(`    - 成功率: ${tactical.getStats().successRate}`);
console.log(`    - 平均耗时: ${tactical.getStats().avgExecutionTimeMs.toFixed(2)}ms`);

console.log(`\n  特征字段总数: ${FEATURE_NAMES.golden.length + FEATURE_NAMES.tactical.length}`);

// ============================================================================
// 测试完成
// ============================================================================

console.log('\n✅ Extractors_V4 高压测试套件全部通过！');
console.log('   - BaseExtractor: 抽象协议验证 ✓');
console.log('   - GoldenExtractor: 黄金特征提取 ✓');
console.log('   - TacticalExtractor: 战术动量特征 ✓');
console.log('   - 极端场景: 破坏性测试 ✓');
console.log('   - 性能: 执行时间和内存效率 ✓');
console.log('\n📈 Phase 2 提取器接口标准化完成！准备进入 Phase 3...\n');
