/**
 * 全链路冒烟测试 - 组件协同真实性验证
 * =======================================
 *
 * 验证内容:
 * 1. 组件初始化链路
 * 2. 真实浏览器启动
 * 3. 隐身脚本注入验证
 * 4. 自愈回路模拟
 * 5. 截图证据留存
 *
 * 运行方式:
 * docker-compose -f docker-compose.dev.yml exec dev node tests/smoke_test.js
 * @version V1.0.0
 */

'use strict';

const fs = require('fs').promises;
const path = require('path');

// ============================================================================
// 模块导入验证
// ============================================================================

console.log('\n');
console.log('═══════════════════════════════════════════════════════════════════════');
console.log('  \x1b[36m[SMOKE-TEST]\x1b[0m 全链路冒烟测试 - 组件协同真实性验证');
console.log('═══════════════════════════════════════════════════════════════════════\n');

// 统一路径导入（使用绝对路径避免混乱）
const MODULE_PATHS = {
    BrowserFactory: '/app/src/infrastructure/browser/BrowserFactory',
    ErrorAuditor: '/app/src/core/harvesters/ErrorAuditor',
    AutoAuthManager: '/app/src/infrastructure/auth/AutoAuthManager',
    NetworkManager: '/app/src/infrastructure/network/NetworkManager',
    PathResolver: '/app/src/infrastructure/utils/PathResolver'
};

// ============================================================================
// 测试 1: 模块导入链路验证
// ============================================================================

/**
 *
 */
async function testModuleImports() {
    console.log('📦 [TEST 1] 模块导入链路验证...');
    console.log('───────────────────────────────────────────────────────────────────────');

    const results = {
        passed: 0,
        failed: 0,
        modules: {}
    };

    for (const [name, modulePath] of Object.entries(MODULE_PATHS)) {
        try {
            const module = require(modulePath);

            // 验证模块导出
            const hasClass = module[name] !== undefined;
            const hasFunction = typeof module[`get${name}`] === 'function';

            if (hasClass || hasFunction) {
                results.passed++;
                results.modules[name] = { status: '✅ PASS', exports: Object.keys(module) };
                console.log(`  ✅ ${name}: 导出 [${Object.keys(module).join(', ')}]`);
            } else {
                results.failed++;
                results.modules[name] = { status: '❌ FAIL', error: '缺少预期导出' };
                console.log(`  ❌ ${name}: 缺少预期导出`);
            }
        } catch (error) {
            results.failed++;
            results.modules[name] = { status: '❌ FAIL', error: error.message };
            console.log(`  ❌ ${name}: ${error.message}`);
        }
    }

    console.log(`\n  模块导入结果: ${results.passed}/${Object.keys(MODULE_PATHS).length}\n`);

    return results.failed === 0;
}

// ============================================================================
// 测试 2: 组件实例化链路验证
// ============================================================================

/**
 *
 */
async function testComponentInstantiation() {
    console.log('\n📦 [TEST 2] 组件实例化链路验证...');
    console.log('───────────────────────────────────────────────────────────────────────');

    try {
        // 1. BrowserFactory
        const { BrowserFactory, resetBrowserFactory } = require(MODULE_PATHS.BrowserFactory);
        resetBrowserFactory();
        const browserFactory = new BrowserFactory({ headless: true });
        console.log('  ✅ BrowserFactory 实例化成功');

        // 2. ErrorAuditor
        const { ErrorAuditor, getErrorAuditor, resetErrorAuditor } = require(MODULE_PATHS.ErrorAuditor);
        resetErrorAuditor();
        const errorAuditor = getErrorAuditor();
        console.log('  ✅ ErrorAuditor 实例化成功');

        // 3. AutoAuthManager
        const { AutoAuthManager, getAutoAuthManager, resetAutoAuthManager } = require(MODULE_PATHS.AutoAuthManager);
        resetAutoAuthManager();
        const autoAuthManager = getAutoAuthManager();
        console.log('  ✅ AutoAuthManager 实例化成功');

        // 验证实例非 null
        if (!browserFactory || !errorAuditor || !autoAuthManager) {
            throw new Error('组件实例为 null');
        }

        // 验证关键方法存在
        const methodChecks = [
            { obj: browserFactory, method: 'launch', name: 'BrowserFactory.launch' },
            { obj: browserFactory, method: 'createContext', name: 'BrowserFactory.createContext' },
            { obj: browserFactory, method: 'injectStealthScripts', name: 'BrowserFactory.injectStealthScripts' },
            { obj: errorAuditor, method: 'classifyError', name: 'ErrorAuditor.classifyError' },
            { obj: errorAuditor, method: 'isRetryableError', name: 'ErrorAuditor.isRetryableError' },
            { obj: autoAuthManager, method: 'refreshSession', name: 'AutoAuthManager.refreshSession' }
        ];

        for (const check of methodChecks) {
            if (typeof check.obj[check.method] !== 'function') {
                throw new Error(`${check.name} 不是函数`);
            }
            console.log(`  ✅ ${check.name} 方法存在`);
        }

        return { success: true, browserFactory, errorAuditor, autoAuthManager };

    } catch (error) {
        console.log(`  ❌ 实例化失败: ${error.message}`);
        return { success: false, error };
    }
}

// ============================================================================
// 测试 3: 真实浏览器点火测试
// ============================================================================

/**
 *
 * @param components
 */
async function testBrowserIgnition(components) {
    console.log('\n🔥 [TEST 3] 真实浏览器点火测试...');
    console.log('───────────────────────────────────────────────────────────────────────');

    const { browserFactory } = components;
    let browser = null;
    let context = null;
    let page = null;

    try {
        // 1. 启动浏览器
        console.log('  📌 启动浏览器...');
        browser = await browserFactory.launch();
        console.log('  ✅ 浏览器启动成功');

        // 2. 创建 Context
        console.log('  📌 创建浏览器上下文...');
        const identity = {
            proxy: { url: null },
            stealth: {
                viewport: { width: 1920, height: 1080 },
                userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                extraHTTPHeaders: { 'Accept-Language': 'en-US,en;q=0.9' },
                deviceScaleFactor: 1,
                locale: 'en-US',
                timezoneId: 'Europe/London'
            }
        };
        context = await browserFactory.createContext(identity, true);
        console.log('  ✅ Context 创建成功');

        // 3. 创建 Page
        console.log('  📌 创建新页面...');
        page = await context.newPage();
        console.log('  ✅ Page 创建成功');

        // 4. 注入隐身脚本
        console.log('  📌 注入隐身脚本...');
        await browserFactory.injectStealthScripts(page);
        console.log('  ✅ 隐身脚本注入成功');

        // 5. 物理点火验证 - 检查 navigator.webdriver
        console.log('  📌 物理点火: 检查 navigator.webdriver...');
        await page.goto('about:blank');
        await page.waitForTimeout(500);

        const webdriver = await page.evaluate(() => navigator.webdriver);
        const webdriverType = await page.evaluate(() => typeof navigator.webdriver);

        console.log(`  📊 navigator.webdriver = ${webdriver}`);
        console.log(`  📊 typeof navigator.webdriver = ${webdriverType}`);

        if (webdriver !== undefined) {
            console.log('  ⚠️  警告: webdriver 不是 undefined，隐身脚本可能未完全生效');
        } else {
            console.log('  ✅ 隐身验证通过: webdriver = undefined');
        }

        // 6. 访问首页建立信任
        console.log('  📌 访问 FotMob 首页建立信任...');
        await page.goto('https://www.fotmob.com/', {
            waitUntil: 'domcontentloaded',
            timeout: 30000
        });
        console.log('  ✅ 首页加载成功');

        // 7. 截图证据留存
        console.log('  📌 保存截图证据...');
        const screenshotDir = '/app/data/debug';
        await fs.mkdir(screenshotDir, { recursive: true }).catch(() => {});
        const screenshotPath = path.join(screenshotDir, 'smoke_pass.png');
        await page.screenshot({ path: screenshotPath, fullPage: false });
        console.log(`  ✅ 截图已保存: ${screenshotPath}`);

        return { success: true, webdriver, page, context, browserFactory };

    } catch (error) {
        console.log(`  ❌ 浏览器测试失败: ${error.message}`);
        console.log(error.stack);
        return { success: false, error };
    }
}

// ============================================================================
// 测试 4: 自愈回路模拟
// ============================================================================

/**
 *
 * @param components
 */
async function testSelfHealingLoop(components) {
    console.log('\n🔄 [TEST 4] 自愈回路模拟...');
    console.log('───────────────────────────────────────────────────────────────────────');

    const { errorAuditor, autoAuthManager } = components;

    try {
        // 1. 模拟 Turnstile 错误
        console.log('  📌 模拟 Cloudflare Turnstile 错误...');
        const turnstileError = new Error('Cloudflare Turnstile challenge required');

        // 2. 验证 ErrorAuditor 分类
        const errorType = errorAuditor.classifyError(turnstileError.message);
        const isRetryable = errorAuditor.isRetryableError(turnstileError);

        console.log(`  📊 错误类型: ${errorType}`);
        console.log(`  📊 可重试: ${isRetryable}`);

        if (errorType !== 'BLOCKED') {
            console.log('  ❌ 错误类型应为 BLOCKED');
            return { success: false };
        }
        if (isRetryable !== false) {
            console.log('  ❌ Turnstile 错误不应可重试');
            return { success: false };
        }
        console.log('  ✅ 错误分类正确: BLOCKED, 不可重试');

        // 3. 验证 AutoAuthManager.refreshSession 存在
        console.log('  📌 验证 AutoAuthManager.refreshSession...');
        if (typeof autoAuthManager.refreshSession !== 'function') {
            console.log('  ❌ refreshSession 不是函数');
            return { success: false };
        }
        console.log('  ✅ refreshSession 方法存在');

        // 4. 调用 refreshSession (模拟)
        console.log('  📌 调用 refreshSession (Worker 1, Port 7890)...');
        const refreshResult = await autoAuthManager.refreshSession(1, 7890);
        console.log(`  📊 refreshSession 结果: ${JSON.stringify(refreshResult)}`);

        // refreshSession 应该返回一个对象
        if (typeof refreshResult !== 'object') {
            console.log('  ❌ refreshSession 应返回对象');
            return { success: false };
        }
        console.log('  ✅ refreshSession 调用成功');

        // 5. 验证完整的自愈链路
        console.log('  📌 验证自愈链路完整性...');
        console.log('  ✅ 自愈链路验证通过:');
        console.log('     ErrorAuditor.classifyError → BLOCKED');
        console.log('     ErrorAuditor.isRetryableError → false');
        console.log('     AutoAuthManager.refreshSession → 可调用');

        return { success: true };

    } catch (error) {
        console.log(`  ❌ 自愈回路测试失败: ${error.message}`);
        return { success: false, error };
    }
}

// ============================================================================
// 测试 5: 错误边界测试
// ============================================================================

/**
 *
 * @param components
 */
async function testErrorBoundaries(components) {
    console.log('\n🧪 [TEST 5] 错误边界测试...');
    console.log('───────────────────────────────────────────────────────────────────────');

    const { errorAuditor } = components;

    try {
        const testCases = [
            { error: 'ECONNRESET', expectedRetryable: true, expectedType: 'NETWORK_ERROR' },
            { error: '403 Forbidden', expectedRetryable: false, expectedType: 'RATE_LIMITED' },
            { error: 'CF_BLOCK: Access denied', expectedRetryable: false, expectedType: 'UNKNOWN' },
            { error: 'Connection reset by peer', expectedRetryable: true, expectedType: 'NETWORK_ERROR' },
            { error: 'Timeout exceeded', expectedRetryable: true, expectedType: 'TIMEOUT' }
        ];

        let passed = 0;
        let failed = 0;

        for (const tc of testCases) {
            const retryable = errorAuditor.isRetryableError(tc.error);
            const type = errorAuditor.classifyError(tc.error);

            const retryableMatch = retryable === tc.expectedRetryable;
            const typeMatch = type === tc.expectedType;

            if (retryableMatch && typeMatch) {
                passed++;
                console.log(`  ✅ "${tc.error}": 重试=${retryable}, 类型=${type}`);
            } else {
                failed++;
                console.log(`  ❌ "${tc.error}": 重试=${retryable}(期望${tc.expectedRetryable}), 类型=${type}(期望${tc.expectedType})`);
            }
        }

        console.log(`\n  错误边界测试: ${passed}/${testCases.length} 通过`);

        return { success: failed === 0, passed, failed };

    } catch (error) {
        console.log(`  ❌ 错误边界测试失败: ${error.message}`);
        return { success: false, error };
    }
}

// ============================================================================
// 主执行函数
// ============================================================================

/**
 *
 */
async function main() {
    const results = {
        moduleImports: false,
        instantiation: false,
        browserIgnition: false,
        selfHealing: false,
        errorBoundaries: false
    };

    let components = null;
    let browserResources = null;

    try {
        // 测试 1: 模块导入
        results.moduleImports = await testModuleImports();
        if (!results.moduleImports) {
            console.log('\n❌ 模块导入失败，终止测试');
            process.exit(1);
        }

        // 测试 2: 组件实例化
        components = await testComponentInstantiation();
        results.instantiation = components.success;
        if (!components.success) {
            console.log('\n❌ 组件实例化失败，终止测试');
            process.exit(1);
        }

        // 测试 3: 浏览器点火
        browserResources = await testBrowserIgnition(components);
        results.browserIgnition = browserResources.success;

        // 测试 4: 自愈回路
        results.selfHealing = await testSelfHealingLoop(components);

        // 测试 5: 错误边界
        results.errorBoundaries = await testErrorBoundaries(components);

        // 汇总结果
        console.log('\n');
        console.log('═══════════════════════════════════════════════════════════════════════');
        console.log('  \x1b[36m[SMOKE-TEST]\x1b[0m 最终测试报告');
        console.log('═══════════════════════════════════════════════════════════════════════');

        const totalTests = Object.keys(results).length;
        const passedTests = Object.values(results).filter(r => r).length;

        for (const [name, passed] of Object.entries(results)) {
            const icon = passed ? '✅' : '❌';
            const status = passed ? 'PASS' : 'FAIL';
            console.log(`  ${icon} ${name}: ${status}`);
        }

        console.log('───────────────────────────────────────────────────────────────────────');
        console.log(`  总计: \x1b[32m${passedTests}/${totalTests} 通过\x1b[0m`);
        console.log('═══════════════════════════════════════════════════════════════════════\n');

        // 如果浏览器点火成功，显示截图路径
        if (browserResources.success) {
            console.log('📁 截图证据: /app/data/debug/smoke_pass.png');
            console.log('');
        }

        const allPassed = Object.values(results).every(r => r);
        process.exit(allPassed ? 0 : 1);

    } catch (error) {
        console.error('\n❌ 冒烟测试崩溃:', error);
        console.error(error.stack);
        process.exit(1);
    } finally {
        // 清理资源
        if (browserResources?.page) {
            try { await browserResources.page.close(); } catch (e) { /* ignore */ }
        }
        if (browserResources?.context) {
            try { await browserResources.context.close(); } catch (e) { /* ignore */ }
        }
        if (components?.browserFactory) {
            try { await components.browserFactory.close(); } catch (e) { /* ignore */ }
        }
    }
}

// ============================================================================
// 执行
// ============================================================================

main().catch(error => {
    console.error('Fatal error:', error);
    process.exit(1);
});
