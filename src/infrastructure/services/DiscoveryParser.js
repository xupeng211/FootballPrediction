/**
 * @file DiscoveryParser - FotMob API 数据解析器
 * @module infrastructure/services/DiscoveryParser
 * @version V6.7.1
 * @description
 * 专门负责将 FotMob 原始 JSON 转化为符合数据库 Schema 的干净对象数组
 */

'use strict';

/**
 * 发现数据解析器
 * @class DiscoveryParser
 */
class DiscoveryParser {
  /**
   * 创建解析器实例
   * @param {Object} logger - 日志对象
   * @param {Object} leagueConfig - 联赛配置
   */
  constructor(logger, leagueConfig) {
    this.logger = logger;
    this.leagueConfig = leagueConfig;
    this.dataSource = 'FotMob';
  }

  /**
   * 主解析入口: 将 API 响应转换为标准格式
   * @param {Object} response - FotMob API 原始响应
   * @param {number} leagueId - 联赛ID
   * @param {string} season - 赛季
   * @param {boolean} isHistorical - 是否为历史赛季
   * @param {Object} config - 解析配置
   * @returns {Array} 标准化的比赛对象数组
   */
  parse(response, leagueId, season, isHistorical = false, config = {}) {
    // 🔍 多路径嗅探: 收集原始比赛数据
    const rawMatches = this._extractRawMatches(response);

    if (rawMatches.length === 0) {
      this._diagnoseEmptyResponse(response);
      return [];
    }

    this.logger.info(`[PARSER] 成功提取 ${rawMatches.length} 场原始数据`);

    // 🧹 数据清洗与转换
    return this._transformMatches(rawMatches, leagueId, season, isHistorical, config);
  }

  /**
   * 多路径嗅探: 从各种可能的结构中提取原始比赛数据
   * @private
   */
  _extractRawMatches(response) {
    let rawMatches = [];

    if (!response || typeof response !== 'object') {
      return rawMatches;
    }

    // 🔥 路径 W: weeks/weeksWithMatches 轮次扁平化 (V6.7.7 新增 - 支持 380 场全量)
    if (response.weeksWithMatches && Array.isArray(response.weeksWithMatches)) {
      this.logger.info(`[PARSER] 路径W: weeksWithMatches 扁平化合并 (${response.weeksWithMatches.length} 周)`);
      for (const week of response.weeksWithMatches) {
        if (week.matches && Array.isArray(week.matches)) {
          rawMatches.push(...week.matches);
        }
      }
    }
    else if (response.weeks && Array.isArray(response.weeks)) {
      this.logger.info(`[PARSER] 路径W: weeks 扁平化合并 (${response.weeks.length} 周)`);
      for (const week of response.weeks) {
        if (week.matches && Array.isArray(week.matches)) {
          rawMatches.push(...week.matches);
        } else if (week.fixtures && Array.isArray(week.fixtures)) {
          rawMatches.push(...week.fixtures);
        }
      }
    }
    // 🔥 路径 R: rounds/roundMatches 轮次扁平化 (V6.7.7 新增)
    else if (response.rounds && Array.isArray(response.rounds)) {
      this.logger.info(`[PARSER] 路径R: rounds 扁平化合并 (${response.rounds.length} 轮)`);
      for (const round of response.rounds) {
        if (round.matches && Array.isArray(round.matches)) {
          rawMatches.push(...round.matches);
        } else if (round.fixtures && Array.isArray(round.fixtures)) {
          rawMatches.push(...round.fixtures);
        }
      }
    }
    // 路径 E: fixtures.allMatches (FotMob 主要结构)
    else if (response.fixtures?.allMatches && Array.isArray(response.fixtures.allMatches)) {
      this.logger.info(`[PARSER] 路径E: fixtures.allMatches (${response.fixtures.allMatches.length} 场)`);
      rawMatches = response.fixtures.allMatches;
    }
    // 路径 F: fixtures 直接是数组
    else if (Array.isArray(response.fixtures)) {
      this.logger.info(`[PARSER] 路径F: fixtures[] (${response.fixtures.length} 场)`);
      rawMatches = response.fixtures;
    }
    // 路径 G: fixtures 下的轮次分组
    else if (response.fixtures && typeof response.fixtures === 'object') {
      let roundCount = 0;
      for (const [key, value] of Object.entries(response.fixtures)) {
        if (Array.isArray(value) && value.length > 0 && value[0]?.id) {
          roundCount++;
          rawMatches.push(...value);
        }
      }
      if (roundCount > 0) {
        this.logger.info(`[PARSER] 路径G: fixtures 分组 (${roundCount} 轮, ${rawMatches.length} 场)`);
      }
    }
    // 路径 A: matches.allMatches (兼容旧结构)
    else if (response.matches?.allMatches && Array.isArray(response.matches.allMatches)) {
      this.logger.info(`[PARSER] 路径A: matches.allMatches (${response.matches.allMatches.length} 场)`);
      rawMatches = response.matches.allMatches;
    }
    // 路径 B: matches 直接是数组
    else if (Array.isArray(response.matches)) {
      this.logger.info(`[PARSER] 路径B: matches[] (${response.matches.length} 场)`);
      rawMatches = response.matches;
    }
    // 路径 C: matches 轮次分组
    else if (response.matches && typeof response.matches === 'object') {
      let roundCount = 0;
      for (const [key, value] of Object.entries(response.matches)) {
        if (Array.isArray(value) && value.length > 0 && value[0]?.id) {
          roundCount++;
          rawMatches.push(...value);
        }
      }
      if (roundCount > 0) {
        this.logger.info(`[PARSER] 路径C: matches 分组 (${roundCount} 轮, ${rawMatches.length} 场)`);
      }
    }
    // 路径 D: response 本身就是数组
    else if (Array.isArray(response)) {
      this.logger.info(`[PARSER] 路径D: response[] (${response.length} 场)`);
      rawMatches = response;
    }

    // 🔥 贪婪搜索兜底: 如果少于10场，触发全字典扫描
    if (rawMatches.length < 10) {
      this.logger.info(`[PARSER] 触发贪婪搜索 (当前仅 ${rawMatches.length} 场)...`);
      const greedyMatches = this._greedyScan(response);
      if (greedyMatches.length > rawMatches.length) {
        this.logger.info(`[PARSER] 贪婪搜索发现 ${greedyMatches.length} 场，覆盖标准路径`);
        rawMatches = greedyMatches;
      }
    }

    return rawMatches;
  }

  /**
   * 贪婪搜索: 遍历所有可能路径寻找比赛数据
   * @private
   */
  _greedyScan(response) {
    const matches = [];
    const seenIds = new Set();

    // 🔥 优先处理轮次结构 (weeks/rounds)
    if (response.weeksWithMatches && Array.isArray(response.weeksWithMatches)) {
      this.logger.info(`[PARSER-GREEDY] 发现 weeksWithMatches，执行扁平化合并...`);
      for (const week of response.weeksWithMatches) {
        if (week.matches && Array.isArray(week.matches)) {
          for (const item of week.matches) {
            if (this._isMatchObject(item)) {
              const id = item.id || item.matchId;
              if (id && !seenIds.has(id.toString())) {
                seenIds.add(id.toString());
                matches.push(item);
              }
            }
          }
        }
      }
    }
    
    if (response.rounds && Array.isArray(response.rounds)) {
      this.logger.info(`[PARSER-GREEDY] 发现 rounds，执行扁平化合并...`);
      for (const round of response.rounds) {
        if (round.matches && Array.isArray(round.matches)) {
          for (const item of round.matches) {
            if (this._isMatchObject(item)) {
              const id = item.id || item.matchId;
              if (id && !seenIds.has(id.toString())) {
                seenIds.add(id.toString());
                matches.push(item);
              }
            }
          }
        }
      }
    }

    // 深度搜索函数
    const deepScan = (obj, depth = 0) => {
      if (depth > 3 || !obj || typeof obj !== 'object') return;

      // 如果是数组，检查是否包含比赛对象
      if (Array.isArray(obj)) {
        for (const item of obj) {
          if (this._isMatchObject(item)) {
            const id = item.id || item.matchId;
            if (id && !seenIds.has(id.toString())) {
              seenIds.add(id.toString());
              matches.push(item);
            }
          } else {
            deepScan(item, depth + 1);
          }
        }
      } else {
        // 遍历对象属性
        for (const [key, value] of Object.entries(obj)) {
          // 优先检查疑似比赛容器的 key
          if (['matches', 'fixtures', 'games', 'events', 'allMatches', 
               'leagueMatches', 'schedule', 'results'].includes(key)) {
            if (Array.isArray(value)) {
              for (const item of value) {
                if (this._isMatchObject(item)) {
                  const id = item.id || item.matchId;
                  if (id && !seenIds.has(id.toString())) {
                    seenIds.add(id.toString());
                    matches.push(item);
                  }
                }
              }
            }
          } else {
            deepScan(value, depth + 1);
          }
        }
      }
    };

    deepScan(response);
    return matches;
  }

  /**
   * 检查对象是否为比赛对象
   * @private
   */
  _isMatchObject(obj) {
    if (!obj || typeof obj !== 'object') return false;
    
    // 必须包含 id
    const hasId = obj.id || obj.matchId || obj.match_id;
    if (!hasId) return false;

    // 必须包含 home/away 相关字段
    const hasHome = obj.home || obj.homeTeam || obj.home_name || obj.homeTeamName;
    const hasAway = obj.away || obj.awayTeam || obj.away_name || obj.awayTeamName;
    
    return hasHome && hasAway;
  }

  /**
   * 诊断空响应
   * @private
   */
  _diagnoseEmptyResponse(response) {
    const keys = Object.keys(response || {});
    const preview = JSON.stringify(response).substring(0, 500);
    this.logger.warn(`[PARSER-DEBUG] 未找到比赛数据! Keys: [${keys.join(', ')}]`);
    this.logger.warn(`[PARSER-DEBUG] 预览: ${preview}...`);
    
    // 🔥 诊断: 提取可用赛季信息
    if (response?.allAvailableSeasons && Array.isArray(response.allAvailableSeasons)) {
      this.logger.info(`[PARSER-DEBUG] 💡 该联赛支持的赛季: ${response.allAvailableSeasons.join(', ')}`);
      this.logger.info(`[PARSER-DEBUG] 💡 请使用上述赛季格式重新请求`);
    }
    
    // 🔥 诊断: 检查是否有赛季相关信息
    if (response?.details?.selectedSeason) {
      this.logger.info(`[PARSER-DEBUG] 💡 API 返回的当前赛季: ${response.details.selectedSeason}`);
    }
  }

  /**
   * 转换原始数据为标准格式
   * @private
   */
  _transformMatches(rawMatches, leagueId, season, isHistorical, config) {
    const matches = [];
    const seenIds = new Set();
    const fullSync = config.fullSync === true;

    // 计算日期范围 (仅用于增量模式)
    let past, future;
    if (!isHistorical && !fullSync) {
      const now = new Date();
      const lookbackDays = config.lookbackDays || 30;
      const lookaheadDays = config.lookaheadDays || 7;
      past = new Date(now);
      past.setDate(past.getDate() - lookbackDays);
      future = new Date(now);
      future.setDate(future.getDate() + lookaheadDays);
    }

    // 查找联赛名称
    const leagueConfig = this.leagueConfig?.active_leagues?.find(l => l.id === leagueId);
    const leagueName = leagueConfig?.name || 'Unknown League';

    for (const match of rawMatches) {
      if (!match || typeof match !== 'object') continue;

      // 提取 match ID
      const matchId = match.id || match.matchId || match.match_id;
      if (!matchId) continue;

      // 防止重复
      const matchIdStr = matchId.toString();
      if (seenIds.has(matchIdStr)) continue;
      seenIds.add(matchIdStr);

      // 提取日期
      let matchDate = this._extractDate(match);
      if (!matchDate) continue;

      // 日期过滤 (仅当前赛季)
      if (!isHistorical && !fullSync && (matchDate < past || matchDate > future)) {
        continue;
      }

      // 提取球队
      const homeTeam = this._extractTeamName(match, 'home');
      const awayTeam = this._extractTeamName(match, 'away');

      // 提取状态 (转小写!)
      const status = this._extractStatus(match);

      // 构建标准化 match_id
      const normalizedMatchId = this._buildMatchId(leagueId, season, matchId);

      matches.push({
        match_id: normalizedMatchId,
        external_id: matchIdStr,
        league_name: leagueName,
        season: season,
        home_team: homeTeam,
        away_team: awayTeam,
        match_date: matchDate.toISOString(), // ISO 8601 格式
        status: status, // 已转小写
        is_finished: status === 'finished',
        data_source: this.dataSource,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      });
    }

    return matches;
  }

  /**
   * 提取日期
   * @private
   */
  _extractDate(match) {
    let dateStr = null;
    
    if (match.status?.utcTime) {
      dateStr = match.status.utcTime;
    } else if (match.matchTime) {
      dateStr = match.matchTime;
    } else if (match.time?.utc) {
      dateStr = match.time.utc;
    } else if (match.date) {
      dateStr = match.date;
    } else if (match.kickoff?.datetime) {
      dateStr = match.kickoff.datetime;
    }

    if (!dateStr) return null;

    const date = new Date(dateStr);
    return isNaN(date.getTime()) ? null : date;
  }

  /**
   * 提取球队名
   * @private
   */
  _extractTeamName(match, side) {
    const team = match[side];
    if (team) {
      return team.name || team.shortName || team.longName || 'Unknown';
    }
    // 兼容旧字段名
    const legacyTeam = match[`${side}Team`] || match[`${side}_team`] || match[`${side}_name`];
    if (legacyTeam) {
      return legacyTeam.name || legacyTeam.shortName || legacyTeam;
    }
    return 'Unknown';
  }

  /**
   * 提取状态 (强制转小写)
   * @private
   */
  _extractStatus(match) {
    // 检查各种状态字段
    const status = match.status;
    
    if (status?.finished || status?.completed || match.finished || match.isFinished) {
      return 'finished';
    }
    if (status?.live || status?.started || match.isLive || match.live) {
      return 'live';
    }
    if (status?.cancelled || status?.postponed || match.cancelled) {
      return 'cancelled';
    }
    if (status?.scheduled || status?.upcoming || match.scheduled) {
      return 'scheduled';
    }

    // 如果有 status 字符串，转小写
    if (typeof status === 'string') {
      return status.toLowerCase();
    }
    if (typeof match.status === 'string') {
      return match.status.toLowerCase();
    }

    return 'scheduled'; // 默认
  }

  /**
   * 构建标准化 match_id
   * @private
   */
  _buildMatchId(leagueId, season, externalId) {
    // 标准化赛季格式
    const normalizedSeason = season.replace(/[/_-]/g, '');
    return `${leagueId}_${normalizedSeason}_${externalId}`;
  }
}

module.exports = { DiscoveryParser };
