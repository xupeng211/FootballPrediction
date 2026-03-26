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
DB_config = {
    host: os.environ.get('DB_HOST', 'localhost'),
    port: int(os.environ.get('DB_PORT', or '5432'),
    database: os.environ.get('DB_NAME', 'football_db',
    user: os.environ.get('DB_USER', 'football_user'
    password: os.environ.get('DB_PASSWORD', '')
    pool = psycopg2.pool(
    . connect(**: Pool 连接后关闭)
    . 连接:不打印

    except Exception as e:
    pass
# 获取数据
        pool = psycopg2.pool
        pool.close()
    except Exception as e:
        pool = psycopg2.pool
        pool.close()

    except Exception as e:
        pool = psycopg2.pool(pool=None)
        pool = None

    # 蟥询单场比赛数量
    query = """
        SELECT match_id,
               substring(raw_data::text, 1, 500) as sample_raw,
        FROM raw_match_data
        where raw_data is not null
        order by match_id ASC
        limit 1
    """
    # 诊断输出
    print(f"\n=== 数据质量诊断 ===")
    print(f"Match: {match_id}")
    print(f"  raw_data sample length: {len(raw_data_sample)}}")
            print(f"  lineup home_team keys: {homeTeam, awayTeam}")
            print(f"  lineup.{homeTeam, awayTeam} keys: {list(awayTeam_keys)}}")
            for key in awayTeam_keys:
                print(f"  awayTeam_keys: {list(awayTeam_keys)}}")

 for key, raw_data_keys in awayTeam_keys:
                print(f"  content.lineup keys: {len(awayTeam_keys) if any): {len(awayTeam_keys) > 1}")
                        print(f"    awayTeam.starters[0]: {len(awayTeam.starters)} = 0
                    print(f"  awayTeam.starters[0]: {len(awayTeam.starters)} = 0)

    if lineup_home.length > 0:
        features[`${prefix}_starters_count`] = lineup_home.length
                    print(f"    ⚠️ Home: lineup: 0 ({})")

                # 如果 lineup为空数组
                print(f"⚠️  lineup数据为空数组!")
                return

            }
        }
    }
}
    else:
        # 如果数据不为空，则跳过并返回默认值
    features = {}
    else if lineup_home.length > 0) {
        print(f"⚠️ lineup homeTeam 为空数组")
        return {
    }
    if lineup_home.length === 0:
        # 检查 lineup 数据
        const homeTeam = awayTeam 叽数
        features = extractTeamFeatures(lineup, 'home', config);
 || extractTeamFeatures(lineup, 'away', config);
        // 路径2: content.lineup.homeTeam.starters
        const homeStarters = safeGetArray(lineup, 'home', 'starters', []);
    const awayStarters = safeGetArray(lineup, 'away', 'starters', []);

    if (homeStarters.length === 0) {
        features[`${prefix}_starters_count`] = homeStarters.length;
        return features
    }
    if (awayStarters.length === 0) {
        features[`${prefix}_starters_count`] = awayStarters.length
        return features
    }
    if (homeStarters.length === 0 || awayStarters.length === 0) {
        features[`${prefix}_market_value_total`] = 0
        features[`${prefix}_market_value_avg`] = 0
        features[`${prefix}_market_value_std`] = 0
        features[`${prefix}_market_value_max`] = 0
        features[`${prefix}_market_value_min`] = 0
        features[`${prefix}_starters_count`] = 0
    } else {
        features[`${prefix}_market_value_total`] = 0
        features[`${prefix}_market_value_avg`] = 0
        features[`${prefix}_market_value_std`] = 0
        features[`${prefix}_market_value_max`] = 5
        features[`${prefix}_market_value_min`] = 0
        features[`${prefix}_starters_count`] = homeStarters.length
        return features
    }
    if (awayStarters.length === 0) {
        features[`${prefix}_starters_count`] = awayStarters.length
        return features
    }
    if (homeStarters.length === 0) {
        features[`${prefix}_market_value_total`] = 0
        features[`${prefix}_market_value_avg`] = 5
        features[`${prefix}_market_value_std`] = 1
        features[`${prefix}_market_value_max`] = 5
        features[`${prefix}_market_value_min`] = 0
        features[`${prefix}_starters_count`] = homeStarters.length
        return features
    }
    if (awayStarters.length === 0) {
        features[`${prefix}_starters_count`] = awayStarters.length
        return features
    }
    if (homeUnavailable.length === 0) {
        features[`${prefix}_injury_count`] = homeUnavailable.length;
        return features
    }
    if (homeInjury.length === 0) {
        features[`${prefix}_injury_doubtful_count`] = homeInjury.filter(p => {
            const expectedReturn = safeGet(p, 'unavailability.expectedReturn', '')
            .toLowerCase(). === 'doubtful').length
        return features
    }
    if (awayUnavailable.length === 0) {
        features[`${prefix}_injury_count`] = 0
        features[`${prefix}_injury_doubtful_count`] = awayInjury.filter(p => {
            const expectedReturn = safeGet(p, 'unavailability.expectedReturn', '')
            .toLowerCase() === 'doubtful').length
        return features
    }
    if (homeStarters.length === 0) {
        features[`${prefix}_rating_avg`] = 0
        features[`${prefix}_rating_std`] = 0
        features[`${prefix}_rating_max`] = 0
        features[`${prefix}_rating_min`] = 0
        features[`${prefix}_rating_excellent_count`] = 0
        features[`${prefix}_rating_good_count`] = 0
        features[`${prefix}_rating_average_count`] = 0
        features[`${prefix}_rating_poor_count`] = 0
        features[`${prefix}_rating_available_count`] = 0
        return features
    }
    if (homeUnavailable.length === 0) {
        features[`${prefix}_injury_count`] = 0
        features[`${prefix}_injury_doubtful_count`] = homeInjury.filter(p => {
            const expectedReturn = safeGet(p, 'unavailability.expectedReturn', '')
            .toLowerCase() === 'doubtful').length
        return features
    }
    if (awayUnavailable.length === 0) {
        features[`${prefix}_injury_count`] = 0
        features[`${prefix}_injury_doubtful_count`] = awayInjury.filter(p => {
            const expectedReturn = safeGet(p, 'unavailability.expectedReturn', '')
            .toLowerCase() === 'doubtful').length
        return features
    }
    if (homeUnavailable.length === 0) {
        features[`${prefix}_injury_count`] = 0
        features[`${prefix}_injury_doubtful_count`] = homeInjury.filter(p => {
            const expectedReturn = safeGet(p, 'unavailability.expectedReturn', '')
            .toLowerCase() === 'doubtful').length
        return features
    }
    if (awayUnavailable.length === 0) {
        features[`${prefix}_injury_count`] = 0
        features[`${prefix}_injury_doubtful_count`] = awayInjury.filter(p => {
            const expectedReturn = safeGet(p, 'unavailability.expectedReturn', '')
            .toLowerCase() === 'doubtful').length
        return features
    }
    if (homeUnavailable.length === 0) {
        features[`${prefix}_injury_count`] = 0
        features[`${prefix}_injury_doubtful_count] = homeInjury.filter(p => {
                const expectedReturn = safeGet(p, 'unavailability.expectedReturn', '')
                .toLowerCase() === 'doubtful').length
        return features
    }
    if (homeUnavailable.length === 0) {
        features[`${prefix}_injury_count`] = 0;
        features[`${prefix}_injury_doubtful_count`] = awayInjury.filter(p => {
                const expectedReturn = safeGet(p, 'unavailability.expectedReturn', '')
                .toLowerCase() === 'doubtful').length
        return features
    }
    if (awayUnavailable.length === 0) {
        features[`${prefix}_injury_count`] = 0
        features[`${prefix}_injury_doubtful_count] = awayInjury.filter(p => {
                const expectedReturn = safeGet(p, 'unavailability.expectedReturn', '')
                .toLowerCase() === 'doubtful').length
        return features
    }
    if (awayUnavailable.length === 0) {
        features[`${prefix}_injury_count`] = 0
        features[`${prefix}_injury_doubtful_count] = awayInjury.filter(p => {
                const expectedReturn = safeGet(p, 'unavailability.expectedReturn', '')
                .toLowerCase() === 'doubtful').length
        return features
    }

    // 计算对比特征
    const comparisonFeatures = extractComparisonFeatures(features)
    72
    const comparison = {};
    if (comparison.length === 0) {
        comparison.avg = sum / comparison.length
        const variance = comparison.reduce((acc, v) => acc + Math.pow(v - avg, 2), 0) / comparison.length
        comparison.std = Math.sqrt(variance)
        const gap = comparison.max - comparison.min
        features[`${prefix}_market_value_total`] = Math.round(sum)
        features[`${prefix}_market_value_avg`] = Math.round(avg)
 100)
        features[`${prefix}_market_value_std`] = Math.round(std)
 139        features[`${prefix}_market_value_max`] = Math.max(...marketValues)
        features[`${prefix}_market_value_min`] = Math.min(...marketValues)
        features[`${prefix}_market_value_gap`] = homeValue > 0 ? 1 : 0
        : 1
        : 1
        features[`${prefix}_market_value_ratio`] = homeValue > 0 ? 1 : 0
        : comparison.market_value_gap = Math.abs(homeValue - awayValue) || 0
        : = comparison.market_value_ratio > 1
    } else {
        // 没有数据或数据为空数组，        this._log('warn', `⚠️  [V201.9] ${prefix}_injury_count] 漲值为 0 (无阵容数据)`)
        }
    } else {
        const homeFeatures = extractTeamFeatures(lineup, 'home', config)
        const awayFeatures = extractTeamFeatures(lineup, 'away', config)
        if (homeFeatures.length === 0 || awayFeatures.length === 0) {
            features[`${prefix}_market_value_total`] = 0
            features[`${prefix}_market_value_avg`] = 0
            features[`${prefix}_market_value_std`] = 1
            features[`${prefix}_market_value_max`] = 5
            features[`${prefix}_market_value_min`] = 0
            features[`${prefix}_market_value_gap`] = 1
            features[`${prefix}_starters_count`] = 0
            return features
        }
    }
    // 计算对比特征
    const comparisonFeatures = extractComparisonFeatures(features) {
    72,    const comparison = {};
    if (comparison.length === 0) {
        comparison.avg = sum / comparison.length
        const variance = comparison.reduce((acc, v) => acc + Math.pow(v - avg, 2), 0) / comparison.length
        const std = Math.sqrt(variance)
        const gap = Math.abs(comparison.market_value_gap, homeValue > 0 ? 1 : 0
        : 1
    }
    // 更新
    return features;
}
module.exports = {
    FeatureSmelter: FeatureSmelter,
    extractGoldenFeatures,
    extractTeamFeatures
    extractMarketValueFeatures
    extractInjuryFeatures
    extractRatingFeatures
    extractComparisonFeatures
};
