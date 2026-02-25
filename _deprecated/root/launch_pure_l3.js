
const { QuantHarvester } = require('./src/infrastructure/engines/QuantHarvester');
const { Client } = require('pg');
const fs = require('fs');
const path = require('path');

// データベース配置
const dbConfig = {
    host: 'localhost',
    user: 'football_user',
    password: 'football_pass',
    database: 'football_db',
    port: 5432,
};

// 日志配置
const logFile = path.join(process.cwd(), 'logs/l3_ignition.log');
if (!fs.existsSync(path.dirname(logFile))) fs.mkdirSync(path.dirname(logFile), { recursive: true });

function log(msg) {
    const timestamp = new Date().toISOString();
    const formattedMsg = `[${timestamp}] ${msg}`;
    console.log(formattedMsg);
    fs.appendFileSync(logFile, formattedMsg + '\n');
}

async function run() {
    const client = new Client(dbConfig);
    await client.connect();

    log("[Genesis.DirectL3] Starting Pure L3 Ignition...");

    try {
        // 1. 选取 50 场未收割 L3 数据的五大联赛比赛 (英超: 47, 西甲: 87)
        // 假设 page_url 存储了 OddsPortal 的相对路径
        const query = `
            SELECT match_id as id, page_url 
            FROM matches 
            WHERE (league_name ILIKE '%Premier League%' OR league_name ILIKE '%LaLiga%') 
            AND (l3_odds_data IS NULL OR l3_odds_data = '{}')
            AND page_url IS NOT NULL
            ORDER BY match_date DESC
            LIMIT 50;
        `;
        
        const res = await client.query(query);
        const matches = res.rows.map(r => ({
            id: r.id,
            url: r.page_url.startsWith('http') ? r.page_url : `https://www.oddsportal.com${r.page_url}`
        }));

        log(`[Genesis.DirectL3] Found ${matches.length} target matches.`);

        if (matches.length === 0) {
            log("No matches found for L3 ignition. Exit.");
            return;
        }

        // 2. 初始化 Harvester
        const harvester = new QuantHarvester({
            logLevel: 'INFO'
        });
        await harvester.init();

        // 3. 执行 Batch Harvest (内部已处理并发 5 和随机延迟)
        log(`Executing batch harvest for 20 matches...`);
        const results = await harvester.harvestBatch(matches.slice(0, 20));

        let totalSuccess = results.filter(r => r.success).length;

        log(`[Genesis.DirectL3] Ignition Complete. Results: ${totalSuccess}/${results.length}`);
        log(`Real gold secured in database.`);

    } catch (err) {
        log(`CRITICAL ERROR: ${err.message}`);
    } finally {
        await client.end();
    }
}

run();
