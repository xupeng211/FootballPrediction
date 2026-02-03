const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');

const CONCURRENCY = 12;
const MEMORY_LIMIT_MB = 1024;
const MATCHES_FILE = 'canary_matches.txt';
const BASE_URL = 'https://www.oddsportal.com';

async function runCanary() {
    const startTime = Date.now();
    console.log(`[Genesis.Canary500] Starting Stress Test with 500 matches...`);
    
    if (!fs.existsSync(MATCHES_FILE)) {
        console.error('Error: canary_matches.txt not found!');
        process.exit(1);
    }

    const lines = fs.readFileSync(MATCHES_FILE, 'utf8').split('\n').filter(l => l.trim());
    console.log(`[Genesis.Canary500] Loaded ${lines.length} matches. Concurrency: ${CONCURRENCY}`);

    let stats = {
        total: lines.length,
        processed: 0,
        success: 0,
        fallback: 0,
        failed: 0
    };

    const chunks = [];
    for (let i = 0; i < lines.length; i += CONCURRENCY) {
        chunks.push(lines.slice(i, i + CONCURRENCY));
    }

    for (const chunk of chunks) {
        const memoryUsage = process.memoryUsage().rss / 1024 / 1024;
        if (memoryUsage > MEMORY_LIMIT_MB) {
            console.error(`[Genesis.Canary500] 🚨 FATAL: Memory Limit Exceeded (${memoryUsage.toFixed(2)}MB).`);
            break;
        }

        const promises = chunk.map(line => {
            let [matchId, url] = line.split('|');
            // 补全 URL
            if (url && url.startsWith('/')) url = BASE_URL + url;
            
            return new Promise((resolve) => {
                const cmd = `node -e "const { QuantHarvester } = require('./src/infrastructure/engines/QuantHarvester'); const harvester = new QuantHarvester({ logLevel: 'ERROR' }); harvester.harvestMatch('${url}', '${matchId}').then(r => console.log('RESULT:' + JSON.stringify(r))).catch(e => console.log('ERROR:' + e.message))"`;
                
                const proc = exec(cmd, { 
                    timeout: 300000, 
                    env: { ...process.env, DB_PASSWORD: 'football_pass' } 
                });
                let output = '';
                proc.stdout.on('data', d => output += d);
                proc.stderr.on('data', d => output += d);
                
                proc.on('exit', (code) => {
                    stats.processed++;
                    if (output.includes('RESULT:')) {
                        const resultMatch = output.match(/RESULT:(.*)/);
                        if (resultMatch) {
                            try {
                                const res = JSON.parse(resultMatch[1]);
                                if (res.success) {
                                    stats.success++;
                                    if (output.includes('DOM_FALLBACK')) stats.fallback++;
                                } else {
                                    stats.failed++;
                                }
                            } catch(e) { stats.failed++; }
                        }
                    } else {
                        stats.failed++;
                        if (stats.failed <= 3) console.log(`[DEBUG_FAILED] ${matchId}: ${output.substring(0, 300)}`);
                    }

                    if (stats.processed % 5 === 0) {
                        const elapsed = (Date.now() - startTime) / 1000;
                        console.log(`[Genesis.Canary500] Progress: ${stats.processed}/${stats.total} | Success: ${stats.success} | Fallback: ${stats.fallback} | Time: ${elapsed.toFixed(0)}s`);
                    }
                    resolve();
                });
            });
        });

        await Promise.all(promises);
    }

    const finalSuccessRate = stats.processed > 0 ? (stats.success / stats.processed) * 100 : 0;
    const fallbackRate = stats.success > 0 ? (stats.fallback / stats.success) * 100 : 0;

    console.log('\n============================================================');
    console.log(`[Genesis.Canary500] STRESS TEST COMPLETE`);
    console.log(`Processed: ${stats.processed}/${stats.total}`);
    console.log(`Success Rate: ${finalSuccessRate.toFixed(2)}%`);
    console.log(`Fallback Ratio: ${fallbackRate.toFixed(2)}%`);
    console.log(`Final Memory: ${(process.memoryUsage().rss / 1024 / 1024).toFixed(2)}MB`);
    console.log('============================================================\n');

    process.exit(finalSuccessRate >= 85 ? 0 : 1);
}

runCanary();
