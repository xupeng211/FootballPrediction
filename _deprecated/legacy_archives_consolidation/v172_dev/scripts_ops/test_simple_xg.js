/**
 * V172-L2-08 简化测试 (禁用 GPU 避免崩溃)
 */

const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
    const statePath = '/app/data/browser_profile/browser_state.json';
    const state = JSON.parse(fs.readFileSync(statePath, 'utf8'));

    console.log('=== 简化测试 (禁用 GPU) ===');
    console.log('Cookies:', state.cookies ? state.cookies.length : 0);

    const browser = await chromium.launch({
        headless: true,
        proxy: { server: process.env.HTTPS_PROXY },
        args: ['--disable-gpu', '--disable-software-rasterizer', '--no-sandbox', '--disable-dev-shm-usage']
    });

    const context = await browser.newContext({
        storageState: statePath,
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36',
        viewport: { width: 1287, height: 1271 },
        locale: 'zh-CN',
        timezoneId: 'Asia/Shanghai'
    });

    const page = await context.newPage();

    let apiData = null;
    page.on('response', async (response) => {
        if (response.url().includes('/api/matchDetails')) {
            try {
                apiData = await response.json();
                console.log('🎯 API 拦截成功');
            } catch(e) {}
        }
    });

    // 先访问首页
    console.log('访问首页...');
    await page.goto('https://www.fotmob.com/', { timeout: 30000 });
    await page.waitForTimeout(3000);

    // 访问比赛页
    console.log('访问比赛页 (曼联 vs 狼队)...');
    await page.goto('https://www.fotmob.com/matches/-/4813561', { timeout: 60000 });
    await page.waitForTimeout(10000);

    if (apiData) {
        const isTurnstile = JSON.stringify(apiData).includes('TURNSTILE');
        console.log('数据状态:', isTurnstile ? '❌ TURNSTILE 错误' : '✅ VALID_DATA');
        console.log('数据大小:', JSON.stringify(apiData).length, 'bytes');

        if (isTurnstile === false) {
            // 解析 xG
            const content = apiData.content || {};
            const stats = content.stats || [];

            console.log('');
            console.log('=== 📊 xG 数据 ===');

            const xgStats = stats.find(s => {
                const title = (s.title || '').toLowerCase();
                return title.includes('expected') || title.includes('xg');
            });

            if (xgStats && xgStats.stats) {
                console.log('分组标题:', xgStats.title);
                console.log('');
                xgStats.stats.forEach((stat, i) => {
                    console.log(`  [${i}]`, JSON.stringify(stat));
                });
            } else {
                console.log('未找到 xG 数据');
            }

            // 打印所有 stats 标题
            console.log('');
            console.log('=== 所有统计分组 ===');
            stats.forEach((s, i) => {
                console.log(`  [${i}] ${s.title}`);
            });
        }
    } else {
        console.log('❌ 未拦截到 API');
    }

    await browser.close();
    console.log('');
    console.log('完成');
})();
