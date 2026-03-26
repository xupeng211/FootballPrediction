/**
 * @file Audit Dataset 审计系统单元测试
 * @description 测试物理清点、内容抽检、损坏文件识别
 * @version 1.0.0
 */

'use strict';

const { describe, it, beforeEach, afterEach } = require('node:test');
const assert = require('node:assert');
const fs = require('fs').promises;
const os = require('os');
const path = require('path');

// 模拟的 Auditor 类
/**
 *
 */
class MockAuditor {
  /**
   *
   * @param dataPath
   */
  constructor(dataPath) {
    this.dataPath = dataPath;
    this.corruptedFiles = [];
    this.validFiles = [];
  }

  /**
   * 获取文件列表
   */
  async getFileList() {
    try {
      const files = await fs.readdir(this.dataPath);
      return files.filter(f => f.endsWith('.json') && !f.startsWith('.'));
    } catch (error) {
      return [];
    }
  }

  /**
   * 验证单个文件
   * @param filePath
   */
  async validateFile(filePath) {
    try {
      const content = await fs.readFile(filePath, 'utf8');
      const data = JSON.parse(content);

      // 检查必要字段（V4.51.2: 修复 match_id: 0 被误判为无效的问题）
      const hasMatchId = data.match_id !== undefined && data.match_id !== null;
      const hasRawData = data.raw_data && Object.keys(data.raw_data).length > 0;
      const hasSavedAt = !!data.saved_at;

      if (hasMatchId && hasRawData && hasSavedAt) {
        return { valid: true, file: path.basename(filePath) };
      } else {
        return {
          valid: false,
          file: path.basename(filePath),
          missing: this._getMissingFields(data)
        };
      }
    } catch (error) {
      return {
        valid: false,
        file: path.basename(filePath),
        error: error.message
      };
    }
  }

  /**
   * 获取缺失字段
   * @param data
   */
  _getMissingFields(data) {
    const missing = [];
    if (!data.match_id) missing.push('match_id');
    if (!data.raw_data || Object.keys(data.raw_data).length === 0) missing.push('raw_data');
    if (!data.saved_at) missing.push('saved_at');
    return missing;
  }

  /**
   * 批量抽检
   * @param sampleSize
   */
  async sampleValidation(sampleSize = 50) {
    const files = await this.getFileList();
    const samples = [...files].sort().slice(0, Math.min(sampleSize, files.length));

    let valid = 0;
    let corrupted = 0;
    const corruptedFiles = [];

    for (const file of samples) {
      const filePath = path.join(this.dataPath, file);
      const result = await this.validateFile(filePath);

      if (result.valid) {
        valid++;
      } else {
        corrupted++;
        corruptedFiles.push(file.replace('.json', ''));
      }
    }

    return {
      checked: samples.length,
      valid,
      corrupted,
      passRate: samples.length > 0 ? ((valid / samples.length) * 100).toFixed(2) : 0,
      corruptedFiles
    };
  }

  /**
   * 计算对齐率
   * @param fileCount
   * @param dbCount
   */
  calculateAlignmentRate(fileCount, dbCount) {
    if (dbCount === 0) return 0;
    return ((fileCount / dbCount) * 100).toFixed(2);
  }

  /**
   * 生成审计报告
   * @param inventory
   * @param sampling
   * @param alignment
   */
  generateReport(inventory, sampling, alignment) {
    const passRate = parseFloat(sampling.passRate);
    const alignmentRate = parseFloat(alignment.alignmentRate);

    let quality = '需关注';
    if (passRate >= 95 && alignmentRate >= 95) {
      quality = '优秀';
    } else if (passRate >= 90 && alignmentRate >= 90) {
      quality = '良好';
    }

    return {
      totalFiles: inventory,
      dbCount: alignment.dbCount,
      alignmentRate: alignment.alignmentRate,
      checked: sampling.checked,
      valid: sampling.valid,
      corrupted: sampling.corrupted,
      passRate: sampling.passRate,
      quality,
      corruptedFiles: sampling.corruptedFiles
    };
  }
}

// ==================== 测试套件 ====================

describe('Audit Dataset 审计系统', () => {
  let auditor;
  let tempDir;

  beforeEach(async () => {
    tempDir = await fs.mkdtemp(path.join(os.tmpdir(), 'audit-dataset-test-'));
    auditor = new MockAuditor(tempDir);
  });

  afterEach(async () => {
    try {
      await fs.rm(tempDir, { recursive: true, force: true });
    } catch (err) {
      // 忽略
    }
  });

  describe('物理清点', () => {
it('✅ 应正确列出所有 JSON 文件', async () => {
      await fs.writeFile(path.join(tempDir, 'match1.json'), '{}');
      await fs.writeFile(path.join(tempDir, 'match2.json'), '{}');
      await fs.writeFile(path.join(tempDir, 'other.txt'), 'text');

      const files = await auditor.getFileList();
      assert.strictEqual(files.length, 2);
      assert.ok(files.includes('match1.json'));
      assert.ok(files.includes('match2.json'));
    });

it('✅ 空目录应返回空数组', async () => {
      const files = await auditor.getFileList();
      assert.deepStrictEqual(files, []);
    });

it('✅ 应忽略隐藏文件', async () => {
      await fs.writeFile(path.join(tempDir, 'match.json'), '{}');
      await fs.writeFile(path.join(tempDir, '.hidden.json'), '{}');

      const files = await auditor.getFileList();
      assert.strictEqual(files.length, 1);
      assert.strictEqual(files[0], 'match.json');
    });
  });

  describe('文件验证', () => {
it('✅ 完整文件应验证通过', async () => {
      const validData = {
        match_id: '12345',
        raw_data: { home: 'Team A', away: 'Team B' },
        saved_at: '2026-03-12T10:00:00Z'
      };

      await fs.writeFile(
        path.join(tempDir, 'valid.json'),
        JSON.stringify(validData)
      );

      const result = await auditor.validateFile(path.join(tempDir, 'valid.json'));
      assert.strictEqual(result.valid, true);
    });

it('❌ 缺少 match_id 应标记为损坏', async () => {
      const invalidData = {
        raw_data: { home: 'Team A' },
        saved_at: '2026-03-12T10:00:00Z'
      };

      await fs.writeFile(
        path.join(tempDir, 'invalid.json'),
        JSON.stringify(invalidData)
      );

      const result = await auditor.validateFile(path.join(tempDir, 'invalid.json'));
      assert.strictEqual(result.valid, false);
      assert.ok(result.missing.includes('match_id'));
    });

it('❌ 空 raw_data 应标记为损坏', async () => {
      const invalidData = {
        match_id: '12345',
        raw_data: {},
        saved_at: '2026-03-12T10:00:00Z'
      };

      await fs.writeFile(
        path.join(tempDir, 'empty_raw.json'),
        JSON.stringify(invalidData)
      );

      const result = await auditor.validateFile(path.join(tempDir, 'empty_raw.json'));
      assert.strictEqual(result.valid, false);
      assert.ok(result.missing.includes('raw_data'));
    });

it('❌ 缺少 saved_at 应标记为损坏', async () => {
      const invalidData = {
        match_id: '12345',
        raw_data: { home: 'Team A' }
      };

      await fs.writeFile(
        path.join(tempDir, 'no_time.json'),
        JSON.stringify(invalidData)
      );

      const result = await auditor.validateFile(path.join(tempDir, 'no_time.json'));
      assert.strictEqual(result.valid, false);
      assert.ok(result.missing.includes('saved_at'));
    });

it('❌ 无效 JSON 应标记为损坏', async () => {
      await fs.writeFile(
        path.join(tempDir, 'corrupt.json'),
        '{ invalid json }'
      );

      const result = await auditor.validateFile(path.join(tempDir, 'corrupt.json'));
      assert.strictEqual(result.valid, false);
      assert.ok(result.error !== undefined);
    });
  });

  describe('批量抽检', () => {
it('✅ 应正确计算通过率', async () => {
      // 创建 5 个文件，3 个有效，2 个损坏
      for (let i = 0; i < 3; i++) {
        await fs.writeFile(
          path.join(tempDir, `valid_${i}.json`),
          JSON.stringify({ match_id: i, raw_data: { test: true }, saved_at: '2026-03-12' })
        );
      }

      for (let i = 0; i < 2; i++) {
        await fs.writeFile(
          path.join(tempDir, `invalid_${i}.json`),
          JSON.stringify({ match_id: null, raw_data: {} })
        );
      }

      const result = await auditor.sampleValidation(10);
      assert.strictEqual(result.checked, 5);
      assert.strictEqual(result.valid, 3);
      assert.strictEqual(result.corrupted, 2);
      assert.strictEqual(parseFloat(result.passRate), 60.00);
    });

it('✅ 样本数不应超过实际文件数', async () => {
      await fs.writeFile(path.join(tempDir, 'match.json'), '{}');

      const result = await auditor.sampleValidation(100);
      assert.strictEqual(result.checked, 1);
    });

it('✅ 空目录应返回 0 通过率', async () => {
      const result = await auditor.sampleValidation(10);
      assert.strictEqual(result.checked, 0);
      assert.strictEqual(result.passRate, 0);
    });
  });

  describe('对齐率计算', () => {
    it('✅ 应正确计算对齐率', () => {
      assert.strictEqual(auditor.calculateAlignmentRate(100, 100), '100.00');
      assert.strictEqual(auditor.calculateAlignmentRate(90, 100), '90.00');
      assert.strictEqual(auditor.calculateAlignmentRate(110, 100), '110.00');
    });

    it('❌ DB 为 0 时应返回 0', () => {
      assert.strictEqual(auditor.calculateAlignmentRate(100, 0), 0);
    });
  });

  describe('审计报告生成', () => {
it('✅ 优秀质量应正确标记', () => {
      const report = auditor.generateReport(
        1000,
        { checked: 50, valid: 48, corrupted: 2, passRate: '96.00', corruptedFiles: [] },
        { dbCount: 1000, alignmentRate: '100.00' }
      );

      assert.strictEqual(report.quality, '优秀');
      assert.strictEqual(report.totalFiles, 1000);
      assert.strictEqual(report.passRate, '96.00');
    });

it('✅ 良好质量应正确标记', () => {
      const report = auditor.generateReport(
        1000,
        { checked: 50, valid: 46, corrupted: 4, passRate: '92.00', corruptedFiles: [] },
        { dbCount: 1050, alignmentRate: '95.24' }
      );

      assert.strictEqual(report.quality, '良好');
    });

it('⚠️  低通过率应标记为需关注', () => {
      const report = auditor.generateReport(
        1000,
        { checked: 50, valid: 40, corrupted: 10, passRate: '80.00', corruptedFiles: ['id1', 'id2'] },
        { dbCount: 1200, alignmentRate: '83.33' }
      );

      assert.strictEqual(report.quality, '需关注');
      assert.strictEqual(report.corruptedFiles.length, 2);
    });
  });
});
