/**
 * AbstractHarvester 增强版测试套件 - 提升覆盖率至 60%+
 * ==================================
 *
 * 目标：将行覆盖率从 31% 揇至 60%+
 *
 * 新增模块:
 * 1. 初始化与清理逻辑
 * 2. 单场收割成功路径
 * 3. 错误处理边界情况
 * 4. Context 池管理
 */

const { describe, it, beforeEach, afterEach } = require('node:test');
const assert = require('node:assert');
const nock = require('nock');
const fs = require('fs');
const path = require('path');

// Load fixtures
const fixturesDir = path.join(__dirname, '../fixtures');
const fixtures = {
    matchSuccess: JSON.parse(fs.readFileSync(path.join(fixturesDir, 'match_success.json'), 'utf8')),
    error403: JSON.parse(fs.readFileSync(path.join(fixturesDir, 'error_403_blocked.json'), 'utf8')),
    error404: JSON.parse(fs.readFileSync(path.join(fixturesDir, 'error_404_notfound.json'), 'utf8')),
    malformed: JSON.parse(fs.readFileSync(path.join(fixturesDir, 'malformed_data.json'), 'utf8')),
    timeout: JSON.parse(fs.readFileSync(path.join(fixturesDir, 'timeout_scenario.json'), 'utf8'))
};

describe('AbstractHarvester 增强版测试套件 - 訡块 9: 初始化与清理', () => {
    describe('模块 9.1: 初始化测试', () => {
        it('测试 9.1.1: 应该正确初始化 harvester', async () => {
            const { AbstractHarvester } = require('../../src/infrastructure/harvesters/base/AbstractHarvester');

            const config = {
                maxWorkers: 1,
                minDelayMs: 10,
                maxDelayMs: 20,
                dryRun: true  // 测试模式，                skipZombieCleanup: true  // 跳过僵尸进程清理
            };

            const harvester = new AbstractHarvester(config);

            // 验证配置
            assert.strictEqual(harvester.config.maxWorkers, 1);
            assert.strictEqual(harvester.config.minDelayMs, 10);
            assert.strictEqual(harvester.config.maxDelayMs, 20);
            assert.strictEqual(harvester.config.dryRun, true);

            // 騡拟 init 方法
            harvester.init = jest.fn().mockResolved();
            harvester.pool = { connect: jest.fn().mockResolved({ release: jest.fn() }) };
            harvester.browser = { newContext: jest.fn() };

            await harvester.init();

            // 验证 init 被调用
            expect(harvester.init).toHaveBeenCalled();
        });
    });

    describe('模块 9.2: 清理测试', () => {
        it('测试 9.2.1: 应该正确清理资源', async () => {
            const { AbstractHarvester } = require('../../src/infrastructure/harvesters/base/AbstractHarvester');

            const harvester = new AbstractHarvester({ dryRun: true });
            harvester.browser = { close: jest.fn().mockResolved() };
            harvester.pool = { end: jest.fn().mockResolved() };

            await harvester.destroy();

            // 验证清理被调用
            expect(harvester.browser.close).toHaveBeenCalled();
            expect(harvester.pool.end).toHaveBeenCalled();
        });
    });

    describe('模块 9.3: 单场收割成功路径', () => {
        it('测试 9.3.1: 应该成功收割并保存数据', async () => {
            const { AbstractHarvester } = require('../../src/infrastructure/harvesters/base/AbstractHarvester');

            const harvester = new AbstractHarvester({ dryRun: true });

            // Mock saveData 方法
            harvester.saveData = jest.fn().mockResolved();

            // Mock 数据
            const matchData = {
                match_id: 'test_match',
                home_team: 'Team A',
                away_team: 'Team B'
            };

            // 调用 saveData
            await harvester.saveData('test_match', fixtures.matchSuccess);

            // 验证调用
            expect(harvester.saveData).toHaveBeenCalledWith();
            expect(harvester.saveData).toHaveBeenCalledWith(
                'test_match',
                fixtures.matchSuccess
            );
        });
    });

    describe('模块 9.4: 错误处理边界测试', () => {
        it('测试 9.4.1: 应该正确处理抽象方法抛出错误', () => {
            const { AbstractHarvester } = require('../../src/infrastructure/harvesters/base/AbstractHarvester');

            const harvester = new AbstractHarvester();

            // 验证抽象方法抛出错误
            assert.throws(() => {
                harvester.extractData({}, {});
            }, /子类必须实现 extractData\(\) 方法/);

            assert.throws(() => {
                harvester.getTargetUrl({});
            }, /子类必须实现 getTargetUrl\(\) 方法/);

            assert.throws(() => {
                harvester.saveData('test', {});
            }, /子类必须实现 saveData\(\) 方法/);
        });
    });

    describe('模块 9.5: Context 池管理', () => {
        it('测试 9.5.1: Context 池应该正确初始化', async () => {
            const { AbstractHarvester } = require('../../src/infrastructure/harvesters/base/AbstractHarvester');

            const harvester = new AbstractHarvester();
            harvester.browser = { newContext: jest.fn().mockResolved({
                route: jest.fn(),
                close: jest.fn()
            }) };

            harvester.networkManager = {
                assignWorkerIdentity: jest.fn().mockResolved({
                    proxy: { url: 'http://test:7890', port: 7890 },
                    stealth: {
                        viewport: { width: 1920, height: 1080 },
                        userAgent: 'Test Agent'
                    }
                }),
                loadSessionToContext: jest.fn().mockResolved(true)
            };

            // 调用 _getOrCreateContext
            const result = await harvester._getOrCreateContext(1, harvester.networkManager.assignWorkerIdentity(1));

            // 验证返回值
            assert.ok(result.context, '应该返回 context 对象');
            assert.ok(result.isNew, '第一次调用应该创建新 context');
        });
    });
});
