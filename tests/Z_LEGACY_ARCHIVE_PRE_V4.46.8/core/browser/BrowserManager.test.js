/**
 * BrowserManager 单元测试
 * @module tests/core/browser/BrowserManager.test
 */

'use strict';

const assert = require('assert');
const { BrowserManager } = require('../../../src/core/browser');
const { StealthInjector } = require('../../../src/core/browser/StealthInjector');

// ============================================================================
// 测试用例
// ============================================================================

async function testConstructor() {
    console.log('测试: BrowserManager 构造函数');

    const manager = new BrowserManager({
        workerId: 5,
        proxyPort: 7895,
        headless: true,
        silent: true
    });

    assert.strictEqual(manager.workerId, 5);
    assert.strictEqual(manager.proxyPort, 7895);
    assert.strictEqual(manager.headless, true);
    assert.strictEqual(manager.currentProxyPort, 7895);
    assert.ok(manager.userDataDir.includes('worker_5'));

    // 默认值测试
    const defaultManager = new BrowserManager();
    assert.strictEqual(defaultManager.workerId, 1);
    assert.strictEqual(defaultManager.proxyPort, 7890);

    console.log('✅ BrowserManager 构造函数测试通过');
}

async function testGetProxyServer() {
    console.log('测试: getProxyServer 方法');

    const manager = new BrowserManager({
        workerId: 1,
        proxyPort: 7891,
        silent: true
    });

    const proxyServer = manager.getProxyServer();
    assert.ok(proxyServer.includes('7891'));

    console.log('✅ getProxyServer 测试通过');
}

async function testGetRandomUA() {
    console.log('测试: getRandomUA 方法');

    const manager = new BrowserManager({ silent: true });

    const ua = manager.getRandomUA();
    assert.ok(typeof ua === 'string');
    assert.ok(ua.includes('Mozilla'));

    console.log('✅ getRandomUA 测试通过');
}

async function testGetRandomViewport() {
    console.log('测试: getRandomViewport 方法');

    const manager = new BrowserManager({ silent: true });

    const viewport = manager.getRandomViewport();
    assert.ok('width' in viewport);
    assert.ok('height' in viewport);
    assert.ok(viewport.width > 0);
    assert.ok(viewport.height > 0);

    console.log('✅ getRandomViewport 测试通过');
}

async function testGetLaunchArgs() {
    console.log('测试: getLaunchArgs 方法');

    const manager = new BrowserManager({ silent: true });

    const args = manager.getLaunchArgs();
    assert.ok(Array.isArray(args));
    assert.ok(args.length > 0);
    assert.ok(args.includes('--disable-dev-shm-usage'));

    console.log('✅ getLaunchArgs 测试通过');
}

async function testCheckCookieExpiry() {
    console.log('测试: checkCookieExpiry 方法');

    const manager = new BrowserManager({ silent: true });

    // 测试不存在的文件
    const result1 = manager.checkCookieExpiry('/non/existent/path.json');
    assert.strictEqual(result1.valid, false);
    assert.strictEqual(result1.reason, 'NOT_FOUND');

    console.log('✅ checkCookieExpiry 测试通过');
}

async function testSwitchProxyPort() {
    console.log('测试: switchProxyPort 方法');

    const manager = new BrowserManager({
        proxyPort: 7890,
        silent: true
    });

    assert.strictEqual(manager.currentProxyPort, 7890);

    manager.switchProxyPort(7895);
    assert.strictEqual(manager.currentProxyPort, 7895);

    console.log('✅ switchProxyPort 测试通过');
}

async function testGetNextProxyPort() {
    console.log('测试: getNextProxyPort 方法');

    const manager = new BrowserManager({
        proxyPort: 7890,
        silent: true
    });

    const nextPort = manager.getNextProxyPort();
    assert.ok(typeof nextPort === 'number');
    assert.ok(nextPort >= 7890 && nextPort <= 7911);

    console.log('✅ getNextProxyPort 测试通过');
}

async function testGetStatus() {
    console.log('测试: getStatus 方法');

    const manager = new BrowserManager({
        workerId: 3,
        proxyPort: 7893,
        silent: true
    });

    const status = manager.getStatus();

    assert.strictEqual(status.workerId, 3);
    assert.strictEqual(status.currentProxyPort, 7893);
    assert.strictEqual(status.hasBrowser, false);
    assert.strictEqual(status.hasContext, false);
    assert.strictEqual(status.hasPage, false);
    assert.ok(status.userDataDir.includes('worker_3'));

    console.log('✅ getStatus 测试通过');
}

async function testStealthInjectorConstructor() {
    console.log('测试: StealthInjector 构造函数');

    const injector = new StealthInjector({
        hardwareConcurrency: 16,
        deviceMemory: 16,
        silent: true
    });

    assert.strictEqual(injector.hardwareConcurrency, 16);
    assert.strictEqual(injector.deviceMemory, 16);

    console.log('✅ StealthInjector 构造函数测试通过');
}

async function testStealthInjectorGenerateScript() {
    console.log('测试: StealthInjector generateScript 方法');

    const injector = new StealthInjector({
        hardwareConcurrency: 12,
        deviceMemory: 32,
        silent: true
    });

    const script = injector.generateScript();

    assert.ok(typeof script === 'function');

    console.log('✅ StealthInjector generateScript 测试通过');
}

async function testSafeClose() {
    console.log('测试: safeClose 方法');

    const manager = new BrowserManager({ silent: true });

    // 在没有浏览器实例时调用应该不报错
    await manager.safeClose();

    assert.strictEqual(manager.browser, null);
    assert.strictEqual(manager.context, null);
    assert.strictEqual(manager.page, null);

    console.log('✅ safeClose 测试通过');
}

// ============================================================================
// 运行测试
// ============================================================================

async function runTests() {
    console.log('\n========================================');
    console.log('BrowserManager 单元测试');
    console.log('========================================\n');

    try {
        await testConstructor();
        await testGetProxyServer();
        await testGetRandomUA();
        await testGetRandomViewport();
        await testGetLaunchArgs();
        await testCheckCookieExpiry();
        await testSwitchProxyPort();
        await testGetNextProxyPort();
        await testGetStatus();
        await testStealthInjectorConstructor();
        await testStealthInjectorGenerateScript();
        await testSafeClose();

        console.log('\n========================================');
        console.log('✅ 所有 BrowserManager 测试通过');
        console.log('========================================\n');

    } catch (error) {
        console.error('\n❌ 测试失败:', error.message);
        console.error(error.stack);
        process.exit(1);
    }
}

// 入口
runTests();
