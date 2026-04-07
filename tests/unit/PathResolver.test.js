'use strict';

const { afterEach, describe, it } = require('node:test');
const assert = require('node:assert');
const path = require('node:path');
const fs = require('node:fs');

const {
  PathResolver,
  getPathResolver,
  resetPathResolver
} = require('../../src/infrastructure/utils/PathResolver');

describe('PathResolver', () => {
  const originalExistsSync = fs.existsSync;
  const originalMkdirSync = fs.mkdirSync;
  const originalCwd = process.cwd;
  const originalConsoleError = console.error;

  afterEach(() => {
    fs.existsSync = originalExistsSync;
    fs.mkdirSync = originalMkdirSync;
    process.cwd = originalCwd;
    console.error = originalConsoleError;
    delete process.env.KUBERNETES_SERVICE_HOST;
    delete process.env.DOCKER_CONTAINER;
    resetPathResolver();
  });

  it('应基于显式 appRoot 暴露统一路径与摘要信息', () => {
    const resolver = new PathResolver({
      appRoot: '/workspace/app',
      isContainer: true
    });

    assert.strictEqual(resolver.getBrowserStatePath(), '/workspace/app/data/browser_profile/browser_state.json');
    assert.strictEqual(resolver.getSessionsPath(), '/workspace/app/data/sessions');
    assert.strictEqual(resolver.getNetworkPath(), '/workspace/app/data/network');
    assert.strictEqual(resolver.getRegistryPath(), '/workspace/app/data/registry');
    assert.strictEqual(resolver.getConfigPath(), '/workspace/app/config');
    assert.strictEqual(resolver.getRegistryLockPath(), '/workspace/app/config/.registry.lock');
    assert.deepStrictEqual(resolver.getLockDirs(), [
      '/workspace/app/data/network',
      '/workspace/app/data/registry',
      '/workspace/app/config'
    ]);
    assert.deepStrictEqual(resolver.getLockFiles(), ['/workspace/app/config/.registry.lock']);
    assert.strictEqual(resolver.getLogsPath(), '/workspace/app/logs');
    assert.strictEqual(resolver.getRegressionPath(), '/workspace/app/data/regression');
    assert.strictEqual(resolver.resolve('/app/config/recon.json'), '/workspace/app/config/recon.json');
    assert.strictEqual(resolver.resolve('logs/app.log'), '/workspace/app/logs/app.log');
    assert.deepStrictEqual(resolver.getSummary(), {
      isContainer: true,
      appRoot: '/workspace/app',
      paths: {
        data: '/workspace/app/data',
        dataBrowserProfile: '/workspace/app/data/browser_profile',
        dataNetwork: '/workspace/app/data/network',
        dataRegistry: '/workspace/app/data/registry',
        dataSessions: '/workspace/app/data/sessions',
        dataRegression: '/workspace/app/data/regression',
        dataLogs: '/workspace/app/data/logs',
        config: '/workspace/app/config',
        logs: '/workspace/app/logs',
        browserState: '/workspace/app/data/browser_profile/browser_state.json',
        registryLock: '/workspace/app/config/.registry.lock'
      },
      environment: {
        nodeEnv: process.env.NODE_ENV,
        cwd: originalCwd()
      }
    });
  });

  it('应检测容器环境、查找项目根目录并在找不到时回退到 cwd', () => {
    const resolver = new PathResolver({
      appRoot: '/tmp/app',
      isContainer: false
    });

    fs.existsSync = (targetPath) => targetPath === '/.dockerenv';
    assert.strictEqual(resolver._detectContainer(), true);

    fs.existsSync = (targetPath) => targetPath === '/app/package.json';
    assert.strictEqual(resolver._detectContainer(), true);

    fs.existsSync = () => false;
    process.env.KUBERNETES_SERVICE_HOST = 'cluster';
    assert.strictEqual(resolver._detectContainer(), true);

    delete process.env.KUBERNETES_SERVICE_HOST;
    process.env.DOCKER_CONTAINER = '1';
    assert.strictEqual(resolver._detectContainer(), true);

    delete process.env.DOCKER_CONTAINER;
    process.cwd = () => '/tmp/project/src/lib';
    fs.existsSync = (targetPath) => targetPath === path.join('/tmp/project', 'package.json');
    assert.strictEqual(resolver._findProjectRoot(), '/tmp/project');

    fs.existsSync = () => false;
    assert.strictEqual(resolver._findProjectRoot(), '/tmp/project/src/lib');
  });

  it('ensureDir、ensureAllDirs、exists 与单例函数应按预期工作', () => {
    const mkdirCalls = [];
    const errorLogs = [];
    const resolver = new PathResolver({
      appRoot: '/tmp/sample-app',
      isContainer: false
    });

    fs.existsSync = (targetPath) => targetPath === '/tmp/sample-app/config';
    fs.mkdirSync = (targetPath, options) => {
      mkdirCalls.push({ targetPath, options });
    };

    assert.strictEqual(resolver.ensureDir('/tmp/sample-app/data'), true);
    assert.deepStrictEqual(mkdirCalls[0], {
      targetPath: '/tmp/sample-app/data',
      options: { recursive: true }
    });

    fs.mkdirSync = () => {
      throw new Error('permission denied');
    };
    console.error = (message) => {
      errorLogs.push(message);
    };
    assert.strictEqual(resolver.ensureDir('/tmp/forbidden'), false);
    assert.ok(errorLogs.some((message) => message.includes('permission denied')));

    const ensured = [];
    resolver.ensureDir = (dir) => {
      ensured.push(dir);
      return true;
    };
    resolver.ensureAllDirs();
    assert.deepStrictEqual(ensured, [
      '/tmp/sample-app/data',
      '/tmp/sample-app/data/browser_profile',
      '/tmp/sample-app/data/network',
      '/tmp/sample-app/data/registry',
      '/tmp/sample-app/data/sessions',
      '/tmp/sample-app/data/regression',
      '/tmp/sample-app/data/logs',
      '/tmp/sample-app/config'
    ]);

    fs.existsSync = (targetPath) => targetPath === '/tmp/sample-app/config';
    assert.strictEqual(resolver.exists('/tmp/sample-app/config'), true);
    assert.strictEqual(resolver.exists('/tmp/sample-app/missing'), false);

    const first = getPathResolver({ appRoot: '/tmp/one', isContainer: false });
    const second = getPathResolver({ appRoot: '/tmp/two', isContainer: true });
    assert.strictEqual(first, second);
    assert.strictEqual(first.appRoot, '/tmp/one');
    resetPathResolver();
    const third = getPathResolver({ appRoot: '/tmp/three', isContainer: true });
    assert.notStrictEqual(first, third);
    assert.strictEqual(third.appRoot, '/tmp/three');
  });
});
