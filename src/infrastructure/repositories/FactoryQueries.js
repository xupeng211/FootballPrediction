/**
 * V172 SQL 查询模块 - 数据工厂
 * =============================
 *
 * 所有 SQL 查询集中管理，便于维护和测试
 *
 * V172 改进:
 * - 动态路径解析 (移除硬编码 /app 路径)
 * - 支持容器外运行
 * - 默认值兜底
 *
 * @module src/infrastructure/repositories/FactoryQueries
 * @version V172.100
 */

'use strict';

const path = require('path');

// ============================================================================
// 动态路径解析
// ============================================================================

// 获取项目根目录 (支持容器内和容器外)
const PROJECT_ROOT = process.env.PROJECT_ROOT || process.cwd();

// 尝试加载配置，失败时使用默认值
let config;
try {
    config = require(path.join(PROJECT_ROOT, 'config/factory_config'));
} catch (e) {
    // 默认配置 (兜底)
    config = {
        INCREMENTAL_CONFIG: {
            targetStatuses: ['completed', 'finished'],
            lookbackDays: 7
        },
        QUALITY_GATE: {
            minSizeBytes: 5000
        }
    };
}

const { INCREMENTAL_CONFIG, QUALITY_GATE } = config;

// ============================================================================
// 增量任务查询
// ============================================================================

const INCREMENTAL_TASKS = `
    SELECT
        m.match_id,
        m.external_id,
        m.home_team,
        m.away_team,
        m.league_name,
        m.match_date,
        m.status
    FROM matches m
    LEFT JOIN raw_match_data r ON m.match_id = r.match_id
    WHERE m.external_id IS NOT NULL
      AND m.external_id <> ''
      AND (m.status = ANY($1))
      AND m.match_date > NOW() - INTERVAL '1 day' * $2
      AND (
          r.match_id IS NULL
          OR r.l2_raw_json IS NULL
          OR r.l2_raw_json::text = '{}'
          OR LENGTH(r.l2_raw_json::text) < $3
      )
    ORDER BY m.match_date DESC
`;

// ============================================================================
// 补漏任务查询
// ============================================================================

const REPAIR_TASKS = `
    SELECT
        m.match_id,
        m.external_id,
        m.home_team,
        m.away_team,
        m.league_name,
        m.match_date,
        m.status
    FROM matches m
    JOIN raw_match_data r ON m.match_id = r.match_id
    WHERE m.external_id IS NOT NULL
      AND m.external_id <> ''
      AND (
          LENGTH(r.l2_raw_json::text) < $1
          OR r.l2_raw_json::text LIKE '%error%'
          OR r.l2_raw_json::text LIKE '%TURNSTILE%'
          OR r.l2_raw_json::text LIKE '%Failed%'
      )
    ORDER BY m.match_date DESC
`;

// ============================================================================
// 全量任务查询
// ============================================================================

const FULL_TASKS = `
    SELECT
        m.match_id,
        m.external_id,
        m.home_team,
        m.away_team,
        m.league_name,
        m.match_date,
        m.status
    FROM matches m
    LEFT JOIN raw_match_data r ON m.match_id = r.match_id
    WHERE m.external_id IS NOT NULL
      AND m.external_id <> ''
      AND (
          r.match_id IS NULL
          OR r.l2_raw_json IS NULL
          OR r.l2_raw_json::text = '{}'
          OR LENGTH(r.l2_raw_json::text) < $1
      )
    ORDER BY m.match_date DESC
`;

// ============================================================================
// 数据插入/更新
// ============================================================================

const INSERT_RAW_DATA = `
    INSERT INTO raw_match_data (match_id, l2_raw_json, collected_at)
    VALUES ($1, $2::jsonb, NOW())
    ON CONFLICT (match_id) DO UPDATE SET
        l2_raw_json = EXCLUDED.l2_raw_json,
        collected_at = NOW()
`;

const UPDATE_MATCH_XG = `
    UPDATE matches SET
        xg_home = $2,
        xg_away = $3,
        updated_at = NOW()
    WHERE match_id = $1
`;

// ============================================================================
// 清理坏账
// ============================================================================

const CLEAN_BAD_RECORDS = `
    DELETE FROM raw_match_data
    WHERE LENGTH(l2_raw_json::text) < $1
       OR l2_raw_json::text LIKE '%error%'
       OR l2_raw_json::text LIKE '%TURNSTILE%'
    RETURNING match_id
`;

// ============================================================================
// 统计查询
// ============================================================================

const STATISTICS = {
    // 总覆盖率
    coverage: `
        SELECT
            COUNT(*) FILTER (WHERE r.l2_raw_json IS NOT NULL AND LENGTH(r.l2_raw_json::text) >= $1) as valid_count,
            COUNT(*) as total_count
        FROM matches m
        LEFT JOIN raw_match_data r ON m.match_id = r.match_id
        WHERE m.external_id IS NOT NULL AND m.external_id <> ''
    `,

    // 坏账统计
    badRecords: `
        SELECT
            COUNT(*) as bad_count
        FROM raw_match_data
        WHERE LENGTH(l2_raw_json::text) < $1
           OR l2_raw_json::text LIKE '%error%'
    `,

    // 最近收割记录
    recentHarvests: `
        SELECT
            match_id,
            LENGTH(l2_raw_json::text) as size,
            collected_at
        FROM raw_match_data
        WHERE collected_at > NOW() - INTERVAL '24 hours'
        ORDER BY collected_at DESC
        LIMIT 10
    `,

    // 按联赛统计
    byLeague: `
        SELECT
            m.league_name,
            COUNT(*) as total,
            COUNT(r.match_id) as harvested,
            COUNT(*) FILTER (WHERE LENGTH(r.l2_raw_json::text) >= $1) as valid
        FROM matches m
        LEFT JOIN raw_match_data r ON m.match_id = r.match_id
        WHERE m.external_id IS NOT NULL
        GROUP BY m.league_name
        ORDER BY total DESC
    `
};

// ============================================================================
// 查询参数工厂
// ============================================================================

const getParams = {
    incremental: () => [
        INCREMENTAL_CONFIG.targetStatuses,
        INCREMENTAL_CONFIG.lookbackDays,
        QUALITY_GATE.minSizeBytes
    ],
    repair: () => [QUALITY_GATE.minSizeBytes],
    full: () => [QUALITY_GATE.minSizeBytes],
    cleanBad: () => [QUALITY_GATE.minSizeBytes],
    insertRaw: (matchId, jsonData) => [matchId, JSON.stringify(jsonData)],
    updateXG: (matchId, xgHome, xgAway) => [matchId, xgHome, xgAway]
};

// ============================================================================
// 导出
// ============================================================================

module.exports = {
    // 查询语句
    INCREMENTAL_TASKS,
    REPAIR_TASKS,
    FULL_TASKS,
    INSERT_RAW_DATA,
    UPDATE_MATCH_XG,
    CLEAN_BAD_RECORDS,
    STATISTICS,

    // 参数工厂
    getParams,

    // 配置引用
    config: {
        INCREMENTAL_CONFIG,
        QUALITY_GATE
    }
};
