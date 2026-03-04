/**
 * 测试真实浏览器 Cookies 是否有效
 */
const { chromium } = require('playwright');

const STEALTH_SCRIPT = `
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
    Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });
    delete navigator.__proto__.webdriver;
    window.chrome = { runtime: {} };
`;

async function test() {
    console.log('启动浏览器测试...');
    const browser = await chromium.launch({
        headless: true,
        args: [
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox',
            '--disable-setuid-sandbox'
        ]
    });

    const context = await browser.newContext({
        storageState: './data/browser_profile/browser_state.json',
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
    });

    await context.addInitScript(STEALTH_SCRIPT);
    const page = await context.newPage();

    // 先访问首页
    console.log('访问 FotMob 首页...');
    await page.goto('https://www.fotmob.com/', { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);

    // 然后访问比赛页面
    console.log('访问比赛详情页...');
    await page.goto('https://www.fotmob.com/matches/-/4813729', { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(3000);

    const content = await page.content();
    const hasTurnstile = content.includes('Turnstile') || content.includes('challenge') || content.includes('cf-challenge');
    const hasData = content.includes('xG') || content.includes('Expected') || content.includes('Expected Goals');
    const hasError = content.includes('error') || content.includes('Error');

    console.log('\n========== 测试结果 ==========');
    console.log('Has Turnstile/Challenge:', hasTurnstile);
    console.log('Has Match Data:', hasData);
    console.log('Has Error:', hasError);
    console.log('==============================\n');

    // 显示部分内容用于调试
    if (!hasData) {
        console.log('页面内容片段:', content.substring(0, 500));
    }

    await browser.close();
}

test().catch(console.error);
