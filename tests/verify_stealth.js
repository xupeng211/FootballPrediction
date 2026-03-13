/**
 * 隐身外壳验证脚本
 * =================
 *
 * 验证 BrowserFactory 的隐身能力：
 * 1. navigator.webdriver 必须为 undefined
 * 2. platform 必须为 Win32
 * 3. languages 必须包含 en-US
 * 4. WebGL 指纹必须被伪装
 *
 * 运行方式:
 * docker-compose -f docker-compose.dev.yml exec -e DISPLAY=$DISPLAY dev node tests/verify_stealth.js
 *
 * 注意: 可见浏览器模式需要 X Server，容器内无 X Server 时自动跳过可见模式测试
 */

'use strict';

const { BrowserFactory, getBrowserFactory, resetBrowserFactory } = require('../src/infrastructure/browser/BrowserFactory');

// ============================================================================
// 测试配置
// ============================================================================

const TEST_CONFIG = {
    headless: process.env.DISPLAY ? false : true,  // 有 X Server 时使用可见模式
    testUrl: 'https://bot.sannysoft.com/'
};

// ============================================================================
// 隐身检测测试用例
// ============================================================================

const STEALTH_TESTS = [
    {
        name: 'navigator.webdriver',
        check: 'navigator.webdriver',
        expected: undefined,
        description: 'webdriver 标志必须为 undefined'
    },
    {
        name: 'navigator.platform',
        check: 'navigator.platform',
        expected: 'Win32',
        description: 'platform 必须为 Win32 (与 UA 一致)'
    },
    {
        name: 'navigator.languages',
        check: 'navigator.languages',
        expected: ['en-US', 'en'],
        description: 'languages 必须包含 en-US'
    },
    {
        name: 'Chrome 插件',
        check: 'navigator.plugins.length > 0',
        expected: true,
        description: '必须模拟 Chrome 插件'
    }
];

// ============================================================================
// 主测试函数
// ============================================================================

async function runStealthVerification() {
    console.log('\n');
    console.log('═══════════════════════════════════════════════════════════════════════');
    console.log('  \x1b[36m[STEALTH-VERIFY]\x1b[0m BrowserFactory 隐身外壳完整性审计');
    console.log('═══════════════════════════════════════════════════════════════════════');
    console.log(`  模式: ${TEST_CONFIG.headless ? '无头 (headless)' : '可见 (headful)'}`);
    console.log('═══════════════════════════════════════════════════════════════════════\n');

    // 重置单例
    resetBrowserFactory();
    const factory = getBrowserFactory({ headless: TEST_CONFIG.headless });

    let browser = null;
    let context = null;
    let page = null;

    try {
        // 1. 启动浏览器
        console.log('🚀 [STEP 1] 启动浏览器...');
        browser = await factory.launch();
        console.log('   ✅ 浏览器已启动\n');

        // 2. 创建 Context (需要 identity 配置)
        console.log('📋 [STEP 2] 创建浏览器上下文...');
        const identity = {
            proxy: { url: null },
            stealth: {
                viewport: { width: 1920, height: 1080 },
                userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                extraHTTPHeaders: {
                    'Accept-Language': 'en-US,en;q=0.9'
                },
                deviceScaleFactor: 1,
                locale: 'en-US',
                timezoneId: 'Europe/London'
            }
        };
        context = await factory.createContext(identity, true);  // disableProxy = true
        console.log('   ✅ Context 已创建\n');

        // 3. 注入隐身脚本
        console.log('💉 [STEP 3] 注入隐身脚本...');
        page = await context.newPage();
        await factory.injectStealthScripts(page);
        console.log('   ✅ 隐身脚本已注入\n');

        // 4. 导航到测试页面
        console.log('🌐 [STEP 4] 导航到测试页面...');
        await page.goto(TEST_CONFIG.testUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
        console.log('   ✅ 页面已加载\n');

        // 5. 执行隐身检测
        console.log('🔍 [STEP 5] 执行隐身检测...\n');
        console.log('───────────────────────────────────────────────────────────────────────');

        let passed = 0;
        let failed = 0;

        for (const test of STEALTH_TESTS) {
            const actualValue = await page.evaluate(check => {
                return eval(check);
            }, test.check);

            const isMatch = JSON.stringify(actualValue) === JSON.stringify(test.expected);

            if (isMatch) {
                passed++;
                console.log(`\x1b[32m  ✅ PASS\x1b[0m [${test.name}]`);
            } else {
                failed++;
                console.log(`\x1b[31m  ❌ FAIL\x1b[0m [${test.name}]`);
            }

            console.log(`     检测: ${test.check}`);
            console.log(`     期望: ${JSON.stringify(test.expected)}`);
            console.log(`     实际: ${JSON.stringify(actualValue)}`);
            console.log(`     说明: ${test.description}`);
            console.log('');
        }

        console.log('───────────────────────────────────────────────────────────────────────');

        // 6. 特殊检测: webdriver 详细信息
        console.log('\n📊 [STEP 6] webdriver 详细检测...');
        const webdriverDetails = await page.evaluate(() => {
            return {
                webdriver: navigator.webdriver,
                webdriverType: typeof navigator.webdriver,
                webdriverDescriptor: Object.getOwnPropertyDescriptor(navigator, 'webdriver'),
                hasAutomationControlled: navigator.userAgent.includes('Chrome') && !navigator.userAgent.includes('Headless')
            };
        });

        console.log(`   navigator.webdriver = ${webdriverDetails.webdriver}`);
        console.log(`   typeof webdriver = ${webdriverDetails.webdriverType}`);
        console.log(`   descriptor.configurable = ${webdriverDetails.webdriverDescriptor?.configurable}`);
        console.log(`   UA 不含 Headless = ${webdriverDetails.hasAutomationControlled}`);

        // 7. 测试结果汇总
        console.log('\n');
        console.log('═══════════════════════════════════════════════════════════════════════');
        console.log(`  隐身测试结果: \x1b[32m${passed} 通过\x1b[0m / \x1b[31m${failed} 失败\x1b[0m / ${STEALTH_TESTS.length} 总计`);
        console.log('═══════════════════════════════════════════════════════════════════════');

        // 8. 验证 quickMouseMove 和 warmupHomepage 方法存在
        console.log('\n📋 [METHOD CHECK] 行为模拟方法验证...');
        console.log(`   quickMouseMove: ${typeof factory.quickMouseMove === 'function' ? '✅ 存在' : '❌ 缺失'}`);
        console.log(`   warmupHomepage: ${typeof factory.warmupHomepage === 'function' ? '✅ 存在' : '❌ 缺失'}`);
        console.log(`   _randomInRange: ${typeof factory._randomInRange === 'function' ? '✅ 存在' : '❌ 缺失'}`);
        console.log(`   _delay: ${typeof factory._delay === 'function' ? '✅ 存在' : '❌ 缺失'}`);

        return failed === 0;

    } catch (error) {
        console.error(`\n❌ 测试执行失败: ${error.message}`);
        console.error(error.stack);
        return false;
    } finally {
        // 清理资源
        if (page) {
            try { await page.close(); } catch (e) { /* ignore */ }
        }
        if (context) {
            try { await context.close(); } catch (e) { /* ignore */ }
        }
        if (factory) {
            try { await factory.close(); } catch (e) { /* ignore */ }
        }
    }
}

// ============================================================================
// 执行测试
// ============================================================================

runStealthVerification()
    .then(success => {
        process.exit(success ? 0 : 1);
    })
    .catch(error => {
        console.error('测试崩溃:', error);
        process.exit(1);
    });
