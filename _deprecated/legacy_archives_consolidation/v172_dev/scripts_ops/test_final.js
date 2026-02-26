/**
 * V172-L2-08 最终 xG 提取
 */

const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
    const statePath = '/app/data/browser_profile/browser_state.json';

    console.log('=== V172-L2-08 最终 xG 提取 ===');

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

    if (apiData.content && apiData.content.stats) {
        const periods = apiData.content.stats.Periods;

        if (periods && periods.All) {
            const all = periods.All;

            console.log('');
            console.log('All 键:', Object.keys(all).join(', '));

            // 检查每个键
            for (const key of Object.keys(all)) {
                const val = all[key];
                console.log('');
                console.log(`--- ${key} ---`);
                console.log('类型:', typeof val, Array.isArray(val) ? '(数组)' : '');
                if (Array.isArray(val)) {
                    console.log('长度:', val.length);
                    if (val.length > 0) {
                        console.log('第一项:', JSON.stringify(val[0]).substring(0, 150));
                    }
                } else if (typeof val === 'object') {
                    console.log('子键:', Object.keys(val).slice(0, 5).join(', '));
                }
            }
        }
    }

    await browser.close();
    console.log('');
    console.log('完成');
})();
