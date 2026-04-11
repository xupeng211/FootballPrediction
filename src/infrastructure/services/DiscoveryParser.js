/**
 * @file DiscoveryParser - FotMob API 数据解析门面
 * @module infrastructure/services/DiscoveryParser
 */

'use strict';

const { DiscoveryAttributeMapper } = require('./DiscoveryAttributeMapper');
const { DiscoveryDataValidator } = require('./DiscoveryDataValidator');

class DiscoveryParser {
  constructor(logger, leagueConfig, options = {}) {
    this.logger = logger;
    this.dataSource = 'FotMob';
    this.validator = options.validator || new DiscoveryDataValidator({ logger });
    this.mapper = options.mapper || new DiscoveryAttributeMapper({
      dataSource: this.dataSource,
      leagueConfig
    });
  }

  parse(response, leagueId, season, isHistorical = false, config = {}) {
    const rawMatches = this.validator.extractRawMatches(response);

    if (rawMatches.length === 0) {
      this.validator.diagnoseEmptyResponse(response);
      return [];
    }

    this.logger.info(`[PARSER] 成功提取 ${rawMatches.length} 场原始数据`);
    return this.mapper.transformMatches(rawMatches, leagueId, season, isHistorical, config);
  }
}

module.exports = { DiscoveryParser };
