/**
 * 调试脚本：检查 FotMob 页面数据
 */
'use strict';

const { chromium } = require('playwright');

async function debug() {
    console.log('🔍 调试：检查 FotMob 页面数据...');

    const browser = await chromium.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    const context = await browser.newContext({
        viewport: { width: 1920, height: 1080 },
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    });

    const page = await context.newPage();

    // 访问首页预热
    console.log('🏠 访问 FotMob 首页...');
    await page.goto('https://www.fotmob.com/', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    // 访问比赛页面
    const matchUrl = 'https://www.fotmob.com/match/4803306';
    console.log('🎯 访问比赛页面:', matchUrl);

    await page.goto(matchUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(5000);

    // 检查页面内容
    const title = await page.title();
    console.log('📄 页面标题:', title);

    // 检查 __NEXT_DATA__
    const nextDataResult = await page.evaluate(() => {
        const script = document.getElementById('__NEXT_DATA__');
        if (!script) return { found: false };

        try {
            const data = JSON.parse(script.textContent);
            return {
                found: true,
                hasProps: !!data.props,
                hasPageProps: !!data.props?.pageProps,
                hasContent: !!data.props?.pageProps?.content,
                keys: Object.keys(data.props?.pageProps || {}),
                contentKeys: Object.keys(data.props?.pageProps?.content || {}),
                dataSize: script.textContent.length
            };
        } catch (e) {
            return { found: true, parseError: e.message };
        }
    });

    console.log('');
    console.log('=== __NEXT_DATA__ 检查结果 ===');
    console.log(JSON.stringify(nextDataResult, null, 2));

    // 检查是否有反爬挑战
    const challengeInfo = await page.evaluate(() => {
        return {
            hasTurnstile: !!document.querySelector('iframe[src*="turnstile"]'),
            hasCaptcha: !!document.querySelector('.g-recaptcha, #captcha, [data-captcha]'),
            bodyText: document.body.innerText.slice(0, 500)
        };
    });

    console.log('');
    console.log('=== 反爬检测 ===');
    console.log('Turnstile:', challengeInfo.hasTurnstile);
    console.log('Captcha:', challengeInfo.hasCaptcha);
    console.log('页面内容预览:', challengeInfo.bodyText.slice(0, 300));

    await browser.close();
    console.log('');
    console.log('✅ 调试完成');
}

debug().catch(e => console.error('调试失败:', e.message));
