#!/usr/bin/env node
/**
 * TITAN V5.0 TURBO - 9900X 12核并行重炼
 * ======================================
 *
 * 利用 worker_threads 实现多核并行30维特征提炼
 * 目标：在一个咖啡时间(5分钟)内完成11,907场比赛
 *
 * 用法:
 *   node scripts/ops/smelt_v5_turbo.js [--workers=12] [--full-recalculate]
 *
 * @version V5.0.0-TURBO
 * @since 2026-03-14
 */

'use strict';

const { Worker } = require('worker_threads');
const { Pool } = require('pg');
const path = require('path');

// 数据库配置 (使用扩容后的连接池)
const DB_CONFIG = {
    host: process.env.DB_HOST || 'host.docker.internal',
    port: parseInt(process.env.DB_PORT || '5432'),
    database: process.env.DB_NAME || 'football_db',
    user: process.env.DB_USER || 'football_user',
    password: process.env.DB_PASSWORD || 'football_pass',
    max: 50,  // V5.0-TURBO: 支持12核并行
    idleTimeoutMillis: 30000,
    connectionTimeoutMillis: 5000,
};

// 默认Worker数量 (9900X = 12核)
const DEFAULT_WORKERS = 12;

/**
 * 主控函数
 */
async function main() {
    const args = parseArgs();
    const numWorkers = args.workers || DEFAULT_WORKERS;
    const fullRecalculate = args.fullRecalculate || false;

    console.log('\n' + '='.repeat(80));
    console.log('🔥🔥🔥 TITAN V5.0 TURBO - 9900X 12核全速重炼 🔥🔥🔥');
    console.log('='.repeat(80));
    console.log(`📅 时间: ${new Date().toISOString()}`);
    console.log(`🖥️  Worker数量: ${numWorkers} (9900X 12核全开)`);
    console.log(`🔄 模式: ${fullRecalculate ? '全量重算' : '增量处理'}`);
    console.log(`🔗 数据库连接池: ${DB_CONFIG.max}`);
    console.log('='.repeat(80) + '\n');

    const pool = new Pool(DB_CONFIG);
    const startTime = Date.now();

    try {
        // 获取待处理的比赛ID列表
        const matchIds = await getMatchIds(pool, fullRecalculate);
        
        if (matchIds.length === 0) {
            console.log('✅ 所有比赛已处理完成，无需重炼');
            return;
        }

        console.log(`📊 待处理比赛: ${matchIds.length.toLocaleString()} 场`);
        console.log(`⚡ 预估速度: ${(numWorkers * 2).toFixed(0)} 场/秒 (12核并行)`);
        console.log(`⏱️  预估耗时: ${(matchIds.length / (numWorkers * 2) / 60).toFixed(1)} 分钟\n`);

        // 将比赛ID分片给各Worker
        const chunks = chunkArray(matchIds, numWorkers);
        console.log(`📦 任务分片: ${chunks.length} 个批次`);
        chunks.forEach((chunk, i) => {
            console.log(`   Worker ${i + 1}: ${chunk.length.toLocaleString()} 场`);
        });
        console.log();

        // 启动Worker进程
        const workers = [];
        const workerStats = new Array(numWorkers).fill(null).map(() => ({
            processed: 0,
            success: 0,
            failed: 0,
            speed: 0,
            status: 'starting'
        }));

        // 创建Worker
        for (let i = 0; i < numWorkers; i++) {
            if (chunks[i].length === 0) continue;

            const worker = new Worker(
                path.resolve(__dirname, 'smelt_v5_worker.js'),
                {
                    workerData: {
                        workerId: i + 1,
                        matchIds: chunks[i],
                        dbConfig: DB_CONFIG
                    }
                }
            );

            // 监听Worker消息
            worker.on('message', (msg) => {
                handleWorkerMessage(msg, workerStats, startTime);
            });

            worker.on('error', (error) => {
                console.error(`❌ Worker ${i + 1} 错误:`, error.message);
                workerStats[i].status = 'error';
            });

            worker.on('exit', (code) => {
                if (code !== 0) {
                    console.error(`❌ Worker ${i + 1} 异常退出，码: ${code}`);
                    workerStats[i].status = 'crashed';
                } else {
                    workerStats[i].status = 'completed';
                }
            });

            workers.push(worker);
        }

        // 启动进度监控
        const progressInterval = setInterval(() => {
            printProgress(workerStats, startTime, matchIds.length);
        }, 10000);  // 每10秒报告

        // 等待所有Worker完成
        await Promise.all(workers.map(w => 
            new Promise((resolve) => {
                w.on('exit', resolve);
            })
        ));

        clearInterval(progressInterval);

        // 最终报告
        const totalElapsed = (Date.now() - startTime) / 1000;
        const totalSuccess = workerStats.reduce((sum, s) => sum + (s.success || 0), 0);
        const totalFailed = workerStats.reduce((sum, s) => sum + (s.failed || 0), 0);
        const avgSpeed = totalSuccess / totalElapsed;

        console.log('\n' + '='.repeat(80));
        console.log('✅ TURBO重炼完成！');
        console.log('='.repeat(80));
        console.log(`📊 总处理: ${matchIds.length.toLocaleString()} 场`);
        console.log(`✅ 成功: ${totalSuccess.toLocaleString()}`);
        console.log(`❌ 失败: ${totalFailed.toLocaleString()}`);
        console.log(`⏱️  总耗时: ${totalElapsed.toFixed(1)} 秒 (${(totalElapsed/60).toFixed(1)} 分钟)`);
        console.log(`⚡ 平均速度: ${avgSpeed.toFixed(2)} 场/秒`);
        console.log(`🚀 加速比: ${(avgSpeed / 0.16).toFixed(1)}x (vs 单核0.16场/秒)`);
        console.log('='.repeat(80));

        // 验证结果
        await verifyResults(pool);

    } catch (error) {
        console.error('\n❌ TURBO重炼失败:', error.message);
        console.error(error.stack);
        process.exit(1);
    } finally {
        await pool.end();
    }
}

/**
 * 解析命令行参数
 */
function parseArgs() {
    const args = { workers: DEFAULT_WORKERS };
    
    process.argv.slice(2).forEach(arg => {
        if (arg.startsWith('--workers=')) {
            args.workers = parseInt(arg.split('=')[1]) || DEFAULT_WORKERS;
        } else if (arg === '--full-recalculate') {
            args.fullRecalculate = true;
        }
    });

    return args;
}

/**
 * 获取待处理的比赛ID列表
 */
async function getMatchIds(pool, fullRecalculate) {
    let query;
    
    if (fullRecalculate) {
        // 全量重算：所有Harvested比赛
        query = `
            SELECT match_id 
            FROM matches 
            WHERE status = 'Harvested'
            ORDER BY match_id
        `;
    } else {
        // 增量：只处理没有30维特征的比赛
        query = `
            SELECT m.match_id 
            FROM matches m
            LEFT JOIN l3_features l ON m.match_id = l.match_id
            WHERE m.status = 'Harvested'
              AND (l.rolling_features IS NULL OR l.rolling_features::text = '{}')
            ORDER BY m.match_id
        `;
    }

    const result = await pool.query(query);
    return result.rows.map(r => r.match_id);
}

/**
 * 将数组分片
 */
function chunkArray(array, numChunks) {
    const chunks = [];
    const chunkSize = Math.ceil(array.length / numChunks);
    
    for (let i = 0; i < numChunks; i++) {
        const start = i * chunkSize;
        const end = Math.min(start + chunkSize, array.length);
        chunks.push(array.slice(start, end));
    }
    
    return chunks;
}

/**
 * 处理Worker消息
 */
function handleWorkerMessage(msg, workerStats, startTime) {
    const idx = msg.workerId - 1;

    switch (msg.type) {
        case 'started':
            workerStats[idx].status = 'running';
            console.log(`🚀 Worker ${msg.workerId} 启动，任务: ${msg.total} 场`);
            break;

        case 'progress':
            workerStats[idx].processed = msg.processed;
            workerStats[idx].success = msg.success;
            workerStats[idx].failed = msg.failed;
            workerStats[idx].speed = parseFloat(msg.speed);
            break;

        case 'completed':
            workerStats[idx].status = 'completed';
            workerStats[idx].stats = msg.stats;
            console.log(`✅ Worker ${msg.workerId} 完成: ${msg.stats.success}/${msg.stats.total} 场 (${msg.stats.avgSpeed} 场/秒)`);
            break;

        case 'error':
            console.error(`⚠️ Worker ${msg.workerId} 比赛错误:`, msg.error);
            break;

        case 'fatal':
            console.error(`❌ Worker ${msg.workerId} 致命错误:`, msg.error);
            workerStats[idx].status = 'fatal';
            break;
    }
}

/**
 * 打印进度报告
 */
function printProgress(workerStats, startTime, totalMatches) {
    const elapsed = (Date.now() - startTime) / 1000;
    const totalProcessed = workerStats.reduce((sum, s) => sum + (s.processed || 0), 0);
    const totalSuccess = workerStats.reduce((sum, s) => sum + (s.success || 0), 0);
    const avgSpeed = totalProcessed / elapsed;
    const progress = (totalProcessed / totalMatches * 100).toFixed(1);
    const eta = totalProcessed > 0 
        ? ((totalMatches - totalProcessed) / avgSpeed / 60).toFixed(1)
        : 'N/A';

    console.log('\n📊 TURBO进度报告 (' + new Date().toLocaleTimeString() + ')');
    console.log('-'.repeat(70));
    console.log(`总进度: ${totalProcessed.toLocaleString()}/${totalMatches.toLocaleString()} (${progress}%)`);
    console.log(`成功率: ${totalSuccess.toLocaleString()}/${totalProcessed.toLocaleString()}`);
    console.log(`当前速度: ${avgSpeed.toFixed(2)} 场/秒`);
    console.log(`已耗时: ${(elapsed/60).toFixed(1)} 分钟`);
    console.log(`预估剩余: ${eta} 分钟`);
    console.log('-'.repeat(70));
    
    // 各Worker状态
    workerStats.forEach((stat, i) => {
        if (stat.processed > 0) {
            const status = stat.status === 'running' ? '🟢' : 
                          stat.status === 'completed' ? '✅' : '⚪';
            console.log(`  ${status} Worker ${i + 1}: ${stat.processed}场 @ ${stat.speed.toFixed(2)}场/秒`);
        }
    });
    console.log();
}

/**
 * 验证重炼结果
 */
async function verifyResults(pool) {
    console.log('\n🔍 验证30维特征存储...');
    console.log('='.repeat(80));

    const result = await pool.query(`
        SELECT 
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE rolling_features IS NOT NULL AND rolling_features::text != '{}') as with_rolling,
            COUNT(*) FILTER (WHERE efficiency_features IS NOT NULL AND efficiency_features::text != '{}') as with_efficiency,
            COUNT(*) FILTER (WHERE draw_features IS NOT NULL AND draw_features::text != '{}') as with_draw
        FROM l3_features
    `);

    const { total, with_rolling, with_efficiency, with_draw } = result.rows[0];
    
    console.log(`📊 数据库统计:`);
    console.log(`  总记录: ${parseInt(total).toLocaleString()}`);
    console.log(`  Rolling特征: ${parseInt(with_rolling).toLocaleString()} (${(with_rolling/total*100).toFixed(1)}%)`);
    console.log(`  Efficiency特征: ${parseInt(with_efficiency).toLocaleString()} (${(with_efficiency/total*100).toFixed(1)}%)`);
    console.log(`  Draw特征: ${parseInt(with_draw).toLocaleString()} (${(with_draw/total*100).toFixed(1)}%)`);

    if (with_rolling === total) {
        console.log('\n✅ 30维特征全量填充完成！');
    } else {
        console.log(`\n⏳ 填充进度: ${(with_rolling/total*100).toFixed(1)}%`);
    }
    
    console.log('='.repeat(80));
}

// 运行主函数
main().catch(error => {
    console.error('Fatal error:', error);
    process.exit(1);
});
