'use strict';

const crypto = require('crypto');
const fs = require('node:fs');
const path = require('node:path');

const DEFAULT_TEAM_MAPPINGS_PATH = path.resolve(__dirname, '../../../../config/recon_team_mappings.json');
let cachedConfigTeamMappings = null;

function normalizeTeamMappings(payload) {
  const rawMappings = Array.isArray(payload)
    ? payload
    : Array.isArray(payload?.mappings)
      ? payload.mappings
      : [];

  return Object.freeze(rawMappings
    .map((entry) => ({
      local_team_name: String(entry?.local_team_name || '').trim(),
      remote_name: String(entry?.remote_name || '').trim()
    }))
    .filter((entry) => entry.local_team_name && entry.remote_name)
    .map((entry) => Object.freeze(entry)));
}

function loadConfigTeamMappings() {
  if (cachedConfigTeamMappings) {
    return cachedConfigTeamMappings;
  }

  const mappingsPath = process.env.RECON_TEAM_MAPPINGS_PATH || DEFAULT_TEAM_MAPPINGS_PATH;
  try {
    const payload = JSON.parse(fs.readFileSync(mappingsPath, 'utf8'));
    cachedConfigTeamMappings = normalizeTeamMappings(payload);
  } catch (_error) {
    cachedConfigTeamMappings = Object.freeze([]);
  }

  return cachedConfigTeamMappings;
}

function normalizeLooseLookupKey(teamName) {
  return String(teamName || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[\\/]+/g, ' ')
    .replace(/[^a-z0-9]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

const reconLocalDictionaryService = {
  async _primeLeagueDictionary(target) {
    if (!this.matchEvaluator || typeof this.matchEvaluator.setLeagueDictionaryEntries !== 'function') {
      return [];
    }

    const leagueId = Number(target?.leagueId || target?.league?.id || 0);
    if (!Number.isInteger(leagueId) || leagueId <= 0) {
      this.matchEvaluator.clearLeagueDictionary?.();
      return [];
    }

    if (!this.repository || typeof this.repository.getLeagueDictionaryEntries !== 'function') {
      this.matchEvaluator.clearLeagueDictionary?.();
      return [];
    }

    const entries = await this.repository.getLeagueDictionaryEntries(leagueId, {
      season: target?.dbSeason || null
    });

    this.matchEvaluator.setLeagueDictionaryEntries(leagueId, entries);
    return entries;
  },

  _shouldUseLocalDictionaryOnly(_target, _pendingMatches = []) {
    return false;
  },

  _canUseLocalDictionaryFallback(target, pendingMatches = []) {
    const entries = Array.isArray(target?.leagueDictionaryEntries) ? target.leagueDictionaryEntries : [];
    if (entries.length === 0) {
      return false;
    }

    return pendingMatches.some((match) => Boolean(this._buildLocalDictionaryCandidate(match, target)));
  },

  _buildLocalDictionarySelectedSource(target, pendingMatches = [], sourceState = 'LOCAL_DICTIONARY_FALLBACK') {
    return {
      source: {
        season: target?.dbSeason || null,
        url: this._buildLocalDictionarySourceUrl(target)
      },
      extractResult: {
        matches: [],
        pagesScanned: 0,
        totalCandidates: pendingMatches.length,
        sourceState
      },
      candidates: [],
      seasonMirror: new Map(),
      sampleLinked: 0,
      localFallbackCandidateCount: pendingMatches.length
    };
  },

  _buildLocalDictionarySourceUrl(target) {
    const leagueId = Number(target?.leagueId || target?.league?.id || 0);
    const season = encodeURIComponent(String(target?.dbSeason || 'unknown'));
    return `dictionary://recon/${leagueId || 0}/${season}`;
  },

  _buildLocalDictionaryIndex(target) {
    if (target?.localDictionaryIndex instanceof Map) {
      return target.localDictionaryIndex;
    }

    const index = new Map();
    const registerEntry = (entry, options = {}) => {
      const overwrite = options.overwrite === true;
      for (const key of this._buildLocalDictionaryLookupKeys(entry?.local_team_name)) {
        if (!key || (!overwrite && index.has(key))) {
          continue;
        }

        index.set(key, entry);
      }
    };

    for (const entry of Array.isArray(target?.leagueDictionaryEntries) ? target.leagueDictionaryEntries : []) {
      registerEntry(entry);
    }

    for (const entry of loadConfigTeamMappings()) {
      registerEntry(
        {
          ...entry,
          source: 'config_alias_override'
        },
        { overwrite: true }
      );
    }

    target.localDictionaryIndex = index;
    return index;
  },

  _normalizeLocalDictionaryTeamName(teamName) {
    if (this.matchEvaluator && typeof this.matchEvaluator.normalizeTeamName === 'function') {
      return this.matchEvaluator.normalizeTeamName(teamName);
    }

    return String(teamName || '').toLowerCase().trim();
  },

  _buildLocalDictionaryLookupKeys(teamName) {
    return [...new Set([
      this._normalizeLocalDictionaryTeamName(teamName),
      normalizeLooseLookupKey(teamName)
    ].filter(Boolean))];
  },

  _resolveLocalDictionaryIndexEntry(teamName, index) {
    for (const key of this._buildLocalDictionaryLookupKeys(teamName)) {
      const entry = index.get(key) || null;
      if (entry) {
        return entry;
      }
    }

    return null;
  },

  _resolveLocalDictionaryRemoteName(teamName, index) {
    const normalizedTeamName = this._normalizeLocalDictionaryTeamName(teamName);
    const directEntry = this._resolveLocalDictionaryIndexEntry(teamName, index);
    if (directEntry?.remote_name) {
      return String(directEntry.remote_name);
    }

    const slashSegments = String(teamName || '')
      .split(/\s*\/\s*/)
      .map((segment) => String(segment || '').trim())
      .filter(Boolean);
    if (slashSegments.length > 1) {
      const resolvedSlashSegments = slashSegments.map((segment) => {
        const entry = this._resolveLocalDictionaryIndexEntry(segment, index);
        return entry?.remote_name ? String(entry.remote_name) : null;
      });
      return resolvedSlashSegments.every(Boolean) ? resolvedSlashSegments.join('/') : null;
    }

    const compositeCandidates = [...new Set([
      normalizedTeamName,
      normalizeLooseLookupKey(teamName)
    ].filter(Boolean))];

    for (const compositeCandidate of compositeCandidates) {
      const tokens = compositeCandidate.split(' ').filter(Boolean);
      for (let splitIndex = 1; splitIndex < tokens.length; splitIndex++) {
        const leftKey = tokens.slice(0, splitIndex).join(' ');
        const rightKey = tokens.slice(splitIndex).join(' ');
        const leftEntry = index.get(leftKey) || null;
        const rightEntry = index.get(rightKey) || null;

        if (leftEntry?.remote_name && rightEntry?.remote_name) {
          return `${leftEntry.remote_name}/${rightEntry.remote_name}`;
        }
      }
    }

    if (this.matchEvaluator?.isPlaceholderTeamName?.(teamName)) {
      return String(teamName || '')
        .trim()
        .replace(/\s+/g, ' ');
    }

    return null;
  },

  _buildLocalDictionaryCandidate(l1Match, target) {
    const index = this._buildLocalDictionaryIndex(target);
    if (!(index instanceof Map) || index.size === 0) {
      return null;
    }

    const homeRemoteName = this._resolveLocalDictionaryRemoteName(l1Match?.home_team || '', index);
    const awayRemoteName = this._resolveLocalDictionaryRemoteName(l1Match?.away_team || '', index);
    if (!homeRemoteName || !awayRemoteName) {
      return null;
    }

    const hashSeed = [
      target?.leagueId || target?.league?.id || 0,
      target?.dbSeason || '',
      l1Match?.match_id || '',
      homeRemoteName,
      awayRemoteName
    ].join('::');

    return {
      hash: `~${crypto.createHash('sha1').update(hashSeed).digest('hex').slice(0, 7)}`,
      url: [
        this._buildLocalDictionarySourceUrl(target),
        encodeURIComponent(String(homeRemoteName)),
        encodeURIComponent(String(awayRemoteName)),
        encodeURIComponent(String(l1Match?.match_id || ''))
      ].join('/'),
      homeTeam: String(homeRemoteName),
      awayTeam: String(awayRemoteName),
      matchDate: l1Match?.match_date || null,
      source: 'local_dictionary'
    };
  },

  async _runLocalDictionaryOnlyTarget(target, pendingMatches, options = {}) {
    const {
      batchSize = this.reconBatchSize,
      confidenceThreshold = this.confidenceThreshold,
      sourceSeason = target?.dbSeason || null,
      sourceUrl = this._buildLocalDictionarySourceUrl(target)
    } = options;

    const outcomes = [];
    for (const l1Match of pendingMatches) {
      outcomes.push(await this._reconcilePendingMatch(l1Match, [], target, confidenceThreshold, null));
    }

    const mappings = [];
    const mismatches = [];
    for (const outcome of outcomes) {
      if (outcome?.status === 'linked' && outcome.mapping) {
        mappings.push(outcome.mapping);
      } else if (outcome?.status === 'mismatch' && outcome.matchId) {
        mismatches.push({
          match_id: String(outcome.matchId),
          evidence: outcome.evidence || null
        });
      }
    }

    const persistResult = await this._persistReconBatches(
      mappings,
      mismatches,
      Math.max(1, Number(batchSize)),
      {
        reconRunId: this._createReconRunId(target),
        season: target.dbSeason,
        league: target.league.name,
        sourceSeason,
        sourceUrl,
        allowMismatchRetry: target?.reconPolicy?.allowMismatchRetry === true
      }
    );

    return {
      pendingTotal: pendingMatches.length,
      linked: Number(persistResult?.linkedStatusUpdated || 0),
      mismatched: Number(persistResult?.mismatchUpdated || 0),
      sourceSeason,
      sourceUrl,
      candidateCount: pendingMatches.length,
      effectiveConfidenceThreshold: confidenceThreshold
    };
  }
};

module.exports = { reconLocalDictionaryService };
