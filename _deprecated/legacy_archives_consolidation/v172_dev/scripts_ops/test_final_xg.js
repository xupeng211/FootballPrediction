/**
 * V172-L2-08 最终 xG 提取
 */

const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
    const statePath = '/app/data/browser_profile/browser_state.json';
    const state = JSON.parse(fs.readFileSync(statePath, 'utf8'));

    console.log('=== V172-L2-08 最终 xG 提取 ===');
    console.log('Cookies:', state.cookies ? state.cookies.length : 0);

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

    console.log('访问首页...');
    await page.goto('https://www.fotmob.com/', { timeout: 30000 });
    await page.waitForTimeout(3000);

    console.log('请求 matchDetails API (ID: 4813561)...');

    const apiData = await page.evaluate(async () => {
        try {
            const res = await fetch('https://www.fotmob.com/api/matchDetails?matchId=4813561', {
                credentials: 'include'
            });
            return await res.json();
        } catch (e) {
            return { error: e.message };
        }
    });

    const isTurnstile = JSON.stringify(apiData).includes('TURNSTILE');
    console.log('状态:', isTurnstile ? '❌ TURNSTILE' : '✅ VALID_DATA');
    console.log('大小:', JSON.stringify(apiData).length, 'bytes');

    if (isTurnstile === false && apiData.content) {
        const content = apiData.content;

        // 查找 stats 数组
        const stats = content.stats;
        if (Array.isArray(stats)) {
            console.log('');
            console.log('═'.repeat(60));
            console.log('  📊 比赛统计');
            console.log('═'.repeat(60));

            // 查找 xG 统计
            const xgStats = stats.find(s => {
                const title = (s.title || '').toLowerCase();
                return title.includes('expected goals');
            });

            if (xgStats) {
                console.log('标题:', xgStats.title);

                // 检查结构
                if (xgStats.stats && Array.isArray(xgStats.stats)) {
                    console.log('数据项数:', xgStats.stats.length);
                    console.log('');

                    xgStats.stats.forEach((item, i) => {
                        console.log(`  [${i}]`, JSON.stringify(item));
                    });
                }
            }
        }

        // 尝试从 content.stats 提取
        console.log('');
        console.log('═'.repeat(60));
        console.log('  🔍 直接提取 xG');
        console.log('═'.repeat(60));

        // 遍历 stats 找 Expected goals
        if (Array.isArray(stats)) {
            for (const group of stats) {
                if (group.stats && Array.isArray(group.stats)) {
                    for (const item of group.stats) {
                        const title = (item.title || item.type || '').toString().toLowerCase();
                        if (title.includes('expected goals') && !title.includes('target')) {
                            console.log('');
                            console.log('分组:', group.title);
                            console.log('项目:', item.title || item.type);

                            // 尝试提取值
                            const val = item.statValue || item.value || item.stats;
                            if (typeof val === 'object') {
                                console.log('值:', JSON.stringify(val));
                            } else {
                                console.log('值:', val);
                            }
                        }
                    }
                }
            }
        }
    }

    await browser.close();
    console.log('');
    console.log('完成');
})();
