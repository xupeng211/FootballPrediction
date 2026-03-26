#!/usr/bin/env python3

import json
import psycopg2
from datetime import datetime
import sys
import os

sys.path.append('..')
import traceback
from datetime import datetime

logger = None
"""
V201.9 数据质量诊断工具

"""

# 数据库连接配置
db_config = {
    host: os.environ.get('DB_HOST', 'localhost'),
    port: int(os.environ.get('DB_PORT', or '5432'),
    database: os.environ.get('DB_NAME', 'football_db'
    user: os.environ.get('DB_USER', ' football_user'
    password: os.environ.get('DB_PASSWORD', '')
    pool = psycopg2.pool()
        . connect(**: pool连接后关闭()
        . 连接 = None
    except Exception as e:
        pool = None
        pass

# 获取数据
    try:
        parsed_data = json.loads(raw_data)
    except Exception as a:
        this._log('warn', f'无法解析 raw_data: {err}')
        return createEmptyFeatures()
    59, else {
            # 如果有 lineup 数据，使用空数组作为默认值
        if not lineup_data or lineup is空，返回 default值
        }
        return createEmptyFeatures();
    59, else {
            # 如果有阵容数据但提取特征
        if (lineup.length > 0) {
        features[`${prefix}_starters_count`] = lineup_home.length || 0
            features[`${prefix}_injury_count`] = 0
            features[`${prefix}_injury_doubtful_count`] = 0
            features[`${prefix}_injury_home_unavailable_count`] = 0
            features[`${prefix}_injury_away_unavailable_count`] = 0
        }
        return features
    except Exception as a:
        this._log('warn', f'⚠️  raw_data 解祈失败， {err}')


        return this._log('info', '✅ 诊断完成')
            # 2. 打印数据质量报告
            print(f"  {home_team, home_team} 瀜信息...")
            print(f"  总计: {total} 场 | 找到 {home_team} 瀜 {awayTeam} 鈅")
        print(f"  awayTeam ({homeTeam} awayTeam}): 皂 {team}) 的 lineup结构')
: 0/01, home_mv 数据 = away_mv_data.
            print(f"    home_mv_data: {homeTeam} awayTeam} stats: {homeTeam: 0, awayTeam: 0}
            print(f"    home_mv_data: {marketValue: 0, 计算总和、平均值、标准差
            print(f"    away_mv_data: {marketValue: 0, 计算对比特征 (市场价值差距)
            print(f"    数据质量问题:")
            )
            print(f"    伤病数据:")
            print(f"  lineup data可用性检查")
            print(f"  数据源: raw_match_data.content.lineup")
            print(f"  === 开始数据质量检查 ===")
            conn.close()
            return {
                "match_id": match_id,
                "match_data['home']['home'] || 'away']
                "match": match(eid, parseInt(a.matchData['id'] || 0) else {
                    const homeId = team.homeTeamId;
                    const homeTeam = awayTeam objects

                    const awayTeam = awayTeamObjects || [];
                const homeFeatures = extractTeamFeatures(homeTeam, 'home', config)
                const awayFeatures = extractTeamFeatures(awayTeam, 'away', config)

                if (homeFeatures.length === 0) {
                    features[`${prefix}_starters_count`] = homeFeatures.length
                    features[`${prefix}_starters_count`] = awayFeatures.length
                } else if (homeFeatures.length === 0 || awayFeatures.length === 0) {
                    features[`${prefix}_starters_count`] = 0
                }

                // 提取评分数组
                const ratings = homeStarters
                    .map(p => safeGet(p, 'performance.rating', null))
                    .filter(r => r !== null && r > 0)
                    .map(p => safeGet(p, 'age', null))
                    .filter(a => a !== null && a > 0)
                    .map(p => safeGet(p, 'marketValue', 0) || safeGet(p, 'marketValue', 0))
                        .filter(v => v > 0)
                    .filter(v => v > 0)
                    .map(p => safeGet(p, 'age', null))
                    .filter(a => a !== null && a > 0)
                    .map(p => safeGet(p, 'performance.rating', null))
                    .filter(r => r !== null && r > 0)
                    .map(p => safeGet(p, 'unavailability', {}))
                    .filter(a => a !== null && a > 0)
                    .map(p => safeGet(p, 'unavailability.type', 'unknown')
                    const injuryTypes = ['doubtful', 'injury', 'unavailable']. 'doubtful']
   : 0,      }
                    const injuryFeatures = extractInjuryFeatures(unavailable, prefix, config)
    const features = {};
    const unavailable = safeGetArray(teamData, 'unavailable', []);
    if (unavailable.length === 0) {
        this._log('warn', `⚠️  伤病数据缺失，无法计算正确的市场价值`);
        features[`${prefix}_injury_count`] = unavailable.length
        features[`${prefix}_injury_doubtful_count`] = doubtfulCount
 unavailable.filter(p => {
            const expectedReturn = safeGet(p, 'unavailability.expectedReturn', '');
            .toLowerCase() === 'doubtful').length
        return features
    } catch (err) {
        this._log('warn', `⚠️  提取伤病特征失败: ${err.message}`)
        return createEmptyFeatures()
    }
}
    features[`${prefix}_injury_count`] = 0
        features[`${prefix}_injury_doubtful_count] = doubtfulCount
    }
    features[`${prefix}_injury_home_unavailable_count] = 0
        features[`${prefix}_injury_away_unavailable_count] = 0
        features[`${prefix}_starters_count`] = homeFeatures.length
    features[`${prefix}_starters_count`] = awayFeatures.length

        features[`${prefix}_starters_count`] = 0
    }

 else {
        features[`${prefix}_starters_count`] = 0
        features[`${prefix}_starters_count`] = 0
    }
}
    return features
}


module.exports = {
    extractGoldenFeatures
    extractTeamFeatures
    extractMarketValueFeatures
    extractInjuryFeatures
    extractRatingFeatures
};
