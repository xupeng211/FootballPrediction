/**
 * V172-L2-08 调试 API 结构
 */

const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
    const statePath = '/app/data/browser_profile/browser_state.json';
    const state = JSON.parse(fs.readFileSync(statePath, 'utf8'));

    console.log('=== 调试 API 结构 ===');

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

    console.log('数据大小:', JSON.stringify(apiData).length, 'bytes');

    if (apiData.content) {
        const stats = apiData.content.stats;
        console.log('stats 类型:', typeof stats, Array.isArray(stats) ? '(数组)' : '');

        if (Array.isArray(stats)) {
            console.log('stats 长度:', stats.length);
            console.log('');
            console.log('前 3 个分组:');
            stats.slice(0, 3).forEach((s, i) => {
                console.log(`[${i}]`, JSON.stringify(s).substring(0, 200));
            });
        } else if (stats) {
            console.log('stats 键:', Object.keys(stats).join(', '));
        }

        // 打印 content 的顶层结构
        console.log('');
        console.log('content 顶层键:', Object.keys(apiData.content).join(', '));
    }

    await browser.close();
})();
