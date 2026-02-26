#!/usr/bin/env node
/**
 * V79.100 Configuration Loader - JavaScript/Node.js 配置加载器
 * =========================================================
 *
 * 提供从外部化配置文件加载配置的功能：
 * 1. team_aliases.json - 队名映射
 * 2. hyper_parameters.yaml - 超参数阈值
 *
 * @file config_loader.js
 * @version V79.100
 * @since 2026-01-25
 * @author V79.100 Engineering Team
 */

'use strict';

const fs = require('fs');
const path = require('path');

// =============================================================================
// JSDOC TYPE DEFINITIONS
// =============================================================================

/**
 * @typedef {Object} TeamAliasesData
 * @property {Object<string, string>} team_name_mappings - 队名映射表
 * @property {string[]} suffixes_to_strip - 需要去除的后缀列表
 * @property {string[]} prefixes_to_strip - 需要去除的前缀列表
 * @property {Object<string, string[]>} youth_keywords - 青年队关键词
 * @property {string[]} youth_patterns - 青年队匹配模式
 * @property {Object<string, string[]>} common_suffixes - 常见后缀
 */

/**
 * @typedef {Object} HyperParametersData
 * @property {Object} fatigue - 疲劳度参数
 * @property {number} fatigue.busy_week_threshold - 忙碌周阈值
 * @property {number} fatigue.default_rest_days - 默认休息天数
 * @property {Object} unavailable - 缺阵参数
 * @property {number} unavailable.star_market_value - 球星身价阈值
 * @property {Object} feature_extraction - 特征提取参数
 * @property {Object} similarity - 相似度参数
 * @property {Object} odds_integrity - 赔率完整性参数
 * @property {Object} database - 数据库参数
 * @property {Object} crawler - 爬虫参数
 * @property {Object} leagues - 联赛参数
 * @property {Object} performance - 性能参数
 * @property {Object} cache - 缓存参数
 * @property {Object} logging - 日志参数
 */

/**
 * @typedef {Object} BridgeConfidence
 * @property {number} excellent_min - 优秀置信度下限
 * @property {number} good_min - 良好置信度下限
 * @property {number} fair_min - 及格置信度下限
 * @property {number} reject_below - 拒绝阈值
 */

// Try to load js-yaml, fallback to JSON-only mode
let yaml;
try {
  yaml = require('js-yaml');
} catch (e) {
  console.warn('js-yaml not found, YAML features disabled. Install with: npm install js-yaml');
  yaml = null;
}

// =============================================================================
// Configuration Paths
// =============================================================================

const CONFIG_DIR = path.resolve(__dirname, '../../config');
const SRC_CONFIG_DIR = path.resolve(__dirname, '../../src/config');
const TEAM_ALIASES_PATH = path.join(CONFIG_DIR, 'team_aliases.json');
const HYPER_PARAMETERS_PATH = path.join(SRC_CONFIG_DIR, 'hyper_parameters.yaml');

// =============================================================================
// Team Aliases Configuration
// =============================================================================

class TeamAliasesConfig {
  constructor(data = {}) {
    this.teamNameMappings = data.team_name_mappings || {};
    this.suffixesToStrip = data.suffixes_to_strip || [];
    this.prefixesToStrip = data.prefixes_to_strip || [];
    this.youthKeywords = data.youth_keywords || {};
    this.youthPatterns = data.youth_patterns || [];
    this.commonSuffixes = data.common_suffixes || {};
  }

  /**
   * Get normalized team name
   * @param {string} rawName - Raw team name
   * @returns {string} Normalized team name
   */
  normalizeTeamName(rawName) {
    if (!rawName) return '';

    let normalized = rawName.toLowerCase().trim();

    // Apply mappings
    if (this.teamNameMappings[normalized]) {
      return this.teamNameMappings[normalized];
    }

    return normalized;
  }

  /**
   * Check if a name is a youth team
   * @param {string} teamName - Team name to check
   * @returns {boolean} True if youth team
   */
  isYouthTeam(teamName) {
    if (!teamName) return false;

    const normalized = teamName.toLowerCase();

    // Check patterns
    for (const pattern of this.youthPatterns) {
      const regex = new RegExp(pattern, 'i');
      if (regex.test(normalized)) {
        return true;
      }
    }

    // Check keywords
    for (const category of Object.values(this.youthKeywords)) {
      for (const keyword of category) {
        if (normalized.includes(keyword)) {
          return true;
        }
      }
    }

    return false;
  }

  /**
   * Load from JSON file
   * @param {string} jsonPath - Path to JSON file
   * @returns {TeamAliasesConfig} Configuration instance
   */
  static fromJson(jsonPath = TEAM_ALIASES_PATH) {
    if (!fs.existsSync(jsonPath)) {
      console.warn(`Team aliases file not found: ${jsonPath}, using defaults`);
      return new TeamAliasesConfig();
    }

    const data = JSON.parse(fs.readFileSync(jsonPath, 'utf8'));
    return new TeamAliasesConfig(data);
  }
}

// =============================================================================
// Hyper-Parameters Configuration
// =============================================================================

class HyperParametersConfig {
  constructor(data = {}) {
    const fatigue = data.fatigue || {};
    const unavailable = data.unavailable || {};
    const feature = data.feature_extraction || {};
    const similarity = data.similarity || {};
    const odds = data.odds_integrity || {};
    const db = data.database || {};
    const crawler = data.crawler || {};
    const leagues = data.leagues || {};

    // Fatigue parameters
    this.busyWeekThreshold = fatigue.busy_week_threshold || 4;
    this.defaultRestDays = fatigue.default_rest_days || 14;

    // Unavailable parameters
    this.starMarketValue = unavailable.star_market_value || 30000000;

    // Feature extraction
    this.corePlayerThreshold = feature.core_player_threshold || 0.7;
    this.sparsityThreshold = feature.sparsity_threshold || 0.90;
    const richness = feature.feature_richness || {};
    this.excellentThreshold = richness.excellent_threshold || 100;
    this.goodThreshold = richness.good_threshold || 80;
    this.fairThreshold = richness.fair_threshold || 50;
    this.minimumThreshold = richness.minimum_threshold || 30;

    // Similarity
    this.teamMatchThreshold = similarity.team_match_threshold || 85.0;
    const bridge = similarity.bridge_confidence || {};
    this.excellentConfidenceMin = bridge.excellent_min || 95;
    this.goodConfidenceMin = bridge.good_min || 85;
    this.fairConfidenceMin = bridge.fair_min || 70;
    this.rejectConfidenceBelow = bridge.reject_below || 70;
    this.youthPenaltyRatio = similarity.youth_penalty_ratio || 0.5;

    // Odds integrity
    this.minPayout = odds.min_payout || 1.02;
    this.maxPayout = odds.max_payout || 1.08;
    this.minOddsValue = odds.min_odds_value || 0.01;

    // Database
    this.poolSize = db.pool_size || 15;
    this.poolMaxOverflow = db.pool_max_overflow || 20;
    this.poolTimeout = db.pool_timeout || 10;
    this.poolRecycle = db.pool_recycle || 600;
    this.queryTimeout = db.query_timeout || 30000;
    this.connectionTimeout = db.connection_timeout || 10000;

    // Crawler
    this.defaultDelay = crawler.default_delay || 5.0;
    this.minDelay = crawler.min_delay || 3.0;
    this.maxDelay = crawler.max_delay || 15.0;
    this.maxRetries = crawler.max_retries || 3;
    this.retryBackoffMultiplier = crawler.retry_backoff_multiplier || 2.0;
    this.retryMaxDelay = crawler.retry_max_delay || 10000;
    this.retryJitterRange = crawler.retry_jitter_range || 0.1;
    const circuit = crawler.circuit_breaker || {};
    this.circuitFailureThreshold = circuit.failure_threshold || 5;
    this.circuitRecoveryTimeout = circuit.recovery_timeout || 60;
    this.circuitSuccessThreshold = circuit.success_threshold || 2;
    const ghost = crawler.ghost || {};
    this.browserPoolSize = ghost.browser_pool_size || 5;

    // Leagues
    this.top5Leagues = leagues.top_5_leagues || [
      'Premier League',
      'La Liga',
      'Bundesliga',
      'Serie A',
      'Ligue 1'
    ];

    // Performance
    const perf = data.performance || {};
    this.targetInferenceLatencyMs = perf.target_inference_latency_ms || 100;
    this.targetFotmobApiLatencyS = perf.target_fotmob_api_latency_s || 3.0;
    this.targetOddsportalRpaLatencyS = perf.target_oddsportal_rpa_latency_s || 8.0;
    this.maxMemoryMb = perf.max_memory_mb || 8192;
    this.maxCpuCores = perf.max_cpu_cores || 4;
    this.minDataCompleteness = perf.min_data_completeness || 0.95;
    this.minMappingSuccessRate = perf.min_mapping_success_rate || 0.90;

    // Cache
    const cache = data.cache || {};
    this.cacheEnable = cache.enable !== false;
    this.cacheSize = cache.size || 1000;
    this.cacheTtlSeconds = cache.ttl_seconds || 3600;

    // Logging
    const logging = data.logging || {};
    this.loggingLevel = logging.level || 'INFO';
  }

  /**
   * Load from YAML file
   * @param {string} yamlPath - Path to YAML file
   * @returns {HyperParametersConfig} Configuration instance
   */
  static fromYaml(yamlPath = HYPER_PARAMETERS_PATH) {
    if (!fs.existsSync(yamlPath)) {
      console.warn(`Hyper parameters file not found: ${yamlPath}, using defaults`);
      return new HyperParametersConfig();
    }

    let data;
    if (yaml) {
      // Use js-yaml if available
      data = yaml.load(fs.readFileSync(yamlPath, 'utf8'));
    } else {
      // Fallback: try JSON parsing (YAML is JSON superset)
      try {
        data = JSON.parse(fs.readFileSync(yamlPath, 'utf8'));
      } catch (e) {
        console.warn(`Failed to parse config file, using defaults: ${e.message}`);
        return new HyperParametersConfig();
      }
    }

    return new HyperParametersConfig(data);
  }

  /**
   * Get configuration as plain object (for logging/debugging)
   * @returns {Object} Plain object representation
   */
  toPlainObject() {
    return {
      fatigue: {
        busy_week_threshold: this.busyWeekThreshold,
        default_rest_days: this.defaultRestDays,
      },
      unavailable: {
        star_market_value: this.starMarketValue,
      },
      feature_extraction: {
        core_player_threshold: this.corePlayerThreshold,
        sparsity_threshold: this.sparsityThreshold,
        feature_richness: {
          excellent_threshold: this.excellentThreshold,
          good_threshold: this.goodThreshold,
          fair_threshold: this.fairThreshold,
          minimum_threshold: this.minimumThreshold,
        },
      },
      similarity: {
        team_match_threshold: this.teamMatchThreshold,
        bridge_confidence: {
          excellent_min: this.excellentConfidenceMin,
          good_min: this.goodConfidenceMin,
          fair_min: this.fairConfidenceMin,
          reject_below: this.rejectConfidenceBelow,
        },
        youth_penalty_ratio: this.youthPenaltyRatio,
      },
    };
  }
}

// =============================================================================
// Singleton Instances
// =============================================================================

let teamAliasesConfigInstance = null;
let hyperParametersConfigInstance = null;

/**
 * Get team aliases configuration singleton
 * @returns {TeamAliasesConfig} Configuration instance
 */
function getTeamAliasesConfig() {
  if (!teamAliasesConfigInstance) {
    teamAliasesConfigInstance = TeamAliasesConfig.fromJson();
  }
  return teamAliasesConfigInstance;
}

/**
 * Get hyper-parameters configuration singleton
 * @returns {HyperParametersConfig} Configuration instance
 */
function getHyperParametersConfig() {
  if (!hyperParametersConfigInstance) {
    hyperParametersConfigInstance = HyperParametersConfig.fromYaml();
  }
  return hyperParametersConfigInstance;
}

// =============================================================================
// Exports
// =============================================================================

module.exports = {
  TeamAliasesConfig,
  HyperParametersConfig,
  getTeamAliasesConfig,
  getHyperParametersConfig,
};
