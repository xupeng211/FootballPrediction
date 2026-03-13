/**
 * TITAN V5.0 Worker 线程 - 30维特征提炼
 * =======================================
 *
 * 9900X 12核并行工作单元
 * 每个Worker独立处理分配到的比赛批次
 *
 * @module scripts/ops/smelt_v5_worker
 * @version V5.0.0-TURBO
 * @since 2026-03-14
 */

'use strict';

const { parentPort, workerData } = require('worker_threads');
const { Pool } = require('pg');

// 从主线程接收配置
const { workerId, matchIds, dbConfig } = workerData;

// 每个Worker独立连接池
const pool = new Pool({
    ...dbConfig,
    max: 4,  // 每个Worker最多4个连接
    application_name: `titan_worker_${workerId}`
});

// 动态导入提取器
let SmelterOrchestrator;

try {
    const smelterModule = require('../../src/feature_engine/smelter/SmelterOrchestrator');
    SmelterOrchestrator = smelterModule.SmelterOrchestrator;
} catch (error) {
    parentPort.postMessage({
        type: 'error',
        workerId,
        error: `Failed to load SmelterOrchestrator: ${error.message}`
    });
    process.exit(1);
}

/**
 * Worker主处理函数
 */
async function processBatch() {
    const startTime = Date.now();
    const stats = {
        total: matchIds.length,
        processed: 0,
        success: 0,
        failed: 0,
        startTime
    };

    parentPort.postMessage({
        type: 'started',
        workerId,
        total: matchIds.length
    });

    try {
        // 创建Orchestrator实例
        const orchestrator = new SmelterOrchestrator({
            pool,
            config: {
                batchSize: 50,
                delayMs: 0,  // Worker内无延时，全速运行
                enableStreaming: false
            }
        });

        await orchestrator.init();

        // 分批处理比赛
        const batchSize = 50;
        for (let i = 0; i < matchIds.length; i += batchSize) {
            const batch = matchIds.slice(i, i + batchSize);

            // 获取比赛数据
            const matchesResult = await pool.query(`
                SELECT 
                    m.match_id,
                    m.external_id,
                    m.home_team,
                    m.away_team,
                    m.match_date,
                    r.raw_data
                FROM matches m
                INNER JOIN raw_match_data r ON m.match_id = r.match_id
                WHERE m.match_id = ANY($1)
            `, [batch]);

            // 处理每场比赛
            for (const match of matchesResult.rows) {
                try {
                    if (!match.raw_data) {
                        stats.failed++;
                        continue;
                    }

                    // 提取全部特征
                    const features = await orchestrator._extractAllFeatures({
                        match_id: match.match_id,
                        home_team: match.home_team,
                        away_team: match.away_team,
                        match_date: match.match_date,
                        ...match.raw_data
                    });

                    // 写入数据库
                    await pool.query(`
                        INSERT INTO l3_features (
                            match_id, external_id,
                            golden_features, tactical_features,
                            odds_movement_features, elo_features,
                            rolling_features, efficiency_features, draw_features,
                            computed_at, updated_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW(), NOW())
                        ON CONFLICT (match_id) DO UPDATE SET
                            golden_features = EXCLUDED.golden_features,
                            tactical_features = EXCLUDED.tactical_features,
                            odds_movement_features = EXCLUDED.odds_movement_features,
                            elo_features = EXCLUDED.elo_features,
                            rolling_features = EXCLUDED.rolling_features,
                            efficiency_features = EXCLUDED.efficiency_features,
                            draw_features = EXCLUDED.draw_features,
                            computed_at = EXCLUDED.computed_at,
                            updated_at = NOW()
                    `, [
                        match.match_id,
                        match.external_id || match.match_id,
                        JSON.stringify(features.golden || {}),
                        JSON.stringify(features.tactical || {}),
                        JSON.stringify(features.odds || {}),
                        JSON.stringify(features.elo || {}),
                        JSON.stringify(features.rolling || {}),
                        JSON.stringify(features.efficiency || {}),
                        JSON.stringify(features.draw || {})
                    ]);

                    stats.success++;
                } catch (error) {
                    stats.failed++;
                    parentPort.postMessage({
                        type: 'match_error',
                        workerId,
                        matchId: match.match_id,
                        error: error.message
                    });
                }

                stats.processed++;
            }

            // 每批完成后报告进度
            if (i % 200 === 0 || i + batchSize >= matchIds.length) {
                const elapsed = (Date.now() - startTime) / 1000;
                const speed = stats.processed / elapsed;
                const progress = (stats.processed / stats.total * 100).toFixed(1);

                parentPort.postMessage({
                    type: 'progress',
                    workerId,
                    processed: stats.processed,
                    total: stats.total,
                    success: stats.success,
                    failed: stats.failed,
                    progress,
                    speed: speed.toFixed(2),
                    elapsed: elapsed.toFixed(1)
                });
            }
        }

        const totalElapsed = (Date.now() - startTime) / 1000;
        const avgSpeed = stats.processed / totalElapsed;

        parentPort.postMessage({
            type: 'completed',
            workerId,
            stats: {
                ...stats,
                elapsed: totalElapsed.toFixed(2),
                avgSpeed: avgSpeed.toFixed(2)
            }
        });

    } catch (error) {
        parentPort.postMessage({
            type: 'fatal',
            workerId,
            error: error.message,
            stack: error.stack
        });
    } finally {
        await pool.end();
    }
}

// 启动处理
processBatch().catch(error => {
    parentPort.postMessage({
        type: 'fatal',
        workerId,
        error: error.message
    });
    process.exit(1);
});
