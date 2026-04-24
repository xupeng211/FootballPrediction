'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');

const { reconSourceProber } = require('../../src/infrastructure/recon/services/ReconSourceProber');
const { Normalizer } = require('../../src/utils/Normalizer');

function createProber(overrides = {}) {
  const events = {
    warn: [],
  };

  return {
    ...reconSourceProber,
    logger: {
      info() {},
      debug() {},
      warn(event, payload) {
        events.warn.push({ event, payload });
      },
    },
    pageSettleWaitMs: 0,
    _resolveRouteProbeTimeoutMs() {
      return 500;
    },
    _resetRouteFailureStreak() {},
    _recordRouteProbeFailure() {
      return {
        shouldDegrade: false,
        sourceState: 'SEARCH_DEGRADED',
        searchBlocked: false,
        signals: { has503: false, hasTimeout: false },
      };
    },
    _isSearchProbeBlocked() {
      return false;
    },
    _buildSeasonMirror(candidates = []) {
      return new Map(
        candidates.map((candidate) => [candidate.hash || candidate.url, candidate])
      );
    },
    _scoreCandidatePoolSample() {
      return 0;
    },
    _buildFallbackEventSlug(homeTeam, awayTeam) {
      const slugify = (value) => String(Normalizer.normalizeTeamName(value) || value || '')
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-+|-+$/g, '');
      const homeSlug = slugify(homeTeam);
      const awaySlug = slugify(awayTeam);
      return homeSlug && awaySlug ? `${homeSlug}-${awaySlug}` : '';
    },
    _resolveTrustedOddsPortalBaseUrl() {
      return 'https://www.oddsportal.com';
    },
    async _executeRouteProbeWithNavigator(_target, _navigator, _options, probe) {
      return probe({
        async resetContextPerBatch() {},
        async navigate() {},
        page: {
          async evaluate() {
            return [];
          },
        },
      });
    },
    __events: events,
    ...overrides,
  };
}

describe('ReconSourceProber Search Audit', () => {
  it('无候选时应回传原始队名与字典远端名样本', async () => {
    const prober = createProber({
      _buildLocalDictionaryIndex() {
        return new Map();
      },
      _resolveLocalDictionaryRemoteName(teamName) {
        const key = String(teamName || '').trim();
        if (key === 'Kyoto Sanga') {
          return 'Kyoto Sanga FC';
        }
        if (key === 'Tokyo Verdy') {
          return 'Verdy';
        }
        return null;
      },
    });

    const result = await prober._collectSearchCandidatesForPendingMatches(
      { league: { name: 'J1 League' }, dbSeason: '2025/2026' },
      [{ match_id: 'm-j1-1', home_team: 'Kyoto Sanga', away_team: 'Tokyo Verdy' }],
      {
        async navigate() {},
        page: {
          async evaluate() {
            return [];
          },
        },
      },
      { timeoutMs: 500 }
    );

    assert.equal(result.matches.length, 0);
    assert.deepEqual(result.emptySearchSamples[0], {
      matchId: 'm-j1-1',
      homeTeamRaw: 'Kyoto Sanga',
      awayTeamRaw: 'Tokyo Verdy',
      dictionaryHomeTeam: 'Kyoto Sanga FC',
      dictionaryAwayTeam: 'Verdy',
      attemptedSearchSlugs: [
        'kyoto-sanga-tokyo-verdy',
        'tokyo-verdy-kyoto-sanga',
        'kyoto-sanga-verdy',
        'verdy-kyoto-sanga',
        'kyoto-sanga'
      ],
      attemptedSearchUrls: [
        'https://www.oddsportal.com/search/kyoto-sanga-tokyo-verdy/',
        'https://www.oddsportal.com/search/tokyo-verdy-kyoto-sanga/',
        'https://www.oddsportal.com/search/kyoto-sanga-verdy/',
        'https://www.oddsportal.com/search/verdy-kyoto-sanga/',
        'https://www.oddsportal.com/search/kyoto-sanga/'
      ],
    });
  });

  it('search route 返回 SOURCE_EMPTY 时应记录 3 组内审计样本', async () => {
    const prober = createProber({
      _buildLocalDictionaryIndex() {
        return new Map();
      },
      _resolveLocalDictionaryRemoteName(teamName) {
        if (teamName === 'Kawasaki Frontale') {
          return 'Frontale';
        }
        if (teamName === 'Shonan Bellmare') {
          return 'Shonan';
        }
        return null;
      },
    });

    const source = await prober._probeSearchCandidateSource(
      { dbSeason: '2025/2026', league: { name: 'J1 League' } },
      [{ match_id: 'm1', home_team: 'Kawasaki Frontale', away_team: 'Shonan Bellmare' }],
      0.75
    );

    assert.equal(source.extractResult.sourceState, 'SOURCE_EMPTY');
    const summaryAuditEvent = prober.__events.warn.find((event) => event.event === 'recon_search_source_empty_audit');
    assert.ok(summaryAuditEvent);
    assert.deepEqual(
      summaryAuditEvent.payload.samples[0],
      {
        matchId: 'm1',
        homeTeamRaw: 'Kawasaki Frontale',
        awayTeamRaw: 'Shonan Bellmare',
        dictionaryHomeTeam: 'Frontale',
        dictionaryAwayTeam: 'Shonan',
        attemptedSearchSlugs: [
          'kawasaki-frontale-shonan-bellmare',
          'shonan-bellmare-kawasaki-frontale',
          'frontale-shonan-bellmare',
          'shonan-bellmare-frontale',
          'kawasaki-frontale'
        ],
        attemptedSearchUrls: [
          'https://www.oddsportal.com/search/kawasaki-frontale-shonan-bellmare/',
          'https://www.oddsportal.com/search/shonan-bellmare-kawasaki-frontale/',
          'https://www.oddsportal.com/search/frontale-shonan-bellmare/',
          'https://www.oddsportal.com/search/shonan-bellmare-frontale/',
          'https://www.oddsportal.com/search/kawasaki-frontale/'
        ],
      }
    );
  });
});
