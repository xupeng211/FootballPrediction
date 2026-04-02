/**
 * @file UIHelper - UI 展示辅助类
 * @module infrastructure/services/UIHelper
 * @version V6.7.6-UI
 * @description
 * 职责: CLI 界面美化和数据格式化输出
 * 包含: 启动横幅、扫描报告、进度显示
 */

'use strict';

/**
 * UI 辅助类
 * @class UIHelper
 */
class UIHelper {
  /**
   * 创建 UI 辅助实例
   * @param {Object} options - 配置选项
   * @param {Object} options.logger - 日志对象
   */
  constructor(options = {}) {
    this.logger = options.logger || {
      info: () => {},
      warn: () => {},
      error: () => {},
      banner: () => {},
      progress: () => {}
    };
  }

  /**
   * 打印启动横幅
   * @param {string} version - 版本号
   */
  printBanner(version = 'V6.7.6') {
    this.logger.banner('');
    this.logger.banner('╔══════════════════════════════════════════════════════════════════╗');
    this.logger.banner('║                                                                  ║');
    this.logger.banner(`║           🐕 PROJECT HOUND ${version} 🐕                      ║`);
    this.logger.banner('║                                                                  ║');
    this.logger.banner('║     多联赛自动扫描 | L1 发现引擎 | 影子浏览器版                  ║');
    this.logger.banner('║     Playwright 隐身 | CloudFront 穿透 | 全球覆盖                 ║');
    this.logger.banner('║                                                                  ║');
    this.logger.banner('╚══════════════════════════════════════════════════════════════════╝');
  }

  /**
   * 生成扫描报告
   * @param {Object} stats - 统计数据
   * @param {number} stats.total - 总计发现
   * @param {number} stats.inserted - 新增入库
   * @param {number} stats.updated - 更新现有
   * @param {number} stats.failed - 失败数量
   * @param {number} startTime - 启动时间戳
   * @returns {Object} 格式化后的报告对象
   */
  generateReport(stats, startTime) {
    const duration = Date.now() - startTime;
    const durationSec = (duration / 1000).toFixed(1);
    const criticalWarnings = stats.criticalWarnings || [];

    const report = {
      total: stats.total,
      inserted: stats.inserted,
      updated: stats.updated,
      failed: stats.failed,
      criticalWarnings,
      duration: `${durationSec}s`,
      rate: stats.total > 0 ? (stats.total / (duration / 60000)).toFixed(1) : '0.0'
    };

    this.logger.banner('\n╔══════════════════════════════════════════════════════════════════╗');
    this.logger.banner('║  🐕 PROJECT HOUND - 发现扫描完成                                 ║');
    this.logger.banner('╠══════════════════════════════════════════════════════════════════╣');
    this.logger.banner(`║  📊 总计发现: ${report.total.toString().padStart(5)} 场比赛                              ║`);
    this.logger.banner(`║  ✅ 新增入库: ${report.inserted.toString().padStart(5)} 场                                  ║`);
    this.logger.banner(`║  🔄 更新现有: ${report.updated.toString().padStart(5)} 场                                  ║`);
    this.logger.banner(`║  ❌ 失败:     ${report.failed.toString().padStart(5)} 场                                  ║`);
    if (criticalWarnings.length > 0) {
      this.logger.banner(`║  🚨 严重告警: ${criticalWarnings.length.toString().padStart(4)} 条                                  ║`);
    }
    this.logger.banner('╠══════════════════════════════════════════════════════════════════╣');
    this.logger.banner(`║  ⏱️  耗时: ${durationSec.padStart(6)}s | 速率: ${report.rate} 场/min                    ║`);
    this.logger.banner('╚══════════════════════════════════════════════════════════════════╝');

    for (const warning of criticalWarnings) {
      this.logger.warn(
        `[CRITICAL WARN] ${warning.name} ${warning.season}: 实得 ${warning.actual} 场，预期 ${warning.expected} 场，缺失 ${warning.missing} 场`
      );
    }

    return report;
  }

  /**
   * 打印扫描进度
   * @param {string} workerId - Worker ID
   * @param {string} name - 联赛名称
   * @param {Object} result - 扫描结果
   */
  printProgress(workerId, name, result) {
    this.logger.progress(
      `[${workerId}] ✅ ${name}: 新增 ${result.inserted} | 更新 ${result.updated} | 失败 ${result.failed}`
    );
  }

  /**
   * 打印扫描目标信息
   * @param {number} count - 目标数量
   */
  printTargets(count) {
    this.logger.banner(`\n🐕 [HOUND] 扫描目标: ${count} 个联赛-赛季组合`);
  }

  /**
   * 打印联赛扫描开始
   * @param {string} workerId - Worker ID
   * @param {string} name - 联赛名称
   * @param {string} season - 赛季
   */
  printScanStart(workerId, name, season) {
    this.logger.info(`\n[${workerId}] 🔍 ${name} | 赛季 ${season}`);
  }

  /**
   * 打印历史赛季模式
   * @param {string} workerId - Worker ID
   * @param {string} season - 赛季
   */
  printHistoricalMode(workerId, season) {
    this.logger.info(`[${workerId}] 📜 历史赛季 ${season}，全量采集模式`);
  }

  /**
   * 打印解析结果
   * @param {string} workerId - Worker ID
   * @param {string} name - 联赛名称
   * @param {number} count - 比赛数量
   */
  printParsedFixtures(workerId, name, count) {
    this.logger.info(`[${workerId}] 📋 ${name}: 解析出 ${count} 场有效比赛`);
  }

  /**
   * 打印关键缺数告警
   * @param {string} workerId - Worker ID
   * @param {string} name - 联赛名称
   * @param {string} season - 赛季
   * @param {number} actual - 实际场次
   * @param {number} expected - 预期场次
   */
  printCriticalWarn(workerId, name, season, actual, expected) {
    const missing = expected - actual;
    this.logger.warn(
      `[${workerId}] [CRITICAL WARN] ${name} ${season}: 实得 ${actual} 场，预期 ${expected} 场，缺失 ${missing} 场`
    );
  }

  /**
   * 打印无新赛程警告
   * @param {string} workerId - Worker ID
   * @param {string} name - 联赛名称
   */
  printNoFixtures(workerId, name) {
    this.logger.info(`[${workerId}] ⚠️ ${name}: 未发现新赛程`);
  }

  /**
   * 打印扫描失败错误
   * @param {string} workerId - Worker ID
   * @param {string} name - 联赛名称
   * @param {string} message - 错误信息
   * @param {number} duration - 耗时(ms)
   */
  printScanError(workerId, name, message, duration) {
    this.logger.error(`[${workerId}] ❌ ${name} 扫描失败: ${message} (${duration}ms)`);
  }

  /**
   * 打印联赛列表 (V6.7.6-PRINCIPAL: 从外部配置加载国际化数据)
   * @param {Array} leagues - 联赛数组
   */
  printLeagueList(leagues) {
    // V6.7.6-PRINCIPAL: 从外部配置加载国际化数据
    const i18nData = this._loadI18nConfig();
    const leagueNames = i18nData.locales?.zh?.leagues || {};

    this.logger.banner('\n╔══════════════════════════════════════════════════════════════════╗');
    this.logger.banner('║           🗺️  TITAN 全球赛事图谱 (Project Atlas)                 ║');
    this.logger.banner('╠══════════════════════════════════════════════════════════════════╣');

    // 按级别分组
    const tiers = { P0: [], P1: [], P2: [], P3: [], P4: [] };
    leagues.forEach(l => {
      if (tiers[l.tier]) tiers[l.tier].push(l);
    });

    // 输出各级别
    const tierLabels = {
      P0: '⭐ P0 - 核心联赛',
      P1: '🏆 P1 - 杯赛与欧战',
      P2: '🥈 P2 - 次级联赛',
      P3: '🌍 P3 - 全球联赛',
      P4: '🌐 P4 - 国际赛事'
    };

    Object.entries(tiers).forEach(([tier, tierLeagues]) => {
      if (tierLeagues.length === 0) return;

      this.logger.banner('║                                                                  ║');
      this.logger.banner(`║  ${tierLabels[tier].padEnd(62)} ║`);
      this.logger.banner('║  ─────────────────────────────────────────────────────────────   ║');

      tierLeagues.forEach(l => {
        const cnName = leagueNames[l.id] || '';
        const displayName = cnName ? `${l.name} (${cnName})` : l.name;
        this.logger.banner(`║  ID: ${l.id.toString().padStart(5)} | ${displayName.padEnd(32)} | ${l.country.padEnd(10)} ║`);
      });
    });

    this.logger.banner('║                                                                  ║');
    this.logger.banner('╠══════════════════════════════════════════════════════════════════╣');
    this.logger.banner(`║  总计: ${leagues.length.toString().padStart(2)} 个联赛 | 覆盖全球主要足球市场              ║`);
    this.logger.banner('╚══════════════════════════════════════════════════════════════════╝\n');
  }

  /**
   * 打印搜索结果 (V6.7.6-FINAL: 从 titan_discovery.js 迁移)
   * @param {Object} results - 搜索结果 { leagues: [], teams: [] }
   */
  printSearchResults(results) {
    this.logger.banner('\n╔══════════════════════════════════════════════════════════════════╗');
    this.logger.banner('║           🔍 搜索结果 - 实时坐标侦察                             ║');
    this.logger.banner('╠══════════════════════════════════════════════════════════════════╣');

    let foundCount = 0;

    // 搜索联赛结果
    if (results.leagues && results.leagues.length > 0) {
      this.logger.banner('║                                                                  ║');
      this.logger.banner(`║  🏆 联赛 (${results.leagues.length})                                                  ║`);
      this.logger.banner('║  ─────────────────────────────────────────────────────────────   ║');
      results.leagues.forEach(league => {
        const id = league.id || league.pageUrl?.match(/\d+/)?.[0] || 'N/A';
        const name = league.name || 'Unknown';
        const country = league.country || league.ccode || 'Unknown';
        this.logger.banner(`║  ID: ${id.toString().padStart(6)} | ${name.padEnd(28)} | ${country.padEnd(12)} ║`);
        foundCount++;
      });
    }

    // 搜索球队结果
    if (results.teams && results.teams.length > 0) {
      this.logger.banner('║                                                                  ║');
      this.logger.banner(`║  ⚽ 球队 (${results.teams.length})                                                   ║`);
      this.logger.banner('║  ─────────────────────────────────────────────────────────────   ║');
      results.teams.slice(0, 10).forEach(team => {
        const id = team.id || 'N/A';
        const name = team.name || 'Unknown';
        const country = team.country || team.ccode || 'Unknown';
        this.logger.banner(`║  ID: ${id.toString().padStart(6)} | ${name.padEnd(28)} | ${country.padEnd(12)} ║`);
      });
      if (results.teams.length > 10) {
        this.logger.banner(`║  ... 还有 ${results.teams.length - 10} 支球队 ...                                ║`);
      }
      foundCount += results.teams.length;
    }

    if (foundCount === 0) {
      this.logger.banner('║                                                                  ║');
      this.logger.banner('║  ⚠️  未找到匹配结果                                                ║');
      this.logger.banner('║                                                                  ║');
    }

    this.logger.banner('╠══════════════════════════════════════════════════════════════════╣');
    this.logger.banner(`║  总计: ${foundCount.toString().padStart(3)} 条结果 | 使用 --league=ID 进行扫描              ║`);
    this.logger.banner('╚══════════════════════════════════════════════════════════════════╝\n');
  }

  /**
   * 加载国际化配置 (V6.7.6-PRINCIPAL: 零硬编码)
   * @private
   */
  _loadI18nConfig() {
    try {
      const fs = require('fs');
      const path = require('path');
      const configPath = path.resolve(__dirname, '../../../config/leagues.i18n.json');
      const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
      return config;
    } catch (e) {
      this.logger.warn(`[UIHelper] 无法加载国际化配置: ${e.message}`);
      // 返回空配置，使用原始名称
      return { locales: { zh: { leagues: {} } } };
    }
  }
}

module.exports = { UIHelper };
