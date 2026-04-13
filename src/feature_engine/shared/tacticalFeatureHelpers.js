'use strict';

const STATS_MAPPING = {
  'Expected goals (xG)': { home: 'home_xg', away: 'away_xg' },
  'Expected goals': { home: 'home_xg', away: 'away_xg' },
  xG: { home: 'home_xg', away: 'away_xg' },
  xGOT: { home: 'home_xgot', away: 'away_xgot' },
  'Ball possession': { home: 'home_possession', away: 'away_possession' },
  Possession: { home: 'home_possession', away: 'away_possession' },
  'Total shots': { home: 'home_shots', away: 'away_shots' },
  Shots: { home: 'home_shots', away: 'away_shots' },
  'Shots on target': { home: 'home_shots_on_target', away: 'away_shots_on_target' },
  'Shots off target': { home: 'home_shots_off_target', away: 'away_shots_off_target' },
  'Shots inside box': { home: 'home_shots_inside_box', away: 'away_shots_inside_box' },
  'Shots outside box': { home: 'home_shots_outside_box', away: 'away_shots_outside_box' },
  'Blocked shots': { home: 'home_blocked_shots', away: 'away_blocked_shots' },
  'Hit woodwork': { home: 'home_hit_woodwork', away: 'away_hit_woodwork' },
  Corners: { home: 'home_corners', away: 'away_corners' },
  'Corner kicks': { home: 'home_corners', away: 'away_corners' },
  'Free kicks': { home: 'home_free_kicks', away: 'away_free_kicks' },
  Fouls: { home: 'home_fouls', away: 'away_fouls' },
  'Yellow cards': { home: 'home_yellow_cards', away: 'away_yellow_cards' },
  'Red cards': { home: 'home_red_cards', away: 'away_red_cards' },
  Offsides: { home: 'home_offsides', away: 'away_offsides' },
  Passes: { home: 'home_passes', away: 'away_passes' },
  'Accurate passes': { home: 'home_accurate_passes', away: 'away_accurate_passes' },
  'Pass accuracy': { home: 'home_pass_accuracy', away: 'away_pass_accuracy' },
  'Big chances': { home: 'home_big_chances', away: 'away_big_chances' },
  'Counter attacks': { home: 'home_counter_attacks', away: 'away_counter_attacks' }
};

const DEFAULT_STAT_FEATURES = {
  home_xg: 0,
  away_xg: 0,
  home_possession: 50,
  away_possession: 50,
  home_possession_pct: 50,
  away_possession_pct: 50,
  home_shots: 0,
  away_shots: 0,
  home_shots_on_target: 0,
  away_shots_on_target: 0,
  home_corners: 0,
  away_corners: 0,
  home_fouls: 0,
  away_fouls: 0,
  home_yellow_cards: 0,
  away_yellow_cards: 0,
  home_red_cards: 0,
  away_red_cards: 0,
  home_big_chances: 0,
  away_big_chances: 0
};

function parseStatValue(value) {
  if (value === null || value === undefined) {
    return 0;
  }
  if (typeof value === 'number') {
    return value;
  }
  if (typeof value === 'string') {
    const normalized = value.includes('%') ? value.replace('%', '') : value;
    const parsed = parseFloat(normalized);
    return Number.isNaN(parsed) ? 0 : parsed;
  }
  return 0;
}

function parsePercentage(value) {
  if (typeof value === 'number') {
    return value > 1 ? value : value * 100;
  }
  return 50;
}

function createDefaultStatsFeatures() {
  return { ...DEFAULT_STAT_FEATURES };
}

function applyMappedStat(features, mapping, values = []) {
  if (!mapping) {
    return;
  }
  features[mapping.home] = parseStatValue(values[0]);
  features[mapping.away] = parseStatValue(values[1]);
}

function extractStatsFromArray(statsArray, mapping = STATS_MAPPING) {
  const features = {};

  for (const statItem of Array.isArray(statsArray) ? statsArray : []) {
    const statName = statItem?.title || '';
    const values = Array.isArray(statItem?.stats) ? statItem.stats : null;
    if (values) {
      if (values.length > 0 && typeof values[0] === 'object') {
        for (const subStat of values) {
          applyMappedStat(features, mapping[subStat?.title], subStat?.stats);
        }
      } else {
        applyMappedStat(features, mapping[statName], values);
      }
    }

    if (statItem?.home !== undefined && statItem?.away !== undefined) {
      applyMappedStat(features, mapping[statName], [statItem.home, statItem.away]);
    }
  }

  if (features.home_possession !== undefined) {
    features.home_possession_pct = parsePercentage(features.home_possession);
  }
  if (features.away_possession !== undefined) {
    features.away_possession_pct = parsePercentage(features.away_possession);
  }

  return features;
}

function resolveMomentumData(rawData, safeGetFn, isObjectFn) {
  let momentum = safeGetFn(rawData, 'content.momentum.main.data', null);
  if (Array.isArray(momentum)) {
    return momentum;
  }

  momentum = safeGetFn(rawData, 'content.momentum.data', null);
  if (Array.isArray(momentum)) {
    return momentum;
  }

  const momentumObj = safeGetFn(rawData, 'content.momentum', null);
  if (!momentumObj || !isObjectFn(momentumObj)) {
    return null;
  }

  return safeGetFn(momentumObj, 'data', null) || safeGetFn(momentumObj, 'main.data', null) || null;
}

function extractMomentumValues(momentum = [], readValue) {
  return momentum
    .map((item) => readValue(item))
    .filter((value) => !Number.isNaN(value));
}

function assignMomentumSegmentFeatures(features, momentum = [], segmentCount, readValue) {
  const normalizedSegments = Math.max(1, Number(segmentCount || 1));
  const segmentSize = Math.ceil(momentum.length / normalizedSegments);

  for (let index = 0; index < normalizedSegments; index++) {
    const segment = momentum.slice(index * segmentSize, (index + 1) * segmentSize);
    const values = extractMomentumValues(segment, readValue);
    if (values.length === 0) {
      continue;
    }

    const mean = values.reduce((sum, value) => sum + value, 0) / values.length;
    const variance = values.reduce((sum, value) => sum + ((value - mean) ** 2), 0) / values.length;
    const std = Math.sqrt(variance);
    const prefix = `momentum_seg${index + 1}`;

    features[`${prefix}_mean`] = Math.round(mean * 100) / 100;
    features[`${prefix}_std`] = Math.round(std * 100) / 100;
    features[`${prefix}_dominance`] = Math.max(0, Math.min(100, Math.round((mean + 100) / 2)));
    features[`${prefix}_samples`] = values.length;
  }
}

function assignMomentumSummary(features, values = []) {
  if (values.length === 0) {
    return;
  }

  const overallMean = values.reduce((sum, value) => sum + value, 0) / values.length;
  features.momentum_overall_mean = Math.round(overallMean * 100) / 100;
  features.momentum_direction = overallMean > 10
    ? 'home_dominant'
    : overallMean < -10
      ? 'away_dominant'
      : 'balanced';

  const halfPoint = Math.floor(values.length / 2);
  const firstHalf = values.slice(0, halfPoint);
  const secondHalf = values.slice(halfPoint);
  if (firstHalf.length === 0 || secondHalf.length === 0) {
    return;
  }

  const firstMean = firstHalf.reduce((sum, value) => sum + value, 0) / firstHalf.length;
  const secondMean = secondHalf.reduce((sum, value) => sum + value, 0) / secondHalf.length;
  features.momentum_trend = Math.round((secondMean - firstMean) * 100) / 100;
}

function applyMomentumFallback(features, segmentCount, dominance = 50) {
  const normalizedSegments = Math.max(1, Number(segmentCount || 1));
  features.has_momentum_data = false;
  features.momentum_samples_count = 0;
  features.momentum_direction = 'unknown';
  features.momentum_trend = 0;
  features.momentum_overall_mean = 0;

  for (let index = 1; index <= normalizedSegments; index++) {
    features[`momentum_seg${index}_mean`] = 0;
    features[`momentum_seg${index}_std`] = 0;
    features[`momentum_seg${index}_dominance`] = dominance;
    features[`momentum_seg${index}_samples`] = 0;
  }
}

function buildXgFeatures(features) {
  const homeXg = features.home_xg || 0;
  const awayXg = features.away_xg || 0;
  const homeShots = features.home_shots || 0;
  const awayShots = features.away_shots || 0;
  return {
    total_xg: homeXg + awayXg,
    xg_diff: homeXg - awayXg,
    xg_ratio: awayXg > 0 ? homeXg / awayXg : (homeXg > 0 ? 99 : 1),
    home_xg_per_shot: homeShots > 0 ? homeXg / homeShots : 0,
    away_xg_per_shot: awayShots > 0 ? awayXg / awayShots : 0
  };
}

function buildPossessionFeatures(features) {
  const homePossession = features.home_possession_pct || 50;
  const awayPossession = features.away_possession_pct || 50;
  return {
    possession_diff: homePossession - awayPossession,
    possession_ratio: awayPossession > 0 ? homePossession / awayPossession : 1
  };
}

function buildShotFeatures(features) {
  const homeShots = features.home_shots || 0;
  const awayShots = features.away_shots || 0;
  const homeShotsOnTarget = features.home_shots_on_target || 0;
  const awayShotsOnTarget = features.away_shots_on_target || 0;
  return {
    home_shot_accuracy: homeShots > 0 ? homeShotsOnTarget / homeShots : 0,
    away_shot_accuracy: awayShots > 0 ? awayShotsOnTarget / awayShots : 0,
    shots_on_target_diff: homeShotsOnTarget - awayShotsOnTarget
  };
}

function buildSetPieceFeatures(features) {
  const homeCorners = features.home_corners || 0;
  const awayCorners = features.away_corners || 0;
  const homeFouls = features.home_fouls || 0;
  const awayFouls = features.away_fouls || 0;
  return {
    corners_diff: homeCorners - awayCorners,
    total_corners: homeCorners + awayCorners,
    fouls_diff: homeFouls - awayFouls,
    total_fouls: homeFouls + awayFouls
  };
}

function buildDisciplineFeatures(features) {
  const homeYellows = features.home_yellow_cards || 0;
  const awayYellows = features.away_yellow_cards || 0;
  const homeReds = features.home_red_cards || 0;
  const awayReds = features.away_red_cards || 0;
  const home_discipline_score = 10 - (homeYellows * 0.5 + homeReds * 2);
  const away_discipline_score = 10 - (awayYellows * 0.5 + awayReds * 2);
  return {
    home_discipline_score,
    away_discipline_score,
    discipline_diff: home_discipline_score - away_discipline_score
  };
}

function buildChanceAndStrengthFeatures(features) {
  const homeXg = features.home_xg || 0;
  const awayXg = features.away_xg || 0;
  const homeShotsOnTarget = features.home_shots_on_target || 0;
  const awayShotsOnTarget = features.away_shots_on_target || 0;
  const homePossession = features.home_possession_pct || 50;
  const awayPossession = features.away_possession_pct || 50;
  const homeBigChances = features.home_big_chances || 0;
  const awayBigChances = features.away_big_chances || 0;
  const home_strength_index = Math.round((homeXg * 30) + (homeShotsOnTarget * 5) + (homePossession * 0.2) + (homeBigChances * 10));
  const away_strength_index = Math.round((awayXg * 30) + (awayShotsOnTarget * 5) + (awayPossession * 0.2) + (awayBigChances * 10));
  return {
    big_chances_diff: homeBigChances - awayBigChances,
    home_strength_index,
    away_strength_index,
    strength_diff: home_strength_index - away_strength_index
  };
}

function calculateAdvancedFeatures(features) {
  return {
    ...buildXgFeatures(features),
    ...buildPossessionFeatures(features),
    ...buildShotFeatures(features),
    ...buildSetPieceFeatures(features),
    ...buildDisciplineFeatures(features),
    ...buildChanceAndStrengthFeatures(features)
  };
}

module.exports = {
  STATS_MAPPING,
  applyMomentumFallback,
  assignMomentumSegmentFeatures,
  assignMomentumSummary,
  calculateAdvancedFeatures,
  createDefaultStatsFeatures,
  extractMomentumValues,
  extractStatsFromArray,
  resolveMomentumData
};
