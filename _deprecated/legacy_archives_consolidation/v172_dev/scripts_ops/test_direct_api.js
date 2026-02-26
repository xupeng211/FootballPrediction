/**
 * V172-L2-08 直接 API 请求测试
 */

const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
    const statePath = '/app/data/browser_profile/browser_state.json';
    const state = JSON.parse(fs.readFileSync(statePath, 'utf8'));

    console.log('=== 直接 API 请求测试 ===');
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

    // 先访问首页建立会话
    console.log('访问首页...');
    await page.goto('https://www.fotmob.com/', { timeout: 30000 });
    await page.waitForTimeout(3000);

    // 直接请求 API
    console.log('直接请求 matchDetails API...');

    const apiData = await page.evaluate(async () => {
        try {
            const res = await fetch('https://www.fotmob.com/api/matchDetails?matchId=4813561', {
                credentials: 'include',
                headers: {
                    'Accept': 'application/json',
                    'Origin': 'https://www.fotmob.com',
                    'Referer': 'https://www.fotmob.com/'
                }
            });
            return await res.json();
        } catch (e) {
            return { error: e.message };
        }
    });

    const isTurnstile = JSON.stringify(apiData).includes('TURNSTILE');
    console.log('数据状态:', isTurnstile ? '❌ TURNSTILE 错误' : '✅ VALID_DATA');
    console.log('数据大小:', JSON.stringify(apiData).length, 'bytes');

    if (isTurnstile === false && apiData.content) {
        const content = apiData.content;

        console.log('');
        console.log('═'.repeat(60));
        console.log('  🔍 API 结构分析');
        console.log('═'.repeat(60));

        // 打印 content 的键
        console.log('content 键:', Object.keys(content).join(', '));

        // 查找 stats
        let stats = content.stats;

        // 如果 stats 不是数组，尝试其他位置
        if (!Array.isArray(stats)) {
            // 检查 content 中的其他属性
            for (const key of Object.keys(content)) {
                if (Array.isArray(content[key])) {
                    console.log(`发现数组: content.${key} (${content[key].length} 项)`);
                }
            }
        }

        if (Array.isArray(stats)) {
            console.log('');
            console.log('═'.repeat(60));
            console.log('  📊 统计分组');
            console.log('═'.repeat(60));

            stats.forEach((s, i) => {
                console.log(`  [${i}] ${s.title || s.type || '未知'}`);
            });

            // 查找 xG
            const xgStats = stats.find(s => {
                const title = (s.title || s.type || '').toLowerCase();
                return title.includes('expected') || title.includes('xg');
            });

            if (xgStats) {
                console.log('');
                console.log('═'.repeat(60));
                console.log('  🎯 xG 数据');
                console.log('═'.repeat(60));
                console.log('分组:', xgStats.title);

                if (xgStats.stats && Array.isArray(xgStats.stats)) {
                    xgStats.stats.forEach((stat, i) => {
                        console.log(`  [${i}]`, JSON.stringify(stat));
                    });
                }
            }
        }

        // 尝试从其他位置查找 xG
        console.log('');
        console.log('═'.repeat(60));
        console.log('  🔎 搜索 xG 数据');
        console.log('═'.repeat(60));

        // 递归搜索
        const findXg = (obj, path = '') => {
            if (!obj || typeof obj !== 'object') return;

            if (Array.isArray(obj)) {
                obj.forEach((item, i) => findXg(item, `${path}[${i}]`));
            } else {
                for (const key of Object.keys(obj)) {
                    const val = obj[key];
                    const keyLower = key.toLowerCase();

                    if (keyLower.includes('xg') || keyLower.includes('expected')) {
                        console.log(`  找到: ${path}.${key} =`, JSON.stringify(val).substring(0, 100));
                    }

                    if (typeof val === 'object' && val !== null) {
                        findXg(val, `${path}.${key}`);
                    }
                }
            }
        };

        findXg(content, 'content');

    } else {
        console.log('');
        console.log('API 响应:', JSON.stringify(apiData).substring(0, 300));
    }

    await browser.close();
    console.log('');
    console.log('完成');
})();
