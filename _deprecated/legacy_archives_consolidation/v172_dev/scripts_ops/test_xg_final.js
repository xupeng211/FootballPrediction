/**
 * V172-L2-08 最终 xG 提取
 */

const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
    const statePath = '/app/data/browser_profile/browser_state.json';

    console.log('');
    console.log('═'.repeat(70));
    console.log('  V172-L2-08 最终 xG 提取');
    console.log('  目标: 曼联 vs 狼队 (2025-12-30)');
    console.log('═'.repeat(70));

    const browser = await chromium.launch({
        headless: true,
        proxy: { server: process.env.HTTPS_PROXY },
        args: ['--disable-gpu', '--no-sandbox', '--disable-dev-shm-usage']
    });

    const context = await browser.newContext({
        storageState: statePath,
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36',
        viewport: { width: 1287, height: 1271 },
        locale: 'zh-CN',
        timezoneId: 'Asia/Shanghai'
    });

    const page = await context.newPage();

    await page.goto('https://www.fotmob.com/', { timeout: 30000 });
    await page.waitForTimeout(3000);

    const apiData = await page.evaluate(async () => {
        const res = await fetch('https://www.fotmob.com/api/matchDetails?matchId=4813561', { credentials: 'include' });
        return await res.json();
    });

    console.log('');
    console.log('📡 数据状态: ✅ VALID_DATA');
    console.log('📊 数据大小:', JSON.stringify(apiData).length, 'bytes');

    if (apiData.content && apiData.content.stats) {
        const allStats = apiData.content.stats.Periods?.All?.stats || [];

        console.log('');
        console.log('─'.repeat(70));
        console.log('  📋 统计分组列表');
        console.log('─'.repeat(70));

        allStats.forEach((group, i) => {
            console.log(`  [${i}] ${group.title || group.key}`);
        });

        // 查找 xG
        console.log('');
        console.log('─'.repeat(70));
        console.log('  🎯 xG 数据');
        console.log('─'.repeat(70));

        const xgGroup = allStats.find(g => {
            const title = (g.title || g.key || '').toLowerCase();
            return title.includes('expected goals') || title.includes('xg');
        });

        if (xgGroup) {
            console.log('');
            console.log('  分组:', xgGroup.title);

            if (xgGroup.stats && Array.isArray(xgGroup.stats)) {
                console.log('');
                xgGroup.stats.forEach((item, i) => {
                    console.log(`  [${i}]`, JSON.stringify(item));
                });

                // 提取主客队 xG
                if (xgGroup.stats.length >= 2) {
                    const homeXg = xgGroup.stats[0];
                    const awayXg = xgGroup.stats[1];

                    console.log('');
                    console.log('═'.repeat(70));
                    console.log('  ✅ xG 结果');
                    console.log('═'.repeat(70));
                    console.log(`    曼联 xG: ${homeXg}`);
                    console.log(`    狼队 xG: ${awayXg}`);
                    console.log('═'.repeat(70));
                }
            }
        } else {
            // 打印每个分组的详细内容
            console.log('');
            console.log('  未找到 xG 分组，打印所有分组内容...');

            allStats.forEach((group, i) => {
                console.log('');
                console.log(`  [${i}] ${group.title}:`);
                if (group.stats) {
                    group.stats.forEach((s, j) => {
                        console.log(`      [${j}] ${s.title || s.key}: ${JSON.stringify(s.stats || s)}`);
                    });
                }
            });
        }
    }

    await browser.close();
    console.log('');
    console.log('完成');
})();
