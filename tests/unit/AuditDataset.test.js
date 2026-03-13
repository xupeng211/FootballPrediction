/**
 * @fileoverview Audit Dataset 审计系统单元测试
 * @description 测试物理清点、内容抽检、损坏文件识别
 * @version 1.0.0
 */

'use strict';

const fs = require('fs').promises;
const path = require('path');

// 模拟的 Auditor 类
class MockAuditor {
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
   */
  async sampleValidation(sampleSize = 50) {
    const files = await this.getFileList();
    const shuffled = [...files].sort(() => 0.5 - Math.random());
    const samples = shuffled.slice(0, Math.min(sampleSize, files.length));

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
   */
  calculateAlignmentRate(fileCount, dbCount) {
    if (dbCount === 0) return 0;
    return ((fileCount / dbCount) * 100).toFixed(2);
  }

  /**
   * 生成审计报告
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
    tempDir = path.join(process.cwd(), 'temp_audit_test');
    await fs.mkdir(tempDir, { recursive: true });
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
    test('✅ 应正确列出所有 JSON 文件', async () => {
      await fs.writeFile(path.join(tempDir, 'match1.json'), '{}');
      await fs.writeFile(path.join(tempDir, 'match2.json'), '{}');
      await fs.writeFile(path.join(tempDir, 'other.txt'), 'text');

      const files = await auditor.getFileList();
      expect(files).toHaveLength(2);
      expect(files).toContain('match1.json');
      expect(files).toContain('match2.json');
    });

    test('✅ 空目录应返回空数组', async () => {
      const files = await auditor.getFileList();
      expect(files).toEqual([]);
    });

    test('✅ 应忽略隐藏文件', async () => {
      await fs.writeFile(path.join(tempDir, 'match.json'), '{}');
      await fs.writeFile(path.join(tempDir, '.hidden.json'), '{}');

      const files = await auditor.getFileList();
      expect(files).toHaveLength(1);
      expect(files[0]).toBe('match.json');
    });
  });

  describe('文件验证', () => {
    test('✅ 完整文件应验证通过', async () => {
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
      expect(result.valid).toBe(true);
    });

    test('❌ 缺少 match_id 应标记为损坏', async () => {
      const invalidData = {
        raw_data: { home: 'Team A' },
        saved_at: '2026-03-12T10:00:00Z'
      };

      await fs.writeFile(
        path.join(tempDir, 'invalid.json'),
        JSON.stringify(invalidData)
      );

      const result = await auditor.validateFile(path.join(tempDir, 'invalid.json'));
      expect(result.valid).toBe(false);
      expect(result.missing).toContain('match_id');
    });

    test('❌ 空 raw_data 应标记为损坏', async () => {
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
      expect(result.valid).toBe(false);
      expect(result.missing).toContain('raw_data');
    });

    test('❌ 缺少 saved_at 应标记为损坏', async () => {
      const invalidData = {
        match_id: '12345',
        raw_data: { home: 'Team A' }
      };

      await fs.writeFile(
        path.join(tempDir, 'no_time.json'),
        JSON.stringify(invalidData)
      );

      const result = await auditor.validateFile(path.join(tempDir, 'no_time.json'));
      expect(result.valid).toBe(false);
      expect(result.missing).toContain('saved_at');
    });

    test('❌ 无效 JSON 应标记为损坏', async () => {
      await fs.writeFile(
        path.join(tempDir, 'corrupt.json'),
        '{ invalid json }'
      );

      const result = await auditor.validateFile(path.join(tempDir, 'corrupt.json'));
      expect(result.valid).toBe(false);
      expect(result.error).toBeDefined();
    });
  });

  describe('批量抽检', () => {
    test('✅ 应正确计算通过率', async () => {
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
      expect(result.checked).toBe(5);
      expect(result.valid).toBe(3);
      expect(result.corrupted).toBe(2);
      expect(parseFloat(result.passRate)).toBe(60.00);
    });

    test('✅ 样本数不应超过实际文件数', async () => {
      await fs.writeFile(path.join(tempDir, 'match.json'), '{}');

      const result = await auditor.sampleValidation(100);
      expect(result.checked).toBe(1);
    });

    test('✅ 空目录应返回 0 通过率', async () => {
      const result = await auditor.sampleValidation(10);
      expect(result.checked).toBe(0);
      expect(result.passRate).toBe(0);
    });
  });

  describe('对齐率计算', () => {
    test('✅ 应正确计算对齐率', () => {
      expect(auditor.calculateAlignmentRate(100, 100)).toBe('100.00');
      expect(auditor.calculateAlignmentRate(90, 100)).toBe('90.00');
      expect(auditor.calculateAlignmentRate(110, 100)).toBe('110.00');
    });

    test('❌ DB 为 0 时应返回 0', () => {
      expect(auditor.calculateAlignmentRate(100, 0)).toBe(0);
    });
  });

  describe('审计报告生成', () => {
    test('✅ 优秀质量应正确标记', () => {
      const report = auditor.generateReport(
        1000,
        { checked: 50, valid: 48, corrupted: 2, passRate: '96.00', corruptedFiles: [] },
        { dbCount: 1000, alignmentRate: '100.00' }
      );

      expect(report.quality).toBe('优秀');
      expect(report.totalFiles).toBe(1000);
      expect(report.passRate).toBe('96.00');
    });

    test('✅ 良好质量应正确标记', () => {
      const report = auditor.generateReport(
        1000,
        { checked: 50, valid: 46, corrupted: 4, passRate: '92.00', corruptedFiles: [] },
        { dbCount: 1050, alignmentRate: '95.24' }
      );

      expect(report.quality).toBe('良好');
    });

    test('⚠️  低通过率应标记为需关注', () => {
      const report = auditor.generateReport(
        1000,
        { checked: 50, valid: 40, corrupted: 10, passRate: '80.00', corruptedFiles: ['id1', 'id2'] },
        { dbCount: 1200, alignmentRate: '83.33' }
      );

      expect(report.quality).toBe('需关注');
      expect(report.corruptedFiles).toHaveLength(2);
    });
  });
});
