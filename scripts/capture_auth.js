/**
 * V172-L2-05 认证状态捕获脚本
 * ==============================
 *
 * 功能：在宿主机上启动可见浏览器，手动完成 Turnstile 验证后保存状态
 * 用途：将"已验证"的浏览器身份同步给 Docker 容器
 *
 * 使用方法：
 *   1. 在宿主机运行: node scripts/capture_auth.js
 *   2. 在弹出的浏览器中手动验证
 *   3. 浏览 1-2 场比赛详情页
 *   4. 回到终端按回车保存状态
 *
 * @module scripts/capture_auth
 * @version V172.500
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const readline = require('readline');

// ============================================================================
// 配置 - 必须与 MatchDetailEngine.js 完全一致
// ============================================================================

const AUTH_CONFIG = {
    // 目标站点
    targetUrl: 'https://www.fotmob.com/',

    // 指纹配置 - 必须与 MatchDetailEngine 一致
    fingerprint: {
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        viewport: { width: 1920, height: 1080 },
        deviceScaleFactor: 1,
        locale: 'en-US,en;q=0.9',
        timezoneId: 'Europe/London'
    },

    // 保存路径 - 对应 Docker Volume
    savePath: './data/browser_profile/browser_state.json',

    // 测试比赛 (用于验证身份有效性)
    testMatches: [
        'https://www.fotmob.com/matches/liverpool-vs-chelsea/4813729',
        'https://www.fotmob.com/matches/-/4813729'
    ]
};

// ============================================================================
// Logger
// ============================================================================

const log = {
    info: (msg) => console.log(`[${new Date().toISOString().slice(11, 19)}] ℹ️  ${msg}`),
    success: (msg) => console.log(`[${new Date().toISOString().slice(11, 19)}] ✅ ${msg}`),
    warn: (msg) => console.log(`[${new Date().toISOString().slice(11, 19)}] ⚠️  ${msg}`),
    error: (msg) => console.log(`[${new Date().toISOString().slice(11, 19)}] ❌ ${msg}`),
    step: (n, msg) => console.log(`\n[${new Date().toISOString().slice(11, 19)}] 📍 步骤 ${n}: ${msg}`)
};

// ============================================================================
// 主函数
// ============================================================================

async function captureAuth() {
    console.log('\n' + '═'.repeat(70));
    console.log('  V172-L2-05 认证状态捕获工具');
    console.log('  目的：绕过 Turnstile，生成可复用的浏览器身份');
    console.log('═'.repeat(70));

    // 显示指纹配置
    console.log('\n📋 当前指纹配置 (必须与 MatchDetailEngine 一致):');
    console.log('   User-Agent:', AUTH_CONFIG.fingerprint.userAgent);
    console.log('   Viewport:', `${AUTH_CONFIG.fingerprint.viewport.width}x${AUTH_CONFIG.fingerprint.viewport.height}`);
    console.log('   Locale:', AUTH_CONFIG.fingerprint.locale);
    console.log('   Timezone:', AUTH_CONFIG.fingerprint.timezoneId);
    console.log('   保存路径:', AUTH_CONFIG.savePath);

    // 检查是否有已保存的状态
    if (fs.existsSync(AUTH_CONFIG.savePath)) {
        const existingState = JSON.parse(fs.readFileSync(AUTH_CONFIG.savePath, 'utf8'));
        console.log('\n⚠️  发现已保存的状态:');
        console.log('   Cookies:', existingState.cookies ? existingState.cookies.length : 0);
        console.log('   Origins:', existingState.origins ? existingState.origins.length : 0);
    }

    log.step(1, '启动可见浏览器...');

    const browser = await chromium.launch({
        headless: false,  // 必须可见，用于手动验证
        slowMo: 50,        // 减慢操作速度，更像人类
        args: [
            '--disable-blink-features=AutomationControlled',
            '--start-maximized'
        ]
    });

    const context = await browser.newContext({
        userAgent: AUTH_CONFIG.fingerprint.userAgent,
        viewport: AUTH_CONFIG.fingerprint.viewport,
        deviceScaleFactor: AUTH_CONFIG.fingerprint.deviceScaleFactor,
        locale: AUTH_CONFIG.fingerprint.locale,
        timezoneId: AUTH_CONFIG.fingerprint.timezoneId,
        // 排除自动化标志
        ignoreHTTPSErrors: true
    });

    // 注入 Stealth 脚本
    await context.addInitScript(() => {
        // 禁用 webdriver
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

        // WebGL 伪装
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(p) {
            if (p === 37445) return 'Google Inc. (NVIDIA)';
            if (p === 37446) return 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Laptop GPU Direct3D11 vs_5_0 ps_5_0, D3D11)';
            return getParameter.apply(this, arguments);
        };

        // WebGL2 伪装
        if (typeof WebGL2RenderingContext !== 'undefined') {
            const getParameter2 = WebGL2RenderingContext.prototype.getParameter;
            WebGL2RenderingContext.prototype.getParameter = function(p) {
                if (p === 37445) return 'Google Inc. (NVIDIA)';
                if (p === 37446) return 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Laptop GPU Direct3D11 vs_5_0 ps_5_0, D3D11)';
                return getParameter2.apply(this, arguments);
            };
        }

        // 硬件伪装
        Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
        Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
    });

    const page = await context.newPage();

    log.step(2, '导航到 FotMob...');
    await page.goto(AUTH_CONFIG.targetUrl, { waitUntil: 'domcontentloaded' });

    console.log('\n' + '═'.repeat(70));
    console.log('  🛑 请在浏览器中完成以下操作:');
    console.log('═'.repeat(70));
    console.log('');
    console.log('  1. 如果出现 Turnstile 验证，请手动完成');
    console.log('  2. 点击任意一场比赛，进入详情页');
    console.log('  3. 确认能看到 xG 数据');
    console.log('  4. 可选：浏览 1-2 场其他比赛');
    console.log('');
    console.log('  ⏳ 完成后，回到此终端按 Enter 键保存状态...');
    console.log('');
    console.log('═'.repeat(70));

    // 等待用户按回车
    await waitForEnter();

    log.step(3, '保存浏览器状态...');

    // 确保目录存在
    const saveDir = path.dirname(AUTH_CONFIG.savePath);
    if (!fs.existsSync(saveDir)) {
        fs.mkdirSync(saveDir, { recursive: true });
    }

    // 保存状态
    const state = await context.storageState({ path: AUTH_CONFIG.savePath });

    log.success(`状态已保存到: ${AUTH_CONFIG.savePath}`);
    log.info(`Cookies: ${state.cookies ? state.cookies.length : 0}`);
    log.info(`Origins: ${state.origins ? state.origins.length : 0}`);

    // 验证 Cookie 有效性
    if (state.cookies && state.cookies.length > 0) {
        const fotmobCookies = state.cookies.filter(c => c.domain.includes('fotmob'));
        log.info(`FotMob Cookies: ${fotmobCookies.length}`);

        if (fotmobCookies.length > 0) {
            console.log('\n   主要 Cookies:');
            fotmobCookies.slice(0, 5).forEach(c => {
                console.log(`   - ${c.name}: ${c.value.substring(0, 30)}...`);
            });
        }
    }

    log.step(4, '验证身份有效性...');

    // 尝试访问测试比赛
    try {
        await page.goto(AUTH_CONFIG.testMatches[1], { timeout: 30000 });
        await page.waitForTimeout(3000);

        const content = await page.content();
        const hasTurnstile = content.includes('Turnstile') || content.includes('challenge');
        const hasMatchData = content.includes('xG') || content.includes('Expected');

        if (hasTurnstile) {
            log.warn('检测到 Turnstile，身份可能未完全验证');
            log.warn('建议：重新运行此脚本，多浏览几场比赛');
        } else if (hasMatchData) {
            log.success('身份验证成功！检测到比赛数据');
        } else {
            log.warn('未检测到比赛数据，请确认已进入比赛详情页');
        }
    } catch (e) {
        log.warn(`验证失败: ${e.message}`);
    }

    await browser.close();

    console.log('\n' + '═'.repeat(70));
    console.log('  ✅ 认证捕获完成！');
    console.log('═'.repeat(70));
    console.log('');
    console.log('  📁 状态文件:', AUTH_CONFIG.savePath);
    console.log('');
    console.log('  🚀 下一步：');
    console.log('     docker exec football_prediction_dev node scripts/ops/test_l2_engine.js');
    console.log('');
    console.log('═'.repeat(70));
}

// ============================================================================
// 工具函数
// ============================================================================

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

// ============================================================================
// 执行
// ============================================================================

captureAuth().catch(error => {
    console.error('\n❌ 捕获失败:', error.message);
    process.exit(1);
});
