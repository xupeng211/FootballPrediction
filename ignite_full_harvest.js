
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');

// [Genesis.EfficiencyBalance] Ignition Configuration
const CONCURRENCY = 12;
const MAX_MATCHES = 8500;
const PENDING_FILE = 'pending_matches.txt';

async function run() {
    console.log(`[Genesis.Balanced] Initializing 8500 Harvest Ignition...`);
    
    if (!fs.existsSync(PENDING_FILE)) {
        console.error('Error: pending_matches.txt not found!');
        process.exit(1);
    }

    const lines = fs.readFileSync(PENDING_FILE, 'utf8').split('\n').filter(l => l.trim());
    console.log(`[Genesis.Balanced] Loaded ${lines.length} matches. Chunking by ${CONCURRENCY}...`);

    const chunks = [];
    for (let i = 0; i < lines.length; i += CONCURRENCY) {
        chunks.push(lines.slice(i, i + CONCURRENCY));
    }

    let processedCount = 0;
    const startTime = Date.now();

    for (const chunk of chunks) {
        const promises = chunk.map(line => {
            const [matchId, url] = line.split('|');
            return new Promise((resolve) => {
                // 执行 QuantHarvester 节点命令 (假设在生产环境模式运行)
                // 这里我们使用 node 直接调用引擎逻辑
                const cmd = `node -e "const QuantHarvester = require('./src/infrastructure/engines/QuantHarvester'); const harvester = new QuantHarvester({ logLevel: 'INFO' }); harvester.harvestSingleMatch('${url}', { id: '${matchId}', enableTrajectoryCapture: true }).then(() => process.exit(0)).catch(() => process.exit(1))"`;
                
                const proc = exec(cmd, { timeout: 120000 }); // 2分钟超时
                proc.on('exit', (code) => {
                    processedCount++;
                    if (processedCount % 10 === 0) {
                        const elapsed = (Date.now() - startTime) / 1000;
                        const rate = (processedCount / elapsed) * 60;
                        console.log(`[Genesis.Balanced] Progress: ${processedCount}/${lines.length} | Rate: ${rate.toFixed(2)} match/min`);
                    }
                    resolve();
                });
            });
        });

        await Promise.all(promises);
    }

    console.log('[Genesis.Balanced] FULL IGNITION COMPLETE.');
}

run();
