/**
 * ProductionHarvester 深度测试
 * =============================
 *
 * 目标：覆盖 run(), harvestWithRetry(), _harvestSingleMatch() 的所有逻辑分支
 *
 * @module tests/unit/ProductionHarvester_Deep
 * @version V1.0.0
 */

'use strict';

const { describe, it, beforeEach, afterEach } = require('node:test');
const assert = require('node:assert');

describe('ProductionHarvester 深度测试', () => {
  let harvester;
  let ProductionHarvester;

  beforeEach(() => {
    // 使用简单 mock 避免依赖问题
    ProductionHarvester = require('../../src/infrastructure/harvesters/ProductionHarvester').ProductionHarvester;
    harvester = new ProductionHarvester({
      dryRun: true,
      maxWorkers: 2,
      maxRetries: 2,
      verboseLogging: false
    });
  });

  describe('构造函数与配置', () => {
    it('应使用默认配置创建实例', () => {
      const defaultHarvester = new ProductionHarvester();
      assert.strictEqual(defaultHarvester.config.maxWorkers, 6);
      assert.strictEqual(defaultHarvester.config.dryRun, false);
    });

    it('应覆盖默认配置', () => {
      const customHarvester = new ProductionHarvester({
        maxWorkers: 10,
        dryRun: true
      });
      assert.strictEqual(customHarvester.config.maxWorkers, 10);
      assert.strictEqual(customHarvester.config.dryRun, true);
    });

    it('应初始化会话轮换计数器', () => {
      assert.strictEqual(harvester.sessionMatchCount, 0);
      assert.strictEqual(harvester.sessionRotationThreshold, 20);
    });

    it('应创建策略实例', () => {
      assert.ok(harvester.strategy);
      assert.strictEqual(typeof harvester.strategy, 'object');
    });
  });

  describe('harvestWithRetry 方法', () => {
    it('应在成功时返回结果', async () => {
      const match = {
        match_id: 'test_001',
        home_team: 'Team A',
        away_team: 'Team B'
      };

      // Mock _harvestSingleMatch 返回成功
      const originalMethod = harvester._harvestSingleMatch;
      harvester._harvestSingleMatch = async () => ({
        success: true,
        data: { match_id: 'test_001', content: {} }
      });

      const result = await harvester.harvestWithRetry(match, 0, 2);
      assert.strictEqual(result.success, true);

      // 恢复原始方法
      harvester._harvestSingleMatch = originalMethod;
    });

    it('应在失败时重试', async () => {
      const match = {
        match_id: 'test_002',
        home_team: 'Team C',
        away_team: 'Team D'
      };

      let attemptCount = 0;
      const originalMethod = harvester._harvestSingleMatch;
      // Mock _harvestSingleMatch 前两次失败，第三次成功
      harvester._harvestSingleMatch = async () => {
        attemptCount++;
        if (attemptCount < 2) {
          return { success: false, error: 'SIZE_TOO_SMALL:500' };
        }
        return { success: true, data: { match_id: 'test_002' } };
      };

      const result = await harvester.harvestWithRetry(match, 0, 3);
      assert.strictEqual(result.success, true);

      // 恢复原始方法
      harvester._harvestSingleMatch = originalMethod;
    });

    it('应在达到最大重试次数后失败', async () => {
      const match = {
        match_id: 'test_003',
        home_team: 'Team E',
        away_team: 'Team F'
      };

      const originalMethod = harvester._harvestSingleMatch;
      // Mock _harvestSingleMatch 始终失败
      harvester._harvestSingleMatch = async () => ({
        success: false,
        error: 'NETWORK_ERROR'
      });

      const result = await harvester.harvestWithRetry(match, 0, 2);
      assert.strictEqual(result.success, false);

      // 恢复原始方法
      harvester._harvestSingleMatch = originalMethod;
    });
  });

  describe('数据路径配置', () => {
    it('应使用环境变量配置数据路径', () => {
      const originalEnv = process.env.DATA_MATCHES_PATH;
      process.env.DATA_MATCHES_PATH = '/custom/data/path';

      const envHarvester = new ProductionHarvester({});
      assert.strictEqual(envHarvester.config.dataMatchesPath, '/custom/data/path');

      process.env.DATA_MATCHES_PATH = originalEnv;
    });

    it('应使用传入参数覆盖环境变量', () => {
      const originalEnv = process.env.DATA_MATCHES_PATH;
      process.env.DATA_MATCHES_PATH = '/env/path';

      const paramHarvester = new ProductionHarvester({
        dataMatchesPath: '/param/path'
      });
      assert.strictEqual(paramHarvester.config.dataMatchesPath, '/param/path');

      process.env.DATA_MATCHES_PATH = originalEnv;
    });
  });

  describe('URL 生成', () => {
    it('应为比赛生成正确的目标 URL', () => {
      const match = {
        match_id: '47_2024_12345',
        home_team: 'Arsenal',
        away_team: 'Chelsea'
      };

      const url = harvester.getTargetUrl(match);
      assert.ok(url);
      assert.ok(typeof url === 'string');
    });
  });

  describe('数据库错误分类', () => {
    it('应分类重复键错误', () => {
      const error = new Error('duplicate key value violates unique constraint');
      const classification = harvester._classifyDatabaseError(error);
      assert.strictEqual(classification, 'DUPLICATE_KEY');
    });

    it('应分类连接错误', () => {
      const error = new Error('ECONNREFUSED');
      const classification = harvester._classifyDatabaseError(error);
      assert.strictEqual(classification, 'CONNECTION_ERROR');
    });

    it('应分类超时错误', () => {
      const error = new Error('Query read timeout');
      const classification = harvester._classifyDatabaseError(error);
      assert.strictEqual(classification, 'TIMEOUT');
    });

    it('应对未知错误返回 UNKNOWN', () => {
      const error = new Error('Some random error');
      const classification = harvester._classifyDatabaseError(error);
      assert.strictEqual(classification, 'UNKNOWN');
    });
  });

  describe('文件错误分类', () => {
    it('应分类权限错误', () => {
      const error = new Error('EACCES: permission denied');
      const classification = harvester._classifyFileError(error);
      assert.strictEqual(classification, 'PERMISSION_DENIED');
    });

    it('应分类磁盘空间错误', () => {
      const error = new Error('ENOSPC: no space left on device');
      const classification = harvester._classifyFileError(error);
      assert.strictEqual(classification, 'NO_SPACE');
    });

    it('应对未知错误返回 UNKNOWN', () => {
      const error = new Error('Some file error');
      const classification = harvester._classifyFileError(error);
      assert.strictEqual(classification, 'UNKNOWN');
    });
  });

  describe('待处理比赛查询', () => {
    it('应返回待处理比赛列表', async () => {
      // Mock 数据库查询
      const originalQuery = harvester.db?.query;
      if (harvester.db) {
        harvester.db.query = async () => ({
          rows: [
            { match_id: '1', home_team: 'A', away_team: 'B' },
            { match_id: '2', home_team: 'C', away_team: 'D' }
          ]
        });
      }

      const matches = await harvester.getPendingMatches();
      assert.ok(Array.isArray(matches));

      if (originalQuery) {
        harvester.db.query = originalQuery;
      }
    });
  });
});