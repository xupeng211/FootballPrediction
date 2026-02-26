/**
 * V172-L2-04 简化版 Stealth 测试
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

async function test() {
    const profilePath = '/app/data/browser_profile';
    const statePath = path.join(profilePath, 'browser_state.json');

    console.log('=== V172-L2-04 Stealth 测试 ===');
    console.log('Profile 路径:', profilePath);
    console.log('代理:', process.env.HTTPS_PROXY);

    // 检查是否有保存的状态
    if (fs.existsSync(statePath)) {
        console.log('✅ 发现已保存的浏览器状态');
        const state = JSON.parse(fs.readFileSync(statePath, 'utf8'));
        console.log('   Cookies:', state.cookies ? state.cookies.length : 0);
    } else {
        console.log('⚠️  无已保存状态，将创建新状态');
    }

    const browser = await chromium.launch({
        headless: true,
        proxy: { server: process.env.HTTPS_PROXY }
    });

    const contextOptions = {
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
    };

    if (fs.existsSync(statePath)) {
        contextOptions.storageState = statePath;
    }

    const context = await browser.newContext(contextOptions);

    // 注入 WebGL 伪装
    await context.addInitScript(() => {
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(p) {
            if (p === 37445) return 'Google Inc. (NVIDIA)';
            if (p === 37446) return 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3060)';
            return getParameter.apply(this, arguments);
        };
    });

    const page = await context.newPage();

    console.log('访问 FotMob 首页...');
    await page.goto('https://www.fotmob.com/', { timeout: 30000 });
    await page.waitForTimeout(3000);

    const title = await page.title();
    console.log('页面标题:', title);

    // 保存状态
    if (!fs.existsSync(profilePath)) {
        fs.mkdirSync(profilePath, { recursive: true });
    }
    const state = await context.storageState();
    fs.writeFileSync(statePath, JSON.stringify(state, null, 2));
    console.log('✅ 浏览器状态已保存');

    await browser.close();
    console.log('完成');
}

test().catch(e => console.error('错误:', e.message));
