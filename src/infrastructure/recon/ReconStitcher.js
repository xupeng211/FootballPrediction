/**
 * ReconStitcher - 缝合将军 (God-Mode 逻辑消除版)
 * =================================================
 *
 * 职责: 调用 FixtureRepository 进行数据持久化
 * 核心升级:
 * 1. 【V9.0】逻辑消除引擎 - Set Closure 算法实现 1:1 强制缝合
 * 2. 【V9.0】搜索引导回填 - 生成定向 URL 狙击顽固比赛
 * 3. 【V9.0】全集闭环校验 - 联赛级最终对账
 *
 * @module infrastructure/recon/ReconStitcher
 * @version V9.0-GOD-MODE
 * @date 2026-03-24
 */

'use strict';

const RECON_CONFIG = require('../../../config/recon_config.json');
const BASE_URL = RECON_CONFIG.oddsportal.base_url;

const { ReconDistributedLock, LockAcquireFailure } = require('./ReconDistributedLock');
const { Normalizer } = require('../../utils/Normalizer');

/**
 * 缝合将军类
 * @class ReconStitcher
 */
class ReconStitcher {
  constructor(options = {}) {
    this.repository = options.repository;
    this.logger = options.logger || console;
    this.parser = options.parser;
    this.enableLocking = options.enableLocking !== false;

    if (!this.repository) {
      throw new Error('ReconStitcher requires a repository instance');
    }

    // 初始化分布式锁
    if (this.enableLocking) {
      if (options.lockManager) {
        this.lockManager = options.lockManager;
      } else if (options.redisClient) {
        this.lockManager = new ReconDistributedLock(options.redisClient, { logger: this.logger });
      } else {
        this.logger.warn('distributed_lock_disabled');
        this.enableLocking = false;
      }
    }

    this.processedHashes = new Set();
    this.unmatchedCache = []; // 缓存未匹配的比赛
  }

  /**
   * 统一赛季格式 (YYYY-YYYY -> YYYY/YYYY)
   * @param {string} season - 赛季字符串
   * @returns {string} 数据库存储格式
   */
  formatSeasonForDb(season) {
    if (!season || typeof season !== 'string') {
      return season;
    }
    return season.includes('-') ? season.replace('-', '/') : season;
  }

  _normalizeTeamName(teamName) {
    const rawTeamName = typeof teamName === 'string' ? teamName : String(teamName || '');
    return String(Normalizer.normalizeTeamName(rawTeamName) || rawTeamName || '')
      .toLowerCase()
      .trim();
  }

  _hasTextualTeamName(teamName) {
    return typeof teamName === 'string' && /[a-z\u00c0-\u024f]/i.test(teamName);
  }

  _resolveWebMatchTeams(match, l1Matches = []) {
    if (!match) {
      return match;
    }

    if (this._hasTextualTeamName(match.homeTeam) && this._hasTextualTeamName(match.awayTeam)) {
      return match;
    }

    const derivedTeams = this._deriveTeamsFromUrl(match.url, l1Matches);
    if (!derivedTeams) {
      return {
        ...match,
        homeTeam: String(match.homeTeam || ''),
        awayTeam: String(match.awayTeam || '')
      };
    }

    return {
      ...match,
      homeTeam: derivedTeams.homeTeam,
      awayTeam: derivedTeams.awayTeam
    };
  }

  _deriveTeamsFromUrl(url, l1Matches = []) {
    const slugMatch = String(url || '').match(/\/([^/]+)-[A-Za-z0-9]{8}\/?$/);
    if (!slugMatch) {
      return null;
    }

    const parts = slugMatch[1].split('-').filter(Boolean);
    if (parts.length < 2) {
      return null;
    }

    let bestSplit = null;

    for (let index = 1; index < parts.length; index++) {
      const left = parts.slice(0, index).join(' ');
      const right = parts.slice(index).join(' ');

      let splitScore = 0;
      let bestL1Pair = null;
      for (const l1Match of l1Matches) {
        const directScore = (
          this._calculateTeamSimilarity(left, l1Match.home_team) +
          this._calculateTeamSimilarity(right, l1Match.away_team)
        ) / 2;
        const swappedScore = (
          this._calculateTeamSimilarity(left, l1Match.away_team) +
          this._calculateTeamSimilarity(right, l1Match.home_team)
        ) / 2;

        if (directScore >= splitScore) {
          splitScore = directScore;
          bestL1Pair = {
            homeTeam: l1Match.home_team,
            awayTeam: l1Match.away_team
          };
        }

        if (swappedScore > splitScore) {
          splitScore = swappedScore;
          bestL1Pair = {
            homeTeam: l1Match.away_team,
            awayTeam: l1Match.home_team
          };
        }
      }

      if (!bestSplit || splitScore > bestSplit.score) {
        bestSplit = { left, right, score: splitScore, bestL1Pair };
      }
    }

    if (!bestSplit) {
      return null;
    }

    if (bestSplit.bestL1Pair) {
      return bestSplit.bestL1Pair;
    }

    return {
      homeTeam: Normalizer.normalizeTeamName(bestSplit.left) || bestSplit.left,
      awayTeam: Normalizer.normalizeTeamName(bestSplit.right) || bestSplit.right
    };
  }

  _calculateTeamSimilarity(left, right) {
    const normalizedLeft = this._normalizeTeamName(left);
    const normalizedRight = this._normalizeTeamName(right);

    if (normalizedLeft && normalizedRight && normalizedLeft === normalizedRight) {
      return 1.0;
    }

    return this.parser
      ? this.parser.calculateSimilarity(left, right)
      : this.simpleSimilarity(left, right);
  }

  _resolveOrientation(sourceHome, sourceAway, l1Home, l1Away) {
    const directHome = this._calculateTeamSimilarity(sourceHome, l1Home);
    const directAway = this._calculateTeamSimilarity(sourceAway, l1Away);
    const swappedHome = this._calculateTeamSimilarity(sourceHome, l1Away);
    const swappedAway = this._calculateTeamSimilarity(sourceAway, l1Home);
    const directScore = (directHome + directAway) / 2;
    const swappedScore = (swappedHome + swappedAway) / 2;

    const directNormalized = this._normalizeTeamName(sourceHome) === this._normalizeTeamName(l1Home)
      && this._normalizeTeamName(sourceAway) === this._normalizeTeamName(l1Away);
    const swappedNormalized = this._normalizeTeamName(sourceHome) === this._normalizeTeamName(l1Away)
      && this._normalizeTeamName(sourceAway) === this._normalizeTeamName(l1Home);

    const directMatch = directNormalized || (directHome > 0.75 && directAway > 0.75);
    const swappedMatch = swappedNormalized || (swappedHome > 0.75 && swappedAway > 0.75);
    const isReversed = swappedMatch && (
      !directMatch ||
      swappedScore > directScore ||
      (swappedNormalized && !directNormalized)
    );

    return {
      directMatch,
      swappedMatch,
      directScore,
      swappedScore,
      isReversed
    };
  }

  /**
   * 【V9.0】增强版批量缝合 - 包含最终对账
   * @param {Array<Object>} matches - 比赛列表
   * @param {string} season - 赛季
   * @param {Object} leagueConfig - 联赛配置
   * @returns {Promise<Object>} 统计结果
   */
  async stitch(matches, season, leagueConfig) {
    this.logger.info('stitch_start', {
      matchCount: matches.length,
      season,
      league: leagueConfig.name
    });

    let inserted = 0;
    let skipped = 0;
    let unmatched = 0;
    this.unmatchedCache = [];

    // 第一阶段：常规缝合
    for (const match of matches) {
      const result = await this.stitchSingle(match, season, leagueConfig);
      if (result.status === 'inserted') inserted++;
      else if (result.status === 'skipped') skipped++;
      else {
        unmatched++;
        this.unmatchedCache.push({ match, reason: result.details });
      }
    }

    // 【V9.0】第二阶段：逻辑消除引擎（Set Closure）
    if (this.unmatchedCache.length > 0) {
      this.logger.info('starting_set_closure_reconciliation', {
        unmatchedCount: this.unmatchedCache.length
      });

      const closureResult = await this.performSetClosure(season, leagueConfig);
      inserted += closureResult.inserted;
      unmatched -= closureResult.inserted;
    }

    // 【V9.0】第三阶段：狙击式回填
    if (this.unmatchedCache.length > 0) {
      this.logger.info('starting_sniper_fill', { remaining: this.unmatchedCache.length });

      const sniperResult = await this.sniperFill(season, leagueConfig);
      inserted += sniperResult.inserted;
      unmatched -= sniperResult.inserted;
    }

    const successRate = matches.length > 0
      ? ((inserted + skipped) / matches.length * 100).toFixed(2) + '%'
      : '0%';

    this.logger.info('stitch_complete', {
      season,
      league: leagueConfig.name,
      inserted,
      skipped,
      unmatched,
      successRate
    });

    return {
      inserted,
      skipped,
      unmatched,
      unmatchedList: this.unmatchedCache.map(u => u.match),
      successRate
    };
  }

  /**
   * 单条缝合
   */
  async stitchSingle(match, season, leagueConfig) {
    // 幂等性检查
    if (match.hash && this.processedHashes.has(match.hash)) {
      return { status: 'skipped', details: { reason: 'idempotent_cache' } };
    }

    // 检查是否已存在
    const existing = await this.checkExistingMapping(match.hash, season);
    if (existing) {
      return { status: 'skipped', details: { reason: 'already_exists' } };
    }

    // 解析队名
    let teams = null;

    // 1. 从 URL 解析
    if (this.parser) {
      teams = this.parser.extractTeamsFromSlug(match.slug);
    }

    // 2. 从 rawText 解析
    if ((!teams || teams.awayTeam === 'Unknown') && match.rawText) {
      const textTeams = this.extractTeamsFromText(match.rawText);
      if (textTeams) teams = textTeams;
    }

    // 3. 时空对账
    if (teams && teams.homeTeam !== 'Unknown' && teams.awayTeam === 'Unknown') {
      const dateMatch = await this.findMatchByHomeAndDate(
        teams.homeTeam, match.date, season, leagueConfig.name
      );
      if (dateMatch) {
        teams.awayTeam = dateMatch.awayTeam;
      }
    }

    if (!teams || teams.homeTeam === 'Unknown' || teams.awayTeam === 'Unknown') {
      return { status: 'unmatched', details: { reason: 'parse_failed', teams } };
    }

    // 查找数据库匹配
    const matchInfo = await this.findMatchInDb(teams.homeTeam, teams.awayTeam, season);

    if (!matchInfo) {
      return { status: 'unmatched', details: { reason: 'db_not_found', teams } };
    }

    // 保存映射
    let result;
    try {
      result = await this.saveMapping(match, teams, matchInfo, season, leagueConfig);
    } catch (error) {
      if (error.code === 'ORIENTATION_UNCERTAIN') {
        this.logger.warn('orientation_uncertain', {
          hash: match.hash,
          season,
          league: leagueConfig.name,
          teams
        });
        return { status: 'unmatched', details: { reason: 'orientation_uncertain', teams } };
      }

      throw error;
    }

    if (result.success) {
      this.processedHashes.add(match.hash);
      return { status: 'inserted', details: { matchId: result.matchId } };
    }

    return { status: 'skipped', details: { reason: 'save_failed' } };
  }

  /**
   * 【V9.0】Set Closure 逻辑消除
   * 当 A 集合(L1未缝合) 与 B 集合(页面未匹配) 数量一致时，使用排除法 1:1 缝合
   */
  async performSetClosure(season, leagueConfig) {
    let inserted = 0;

    try {
      // 1. 获取 L1 总表中该联赛的所有未缝合比赛 (集合 A)
      const dbUnstitched = await this.getDbUnstitchedMatches(season, leagueConfig.name);

      // 2. 获取当前未匹配的页面数据 (集合 B)
      const pageUnmatched = this.unmatchedCache;

      this.logger.info('set_closure_analysis', {
        dbUnstitched: dbUnstitched.length,
        pageUnmatched: pageUnmatched.length
      });

      // 3. 如果数量接近，尝试逻辑匹配
      if (Math.abs(dbUnstitched.length - pageUnmatched.length) <= 5) {
        for (const pageItem of pageUnmatched) {
          const match = pageItem.match;
          let homeTeam = null;

          // 从各种来源提取主队名
          if (this.parser) {
            const parsed = this.parser.extractTeamsFromSlug(match.slug);
            if (parsed && parsed.homeTeam !== 'Unknown') {
              homeTeam = parsed.homeTeam;
            }
          }

          if (!homeTeam && match.rawText) {
            homeTeam = this.extractHomeTeamFromText(match.rawText);
          }

          if (!homeTeam) continue;

          // 在 DB 未缝合列表中查找主队模糊匹配
          const candidates = dbUnstitched.filter(dbMatch => {
            const similarity = this.parser
              ? this.parser.calculateSimilarity(dbMatch.home_team, homeTeam)
              : this.simpleSimilarity(dbMatch.home_team, homeTeam);
            return similarity > 0.75; // 【V9.0】75% 阈值
          });

          // 如果只有一个候选，强制缝合
          if (candidates.length === 1) {
            const dbMatch = candidates[0];
            const teams = {
              homeTeam: dbMatch.home_team,
              awayTeam: dbMatch.away_team
            };

            const matchInfo = {
              matchId: dbMatch.match_id,
              confidence: 0.75,
              method: 'set_closure'
            };

            const result = await this.saveMapping(match, teams, matchInfo, season, leagueConfig);

            if (result.success) {
              inserted++;
              this.processedHashes.add(match.hash);

              // 从未匹配缓存中移除
              const idx = this.unmatchedCache.indexOf(pageItem);
              if (idx > -1) this.unmatchedCache.splice(idx, 1);

              // 从 DB 未缝合列表中移除
              const dbIdx = dbUnstitched.indexOf(dbMatch);
              if (dbIdx > -1) dbUnstitched.splice(dbIdx, 1);

              this.logger.info('set_closure_stitch', {
                hash: match.hash,
                home: teams.homeTeam,
                away: teams.awayTeam
              });
            }
          }
        }
      }
    } catch (e) {
      this.logger.error('set_closure_error', { error: e.message });
    }

    return { inserted };
  }

  /**
   * 【V9.0】狙击式回填 - 针对顽固比赛生成定向 URL
   */
  async sniperFill(season, leagueConfig) {
    let inserted = 0;

    for (const item of [...this.unmatchedCache]) {
      const match = item.match;

      // 尝试从 slug 提取信息生成搜索 URL
      if (match.slug) {
        const searchUrl = `${BASE_URL}/search/${encodeURIComponent(match.slug)}/`;
        this.logger.info('sniper_attempt', { hash: match.hash, url: searchUrl });

        // 这里可以扩展为实际访问搜索页面并提取结果
        // 目前先记录日志，作为后续扩展点
      }
    }

    return { inserted };
  }

  /**
   * 获取数据库中未缝合的比赛
   */
  async getDbUnstitchedMatches(season, leagueName) {
    try {
      const client = await this.repository.dbPool.connect();
      try {
        const query = `
          SELECT m.match_id, m.home_team, m.away_team, m.match_date
          FROM matches m
          LEFT JOIN matches_oddsportal_mapping map
            ON m.match_id = map.match_id AND map.season = $2
          WHERE m.league_name = $1
            AND m.season = $2
            AND map.match_id IS NULL
          ORDER BY m.match_date;
        `;

        const result = await client.query(query, [leagueName, season]);
        return result.rows;
      } finally {
        client.release();
      }
    } catch (e) {
      this.logger.error('getDbUnstitchedMatches_error', { error: e.message });
      return [];
    }
  }

  /**
   * 保存映射
   */
  async saveMapping(match, teams, matchInfo, season, leagueConfig) {
    const l1HomeTeam = matchInfo.dbHome || teams.homeTeam;
    const l1AwayTeam = matchInfo.dbAway || teams.awayTeam;
    const orientation = this._resolveOrientation(
      teams.homeTeam,
      teams.awayTeam,
      l1HomeTeam,
      l1AwayTeam
    );

    if (!orientation.directMatch && !orientation.swappedMatch) {
      const error = new Error('ORIENTATION_UNCERTAIN');
      error.code = 'ORIENTATION_UNCERTAIN';
      throw error;
    }

    const mappingData = {
      match_id: matchInfo.matchId,
      oddsportal_hash: match.hash,
      full_url: match.url,
      season: season.replace('-', '/'),
      league_name: leagueConfig.name,
      home_team: l1HomeTeam,
      away_team: l1AwayTeam,
      is_reversed: orientation.isReversed,
      match_confidence: matchInfo.confidence || 0.75,
      mapping_method: matchInfo.method || 'exact',
      status: 'pending'
    };

    return this.repository.saveOddsPortalMapping(mappingData, {
      pipelineStatus: 'RECON_LINKED'
    });
  }

  /**
   * 在数据库中查找匹配
   */
  async findMatchInDb(homeTeam, awayTeam, season) {
    const matchInfo = await this.repository.findMatchByTeams(homeTeam, awayTeam, season);
    if (matchInfo) return matchInfo;

    if (this.parser) {
      return this.findWithFuzzyMatch(homeTeam, awayTeam, season);
    }

    return null;
  }

  /**
   * 模糊匹配
   */
  async findWithFuzzyMatch(homeTeam, awayTeam, season) {
    const candidates = await this.repository.findMatchesBySeason(season);
    if (!candidates || candidates.length === 0) return null;

    const homeCandidates = candidates.map(m => m.home_team);
    const homeMatch = this.parser.findBestMatch(homeTeam, homeCandidates, 0.75);

    if (!homeMatch) return null;

    const awayCandidates = candidates.map(m => m.away_team);
    const awayMatch = this.parser.findBestMatch(awayTeam, awayCandidates, 0.75);

    if (!awayMatch) return null;

    const matchedGame = candidates.find(m =>
      m.home_team === homeMatch.team && m.away_team === awayMatch.team
    );

    if (matchedGame) {
      return {
        matchId: matchedGame.match_id,
        confidence: (homeMatch.confidence + awayMatch.confidence) / 2,
        method: 'fuzzy'
      };
    }

    return null;
  }

  /**
   * 时空对账
   */
  async findMatchByHomeAndDate(homeTeam, dateStr, season, leagueName) {
    if (!this.repository.findMatchesBySeason) return null;

    try {
      const candidates = await this.repository.findMatchesBySeason(season);
      if (!candidates) return null;

      const homeMatches = candidates.filter(m => {
        const similarity = this.parser
          ? this.parser.calculateSimilarity(m.home_team, homeTeam)
          : this.simpleSimilarity(m.home_team, homeTeam);
        return similarity > 0.75;
      });

      if (homeMatches.length === 1) {
        return {
          matchId: homeMatches[0].match_id,
          awayTeam: homeMatches[0].away_team,
          confidence: 0.85
        };
      }

      return null;
    } catch (e) {
      this.logger.error('findMatchByHomeAndDate_error', { error: e.message });
      return null;
    }
  }

  /**
   * 从文本提取队名
   */
  extractTeamsFromText(text) {
    if (!text || !this.parser) return null;

    const cleanText = text.toLowerCase()
      .replace(/\d{1,2}:\d{2}/g, '')
      .replace(/\d+\.\d+/g, '')
      .replace(/[^\w\s-]/g, ' ')
      .trim();

    const knownTeams = Array.isArray(this.parser.knownTeams) ? this.parser.knownTeams : [];
    const foundTeams = [];

    for (const team of knownTeams) {
      const teamLower = team.toLowerCase();
      if (cleanText.includes(teamLower)) {
        foundTeams.push(team);
      } else if (this.parser.fuzzball) {
        const score = this.parser.fuzzball.partial_ratio(teamLower, cleanText);
        if (score > 75) foundTeams.push(team);
      }
      if (foundTeams.length >= 2) break;
    }

    if (foundTeams.length >= 2) {
      return { homeTeam: foundTeams[0], awayTeam: foundTeams[1] };
    }

    return null;
  }

  /**
   * 提取主队名
   */
  extractHomeTeamFromText(text) {
    if (!text) return null;
    const parts = text.split(/\s+vs\s+|\s+-\s+|\n/);
    return parts[0]?.trim() || null;
  }

  /**
   * 简单相似度计算
   */
  simpleSimilarity(s1, s2) {
    const a = s1.toLowerCase().trim();
    const b = s2.toLowerCase().trim();

    if (a === b) return 1.0;
    if (a.includes(b) || b.includes(a)) {
      return Math.min(a.length, b.length) / Math.max(a.length, b.length);
    }

    const words1 = new Set(a.split(' '));
    const words2 = new Set(b.split(' '));
    const intersection = new Set([...words1].filter(x => words2.has(x)));
    const union = new Set([...words1, ...words2]);

    return intersection.size / union.size;
  }

  /**
   * 检查已存在映射
   */
  async checkExistingMapping(hash, season) {
    try {
      if (this.repository.findMappingByHash) {
        return await this.repository.findMappingByHash(hash, season.replace('-', '/'));
      }
      return null;
    } catch (e) {
      return null;
    }
  }

  /**
   * 【V10.0】Hash 强效锁定缝合
   * @param {Array<Object>} interceptedMatches - 拦截到的比赛
   * @param {Array<Object>} l1Matches - L1 比赛列表
   * @param {string} season - 赛季
   * @param {Object} leagueConfig - 联赛配置
   * @returns {Promise<Object>} 缝合结果
   */
  async stitchWithHashLock(interceptedMatches, l1Matches, season, leagueConfig) {
    this.logger.info('hash_lock_start', {
      intercepted: interceptedMatches.length,
      l1Total: l1Matches.length
    });

    let inserted = 0;
    let skipped = 0;
    let unmatched = 0;
    const dbSeason = this.formatSeasonForDb(season);

    // 建立 L1 映射
    const l1Map = new Map();
    for (const match of l1Matches) {
      const key = `${this._normalizeTeamName(match.home_team)}_${this._normalizeTeamName(match.away_team)}`;
      l1Map.set(key, match);
    }

    for (const rawMatch of interceptedMatches) {
      try {
        const match = this._resolveWebMatchTeams(rawMatch, l1Matches);
        if (match.hash && this.processedHashes.has(match.hash)) {
          skipped++;
          continue;
        }

        const existing = await this.checkExistingMapping(match.hash, season);
        if (existing) {
          this.processedHashes.add(match.hash);
          skipped++;
          continue;
        }

        // Hash 锁定匹配
        let targetL1 = null;
        let orientation = null;
        const exactKey = `${this._normalizeTeamName(match.homeTeam)}_${this._normalizeTeamName(match.awayTeam)}`;
        targetL1 = l1Map.get(exactKey);
        if (targetL1) {
          orientation = this._resolveOrientation(match.homeTeam, match.awayTeam, targetL1.home_team, targetL1.away_team);
        }

        if (!targetL1) {
          const reversedKey = `${this._normalizeTeamName(match.awayTeam)}_${this._normalizeTeamName(match.homeTeam)}`;
          targetL1 = l1Map.get(reversedKey);
          if (targetL1) {
            orientation = this._resolveOrientation(match.homeTeam, match.awayTeam, targetL1.home_team, targetL1.away_team);
          }
        }

        // 模糊匹配兜底
        if (!targetL1) {
          for (const [, l1] of l1Map.entries()) {
            const candidateOrientation = this._resolveOrientation(match.homeTeam, match.awayTeam, l1.home_team, l1.away_team);
            if (candidateOrientation.directMatch || candidateOrientation.swappedMatch) {
              targetL1 = l1;
              orientation = candidateOrientation;
              break;
            }
          }
        }

        if (!targetL1 || !orientation || (!orientation.directMatch && !orientation.swappedMatch)) {
          unmatched++;
          continue;
        }

        const result = await this.repository.saveOddsPortalMapping({
          match_id: targetL1.match_id,
          oddsportal_hash: match.hash,
          full_url: match.url,
          season: dbSeason,
          league_name: leagueConfig.name,
          home_team: targetL1.home_team,
          away_team: targetL1.away_team,
          is_reversed: orientation.isReversed,
          match_confidence: 0.9,
          mapping_method: 'hash_lock',
          status: 'pending'
        }, {
          pipelineStatus: 'RECON_LINKED'
        });

        if (result.success) {
          this.processedHashes.add(match.hash);
          inserted++;
        } else {
          skipped++;
        }
      } catch (e) {
        this.logger.error('hash_lock_error', { hash: rawMatch?.hash, error: e.message });
        unmatched++;
      }
    }

    return { inserted, skipped, unmatched };
  }

  /**
   * 【Total War】数独排除法引擎 - Set Reconciliation
   * 当 L1 剩余 N 场，网页剩余 N 条时，强制 1:1 缝合
   * @param {Array<Object>} webMatches - 网页抓取的比赛
   * @param {Array<Object>} l1Matches - L1 未缝合比赛
   * @param {string} season - 赛季
   * @param {Object} leagueConfig - 联赛配置
   * @returns {Promise<Object>} 缝合结果
   */
  async setReconciliation(webMatches, l1Matches, season, leagueConfig) {
    this.logger.info('set_reconciliation_start', {
      webCount: webMatches.length,
      l1Count: l1Matches.length
    });

    let inserted = 0;
    let unmatched = 0;

    // 过滤掉已处理的
    const pendingWeb = webMatches.filter(m => !this.processedHashes.has(m.hash));
    const pendingL1 = l1Matches.filter(m => !this.processedHashes.has(m.match_id));

    // 如果数量匹配，启动强制缝合
    if (Math.abs(pendingWeb.length - pendingL1.length) <= 2) {
      this.logger.info('set_match_confirmed', {
        web: pendingWeb.length,
        l1: pendingL1.length
      });

      for (const rawWebMatch of pendingWeb) {
        const webMatch = this._resolveWebMatchTeams(rawWebMatch, pendingL1);
        // 找到最佳 L1 匹配
        let bestMatch = null;
        let bestScore = 0;

        for (const l1 of pendingL1) {
          // 使用词根匹配
          const homeRoot = this.getWordRoot(webMatch.homeTeam);
          const l1HomeRoot = this.getWordRoot(l1.home_team);
          const homeSim = this.calculateRootSimilarity(homeRoot, l1HomeRoot);

          if (homeSim > bestScore && homeSim > 0.6) {
            bestScore = homeSim;
            bestMatch = l1;
          }
        }

        if (bestMatch) {
          try {
            const orientation = this._resolveOrientation(
              webMatch.homeTeam,
              webMatch.awayTeam,
              bestMatch.home_team,
              bestMatch.away_team
            );

            if (!orientation.directMatch && !orientation.swappedMatch) {
              unmatched++;
              continue;
            }

            const result = await this.repository.saveOddsPortalMapping({
              match_id: bestMatch.match_id,
              oddsportal_hash: webMatch.hash,
              full_url: webMatch.url,
              season: season.replace('-', '/'),
              league_name: leagueConfig.name,
              home_team: bestMatch.home_team,
              away_team: bestMatch.away_team,
              is_reversed: orientation.isReversed,
              match_confidence: bestScore,
              mapping_method: 'set_reconciliation',
              status: 'pending'
            }, {
              pipelineStatus: 'RECON_LINKED'
            });

            if (result.success) {
              this.processedHashes.add(webMatch.hash);
              inserted++;

              // 从 pendingL1 中移除已匹配的
              const idx = pendingL1.indexOf(bestMatch);
              if (idx > -1) pendingL1.splice(idx, 1);

              this.logger.info('reconciliation_stitch', {
                hash: webMatch.hash,
                home: bestMatch.home_team,
                score: bestScore
              });
            }
          } catch (e) {
            this.logger.error('reconciliation_error', { hash: webMatch.hash, error: e.message });
            unmatched++;
          }
        } else {
          unmatched++;
        }
      }
    } else {
      this.logger.warn('set_mismatch', {
        web: pendingWeb.length,
        l1: pendingL1.length,
        diff: Math.abs(pendingWeb.length - pendingL1.length)
      });
      unmatched = pendingWeb.length;
    }

    return { inserted, unmatched };
  }

  /**
   * 【Total War】获取词根
   * @param {string} teamName - 队名
   * @returns {string} 词根
   */
  getWordRoot(teamName) {
    if (!teamName) return '';

    // 标准化并分词
    const normalized = String(teamName)
      .toLowerCase()
      .replace(/[^a-z\s]/g, '')
      .trim();

    // 取前 3 个字符作为词根
    return normalized.split(' ').map(w => w.substring(0, 4)).join(' ');
  }

  /**
   * 【Total War】计算词根相似度
   * @param {string} root1 - 词根1
   * @param {string} root2 - 词根2
   * @returns {number} 相似度
   */
  calculateRootSimilarity(root1, root2) {
    const r1 = root1.split(' ');
    const r2 = root2.split(' ');

    let matches = 0;
    for (const word1 of r1) {
      for (const word2 of r2) {
        if (word1 === word2 || word1.includes(word2) || word2.includes(word1)) {
          matches++;
        }
      }
    }

    return matches / Math.max(r1.length, r2.length);
  }
}

module.exports = { ReconStitcher };
