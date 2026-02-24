/**
 * V171-Standard-05 数据验证测试
 * ==============================
 *
 * 展示数据验证机制如何优雅处理"数据缺失"情况
 */

'use strict';

const {
    MatchSchema,
    PredictionSchema,
    OddsSchema,
    validateOrThrow,
    validateOrWarn
} = require('./lib/schemas');

console.log('═══════════════════════════════════════════════════════════════');
console.log('  V171-Standard-05 数据验证测试');
console.log('═══════════════════════════════════════════════════════════════');
console.log('');

// ============================================================================
// 测试 1: 正常数据
// ============================================================================

console.log('📋 测试 1: 正常数据');
console.log('───────────────────────────────────────────────────────────────');

const validMatch = {
    match_id: 'EPL_20260228_LIV_WHU',
    home_team: 'Liverpool',
    away_team: 'West Ham',
    league_name: 'Premier League',
    match_date: '2026-02-28T15:00:00Z'
};

const result1 = MatchSchema.validate(validMatch);
console.log('  验证结果:', result1.valid ? '✅ 通过' : '❌ 失败');
if (!result1.valid) {
    console.log('  错误:', result1.errors);
}

console.log('');

// ============================================================================
// 测试 2: 数据缺失 - 缺少必填字段
// ============================================================================

console.log('📋 测试 2: 数据缺失 - 缺少 match_id');
console.log('───────────────────────────────────────────────────────────────');

const missingIdMatch = {
    home_team: 'Liverpool',
    away_team: 'West Ham',
    // match_id 缺失
};

const result2 = MatchSchema.validate(missingIdMatch);
console.log('  验证结果:', result2.valid ? '✅ 通过' : '❌ 失败');
console.log('  错误详情:');
result2.errors.forEach(e => {
    console.log(`    - ${e.field}: ${e.message}`);
});

console.log('');

// ============================================================================
// 测试 3: 格式错误
// ============================================================================

console.log('📋 测试 3: match_id 格式错误');
console.log('───────────────────────────────────────────────────────────────');

const wrongFormatMatch = {
    match_id: 'invalid-id-format',
    home_team: 'Liverpool',
    away_team: 'West Ham',
    league_name: 'Premier League'
};

const result3 = MatchSchema.validate(wrongFormatMatch);
console.log('  验证结果:', result3.valid ? '✅ 通过' : '❌ 失败');
console.log('  错误详情:');
result3.errors.forEach(e => {
    console.log(`    - ${e.field}: ${e.message}`);
});

console.log('');

// ============================================================================
// 测试 4: 预测数据 - 置信度超出范围
// ============================================================================

console.log('📋 测试 4: 预测数据 - 置信度超出范围 (1.5 > 1.0)');
console.log('───────────────────────────────────────────────────────────────');

const invalidPrediction = {
    match_id: 'EPL_20260228_LIV_WHU',
    predicted_result: 'home',
    final_confidence: 1.5,  // 超出范围
    home_win_prob: 0.7,
    draw_prob: 0.2,
    away_win_prob: 0.1
};

const result4 = PredictionSchema.validate(invalidPrediction);
console.log('  验证结果:', result4.valid ? '✅ 通过' : '❌ 失败');
console.log('  错误详情:');
result4.errors.forEach(e => {
    console.log(`    - ${e.field}: ${e.message}`);
});

console.log('');

// ============================================================================
// 测试 5: 预测数据 - 概率和不为 1
// ============================================================================

console.log('📋 测试 5: 预测数据 - 概率和不等于 1');
console.log('───────────────────────────────────────────────────────────────');

const badProbsPrediction = {
    match_id: 'EPL_20260228_LIV_WHU',
    predicted_result: 'home',
    final_confidence: 0.68,
    home_win_prob: 0.5,
    draw_prob: 0.3,
    away_win_prob: 0.4  // 总和 1.2
};

const result5 = PredictionSchema.validate(badProbsPrediction);
console.log('  验证结果:', result5.valid ? '✅ 通过' : '❌ 失败');
console.log('  错误详情:');
result5.errors.forEach(e => {
    console.log(`    - ${e.field}: ${e.message}`);
});

console.log('');

// ============================================================================
// 测试 6: 安全提取
// ============================================================================

console.log('📋 测试 6: 安全提取 - 自动修复无效数据');
console.log('───────────────────────────────────────────────────────────────');

const dirtyData = {
    match_id: 'EPL_20260228_LIV_WHU',
    predicted_result: 'HOME',  // 大写
    final_confidence: 1.5,    // 超出范围
    home_win_prob: undefined,
    draw_prob: null
};

console.log('  原始数据:', JSON.stringify(dirtyData));

const safeResult = PredictionSchema.validate(dirtyData);
if (!safeResult.valid) {
    console.log('  验证失败，尝试自动修复...');

    // 手动修复
    const fixedData = {
        match_id: dirtyData.match_id,
        predicted_result: (dirtyData.predicted_result || 'home').toLowerCase(),
        final_confidence: Math.max(0, Math.min(1, dirtyData.final_confidence || 0.5)),
        home_win_prob: dirtyData.home_win_prob ?? 0.33,
        draw_prob: dirtyData.draw_prob ?? 0.33,
        away_win_prob: dirtyData.away_win_prob ?? (1 - (dirtyData.home_win_prob ?? 0.33) - (dirtyData.draw_prob ?? 0.33))
    };

    console.log('  修复后数据:', JSON.stringify(fixedData));

    const revalidate = PredictionSchema.validate(fixedData);
    console.log('  重新验证:', revalidate.valid ? '✅ 通过' : '❌ 仍失败');
}

console.log('');

// ============================================================================
// 测试 7: 赔率数据验证
// ============================================================================

console.log('📋 测试 7: 赔率数据 - 赔率为 0');
console.log('───────────────────────────────────────────────────────────────');

const zeroOdds = {
    home_odds: 0,
    draw_odds: 3.5,
    away_odds: 2.1
};

const oddsResult = OddsSchema.validate(zeroOdds);
console.log('  验证结果:', oddsResult.valid ? '✅ 通过' : '❌ 失败');
if (!oddsResult.valid) {
    console.log('  错误详情:');
    oddsResult.errors.forEach(e => {
        console.log(`    - ${e.field}: ${e.message}`);
    });

    // 安全提取
    const safeOdds = OddsSchema.safeExtract(zeroOdds, { home_odds: 2.5, draw_odds: 3.5, away_odds: 2.8 });
    console.log('  安全提取后:', JSON.stringify(safeOdds));
}

console.log('');

// ============================================================================
// 总结
// ============================================================================

console.log('═══════════════════════════════════════════════════════════════');
console.log('  测试总结');
console.log('═══════════════════════════════════════════════════════════════');
console.log('');
console.log('  ✅ 数据验证机制测试完成');
console.log('');
console.log('  验证能力:');
console.log('    • 必填字段检查');
console.log('    • 数据类型验证');
console.log('    • 数值范围验证 (0-1)');
console.log('    • 格式模式验证 (正则)');
console.log('    • 概率和一致性检查');
console.log('');
console.log('  容错能力:');
console.log('    • 自动跳过无效数据');
console.log('    • 安全提取 + 默认值');
console.log('    • 详细错误报告');
console.log('');
console.log('  优雅处理:');
console.log('    • 不崩溃，只记录警告');
console.log('    • 可选的严格模式');
console.log('    • 数据标准化 (如大小写转换)');
console.log('');
console.log('═══════════════════════════════════════════════════════════════');
