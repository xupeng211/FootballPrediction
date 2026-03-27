/**
 * ReconEngine - 侦察引擎 (V11.0 Clean Sweep)
 * ==========================================
 *
 * 职责: 封装所有侦察扫描算法
 * 包含: archiveSniper, dateSniper, protocolExtract
 * 从 recon_scanner.js 解耦，独立可测试
 *
 * @module infrastructure/recon/ReconEngine
 * @version V11.0-CLEAN-SWEEP
 * @date 2026-03-25
 */

'use strict';

const pLimit = require('p-limit');
const { L1ConfigManager } = require('../services/L1ConfigManager');

/**
 * 侦察引擎类
 * @class ReconEngine
 */
class ReconEngine {
  constructor(options = {}) {
    this.navigator = options.navigator;
    this.stitcher = options.stitcher;
    this.repository = options.repository;
    this.parser = options.parser;
    this.logger = options.logger || console;
    this.proxyRotator = options.proxyRotator;
    this.traceId = options.traceId || null;
    this.configManager = options.configManager || new L1ConfigManager({ logger: this.logger });
    this.baseUrl = options.baseUrl || options.config?.oddsportal?.base_url || 'https://www.oddsportal.com';
    this.reconBatchSize = Math.max(1, Number(options.reconBatchSize || 25));
    this.defaultReconConcurrency = Math.max(1, Number(options.defaultReconConcurrency || 5));
    this.confidenceThreshold = Number(options.confidenceThreshold || 0.75);
  }

  /**
   * 构建配置驱动的扫描目标列表
   * @param {Object} options
   * @returns {Promise<Array<Object>>}
   */
  async buildScanTargets(options = {}) {
    const { season, tier = null, leagueIds = null } = options;

    if (!season || typeof season !== 'string') {
      throw new Error('season is required for buildScanTargets');
    }

    const allowedLeagueIds = Array.isArray(leagueIds) && leagueIds.length > 0
      ? new Set(leagueIds.map((id) => Number(id)))
      : null;

    const leagues = this.configManager
      .getActiveLeagues({ tier })
      .filter((league) => league.enabled !== false)
      .filter((league) => !allowedLeagueIds || allowedLeagueIds.has(Number(league.id)));

    return leagues.map((league) => ({
      leagueId: Number(league.id),
      league,
      season,
      dbSeason: this._normalizeDbSeason(season),
      resultsUrl: this._buildResultsUrl(league, season)
    }));
  }

  /**
   * Recon Matrix 批量模式
   * @param {Object} options
   * @returns {Promise<Object>}
   */
  async runReconMatrix(options = {}) {
    const {
      season,
      concurrency = this.defaultReconConcurrency,
      tier = null,
      leagueIds = null,
      batchSize = this.reconBatchSize,
      confidenceThreshold = this.confidenceThreshold,
      limit = null
    } = options;

    const targets = await this.buildScanTargets({ season, tier, leagueIds });
    const summary = {
      success: true,
      season,
      scannedLeagues: 0,
      totalPending: 0,
      linked: 0,
      mismatched: 0,
      errors: [],
      perLeague: []
    };

    const targetPendingMap = await this._prepareReconPendingTargets(targets, limit);

    for (const { target, pendingMatches, desiredLimit = null } of targetPendingMap) {
      try {
        const result = await this._runReconTarget(target, {
          concurrency,
          batchSize,
          confidenceThreshold,
          pendingMatches,
          matchLimit: desiredLimit
        });

        summary.scannedLeagues++;
        summary.totalPending += result.pendingTotal;
        summary.linked += result.linked;
        summary.mismatched += result.mismatched;
        summary.perLeague.push({
          league: target.league.name,
          season: target.dbSeason,
          pendingTotal: result.pendingTotal,
          linked: result.linked,
          mismatched: result.mismatched,
          sourceSeason: result.sourceSeason,
          sourceUrl: result.sourceUrl,
          candidateCount: result.candidateCount
        });
      } catch (error) {
        summary.success = false;
        summary.errors.push({
          league: target.league.name,
          error: error.message
        });
        this.logger.error('recon_matrix_target_failed', {
          league: target.league.name,
          season,
          error: error.message
        });
      }
    }

    return summary;
  }

  async _prepareReconPendingTargets(targets, limit = null) {
    const prepared = [];

    for (const target of targets) {
      const pendingMatches = await this._loadReconPendingMatches(target);
      if (Array.isArray(pendingMatches) && pendingMatches.length > 0) {
        prepared.push({
          target,
          pendingMatches: [...pendingMatches].sort((a, b) =>
            String(a.match_id).localeCompare(String(b.match_id))
          ),
          desiredLimit: null
        });
      }
    }

    if (!Number.isInteger(limit) || limit <= 0) {
      return prepared;
    }

    const capped = prepared.map(({ target, pendingMatches }) => ({
      target,
      pendingMatches,
      desiredLimit: 0
    }));

    let selected = 0;
    let cursor = 0;
    const capacities = prepared.map(({ pendingMatches }) => pendingMatches.length);

    while (selected < limit) {
      let pickedInRound = false;

      for (let i = 0; i < prepared.length && selected < limit; i++) {
        const index = (cursor + i) % prepared.length;
        if (capped[index].desiredLimit >= capacities[index]) {
          continue;
        }

        capped[index].desiredLimit += 1;
        selected++;
        pickedInRound = true;
      }

      if (!pickedInRound) {
        break;
      }

      cursor = (cursor + 1) % Math.max(prepared.length, 1);
    }

    return capped.filter(({ desiredLimit }) => desiredLimit > 0);
  }

  /**
   * 协议档案扫描 (V11.0 主要扫描方式)
   * @param {string} season - 赛季 (动态透传)
   * @param {Object} leagueConfig - 联赛配置
   * @returns {Promise<Object>}
   */
  async protocolArchiveScan(season, leagueConfig) {
    const startTime = Date.now();
    
    // V11.0 FIX: 转换 season 格式为数据库存储格式 (2024-2025 -> 2024/2025)
    const dbSeason = season.replace('-', '/');
    
    this.logger.info('protocol_archive_scan_start', { season, dbSeason, league: leagueConfig.name });

    try {
      // 1. 获取未缝合比赛
      const unstitched = await this._loadReconPendingMatches({
        dbSeason,
        league: leagueConfig
      });
      if (unstitched.length === 0) {
        return { success: true, season, league: leagueConfig.name, inserted: 0, reason: 'no_pending_matches' };
      }

      // 2. 执行协议级抓取
      const oddsportalSeason = this._formatSeasonForUrl(season);
      const resultsUrl = this._buildResultsUrl(leagueConfig, season);
      
      const extractResult = await this.navigator.protocolArchiveExtract(resultsUrl, {
        maxPages: 50, timeoutMs: 90000
      });

      this.logger.info('protocol_extract_complete', {
        candidates: extractResult.matches.length,
        pagesScanned: extractResult.pagesScanned
      });

      // 3. 严格匹配并缝合
      const { inserted, unmatched } = await this._matchAndStitch(
        extractResult.matches, unstitched, dbSeason, leagueConfig
      );

      // 4. 数独排除法兜底
      let reconciled = 0;
      if (unmatched > 0 && this.stitcher?.setReconciliation) {
        const recResult = await this.stitcher.setReconciliation(
          extractResult.matches, unstitched, dbSeason, leagueConfig
        );
        reconciled = recResult.inserted || 0;
      }

      const totalInserted = inserted + reconciled;
      const coverage = unstitched.length > 0 ? (totalInserted / unstitched.length * 100).toFixed(2) : '0.00';

      return {
        success: true,
        season,
        league: leagueConfig.name,
        pendingTotal: unstitched.length,
        candidatesFound: extractResult.matches.length,
        inserted: totalInserted,
        unmatched: unmatched - reconciled,
        coverage: parseFloat(coverage),
        durationMs: Date.now() - startTime
      };

    } catch (error) {
      this.logger.error('protocol_archive_scan_failed', { error: error.message });
      return { success: false, season, league: leagueConfig.name, error: error.message };
    }
  }

  /**
   * 日期驱动扫描
   * @param {string} season
   * @param {Object} leagueConfig
   * @returns {Promise<Object>}
   */
  async dateDrivenScan(season, leagueConfig) {
    const startTime = Date.now();
    
    // V11.0 FIX: 转换 season 格式为数据库存储格式
    const dbSeason = season.replace('-', '/');
    
    this.logger.info('date_driven_scan_start', { season, dbSeason, league: leagueConfig.name });

    try {
      // 1. 获取未缝合比赛
      const unstitched = await this._loadReconPendingMatches({
        dbSeason,
        league: leagueConfig
      });
      if (unstitched.length === 0) {
        return { success: true, inserted: 0, reason: 'no_pending_matches' };
      }

      // 2. 按日期分组
      const dateBuckets = this._bucketByDate(unstitched);
      const dateKeys = Array.from(dateBuckets.keys()).sort();

      this.logger.info('date_buckets_ready', { 
        totalMatches: unstitched.length, 
        dateCount: dateKeys.length 
      });

      // 3. 逐日期扫描
      let totalInserted = 0;
      let totalFound = 0;

      for (const dateKey of dateKeys) {
        const dayMatches = dateBuckets.get(dateKey);
        const dayResult = await this.navigator.protocolArchiveExtract(
          `${this.baseUrl}/matches/football/${dateKey}/`,
          { maxPages: 20, timeoutMs: 60000 }
        );

        const { inserted } = await this._matchAndStitch(
          dayResult.matches, dayMatches, dbSeason, leagueConfig
        );

        totalInserted += inserted;
        totalFound += dayResult.matches.length;

        this.logger.info('date_scan_progress', { 
          date: dateKey, 
          dayInserted: inserted,
          totalProgress: `${totalInserted}/${unstitched.length}`
        });
      }

      const coverage = unstitched.length > 0 ? (totalInserted / unstitched.length * 100).toFixed(2) : '0.00';

      return {
        success: true,
        season,
        league: leagueConfig.name,
        pendingTotal: unstitched.length,
        datesScanned: dateKeys.length,
        inserted: totalInserted,
        coverage: parseFloat(coverage),
        durationMs: Date.now() - startTime
      };

    } catch (error) {
      this.logger.error('date_driven_scan_failed', { error: error.message });
      return { success: false, error: error.message };
    }
  }

  /**
   * 跨联赛扫描 (处理德乙、德国杯等)
   * @param {string} season
   * @param {Object} leagueConfig
   * @param {Array} additionalSlugs
   * @returns {Promise<Object>}
   */
  async crossLeagueScan(season, leagueConfig, additionalSlugs = []) {
    const startTime = Date.now();
    this.logger.info('cross_league_scan_start', { 
      season, 
      league: leagueConfig.name,
      additionalSlugs 
    });

    const allResults = [];
    const oddsportalSeason = this._formatSeasonForUrl(season);

    // 1. 主联赛扫描
    const mainResult = await this.protocolArchiveScan(season, leagueConfig);
    allResults.push({ slug: leagueConfig.slug, ...mainResult });

    // 2. 附加联赛扫描
    for (const slug of additionalSlugs) {
      const slugConfig = { ...leagueConfig, slug };
      const slugResult = await this.protocolArchiveScan(season, slugConfig);
      allResults.push({ slug, ...slugResult });
    }

    // 3. 汇总结果
    const totalInserted = allResults.reduce((sum, r) => sum + (r.inserted || 0), 0);
    
    return {
      success: true,
      season,
      primaryLeague: leagueConfig.name,
      scannedLeagues: allResults.length,
      totalInserted,
      details: allResults,
      durationMs: Date.now() - startTime
    };
  }

  /**
   * 智能扫描 (自动选择最佳策略)
   * @param {string} season
   * @param {Object} leagueConfig
   * @returns {Promise<Object>}
   */
  async smartScan(season, leagueConfig) {
    const dbSeason = season.replace('-', '/');
    this.logger.info('smart_scan_start', { season, league: leagueConfig.name });

    // 策略1: 协议档案扫描 (最快最完整)
    const protocolResult = await this.protocolArchiveScan(season, leagueConfig);
    
    if (protocolResult.coverage >= 95) {
      this.logger.info('smart_scan_complete', { strategy: 'protocol', coverage: protocolResult.coverage });
      return { ...protocolResult, strategy: 'protocol' };
    }

    // 策略2: 如果覆盖率不足，追加日期驱动扫描
    this.logger.info('protocol_insufficient', { coverage: protocolResult.coverage, fallback: 'date_driven' });
    
    const dateResult = await this.dateDrivenScan(season, leagueConfig);
    let combinedInserted = protocolResult.inserted + dateResult.inserted;
    let coverage = dateResult.coverage;

    // 策略3: 如果仍然不足，启用 DOM 降级收割
    if (coverage < 80) {
      this.logger.info('date_driven_insufficient', { coverage, fallback: 'dom_fallback' });
      const domResult = await this.domFallbackScan(season, leagueConfig);
      combinedInserted += domResult.inserted;
      
      const unstitched = await this._loadReconPendingMatches({
        dbSeason,
        league: leagueConfig
      });
      coverage = unstitched.length > 0 ? (combinedInserted / unstitched.length * 100).toFixed(2) : 0;
    }
    
    return {
      success: true,
      season,
      league: leagueConfig.name,
      strategy: 'hybrid',
      protocolInserted: protocolResult.inserted,
      dateInserted: dateResult.inserted,
      totalInserted: combinedInserted,
      coverage
    };
  }

  /**
   * 【V11.0 DOM 降级收割】直接提取页面渲染后的 DOM 数据
   * @param {string} season
   * @param {Object} leagueConfig
   * @returns {Promise<Object>}
   */
  async domFallbackScan(season, leagueConfig) {
    const startTime = Date.now();
    this.logger.info('dom_fallback_scan_start', { season, league: leagueConfig.name });

    try {
      const dbSeason = season.replace('-', '/');
      const unstitched = await this._loadReconPendingMatches({
        dbSeason,
        league: leagueConfig
      });
      
      if (unstitched.length === 0) {
        return { success: true, inserted: 0, reason: 'no_pending_matches' };
      }

      // 构建 results 页面 URL
      const oddsportalSeason = this._formatSeasonForUrl(season);
      const baseUrl = this._buildResultsUrl(leagueConfig, season);
      
      // 导航到页面
      await this.navigator.navigate(baseUrl, { waitUntil: 'networkidle' });
      await this.navigator.page.waitForTimeout(3000);

      // 滚动加载更多数据
      for (let i = 0; i < 5; i++) {
        await this.navigator.page.evaluate(() => window.scrollBy(0, 1000));
        await this.navigator.page.waitForTimeout(1500);
      }

      // 直接从 DOM 提取比赛数据
      const domMatches = await this.navigator.page.evaluate(() => {
        const matches = [];
        const hashPattern = /-([a-zA-Z0-9]{8})\/$/;
        
        // 查找所有包含比赛链接的元素
        document.querySelectorAll('a[href*="/football/"]').forEach(link => {
          const href = link.getAttribute('href') || '';
          const match = href.match(hashPattern);
          
          if (match && href.includes('germany') && href.includes('bundesliga')) {
            const hash = match[1];
            
            // 尝试从父元素获取队名
            let parent = link.closest('div[class*="event"], tr, .eventRow');
            let text = '';
            
            if (parent) {
              text = parent.innerText || parent.textContent || '';
            } else {
              text = link.innerText || link.textContent || '';
            }
            
            // 清理文本
            text = text.replace(/\s+/g, ' ').trim();
            
            matches.push({
              url: href.startsWith('http') ? href : `${this.baseUrl}${href}`,
              hash: hash,
              rawText: text,
              source: 'dom_fallback'
            });
          }
        });
        
        // 去重
        const seen = new Set();
        return matches.filter(m => {
          if (seen.has(m.hash)) return false;
          seen.add(m.hash);
          return true;
        });
      });

      this.logger.info('dom_extract_complete', { candidates: domMatches.length });

      // 尝试从 DOM 数据中提取队名并匹配
      let inserted = 0;
      for (const l1 of unstitched) {
        // 查找匹配的 DOM 数据
        const matched = domMatches.find(dom => {
          // 使用队名相似度匹配
          const text = dom.rawText.toLowerCase();
          const home = l1.home_team.toLowerCase();
          const away = l1.away_team.toLowerCase();
          
          return text.includes(home) && text.includes(away);
        });

        if (matched && this.stitcher) {
          try {
            const result = await this.stitcher.stitchWithHashLock(
              [{
                ...matched,
                homeTeam: l1.home_team,
                awayTeam: l1.away_team
              }], 
              [l1], 
              dbSeason, 
              leagueConfig
            );
            inserted += result.inserted || 0;
          } catch (e) {
            this.logger.warn('dom_stitch_failed', { matchId: l1.match_id, error: e.message });
          }
        }
      }

      this.logger.info('dom_fallback_scan_complete', { inserted, candidates: domMatches.length });
      
      return {
        success: true,
        season,
        league: leagueConfig.name,
        candidatesFound: domMatches.length,
        inserted,
        durationMs: Date.now() - startTime
      };

    } catch (error) {
      this.logger.error('dom_fallback_scan_failed', { error: error.message });
      return { success: false, error: error.message };
    }
  }

  /**
   * 匹配并缝合
   * @private
   */
  async _matchAndStitch(candidates, l1Matches, season, leagueConfig) {
    let inserted = 0;
    let unmatched = 0;
    const usedCandidates = new Set();

    for (const l1 of l1Matches) {
      let matched = null;

      for (const candidate of candidates) {
        const key = candidate.hash || candidate.url;
        if (!key || usedCandidates.has(key)) continue;

        if (this._isStrictMatch(candidate, l1)) {
          matched = candidate;
          usedCandidates.add(key);
          break;
        }
      }

      if (matched && this.stitcher) {
        try {
          const result = await this.stitcher.stitchWithHashLock(
            [matched], [l1], season, leagueConfig
          );
          inserted += result.inserted || 0;
        } catch (error) {
          this.logger.error('stitch_failed', { matchId: l1.match_id, error: error.message });
          unmatched++;
        }
      } else {
        unmatched++;
      }
    }

    return { inserted, unmatched };
  }

  /**
   * 严格匹配检查
   * @private
   */
  _isStrictMatch(candidate, l1Match) {
    if (!candidate.homeTeam || !candidate.awayTeam) return false;

    const homeSim = this._calculateSimilarity(candidate.homeTeam, l1Match.home_team);
    const awaySim = this._calculateSimilarity(candidate.awayTeam, l1Match.away_team);

    // 双向检查：允许主客互换
    const direct = homeSim > 0.75 && awaySim > 0.75;
    const swapped = this._calculateSimilarity(candidate.homeTeam, l1Match.away_team) > 0.75 &&
                    this._calculateSimilarity(candidate.awayTeam, l1Match.home_team) > 0.75;

    return direct || swapped;
  }

  /**
   * 计算队名相似度
   * @private
   */
  _calculateSimilarity(a, b) {
    if (!a || !b) return 0;
    if (this.parser?.calculateSimilarity) {
      return this.parser.calculateSimilarity(a, b);
    }
    // Fallback: 简单包含检查
    const na = a.toLowerCase().trim();
    const nb = b.toLowerCase().trim();
    if (na === nb) return 1.0;
    if (na.includes(nb) || nb.includes(na)) return 0.8;
    return 0;
  }

  /**
   * 按日期分组
   * @private
   */
  _bucketByDate(matches) {
    const buckets = new Map();
    for (const match of matches) {
      const dateKey = this._toDateKey(match.match_date);
      if (!dateKey) continue;
      if (!buckets.has(dateKey)) buckets.set(dateKey, []);
      buckets.get(dateKey).push(match);
    }
    return buckets;
  }

  /**
   * 转换为日期键
   * @private
   */
  _toDateKey(dateInput) {
    if (!dateInput) return null;
    const d = new Date(dateInput);
    if (Number.isNaN(d.getTime())) return null;
    const y = d.getUTCFullYear();
    const m = String(d.getUTCMonth() + 1).padStart(2, '0');
    const day = String(d.getUTCDate()).padStart(2, '0');
    return `${y}${m}${day}`;
  }

  _calculateDateConfidence(candidateDate, matchDate) {
    const candidate = new Date(candidateDate);
    const target = new Date(matchDate);

    if (Number.isNaN(candidate.getTime()) || Number.isNaN(target.getTime())) {
      return null;
    }

    const diffDays = Math.abs(candidate.getTime() - target.getTime()) / 86400000;

    if (diffDays <= 0.5) return 1;
    if (diffDays <= 1.5) return 0.92;
    if (diffDays <= 3) return 0.8;
    if (diffDays <= 7) return 0.55;
    return 0;
  }

  /**
   * 格式化赛季为 URL 格式
   * @private
   */
  _formatSeasonForUrl(season) {
    if (!season) return '';
    // 支持 2024-2025 -> 2024-2025 或 2024/2025 -> 2024-2025
    return season.replace('/', '-');
  }

  _normalizeDbSeason(season) {
    return String(season || '').replace('-', '/');
  }

  _shiftSeason(season, delta) {
    const normalized = this._formatSeasonForUrl(season);
    const match = normalized.match(/^(\d{4})-(\d{4})$/);
    if (!match) {
      return normalized;
    }

    const start = Number(match[1]) + Number(delta || 0);
    const end = Number(match[2]) + Number(delta || 0);
    return `${start}-${end}`;
  }

  _isCurrentSeason(season) {
    const normalized = this._formatSeasonForUrl(season);
    const match = normalized.match(/^(\d{4})-(\d{4})$/);
    if (!match) {
      return false;
    }

    const now = new Date();
    const year = now.getUTCFullYear();
    const month = now.getUTCMonth() + 1;
    const seasonStartYear = month >= 7 ? year : year - 1;
    const seasonEndYear = seasonStartYear + 1;

    return Number(match[1]) === seasonStartYear && Number(match[2]) === seasonEndYear;
  }

  _buildResultsUrl(leagueConfig, season) {
    const oddsportalSeason = this._formatSeasonForUrl(season);
    const country = String(leagueConfig.country || '')
      .trim()
      .toLowerCase();
    const slug = String(leagueConfig.slug || '')
      .trim()
      .toLowerCase();

    return `${this.baseUrl}/football/${country}/${slug}-${oddsportalSeason}/results/`;
  }

  _buildCandidateSources(target) {
    const baseSeason = this._formatSeasonForUrl(target.season || target.dbSeason);
    return [{
      season: baseSeason,
      url: this._buildResultsUrl(target.league, baseSeason)
    }];
  }

  async _selectCandidateSource(target, pendingMatches, confidenceThreshold) {
    const orderedPending = [...pendingMatches]
      .sort((a, b) => String(a.match_id).localeCompare(String(b.match_id)));
    const sample = orderedPending.slice(0, Math.min(12, orderedPending.length));
    const sources = this._buildCandidateSources(target);
    let best = null;

    for (const source of sources) {
      const extractResult = await this.navigator.protocolArchiveExtract(source.url, {
        maxPages: 50,
        timeoutMs: 90000,
        preferCurrentSeasonSource: this._isCurrentSeason(source.season)
      });
      const candidates = Array.isArray(extractResult?.matches) ? extractResult.matches : [];
      const sampleLinked = sample.reduce((count, l1Match) => {
        const matched = this._findBestCandidate(l1Match, candidates);
        return matched && matched.confidence >= confidenceThreshold ? count + 1 : count;
      }, 0);

      const evaluated = {
        source,
        extractResult,
        candidates,
        sampleLinked
      };

      this.logger.info('recon_candidate_source_evaluated', {
        league: target.league.name,
        dbSeason: target.dbSeason,
        requestedSeason: target.season,
        sourceSeason: source.season,
        sourceUrl: source.url,
        sampleSize: sample.length,
        sampleLinked,
        candidateCount: candidates.length,
        sourceState: extractResult?.sourceState || null
      });

      if (
        !best ||
        evaluated.sampleLinked > best.sampleLinked ||
        (
          evaluated.sampleLinked === best.sampleLinked &&
          evaluated.candidates.length > best.candidates.length
        )
      ) {
        best = evaluated;
      }
    }

    return best || {
      source: {
        season: this._formatSeasonForUrl(target.season || target.dbSeason),
        url: target.resultsUrl
      },
      extractResult: { matches: [], pagesScanned: 0, totalCandidates: 0, sourceState: 'SOURCE_EMPTY' },
      candidates: [],
      sampleLinked: 0
    };
  }

  async _runReconTarget(target, options = {}) {
    const {
      concurrency = this.defaultReconConcurrency,
      batchSize = this.reconBatchSize,
      confidenceThreshold = this.confidenceThreshold,
      pendingMatches: pendingMatchesOverride = null,
      matchLimit = null
    } = options;

    const pendingMatches = Array.isArray(pendingMatchesOverride)
      ? pendingMatchesOverride
      : await this._loadReconPendingMatches(target);

    if (!Array.isArray(pendingMatches) || pendingMatches.length === 0) {
      return { pendingTotal: 0, linked: 0, mismatched: 0 };
    }

    const limiter = pLimit(Math.max(1, Number(concurrency)));
    const orderedPending = [...pendingMatches].sort((a, b) => String(a.match_id).localeCompare(String(b.match_id)));
    const selectedSource = await this._selectCandidateSource(target, orderedPending, confidenceThreshold);
    const candidates = selectedSource.candidates;

    if (!Array.isArray(candidates) || candidates.length === 0) {
      const sourceState = selectedSource?.extractResult?.sourceState || 'SOURCE_EMPTY';
      const error = new Error(sourceState);
      error.code = sourceState;
      error.sourceUrl = selectedSource?.source?.url || target.resultsUrl;
      error.sourceSeason = selectedSource?.source?.season || this._formatSeasonForUrl(target.season);
      throw error;
    }

    const selectedPending = this._selectProcessablePendingMatches(
      orderedPending,
      candidates,
      confidenceThreshold,
      matchLimit
    );

    const outcomes = await Promise.all(
      selectedPending.map((l1Match) => limiter(() =>
        this._reconcilePendingMatch(l1Match, candidates, target, confidenceThreshold)
      ))
    );

    const mappings = [];
    const mismatches = [];

    for (const outcome of outcomes) {
      if (outcome?.status === 'linked' && outcome.mapping) {
        mappings.push(outcome.mapping);
      } else if (outcome?.status === 'mismatch' && outcome.matchId) {
        mismatches.push(outcome.matchId);
      }
    }

    await this._persistReconBatches(mappings, mismatches, Math.max(1, Number(batchSize)));

    return {
      pendingTotal: selectedPending.length,
      linked: mappings.length,
      mismatched: mismatches.length,
      sourceSeason: selectedSource?.source?.season || this._formatSeasonForUrl(target.season),
      sourceUrl: selectedSource?.source?.url || target.resultsUrl,
      candidateCount: Array.isArray(candidates) ? candidates.length : 0
    };
  }

  async _loadReconPendingMatches(target) {
    if (this.repository && typeof this.repository.getReconEligibleMatches === 'function') {
      return this.repository.getReconEligibleMatches(target.dbSeason, target.league.name);
    }

    return this.repository.getUnstitchedMatches(target.dbSeason, target.league.name);
  }

  _selectProcessablePendingMatches(pendingMatches, candidates, confidenceThreshold, matchLimit = null) {
    const orderedPending = [...pendingMatches].sort((a, b) =>
      String(a.match_id).localeCompare(String(b.match_id))
    );

    if (!Number.isInteger(matchLimit) || matchLimit <= 0 || orderedPending.length <= matchLimit) {
      return orderedPending;
    }

    const ranked = orderedPending.map((match) => {
      const candidateMatch = this._findBestCandidate(match, candidates);
      return {
        match,
        confidence: candidateMatch?.confidence || 0,
        matchDate: match.match_date || null
      };
    });

    const linkedFirst = ranked
      .filter((item) => item.confidence >= confidenceThreshold)
      .sort((left, right) => {
        if (right.confidence !== left.confidence) {
          return right.confidence - left.confidence;
        }

        const rightDate = right.matchDate ? new Date(right.matchDate).getTime() : 0;
        const leftDate = left.matchDate ? new Date(left.matchDate).getTime() : 0;
        if (rightDate !== leftDate) {
          return rightDate - leftDate;
        }

        return String(right.match.match_id).localeCompare(String(left.match.match_id));
      })
      .slice(0, matchLimit)
      .map((item) => item.match);

    if (linkedFirst.length >= matchLimit) {
      return linkedFirst;
    }

    const selectedIds = new Set(linkedFirst.map((item) => item.match_id));
    const fallbackMatches = orderedPending
      .filter((item) => !selectedIds.has(item.match_id))
      .slice(0, matchLimit - linkedFirst.length);

    return [...linkedFirst, ...fallbackMatches];
  }

  async _persistReconBatches(mappings, mismatchIds, batchSize) {
    const orderedMappings = [...mappings].sort((a, b) => String(a.match_id).localeCompare(String(b.match_id)));
    const orderedMismatchIds = [...new Set(mismatchIds.map((id) => String(id)))]
      .sort((a, b) => a.localeCompare(b));

    for (let index = 0; index < orderedMappings.length; index += batchSize) {
      const batch = orderedMappings.slice(index, index + batchSize);
      await this.repository.batchSaveOddsPortalMappings(batch, {
        pipelineStatus: 'RECON_LINKED'
      });
    }

    for (let index = 0; index < orderedMismatchIds.length; index += batchSize) {
      const batch = orderedMismatchIds.slice(index, index + batchSize);
      await this.repository.batchUpdateMatchPipelineStatus(batch, 'RECON_MISMATCH');
    }
  }

  async _reconcilePendingMatch(l1Match, candidates, target, confidenceThreshold) {
    const candidateMatch = this._findBestCandidate(l1Match, candidates);

    if (!candidateMatch || candidateMatch.confidence < confidenceThreshold) {
      return {
        status: 'mismatch',
        matchId: l1Match.match_id
      };
    }

    return {
      status: 'linked',
      mapping: {
        match_id: l1Match.match_id,
        oddsportal_hash: candidateMatch.candidate.hash,
        full_url: candidateMatch.candidate.url,
        season: target.dbSeason,
        league_name: target.league.name,
        home_team: l1Match.home_team,
        away_team: l1Match.away_team,
        match_confidence: candidateMatch.confidence,
        mapping_method: candidateMatch.method || 'recon_matrix',
        status: 'pending'
      }
    };
  }

  _findBestCandidate(l1Match, candidates) {
    if (!Array.isArray(candidates) || candidates.length === 0) {
      return null;
    }

    let best = null;

    for (const candidate of candidates) {
      if (!candidate?.homeTeam || !candidate?.awayTeam) {
        continue;
      }

      const directHome = this._calculateSimilarity(candidate.homeTeam, l1Match.home_team);
      const directAway = this._calculateSimilarity(candidate.awayTeam, l1Match.away_team);
      const swappedHome = this._calculateSimilarity(candidate.homeTeam, l1Match.away_team);
      const swappedAway = this._calculateSimilarity(candidate.awayTeam, l1Match.home_team);

      const directScore = (directHome + directAway) / 2;
      const swappedScore = (swappedHome + swappedAway) / 2;
      const teamConfidence = Math.max(directScore, swappedScore);
      const dateConfidence = this._calculateDateConfidence(
        candidate.matchDate || candidate.match_date,
        l1Match.match_date
      );
      const confidence = dateConfidence === null
        ? teamConfidence
        : Math.max(0, Math.min(1, (teamConfidence * 0.85) + (dateConfidence * 0.15)));

      if (!best || confidence > best.confidence) {
        best = {
          candidate,
          confidence,
          method: confidence >= 0.99 ? 'exact' : 'fuzzy'
        };
      }
    }

    return best;
  }
}

module.exports = { ReconEngine };
