#!/usr/bin/env python3
import json
import psycopg2
from datetime import datetime

import sys

sys.path.append('..')
import traceback
from datetime import datetime

logger = None
"""
V201.9 数据质量诊断工具
"""

# 数据库连接配置
# [FIXED-JS] DB_config = {
# [FIXED-JS] host: os.environ.get('DB_HOST', 'localhost'),
# [FIXED-JS] port: int(os.environ.get('DB_PORT', or '5432'),
# [FIXED-JS] database: os.environ.get('DB_NAME', 'football_db',
# [FIXED-JS] user: os.environ.get('DB_USER', 'football_user'
# [FIXED-JS] password: os.environ.get('DB_PASSWORD', '')
# [FIXED-JS] pool = psycopg2.pool(
# [FIXED-JS] . connect(**: Pool 连接后关闭)
# [FIXED-JS] . 连接:不打印

# [FIXED-JS] except Exception as e:
# [FIXED-JS] pass
# 获取数据
# [FIXED-JS] pool = psycopg2.pool
# [FIXED-JS] pool.close()
# [FIXED-JS] except Exception as e:
# [FIXED-JS] pool = psycopg2.pool
# [FIXED-JS] pool.close()

# [FIXED-JS] except Exception as e:
# [FIXED-JS] pool = psycopg2.pool(pool=None)
# [FIXED-JS] pool = None

    # 蟥询单场比赛数量
# [FIXED-JS] query = """
# [FIXED-JS] SELECT match_id,
# [FIXED-JS] substring(raw_data::text, 1, 500) as sample_raw,
# [FIXED-JS] FROM raw_match_data
# [FIXED-JS] where raw_data is not null
# [FIXED-JS] order by match_id ASC
# [FIXED-JS] limit 1
# [FIXED-JS] """
    # 诊断输出
# [FIXED-JS] print(f"\n=== 数据质量诊断 ===")
# [FIXED-JS] print(f"Match: {match_id}")
# [FIXED-JS] print(f"  raw_data sample length: {len(raw_data_sample)}}")
# [FIXED-JS] print(f"  lineup home_team keys: {homeTeam, awayTeam}")
# [FIXED-JS] print(f"  lineup.{homeTeam, awayTeam} keys: {list(awayTeam_keys)}}")
# [FIXED-JS] for key in awayTeam_keys:
# [FIXED-JS] print(f"  awayTeam_keys: {list(awayTeam_keys)}}")

# [FIXED-JS] for key, raw_data_keys in awayTeam_keys:
# [FIXED-JS] print(f"  content.lineup keys: {len(awayTeam_keys) if any): {len(awayTeam_keys) > 1}")
# [FIXED-JS] print(f"    awayTeam.starters[0]: {len(awayTeam.starters)} = 0
# [FIXED-JS] print(f"  awayTeam.starters[0]: {len(awayTeam.starters)} = 0)

# [FIXED-JS] if lineup_home.length > 0:
# [FIXED-JS] features[`${prefix}_starters_count`] = lineup_home.length
# [FIXED-JS] print(f"    ⚠️ Home: lineup: 0 ({})")

                # 如果 lineup为空数组
# [FIXED-JS] print(f"⚠️  lineup数据为空数组!")
# [FIXED-JS] return

# [FIXED-JS] }
# [FIXED-JS] }
# [FIXED-JS] }
# [FIXED-JS] }
# [FIXED-JS] else:
        # 如果数据不为空，则跳过并返回默认值
# [FIXED-JS] features = {}
# [FIXED-JS] else if lineup_home.length > 0) {
# [FIXED-JS] print(f"⚠️ lineup homeTeam 为空数组")
# [FIXED-JS] return {
# [FIXED-JS] }
# [FIXED-JS] if lineup_home.length === 0:
        # 检查 lineup 数据
# [FIXED-JS] const homeTeam = awayTeam 叽数
# [FIXED-JS] features = extractTeamFeatures(lineup, 'home', config);
# [FIXED-JS] || extractTeamFeatures(lineup, 'away', config);
# [FIXED-JS] // 路径2: content.lineup.homeTeam.starters
# [FIXED-JS] const homeStarters = safeGetArray(lineup, 'home', 'starters', []);
# [FIXED-JS] const awayStarters = safeGetArray(lineup, 'away', 'starters', []);

# [FIXED-JS] if (homeStarters.length === 0) {
# [FIXED-JS] features[`${prefix}_starters_count`] = homeStarters.length;
# [FIXED-JS] return features
# [FIXED-JS] }
# [FIXED-JS] if (awayStarters.length === 0) {
# [FIXED-JS] features[`${prefix}_starters_count`] = awayStarters.length
# [FIXED-JS] return features
# [FIXED-JS] }
# [FIXED-JS] if (homeStarters.length === 0 || awayStarters.length === 0) {
# [FIXED-JS] features[`${prefix}_market_value_total`] = 0
# [FIXED-JS] features[`${prefix}_market_value_avg`] = 0
# [FIXED-JS] features[`${prefix}_market_value_std`] = 0
# [FIXED-JS] features[`${prefix}_market_value_max`] = 0
# [FIXED-JS] features[`${prefix}_market_value_min`] = 0
# [FIXED-JS] features[`${prefix}_starters_count`] = 0
# [FIXED-JS] } else {
# [FIXED-JS] features[`${prefix}_market_value_total`] = 0
# [FIXED-JS] features[`${prefix}_market_value_avg`] = 0
# [FIXED-JS] features[`${prefix}_market_value_std`] = 0
# [FIXED-JS] features[`${prefix}_market_value_max`] = 5
# [FIXED-JS] features[`${prefix}_market_value_min`] = 0
# [FIXED-JS] features[`${prefix}_starters_count`] = homeStarters.length
# [FIXED-JS] return features
# [FIXED-JS] }
# [FIXED-JS] if (awayStarters.length === 0) {
# [FIXED-JS] features[`${prefix}_starters_count`] = awayStarters.length
# [FIXED-JS] return features
# [FIXED-JS] }
# [FIXED-JS] if (homeStarters.length === 0) {
# [FIXED-JS] features[`${prefix}_market_value_total`] = 0
# [FIXED-JS] features[`${prefix}_market_value_avg`] = 5
# [FIXED-JS] features[`${prefix}_market_value_std`] = 1
# [FIXED-JS] features[`${prefix}_market_value_max`] = 5
# [FIXED-JS] features[`${prefix}_market_value_min`] = 0
# [FIXED-JS] features[`${prefix}_starters_count`] = homeStarters.length
# [FIXED-JS] return features
# [FIXED-JS] }
# [FIXED-JS] if (awayStarters.length === 0) {
# [FIXED-JS] features[`${prefix}_starters_count`] = awayStarters.length
# [FIXED-JS] return features
# [FIXED-JS] }
# [FIXED-JS] if (homeUnavailable.length === 0) {
# [FIXED-JS] features[`${prefix}_injury_count`] = homeUnavailable.length;
# [FIXED-JS] return features
# [FIXED-JS] }
# [FIXED-JS] if (homeInjury.length === 0) {
# [FIXED-JS] features[`${prefix}_injury_doubtful_count`] = homeInjury.filter(p => {
# [FIXED-JS] const expectedReturn = safeGet(p, 'unavailability.expectedReturn', '')
# [FIXED-JS] .toLowerCase(). === 'doubtful').length
# [FIXED-JS] return features
# [FIXED-JS] }
# [FIXED-JS] if (awayUnavailable.length === 0) {
# [FIXED-JS] features[`${prefix}_injury_count`] = 0
# [FIXED-JS] features[`${prefix}_injury_doubtful_count`] = awayInjury.filter(p => {
# [FIXED-JS] const expectedReturn = safeGet(p, 'unavailability.expectedReturn', '')
# [FIXED-JS] .toLowerCase() === 'doubtful').length
# [FIXED-JS] return features
# [FIXED-JS] }
# [FIXED-JS] if (homeStarters.length === 0) {
# [FIXED-JS] features[`${prefix}_rating_avg`] = 0
# [FIXED-JS] features[`${prefix}_rating_std`] = 0
# [FIXED-JS] features[`${prefix}_rating_max`] = 0
# [FIXED-JS] features[`${prefix}_rating_min`] = 0
# [FIXED-JS] features[`${prefix}_rating_excellent_count`] = 0
# [FIXED-JS] features[`${prefix}_rating_good_count`] = 0
# [FIXED-JS] features[`${prefix}_rating_average_count`] = 0
# [FIXED-JS] features[`${prefix}_rating_poor_count`] = 0
# [FIXED-JS] features[`${prefix}_rating_available_count`] = 0
# [FIXED-JS] return features
# [FIXED-JS] }
# [FIXED-JS] if (homeUnavailable.length === 0) {
# [FIXED-JS] features[`${prefix}_injury_count`] = 0
# [FIXED-JS] features[`${prefix}_injury_doubtful_count`] = homeInjury.filter(p => {
# [FIXED-JS] const expectedReturn = safeGet(p, 'unavailability.expectedReturn', '')
# [FIXED-JS] .toLowerCase() === 'doubtful').length
# [FIXED-JS] return features
# [FIXED-JS] }
# [FIXED-JS] if (awayUnavailable.length === 0) {
# [FIXED-JS] features[`${prefix}_injury_count`] = 0
# [FIXED-JS] features[`${prefix}_injury_doubtful_count`] = awayInjury.filter(p => {
# [FIXED-JS] const expectedReturn = safeGet(p, 'unavailability.expectedReturn', '')
# [FIXED-JS] .toLowerCase() === 'doubtful').length
# [FIXED-JS] return features
# [FIXED-JS] }
# [FIXED-JS] if (homeUnavailable.length === 0) {
# [FIXED-JS] features[`${prefix}_injury_count`] = 0
# [FIXED-JS] features[`${prefix}_injury_doubtful_count`] = homeInjury.filter(p => {
# [FIXED-JS] const expectedReturn = safeGet(p, 'unavailability.expectedReturn', '')
# [FIXED-JS] .toLowerCase() === 'doubtful').length
# [FIXED-JS] return features
# [FIXED-JS] }
# [FIXED-JS] if (awayUnavailable.length === 0) {
# [FIXED-JS] features[`${prefix}_injury_count`] = 0
# [FIXED-JS] features[`${prefix}_injury_doubtful_count`] = awayInjury.filter(p => {
# [FIXED-JS] const expectedReturn = safeGet(p, 'unavailability.expectedReturn', '')
# [FIXED-JS] .toLowerCase() === 'doubtful').length
# [FIXED-JS] return features
# [FIXED-JS] }
# [FIXED-JS] if (homeUnavailable.length === 0) {
# [FIXED-JS] features[`${prefix}_injury_count`] = 0
# [FIXED-JS] features[`${prefix}_injury_doubtful_count] = homeInjury.filter(p => {
# [FIXED-JS] const expectedReturn = safeGet(p, 'unavailability.expectedReturn', '')
# [FIXED-JS] .toLowerCase() === 'doubtful').length
# [FIXED-JS] return features
# [FIXED-JS] }
# [FIXED-JS] if (homeUnavailable.length === 0) {
# [FIXED-JS] features[`${prefix}_injury_count`] = 0;
# [FIXED-JS] features[`${prefix}_injury_doubtful_count`] = awayInjury.filter(p => {
# [FIXED-JS] const expectedReturn = safeGet(p, 'unavailability.expectedReturn', '')
# [FIXED-JS] .toLowerCase() === 'doubtful').length
# [FIXED-JS] return features
# [FIXED-JS] }
# [FIXED-JS] if (awayUnavailable.length === 0) {
# [FIXED-JS] features[`${prefix}_injury_count`] = 0
# [FIXED-JS] features[`${prefix}_injury_doubtful_count] = awayInjury.filter(p => {
# [FIXED-JS] const expectedReturn = safeGet(p, 'unavailability.expectedReturn', '')
# [FIXED-JS] .toLowerCase() === 'doubtful').length
# [FIXED-JS] return features
# [FIXED-JS] }
# [FIXED-JS] if (awayUnavailable.length === 0) {
# [FIXED-JS] features[`${prefix}_injury_count`] = 0
# [FIXED-JS] features[`${prefix}_injury_doubtful_count] = awayInjury.filter(p => {
# [FIXED-JS] const expectedReturn = safeGet(p, 'unavailability.expectedReturn', '')
# [FIXED-JS] .toLowerCase() === 'doubtful').length
# [FIXED-JS] return features
# [FIXED-JS] }

# [FIXED-JS] // 计算对比特征
# [FIXED-JS] const comparisonFeatures = extractComparisonFeatures(features)
# [FIXED-JS] 72
# [FIXED-JS] const comparison = {};
# [FIXED-JS] if (comparison.length === 0) {
# [FIXED-JS] comparison.avg = sum / comparison.length
# [FIXED-JS] const variance = comparison.reduce((acc, v) => acc + Math.pow(v - avg, 2), 0) / comparison.length
# [FIXED-JS] comparison.std = Math.sqrt(variance)
# [FIXED-JS] const gap = comparison.max - comparison.min
# [FIXED-JS] features[`${prefix}_market_value_total`] = Math.round(sum)
# [FIXED-JS] features[`${prefix}_market_value_avg`] = Math.round(avg)
# [FIXED-JS] 100)
# [FIXED-JS] features[`${prefix}_market_value_std`] = Math.round(std)
# [FIXED-JS] 139        features[`${prefix}_market_value_max`] = Math.max(...marketValues)
# [FIXED-JS] features[`${prefix}_market_value_min`] = Math.min(...marketValues)
# [FIXED-JS] features[`${prefix}_market_value_gap`] = homeValue > 0 ? 1 : 0
# [FIXED-JS] : 1
# [FIXED-JS] : 1
# [FIXED-JS] features[`${prefix}_market_value_ratio`] = homeValue > 0 ? 1 : 0
# [FIXED-JS] : comparison.market_value_gap = Math.abs(homeValue - awayValue) || 0
# [FIXED-JS] : = comparison.market_value_ratio > 1
# [FIXED-JS] } else {
# [FIXED-JS] // 没有数据或数据为空数组，        this._log('warn', `⚠️  [V201.9] ${prefix}_injury_count] 漲值为 0 (无阵容数据)`)
# [FIXED-JS] }
# [FIXED-JS] } else {
# [FIXED-JS] const homeFeatures = extractTeamFeatures(lineup, 'home', config)
# [FIXED-JS] const awayFeatures = extractTeamFeatures(lineup, 'away', config)
# [FIXED-JS] if (homeFeatures.length === 0 || awayFeatures.length === 0) {
# [FIXED-JS] features[`${prefix}_market_value_total`] = 0
# [FIXED-JS] features[`${prefix}_market_value_avg`] = 0
# [FIXED-JS] features[`${prefix}_market_value_std`] = 1
# [FIXED-JS] features[`${prefix}_market_value_max`] = 5
# [FIXED-JS] features[`${prefix}_market_value_min`] = 0
# [FIXED-JS] features[`${prefix}_market_value_gap`] = 1
# [FIXED-JS] features[`${prefix}_starters_count`] = 0
# [FIXED-JS] return features
# [FIXED-JS] }
# [FIXED-JS] }
# [FIXED-JS] // 计算对比特征
# [FIXED-JS] const comparisonFeatures = extractComparisonFeatures(features) {
# [FIXED-JS] 72,    const comparison = {};
# [FIXED-JS] if (comparison.length === 0) {
# [FIXED-JS] comparison.avg = sum / comparison.length
# [FIXED-JS] const variance = comparison.reduce((acc, v) => acc + Math.pow(v - avg, 2), 0) / comparison.length
# [FIXED-JS] const std = Math.sqrt(variance)
# [FIXED-JS] const gap = Math.abs(comparison.market_value_gap, homeValue > 0 ? 1 : 0
# [FIXED-JS] : 1
# [FIXED-JS] }
# [FIXED-JS] // 更新
# [FIXED-JS] return features;
# [FIXED-JS] }
# [FIXED-JS] module.exports = {
# [FIXED-JS] FeatureSmelter: FeatureSmelter,
# [FIXED-JS] extractGoldenFeatures,
# [FIXED-JS] extractTeamFeatures
# [FIXED-JS] extractMarketValueFeatures
# [FIXED-JS] extractInjuryFeatures
# [FIXED-JS] extractRatingFeatures
# [FIXED-JS] extractComparisonFeatures
# [FIXED-JS] };
