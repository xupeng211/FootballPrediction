#!/usr/bin/env node
/**
 * TITAN-WAREHOUSE-IMPORT - 磁盘 JSON 全量入库
 * =============================================
 *
 * 将 data/matches/*.json 批量导入 raw_match_data 表
 *
 * 用法:
 *   node scripts/ops/bulk_import_matches.js
 *
 * @version V1.0.0
 */

'use strict';

const fs = require('fs');
const path = require('path');
const { getPool } = require('../../config/database');

const DATA_DIR = process.env.DATA_MATCHES_PATH
    ? path.resolve(process.cwd(), process.env.DATA_MATCHES_PATH)
    : path.join(process.cwd(), 'data', 'matches');
const BATCH_SIZE = 500;

/**
 * 主函数
 */
async function main() {
    const startTime = Date.now();
    console.log('🔥 TITAN-WAREHOUSE-IMPORT 启动');
    console.log(`📁 目标目录: ${DATA_DIR}`);
    console.log(`📦 批次大小: ${BATCH_SIZE}`);
    console.log('');

    // 获取数据库连接
    const pool = getPool();

    // 读取所有 JSON 文件
    const files = fs.readdirSync(DATA_DIR)
        .filter(f => f.endsWith('.json'))
        .map(f => path.join(DATA_DIR, f));

    console.log(`📊 发现 ${files.length} 个 JSON 文件`);
    console.log('');

    let totalImported = 0;
    let totalSkipped = 0;
    let totalErrors = 0;

    // 分批处理
    for (let i = 0; i < files.length; i += BATCH_SIZE) {
        const batch = files.slice(i, i + BATCH_SIZE);
        const batchNum = Math.floor(i / BATCH_SIZE) + 1;
        const totalBatches = Math.ceil(files.length / BATCH_SIZE);

        console.log(`🔄 处理批次 ${batchNum}/${totalBatches} (${batch.length} 文件)`);

        const client = await pool.connect();
        let batchImported = 0;
        let batchSkipped = 0;
        let batchErrors = 0;

        try {
            await client.query('BEGIN');

            for (const filePath of batch) {
                try {
                    // 读取并解析 JSON
                    const content = fs.readFileSync(filePath, 'utf8');
                    const data = JSON.parse(content);

                    // 获取 match_id (从文件内容或文件名)
                    const matchId = data.match_id || path.basename(filePath, '.json');

                    // 准备 raw_data (如果文件结构是 {match_id, raw_data}，则取 raw_data，否则取整个内容)
                    const rawData = data.raw_data || data;

                    // 插入数据库
                    const result = await client.query(
                        `INSERT INTO raw_match_data (match_id, raw_data, collected_at)
                         VALUES ($1, $2, CURRENT_TIMESTAMP)
                         ON CONFLICT (match_id) DO NOTHING
                         RETURNING match_id`,
                        [matchId, JSON.stringify(rawData)]
                    );

                    if (result.rowCount > 0) {
                        batchImported++;
                    } else {
                        batchSkipped++;
                    }
                } catch (err) {
                    batchErrors++;
                    console.error(`   ❌ 文件错误: ${path.basename(filePath)} - ${err.message}`);
                }
            }

            await client.query('COMMIT');

            totalImported += batchImported;
            totalSkipped += batchSkipped;
            totalErrors += batchErrors;

            console.log(`   ✅ 导入: ${batchImported} | ⏭️ 跳过: ${batchSkipped} | ❌ 错误: ${batchErrors}`);
            console.log(`   📈 累计进度: ${totalImported}/${files.length} (${(totalImported/files.length*100).toFixed(1)}%)`);
            console.log('');

        } catch (err) {
            await client.query('ROLLBACK');
            console.error(`   ❌ 批次失败: ${err.message}`);
            totalErrors += batch.length;
        } finally {
            client.release();
        }
    }

    const duration = Date.now() - startTime;

    console.log('');
    console.log('🎉 TITAN-WAREHOUSE-IMPORT 完成');
    console.log('═══════════════════════════════════════');
    console.log(`📊 总文件数: ${files.length}`);
    console.log(`✅ 成功导入: ${totalImported}`);
    console.log(`⏭️ 重复跳过: ${totalSkipped}`);
    console.log(`❌ 错误数量: ${totalErrors}`);
    console.log(`⏱️ 总耗时: ${(duration/1000).toFixed(1)} 秒`);
    console.log(`🚀 平均速度: ${(files.length/(duration/1000)).toFixed(0)} 文件/秒`);
    console.log('═══════════════════════════════════════');

    await pool.end();
    process.exit(0);
}

main().catch(err => {
    console.error('💥 致命错误:', err);
    process.exit(1);
});
