'use strict';

const {
  buildFuzzyPrefixKeyword,
  buildSearchKeywordSlug,
  isSearchNavigationTimeoutError,
  normalizeLeagueDeadlineAt,
  resolveSearchNavigationTimeoutMs,
  shouldTolerateSearchNavigationFailure,
  shouldUseBidirectionalSearchDescriptors
} = require('./ReconSourceProberRouteUtils');

function normalizeAuditText(value) {
  const normalized = String(value ?? '').trim();
  return normalized || null;
}

function normalizeAuditNumber(value) {
  const normalized = Number(value);
  return Number.isFinite(normalized) && normalized > 0 ? normalized : null;
}

const reconSourceProberSearchFlow = {
  async _probeSearchCandidateSource(target, pendingMatches, confidenceThreshold, navigator = null, options = {}) {
    if (!Array.isArray(pendingMatches) || pendingMatches.length === 0) {
      return null;
    }

    const timeoutMs = this._resolveRouteProbeTimeoutMs('search', target);
    if (target?.disableSearchRoute === true) {
      return this._buildDegradedRouteSource(
        'search',
        target,
        'ROUTE_SKIPPED_SEARCH_DISABLED',
        null,
        {
          timeoutMs,
          searchBlocked: true
        }
      );
    }

    if (this._isSearchProbeBlocked(target)) {
      return this._buildDegradedRouteSource(
        'search',
        target,
        'ROUTE_SKIPPED_DEGRADED_LEAGUE',
        null,
        {
          timeoutMs,
          searchBlocked: true
        }
      );
    }

    try {
      const routeSource = await this._executeRouteProbeWithNavigator(
        target,
        navigator,
        {
          routeKind: 'search',
          launchBrowser: true,
          useDedicatedNavigator: options.useDedicatedNavigator === true
        },
        async (activeNavigator) => this._buildSearchRouteSource(
          target,
          pendingMatches,
          confidenceThreshold,
          activeNavigator,
          { timeoutMs }
        )
      );
      this._resetRouteFailureStreak(target, 'search');
      return routeSource;
    } catch (error) {
      if (error?.code === 'LEAGUE_TIMEOUT') {
        throw error;
      }
      const failure = this._recordRouteProbeFailure(target, 'search', error, { timeoutMs });
      if (failure.shouldDegrade || failure.signals.has503 || failure.signals.hasTimeout) {
        return this._buildDegradedRouteSource(
          'search',
          target,
          failure.sourceState,
          error,
          {
            timeoutMs,
            searchBlocked: true
          }
        );
      }
      throw error;
    }
  },

  async _buildSearchRouteSource(target, pendingMatches, confidenceThreshold, navigator, options = {}) {
    const searchResult = await this._collectSearchCandidatesForPendingMatches(
      target,
      pendingMatches,
      navigator,
      options
    );
    const candidates = this._dedupeCandidatesByIdentity(searchResult?.matches || []);
    const seasonMirror = this._buildSeasonMirror(candidates);
    const emptySearchSamples = Array.isArray(searchResult?.emptySearchSamples)
      ? searchResult.emptySearchSamples
      : [];
    const failedSearchSamples = Array.isArray(searchResult?.failedSearchSamples)
      ? searchResult.failedSearchSamples
      : [];

    this._logSearchNavigationFailureAudit(target, pendingMatches, failedSearchSamples);
    this._logSearchSourceEmptyAudit(target, pendingMatches, candidates, emptySearchSamples);

    return {
      routeKind: 'search',
      source: {
        season: target?.dbSeason || null,
        url: (searchResult?.sourceUrls || []).join(' | ')
      },
      extractResult: {
        matches: candidates,
        pagesScanned: Number(searchResult?.pagesScanned || 0),
        totalCandidates: candidates.length,
        sourceState: candidates.length > 0 ? 'SEARCH_SWEEP_READY' : 'SOURCE_EMPTY'
      },
      candidates,
      seasonMirror,
      sampleLinked: this._scoreCandidatePoolSample(pendingMatches, candidates, confidenceThreshold, seasonMirror)
    };
  },

  _logSearchNavigationFailureAudit(target, pendingMatches, failedSearchSamples = []) {
    if (failedSearchSamples.length === 0) {
      return;
    }

    this.logger.warn('recon_search_navigation_failure_audit', {
      league: target?.league?.name || null,
      season: target?.dbSeason || null,
      pendingTotal: Array.isArray(pendingMatches) ? pendingMatches.length : 0,
      sampleCount: Math.min(failedSearchSamples.length, 3),
      samples: failedSearchSamples.slice(0, 3)
    });
  },

  _logSearchSourceEmptyAudit(target, pendingMatches, candidates = [], emptySearchSamples = []) {
    if (candidates.length > 0 || emptySearchSamples.length === 0) {
      return;
    }

    this.logger.warn('recon_search_source_empty_audit', {
      league: target?.league?.name || null,
      season: target?.dbSeason || null,
      pendingTotal: Array.isArray(pendingMatches) ? pendingMatches.length : 0,
      sampleCount: Math.min(emptySearchSamples.length, 3),
      samples: emptySearchSamples.slice(0, 3)
    });
  },

  async _collectSearchCandidatesForPendingMatches(target, pendingMatches, navigator, options = {}) {
    if (!navigator || typeof navigator.navigate !== 'function' || !navigator.page) {
      return { matches: [], pagesScanned: 0, sourceUrls: [], emptySearchSamples: [], failedSearchSamples: [] };
    }

    if (typeof navigator.resetContextPerBatch === 'function') {
      await navigator.resetContextPerBatch({
        reason: 'search_candidate_batch'
      });
    }

    const state = this._createSearchCollectionState(target, pendingMatches, options);
    for (const l1Match of Array.isArray(pendingMatches) ? pendingMatches : []) {
      const shouldStop = await this._processPendingSearchMatch(
        l1Match,
        target,
        navigator,
        options,
        state
      );
      if (shouldStop) {
        break;
      }
    }

    return {
      matches: state.matches,
      pagesScanned: state.sourceUrls.length,
      sourceUrls: state.sourceUrls,
      emptySearchSamples: state.emptySearchSamples,
      failedSearchSamples: state.failedSearchSamples
    };
  },

  _createSearchCollectionState(target, pendingMatches, options = {}) {
    const state = {
      matches: [],
      sourceUrls: [],
      seenCandidateKeys: new Set(),
      searchResultCache: new Map(),
      emptySearchSamples: [],
      failedSearchSamples: [],
      searchBudgetShortCircuited: false
    };
    const leagueDeadlineAt = normalizeLeagueDeadlineAt(target?.leagueDeadlineAt ?? options.leagueDeadlineAt);

    state.searchNavigationTimeoutMs = resolveSearchNavigationTimeoutMs(
      target,
      Number(options.timeoutMs || this._resolveRouteProbeTimeoutMs('search', target))
    );
    state.shouldShortCircuitForLeagueBudget = this._buildSearchBudgetShortCircuitGuard(
      target,
      pendingMatches,
      state.emptySearchSamples,
      state.failedSearchSamples,
      state.sourceUrls,
      leagueDeadlineAt,
      () => {
        state.searchBudgetShortCircuited = true;
      }
    );
    return state;
  },

  async _processPendingSearchMatch(l1Match, target, navigator, options = {}, state = {}) {
    if (state.shouldShortCircuitForLeagueBudget('search_match_loop', {
      matchId: l1Match?.match_id || null
    })) {
      return true;
    }

    const searchDescriptors = this._buildSearchDescriptorsForMatch(l1Match, target);
    if (searchDescriptors.length === 0) {
      return false;
    }

    const attemptedDescriptors = [];
    const resolvedCandidateCount = await this._resolveSearchCandidatesForMatch(
      l1Match,
      searchDescriptors,
      attemptedDescriptors,
      target,
      navigator,
      options,
      state
    );

    if (state.searchBudgetShortCircuited) {
      return true;
    }

    if (resolvedCandidateCount === 0) {
      this._recordSearchSourceEmptySample(l1Match, attemptedDescriptors, searchDescriptors, target, state.emptySearchSamples);
    }

    return false;
  },

  async _resolveSearchCandidatesForMatch(
    l1Match,
    searchDescriptors,
    attemptedDescriptors,
    target,
    navigator,
    options = {},
    state = {}
  ) {
    const exactSearchDescriptors = searchDescriptors
      .filter((descriptor) => descriptor?.cascadeStage !== 'fuzzy');
    const fuzzySearchDescriptors = searchDescriptors
      .filter((descriptor) => descriptor?.cascadeStage === 'fuzzy');
    const context = this._buildSearchCascadeContext(target, navigator, options, state);

    let resolvedCandidateCount = await this._executeSearchCascade(
      l1Match,
      exactSearchDescriptors,
      attemptedDescriptors,
      context
    );

    if (!state.searchBudgetShortCircuited && resolvedCandidateCount === 0 && fuzzySearchDescriptors.length > 0) {
      resolvedCandidateCount += await this._executeSearchCascade(
        l1Match,
        fuzzySearchDescriptors,
        attemptedDescriptors,
        context
      );
    }

    return resolvedCandidateCount;
  },

  _buildSearchCascadeContext(target, navigator, options = {}, state = {}) {
    return {
      target,
      navigator,
      options,
      searchNavigationTimeoutMs: state.searchNavigationTimeoutMs,
      searchResultCache: state.searchResultCache,
      sourceUrls: state.sourceUrls,
      seenCandidateKeys: state.seenCandidateKeys,
      matches: state.matches,
      failedSearchSamples: state.failedSearchSamples,
      shouldShortCircuitForLeagueBudget: state.shouldShortCircuitForLeagueBudget
    };
  },

  _recordSearchSourceEmptySample(l1Match, attemptedDescriptors, searchDescriptors, target, emptySearchSamples = []) {
    const emptySearchSample = this._buildSearchSourceEmptySample(
      l1Match,
      attemptedDescriptors.length > 0 ? attemptedDescriptors : searchDescriptors
    );
    emptySearchSamples.push(emptySearchSample);
    this.logger.warn('recon_search_source_empty_deep_audit', {
      league: target?.league?.name || null,
      season: target?.dbSeason || null,
      target_match_id: emptySearchSample.matchId,
      home_team_raw: emptySearchSample.homeTeamRaw,
      away_team_raw: emptySearchSample.awayTeamRaw,
      attempted_slugs: emptySearchSample.attemptedSearchSlugs
    });
  },

  _buildSearchBudgetShortCircuitGuard(
    target,
    pendingMatches,
    emptySearchSamples,
    failedSearchSamples,
    sourceUrls,
    leagueDeadlineAt,
    onShortCircuit = () => {}
  ) {
    return (stage, context = {}) => {
      if (!Number.isFinite(leagueDeadlineAt) || Date.now() < leagueDeadlineAt) {
        return false;
      }

      this.logger.warn('recon_search_budget_short_circuit', {
        league: target?.league?.name || null,
        season: target?.dbSeason || null,
        stage,
        pendingTotal: Array.isArray(pendingMatches) ? pendingMatches.length : 0,
        processedMatches: emptySearchSamples.length + failedSearchSamples.length,
        sourceUrlsScanned: sourceUrls.length,
        ...context
      });
      onShortCircuit();
      return true;
    };
  },

  async _executeSearchCascade(l1Match, searchDescriptors, attemptedDescriptors, context = {}) {
    const {
      target,
      navigator,
      options = {},
      searchNavigationTimeoutMs,
      searchResultCache,
      sourceUrls,
      seenCandidateKeys,
      matches,
      failedSearchSamples,
      shouldShortCircuitForLeagueBudget
    } = context;
    let resolvedCandidateCount = 0;

    for (const descriptor of Array.isArray(searchDescriptors) ? searchDescriptors : []) {
      if (this._shouldShortCircuitSearchDescriptorLoop(shouldShortCircuitForLeagueBudget, l1Match, descriptor)) {
        break;
      }

      const searchUrl = normalizeAuditText(descriptor?.searchUrl);
      if (!searchUrl) {
        continue;
      }

      attemptedDescriptors.push(descriptor);
      const searchCandidates = await this._resolveSearchCandidatesForDescriptor(
        l1Match,
        descriptor,
        navigator,
        target,
        {
          ...options,
          searchNavigationTimeoutMs
        },
        searchResultCache,
        sourceUrls,
        failedSearchSamples
      );

      resolvedCandidateCount += Array.isArray(searchCandidates) ? searchCandidates.length : 0;
      this._appendResolvedSearchCandidates(searchCandidates, seenCandidateKeys, matches);
    }

    return resolvedCandidateCount;
  },

  _shouldShortCircuitSearchDescriptorLoop(shouldShortCircuitForLeagueBudget, l1Match, descriptor) {
    return shouldShortCircuitForLeagueBudget('search_descriptor_loop', {
      matchId: l1Match?.match_id || null,
      searchUrl: descriptor?.searchUrl || null,
      origin: descriptor?.origin || null,
      cascadeStage: descriptor?.cascadeStage || 'exact'
    });
  },

  async _resolveSearchCandidatesForDescriptor(
    l1Match,
    descriptor,
    navigator,
    target,
    options,
    searchResultCache,
    sourceUrls,
    failedSearchSamples
  ) {
    const searchUrl = descriptor.searchUrl;
    const cachedCandidates = searchResultCache.get(searchUrl);
    if (cachedCandidates) {
      return cachedCandidates;
    }

    sourceUrls.push(searchUrl);
    const searchCandidates = await this._fetchSearchCandidatesForDescriptor(
      l1Match,
      descriptor,
      navigator,
      target,
      options,
      failedSearchSamples
    );
    searchResultCache.set(searchUrl, searchCandidates);
    return searchCandidates;
  },

  async _fetchSearchCandidatesForDescriptor(
    l1Match,
    descriptor,
    navigator,
    target,
    options,
    failedSearchSamples = []
  ) {
    try {
      return await this._collectSearchCandidatesFromUrl(descriptor.searchUrl, navigator, target, options);
    } catch (error) {
      if (!shouldTolerateSearchNavigationFailure(target) || !isSearchNavigationTimeoutError(error)) {
        throw error;
      }

      failedSearchSamples.push(this._buildSearchFailureSample(
        l1Match,
        descriptor,
        navigator,
        error,
        options.searchNavigationTimeoutMs
      ));
      await this._recoverSearchNavigatorAfterTimeout(navigator);
      return [];
    }
  },

  async _recoverSearchNavigatorAfterTimeout(navigator) {
    if (typeof navigator.resetContextPerBatch !== 'function') {
      return;
    }

    try {
      await navigator.resetContextPerBatch({
        reason: 'search_candidate_timeout_recover'
      });
    } catch (_resetError) {
      // search route 容错恢复失败时继续使用空结果回退
    }
  },

  _appendResolvedSearchCandidates(searchCandidates, seenCandidateKeys, matches = []) {
    for (const candidate of (Array.isArray(searchCandidates) ? searchCandidates : [])) {
      const candidateKey = normalizeAuditText(candidate?.hash || candidate?.url || '');
      if (!candidateKey || seenCandidateKeys.has(candidateKey)) {
        continue;
      }

      seenCandidateKeys.add(candidateKey);
      matches.push(candidate);
    }
  },

  _buildSearchDescriptorsForMatch(l1Match, target = {}) {
    const descriptors = [];
    const seenUrls = new Set();
    const bidirectional = shouldUseBidirectionalSearchDescriptors(target);
    const pushDescriptor = (origin, homeTeam, awayTeam, options = {}) => {
      const cascadeStage = options.cascadeStage === 'fuzzy' ? 'fuzzy' : 'exact';
      const searchSlug = options.searchSlug || this._buildFallbackEventSlug(homeTeam, awayTeam);
      if (!searchSlug) {
        return;
      }

      const searchUrl = `${this._resolveTrustedOddsPortalBaseUrl()}/search/${encodeURIComponent(searchSlug)}/`;
      if (seenUrls.has(searchUrl)) {
        return;
      }

      seenUrls.add(searchUrl);
      descriptors.push({
        origin,
        cascadeStage,
        homeTeam: String(homeTeam || '').trim(),
        awayTeam: String(awayTeam || '').trim(),
        searchSlug,
        searchUrl
      });
    };

    pushDescriptor('raw', l1Match?.home_team, l1Match?.away_team);
    if (bidirectional) {
      pushDescriptor('raw_reversed', l1Match?.away_team, l1Match?.home_team);
    }

    if (typeof this._buildLocalDictionaryIndex === 'function' && typeof this._resolveLocalDictionaryRemoteName === 'function') {
      try {
        const localDictionaryIndex = this._buildLocalDictionaryIndex(target);
        const remoteHomeTeam = this._resolveLocalDictionaryRemoteName(l1Match?.home_team || '', localDictionaryIndex);
        const remoteAwayTeam = this._resolveLocalDictionaryRemoteName(l1Match?.away_team || '', localDictionaryIndex);
        if (remoteHomeTeam && remoteAwayTeam) {
          pushDescriptor('dictionary_remote', remoteHomeTeam, remoteAwayTeam);
          if (bidirectional) {
            pushDescriptor('dictionary_remote_reversed', remoteAwayTeam, remoteHomeTeam);
          }
        }
      } catch (_error) {
        // 字典增强失败时静默回退到原始队名搜索
      }
    }

    const fuzzyPrefixKeyword = buildFuzzyPrefixKeyword(l1Match?.home_team || '');
    const fuzzyPrefixSlug = buildSearchKeywordSlug(fuzzyPrefixKeyword);
    if (fuzzyPrefixSlug) {
      pushDescriptor('fuzzy_prefix', fuzzyPrefixKeyword, '', {
        cascadeStage: 'fuzzy',
        searchSlug: fuzzyPrefixSlug
      });
    }

    return descriptors;
  },

  _buildSearchUrlForMatch(l1Match) {
    const slug = this._buildFallbackEventSlug(l1Match?.home_team, l1Match?.away_team);
    if (!slug) {
      return '';
    }

    return `${this._resolveTrustedOddsPortalBaseUrl()}/search/${encodeURIComponent(slug)}/`;
  },

  _buildSearchSourceEmptySample(l1Match, searchDescriptors = []) {
    const dictionaryDescriptor = (Array.isArray(searchDescriptors) ? searchDescriptors : [])
      .find((descriptor) => descriptor?.origin === 'dictionary_remote') || null;

    return {
      matchId: String(l1Match?.match_id || '').trim() || null,
      homeTeamRaw: String(l1Match?.home_team || '').trim() || null,
      awayTeamRaw: String(l1Match?.away_team || '').trim() || null,
      dictionaryHomeTeam: dictionaryDescriptor?.homeTeam || null,
      dictionaryAwayTeam: dictionaryDescriptor?.awayTeam || null,
      attemptedSearchSlugs: (Array.isArray(searchDescriptors) ? searchDescriptors : [])
        .map((descriptor) => String(descriptor?.searchSlug || '').trim())
        .filter(Boolean),
      attemptedSearchUrls: (Array.isArray(searchDescriptors) ? searchDescriptors : [])
        .map((descriptor) => String(descriptor?.searchUrl || '').trim())
        .filter(Boolean)
    };
  },

  _buildSearchFailureSample(l1Match, descriptor = {}, navigator = null, error = null, timeoutMs = 0) {
    return {
      matchId: normalizeAuditText(l1Match?.match_id),
      homeTeamRaw: normalizeAuditText(l1Match?.home_team),
      awayTeamRaw: normalizeAuditText(l1Match?.away_team),
      origin: normalizeAuditText(descriptor?.origin),
      searchSlug: normalizeAuditText(descriptor?.searchSlug),
      searchUrl: normalizeAuditText(descriptor?.searchUrl),
      proxyPort: navigator?.proxy?.port || null,
      timeoutMs: normalizeAuditNumber(timeoutMs),
      error: normalizeAuditText(error?.message || error)
    };
  },

  async _collectSearchCandidatesFromUrl(searchUrl, navigator, target, options = {}) {
    await navigator.navigate(searchUrl, {
      waitUntil: 'domcontentloaded',
      timeout: Number(
        options.searchNavigationTimeoutMs
        || options.timeoutMs
        || this._resolveRouteProbeTimeoutMs('search', target)
      )
    });
    if (typeof navigator.page?.waitForTimeout === 'function') {
      await navigator.page.waitForTimeout(this.pageSettleWaitMs);
    }

    return navigator.page.evaluate(({ baseUrl, sourceUrl }) => {
      const matches = [];
      const seen = new Set();
      const hashPattern = /-([A-Za-z0-9]{8})\/?(?:[#?].*)?$/;

      document.querySelectorAll('a[href*="/football/"]').forEach((link) => {
        const href = String(link.getAttribute('href') || '').trim();
        if (!href) {
          return;
        }

        const absoluteUrl = href.startsWith('http')
          ? href
          : `${String(baseUrl || '').replace(/\/+$/u, '')}/${href.replace(/^\/+/u, '')}`;
        if (/\/(?:results|fixtures)\//iu.test(absoluteUrl)) {
          return;
        }

        const match = absoluteUrl.match(hashPattern);
        if (!match) {
          return;
        }

        const normalizedUrl = absoluteUrl.split('#')[0];
        if (seen.has(normalizedUrl)) {
          return;
        }

        seen.add(normalizedUrl);
        matches.push({
          url: normalizedUrl,
          hash: match[1],
          source: 'search_route',
          sourceUrl
        });
      });

      return matches;
    }, {
      baseUrl: this._resolveTrustedOddsPortalBaseUrl(),
      sourceUrl: searchUrl
    });
  }
};

module.exports = { reconSourceProberSearchFlow };
