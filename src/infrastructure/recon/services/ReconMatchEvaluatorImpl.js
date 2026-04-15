'use strict';

const { RECON_CONFIG, getReconConfigSection } = require('./ReconServiceConfig');
const { ReconScoringEngine } = require('./ReconScoringEngine');
const { ReconTeamSimilarity } = require('./ReconTeamSimilarity');

const TEAM_SIMILARITY_METHODS = [
  'shouldAllowDictionaryStringContains',
  'shouldAllowPlaceNameEquivalence',
  'normalizeTeamName',
  'normalizeDictionaryComparableName',
  'normalizeLeaguePlaceComparableName',
  'resolveLeagueDictionaryEntry',
  'splitCompositeTeamName',
  'resolveDictionaryComparableTeamName',
  'resolveComparableTeamName',
  'isComparableNameEquivalent',
  'calculateSimilarity',
  'isDictionaryExactMatch',
  'isPlaceholderToken',
  'isPlaceholderTeamName',
  'isPlaceholderFixture',
  'hasTextualTeamName',
  'resolveCandidateTeams',
  'deriveTeamsFromCandidateUrl',
  'extractCandidatePathname',
  'extractTeamsFromH2hPath',
  'decodeCandidateTeamSegment',
  'tokenizeIdentityName',
  'extractIdentityMarkers',
  'hasIdentityHardConflict'
];

const SCORING_METHODS = [
  'evaluateCandidate',
  'evaluateCandidateOrientation',
  'calculateDateConfidence',
  'findBestCandidate',
  'isStrictMatch'
];

function resolveNumericOption(options, runtimeConfig, matchingConfig, optionKey, configKey) {
  return Number(
    options[optionKey]
    ?? runtimeConfig[configKey]
    ?? matchingConfig[configKey]
  );
}

function resolveDateConfidenceBands(options, matchingConfig) {
  if (Array.isArray(options.dateConfidenceBands)) {
    return options.dateConfidenceBands;
  }

  return Array.isArray(matchingConfig.date_confidence_bands)
    ? matchingConfig.date_confidence_bands
    : [];
}

function buildDelegatedMethods(targetKey, methodNames) {
  return Object.fromEntries(
    methodNames.map((methodName) => [
      methodName,
      function delegatedMethod(...args) {
        return this[targetKey][methodName](...args);
      }
    ])
  );
}

class ReconMatchEvaluator {
  constructor(options = {}) {
    const matchingConfig = RECON_CONFIG.matching || {};
    const runtimeConfig = getReconConfigSection(['recon_runtime', 'match_evaluator'], {});

    this.logger = options.logger || console;
    this.teamSimilarity = new ReconTeamSimilarity({
      parser: options.parser || null,
      activeLeagueId: options.activeLeagueId,
      leagueDictionaryEntries: options.leagueDictionaryEntries,
      dictionaryStringContainsLeagueIds: options.dictionaryStringContainsLeagueIds
        ?? runtimeConfig.dictionary_string_contains_league_ids
        ?? [],
      dictionaryStringContainsMinLength: options.dictionaryStringContainsMinLength
        ?? runtimeConfig.dictionary_string_contains_min_length
        ?? 5,
      placeNameEquivalentLeagueIds: options.placeNameEquivalentLeagueIds
        ?? runtimeConfig.place_name_equivalent_league_ids
        ?? []
    });
    this.scoringEngine = new ReconScoringEngine({
      teamSimilarity: this.teamSimilarity,
      mirrorManager: options.mirrorManager || null,
      orientationSimilarityThreshold: resolveNumericOption(
        options,
        runtimeConfig,
        matchingConfig,
        'orientationSimilarityThreshold',
        'orientation_similarity_threshold'
      ),
      exactMatchThreshold: resolveNumericOption(
        options,
        runtimeConfig,
        matchingConfig,
        'exactMatchThreshold',
        'exact_match_threshold'
      ),
      teamWeight: resolveNumericOption(
        options,
        runtimeConfig,
        matchingConfig,
        'teamWeight',
        'team_weight'
      ),
      dateWeight: resolveNumericOption(
        options,
        runtimeConfig,
        matchingConfig,
        'dateWeight',
        'date_weight'
      ),
      teamBalanceWeight: resolveNumericOption(
        options,
        runtimeConfig,
        matchingConfig,
        'teamBalanceWeight',
        'team_balance_weight'
      ),
      perfectKickoffWindowMs: resolveNumericOption(
        options,
        runtimeConfig,
        matchingConfig,
        'perfectKickoffWindowMs',
        'perfect_kickoff_window_ms'
      ),
      dateConfidenceBands: resolveDateConfidenceBands(options, matchingConfig)
    });
  }

  setMirrorManager(mirrorManager) {
    this.scoringEngine.setMirrorManager(mirrorManager);
    return this;
  }

  setLeagueDictionaryEntries(leagueId, entries = []) {
    this.teamSimilarity.setLeagueDictionaryEntries(leagueId, entries);
    return this;
  }

  clearLeagueDictionary() {
    this.teamSimilarity.clearLeagueDictionary();
    return this;
  }
}

Object.assign(
  ReconMatchEvaluator.prototype,
  buildDelegatedMethods('teamSimilarity', TEAM_SIMILARITY_METHODS),
  buildDelegatedMethods('scoringEngine', SCORING_METHODS)
);

Object.defineProperties(ReconMatchEvaluator.prototype, {
  activeLeagueDictionary: {
    get() {
      return this.teamSimilarity.activeLeagueDictionary;
    }
  },
  activeLeagueId: {
    get() {
      return this.teamSimilarity.activeLeagueId;
    }
  },
  dateConfidenceBands: {
    get() {
      return this.scoringEngine.dateConfidenceBands;
    }
  },
  dateWeight: {
    get() {
      return this.scoringEngine.dateWeight;
    }
  },
  dictionaryStringContainsLeagueIds: {
    get() {
      return this.teamSimilarity.dictionaryStringContainsLeagueIds;
    }
  },
  dictionaryStringContainsMinLength: {
    get() {
      return this.teamSimilarity.dictionaryStringContainsMinLength;
    }
  },
  exactMatchThreshold: {
    get() {
      return this.scoringEngine.exactMatchThreshold;
    }
  },
  mirrorManager: {
    get() {
      return this.scoringEngine.mirrorManager;
    }
  },
  orientationSimilarityThreshold: {
    get() {
      return this.scoringEngine.orientationSimilarityThreshold;
    }
  },
  parser: {
    get() {
      return this.teamSimilarity.parser;
    }
  },
  placeNameEquivalentLeagueIds: {
    get() {
      return this.teamSimilarity.placeNameEquivalentLeagueIds;
    }
  },
  teamWeight: {
    get() {
      return this.scoringEngine.teamWeight;
    }
  }
});

module.exports = { ReconMatchEvaluator };
