/**
 * @file SeasonStrategy - 赛季格式策略
 * @module infrastructure/services/SeasonStrategy
 * @version V6.7.7-SEASON
 * @description
 * 职责: 处理单年份/双年份赛季 ID 映射
 * 消除 DiscoveryService 中的硬编码 singleYearLeagues 数组
 */

'use strict';

/**
 * 赛季策略接口
 * @interface ISeasonStrategy
 */

/**
 * 标准双年份策略 (如英超 2024/2025)
 * @class DualYearStrategy
 */
class DualYearStrategy {
  /**
   * 格式化赛季字符串
   * @param {string} season - 原始赛季字符串
   * @returns {string}
   */
  format(season) {
    // 移除所有分隔符，返回连续数字 (如 "2024/2025" -> "20242025")
    return season.replace(/[\/\-_]/g, '');
  }

  /**
   * 验证格式是否有效
   * @param {string} season - 赛季字符串
   * @returns {boolean}
   */
  isValid(season) {
    return /^\d{4}[\/\-_]?\d{4}$/.test(season);
  }

  /**
   * 获取策略名称
   * @returns {string}
   */
  getName() {
    return 'dual_year';
  }
}

/**
 * 单年份策略 (如中超 2024)
 * @class SingleYearStrategy
 */
class SingleYearStrategy {
  /**
   * 格式化赛季字符串
   * @param {string} season - 原始赛季字符串
   * @returns {string}
   */
  format(season) {
    // 提取第一个4位数字 (如 "2024/2025" -> "2024")
    const yearMatch = season.match(/(\d{4})/);
    return yearMatch ? yearMatch[1] : season;
  }

  /**
   * 验证格式是否有效
   * @param {string} season - 赛季字符串
   * @returns {boolean}
   */
  isValid(season) {
    return /\d{4}/.test(season);
  }

  /**
   * 获取策略名称
   * @returns {string}
   */
  getName() {
    return 'single_year';
  }
}

/**
 * 赛季策略工厂
 * @class SeasonStrategyFactory
 */
class SeasonStrategyFactory {
  /**
   * 创建策略工厂
   * @param {Object} leagueConfig - 联赛配置
   */
  constructor(leagueConfig = {}) {
    this.config = leagueConfig;
    this.strategies = {
      single_year: new SingleYearStrategy(),
      dual_year: new DualYearStrategy()
    };
    
    // 默认单年份联赛 ID 列表 (从硬编码迁移到配置)
    this.singleYearLeagues = leagueConfig.singleYearLeagues || [
      120,   // CSL 中超
      223,   // J1 League 日职联
      8974,  // J2 League 日乙
      230,   // Liga MX 墨超
      268,   // Brasileirão 巴甲
      121,   // Primera División 阿甲
      130    // MLS 美职联
    ];
  }

  /**
   * 判断联赛是否为单年份
   * @param {number} leagueId - 联赛 ID
   * @returns {boolean}
   */
  isSingleYearLeague(leagueId) {
    return this.singleYearLeagues.includes(leagueId);
  }

  /**
   * 获取联赛的策略类型
   * @param {number} leagueId - 联赛 ID
   * @returns {string} 'single_year' | 'dual_year'
   */
  getStrategyType(leagueId) {
    return this.isSingleYearLeague(leagueId) ? 'single_year' : 'dual_year';
  }

  /**
   * 获取策略实例
   * @param {number|string} leagueId - 联赛 ID
   * @returns {ISeasonStrategy}
   */
  getStrategy(leagueId) {
    const type = this.getStrategyType(parseInt(leagueId));
    return this.strategies[type];
  }

  /**
   * 格式化赛季 (便捷方法)
   * @param {number|string} leagueId - 联赛 ID
   * @param {string} season - 原始赛季字符串
   * @returns {string}
   */
  format(leagueId, season) {
    const strategy = this.getStrategy(leagueId);
    return strategy.format(season);
  }

  /**
   * 注册单年份联赛
   * @param {number} leagueId - 联赛 ID
   */
  registerSingleYearLeague(leagueId) {
    if (!this.singleYearLeagues.includes(leagueId)) {
      this.singleYearLeagues.push(leagueId);
    }
  }

  /**
   * 注销单年份联赛
   * @param {number} leagueId - 联赛 ID
   */
  unregisterSingleYearLeague(leagueId) {
    const index = this.singleYearLeagues.indexOf(leagueId);
    if (index > -1) {
      this.singleYearLeagues.splice(index, 1);
    }
  }
}

/**
 * 赛季 ID 探测器
 * 用于探测真实赛季 ID 映射
 * @class SeasonDiscovery
 */
class SeasonDiscovery {
  /**
   * 创建赛季探测器
   * @param {Object} options - 配置选项
   * @param {Object} options.logger - 日志对象
   * @param {Function} options.apiRequest - API 请求函数
   */
  constructor(options = {}) {
    this.logger = options.logger || {
      info: () => {},
      warn: () => {},
      error: () => {}
    };
    this.apiRequest = options.apiRequest;
  }

  /**
   * 探测真实赛季 ID
   * @param {number} leagueId - 联赛 ID
   * @param {string} targetYear - 目标年份
   * @returns {Promise<string>} 探测到的赛季 ID
   */
  async discover(leagueId, targetYear) {
    this.logger.info(`[SeasonDiscovery] 🔍 启动赛季指纹探测: ${leagueId} / ${targetYear}`);
    
    try {
      // 请求基础 API (不带 season 参数)
      const discoverUrl = `https://www.fotmob.com/api/data/leagues?id=${leagueId}`;
      const response = await this.apiRequest(discoverUrl);
      
      if (!response || !response.allAvailableSeasons) {
        this.logger.warn('[SeasonDiscovery] ⚠️  未获取到 allAvailableSeasons');
        return targetYear; // 回退到原始值
      }
      
      const availableSeasons = response.allAvailableSeasons;
      this.logger.info(`[SeasonDiscovery] 📋 发现 ${availableSeasons.length} 个可用赛季`);
      
      // 策略 1: 精确匹配
      if (availableSeasons.includes(targetYear)) {
        this.logger.info(`[SeasonDiscovery] ✅ 精确匹配: ${targetYear}`);
        return targetYear;
      }
      
      // 策略 2: 包含匹配
      const partialMatch = availableSeasons.find(s => 
        s.includes(targetYear) || targetYear.includes(s)
      );
      if (partialMatch) {
        this.logger.info(`[SeasonDiscovery] ✅ 包含匹配: ${targetYear} -> ${partialMatch}`);
        return partialMatch;
      }
      
      // 策略 3: 最接近匹配
      const yearPattern = /(\d{4})/;
      const targetYearNum = parseInt(targetYear);
      let closestMatch = null;
      let minDiff = Infinity;
      
      for (const seasonId of availableSeasons) {
        const match = seasonId.match(yearPattern);
        if (match) {
          const year = parseInt(match[1]);
          const diff = Math.abs(year - targetYearNum);
          if (diff < minDiff) {
            minDiff = diff;
            closestMatch = seasonId;
          }
        }
      }
      
      if (closestMatch && minDiff <= 1) {
        this.logger.info(`[SeasonDiscovery] ✅ 最接近匹配: ${targetYear} -> ${closestMatch}`);
        return closestMatch;
      }
      
      // 回退: 使用第一个可用赛季
      const fallbackSeason = availableSeasons[0];
      this.logger.warn(`[SeasonDiscovery] ⚠️  回退到第一个可用赛季: ${fallbackSeason}`);
      return fallbackSeason;
      
    } catch (error) {
      this.logger.warn(`[SeasonDiscovery] ⚠️  探测失败: ${error.message}`);
      return targetYear; // 回退到原始值
    }
  }
}

module.exports = {
  SeasonStrategyFactory,
  SeasonDiscovery,
  SingleYearStrategy,
  DualYearStrategy
};
