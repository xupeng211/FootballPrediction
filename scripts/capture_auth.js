/**
 * V179-SMART-RESTART 认证状态捕获脚本
 * 使用 launchPersistentContext + 隐身模式
 */

const { chromium } = require('playwright');
const fs = require('fs');
const readline = require('readline');

const AUTH_CONFIG = {
    targetUrl: 'https://www.fotmob.com/',
    userDataDir: './data/browser_profile',
    savePath: './data/browser_profile/browser_state.json',
    testMatches: [
        'https://www.fotmob.com/matches/liverpool-vs-chelsea/4813729',
        'https://www.fotmob.com/matches/-/4813729'
    ]
};

const log = {
    info: (msg) => console.log(`[${new Date().toISOString().slice(11, 19)}] ${msg}`),
    success: (msg) => console.log(`[${new Date().toISOString().slice(11, 19)}] ${msg}`),
    warn: (msg) => console.log(`[${new Date().toISOString().slice(11, 19)}] ${msg}`),
    error: (msg) => console.log(`[${new Date().toISOString().slice(11, 19)}] ${msg}`),
    step: (n, msg) => console.log(`\n[${new Date().toISOString().slice(11, 19)}] 步骤 ${n}: ${msg}`)
};

async function captureAuth() {
    console.log('\n' + '='.repeat(70));
    console.log('  V179-SMART-RESTART 认证状态捕获工具');
    console.log('  使用 launchPersistentContext + 隐身模式');
    console.log('='.repeat(70));
    console.log('\n配置:');
    console.log('   User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36');
    console.log('   Viewport: 1920x1080');
    console.log('   数据目录:', AUTH_CONFIG.userDataDir);

    if (!fs.existsSync(AUTH_CONFIG.userDataDir)) {
        fs.mkdirSync(AUTH_CONFIG.userDataDir, { recursive: true });
    }

    log.step(1, '启动隐身持久化浏览器...');

    const context = await chromium.launchPersistentContext(AUTH_CONFIG.userDataDir, {
        headless: false,
        viewport: { width: 1920, height: 1080 },
        deviceScaleFactor: 1,
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        locale: 'en-US',
        timezoneId: 'Europe/London',
        args: [
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding',
            '--disable-features=IsolateOrigins,site-per-process',
            '--start-maximized'
        ],
        ignoreHTTPSErrors: true
    });

    const pages = context.pages();
    const page = pages.length > 0 ? pages[0] : await context.newPage();

    log.step(2, '导航到 FotMob...');
    await page.goto(AUTH_CONFIG.targetUrl, { waitUntil: 'domcontentloaded' });

    console.log('\n' + '='.repeat(70));
    console.log('  请在浏览器中完成以下操作:');
    console.log('='.repeat(70));
    console.log('');
    console.log('  1. 如果出现 Turnstile 验证，请手动完成');
    console.log('  2. 点击任意一场比赛，进入详情页');
    console.log('  3. 确认能看到 xG 数据');
    console.log('  4. 可选：浏览 1-2 场其他比赛');
    console.log('');
    console.log('  完成后，回到此终端按 Enter 键保存状态...');
    console.log('');
    console.log('='.repeat(70));

    await waitForEnter();

    log.step(3, '保存浏览器状态...');

    const state = await context.storageState({ path: AUTH_CONFIG.savePath });

    log.success(`状态已保存到: ${AUTH_CONFIG.savePath}`);
    log.info(`Cookies: ${state.cookies ? state.cookies.length : 0}`);

    if (state.cookies && state.cookies.length > 0) {
        const fotmobCookies = state.cookies.filter(c => c.domain.includes('fotmob'));
        log.info(`FotMob Cookies: ${fotmobCookies.length}`);
    }

    log.step(4, '验证身份有效性...');

    try {
        await page.goto(AUTH_CONFIG.testMatches[1], { timeout: 30000 });
        await page.waitForTimeout(3000);

        const content = await page.content();
        const hasTurnstile = content.includes('Turnstile') || content.includes('challenge');
        const hasMatchData = content.includes('xG') || content.includes('Expected');

        if (hasTurnstile) {
            log.warn('检测到 Turnstile，身份可能未完全验证');
        } else if (hasMatchData) {
            log.success('身份验证成功！检测到比赛数据');
        }
    } catch (e) {
        log.warn(`验证失败: ${e.message}`);
    }

    await context.close();

    console.log('\n' + '='.repeat(70));
    console.log('  认证捕获完成！');
    console.log('='.repeat(70));
}

function waitForEnter() {
    const rl = readline.createInterface({
        input: process.stdin,
        output: process.stdout
    });
    return new Promise(resolve => {
        rl.question('', () => {
            rl.close();
            resolve();
        });
    });
}

captureAuth().catch(error => {
    console.error('\n捕获失败:', error.message);
    process.exit(1);
});
