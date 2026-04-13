/* eslint-disable complexity, max-lines */
'use strict';

const { RECON_CONFIG, getReconConfigSection } = require('./ReconServiceConfig');

class ReconMirrorManager {
  constructor(options = {}) {
    const matchingConfig = RECON_CONFIG.matching || {};
    const runtimeConfig = getReconConfigSection(['recon_runtime', 'mirror_manager'], {});

    this.evaluator = options.evaluator || null;
    this.teamWeight = Number(
      options.teamWeight
      ?? runtimeConfig.team_weight
      ?? matchingConfig.team_weight
    );
    this.dateWeight = Number(
      options.dateWeight
      ?? runtimeConfig.date_weight
      ?? matchingConfig.date_weight
    );
  }

  buildSeasonMirror(candidates) {
    const mirror = new Map();

    for (const candidate of Array.isArray(candidates) ? candidates : []) {
      const candidateHome = candidate?.homeTeam || candidate?.home_team;
      const candidateAway = candidate?.awayTeam || candidate?.away_team;
      const dateKey = this.toDateKey(candidate?.matchDate || candidate?.match_date);

      if (!dateKey) {
        continue;
      }

      if (!this.evaluator?.hasTextualTeamName(candidateHome) || !this.evaluator?.hasTextualTeamName(candidateAway)) {
        continue;
      }

      this.appendSeasonMirrorEntry(
        mirror,
        this.composeMirrorKey(candidateHome, candidateAway, dateKey),
        candidate,
        false
      );
      this.appendSeasonMirrorEntry(
        mirror,
        this.composeMirrorKey(candidateAway, candidateHome, dateKey),
        candidate,
        true
      );
    }

    return mirror;
  }

  appendSeasonMirrorEntry(mirror, key, candidate, isReversed) {
    if (!(mirror instanceof Map) || !key) {
      return;
    }

    if (!mirror.has(key)) {
      mirror.set(key, []);
    }

    mirror.get(key).push({
      candidate,
      isReversed: Boolean(isReversed)
    });
  }

  composeMirrorKey(homeTeam, awayTeam, dateKey) {
    const normalizedHome = this.evaluator?.normalizeTeamName(homeTeam);
    const normalizedAway = this.evaluator?.normalizeTeamName(awayTeam);
    const normalizedDate = String(dateKey || '').trim();

    if (!normalizedHome || !normalizedAway || !normalizedDate) {
      return null;
    }

    return `${normalizedHome}__${normalizedAway}__${normalizedDate}`;
  }

  findMirrorCandidate(l1Match, seasonMirror) {
    if (!(seasonMirror instanceof Map) || seasonMirror.size === 0) {
      return null;
    }

    const mirrorKey = this.composeMirrorKey(
      l1Match?.home_team,
      l1Match?.away_team,
      this.toDateKey(l1Match?.match_date)
    );
    if (!mirrorKey) {
      return null;
    }

    const entries = seasonMirror.get(mirrorKey);
    if (!Array.isArray(entries) || entries.length === 0) {
      return null;
    }

    let best = null;

    for (const entry of entries) {
      const resolvedCandidate = this.evaluator?.resolveCandidateTeams(entry.candidate, l1Match);
      if (!resolvedCandidate?.homeTeam || !resolvedCandidate?.awayTeam) {
        continue;
      }

      const orientation = this.evaluator?.evaluateCandidateOrientation(resolvedCandidate, l1Match);
      const isReversed = entry.isReversed === true ? true : Boolean(orientation?.isReversed);
      const teamConfidence = isReversed
        ? orientation?.swappedScore
        : Math.max(orientation?.directScore || 0, orientation?.swappedScore || 0);
      const dateConfidence = this.evaluator?.calculateDateConfidence(
        resolvedCandidate.matchDate || resolvedCandidate.match_date,
        l1Match.match_date
      );
      const confidence = dateConfidence === null
        ? teamConfidence
        : Math.max(0, Math.min(1, (teamConfidence * this.teamWeight) + (dateConfidence * this.dateWeight)));

      if (!best || confidence > best.confidence) {
        best = {
          candidate: resolvedCandidate,
          confidence,
          method: 'season_mirror',
          isReversed
        };
      }
    }

    return best;
  }

  toDateKey(dateInput) {
    if (!dateInput) return null;
    const date = new Date(dateInput);
    if (Number.isNaN(date.getTime())) return null;
    const year = date.getUTCFullYear();
    const month = String(date.getUTCMonth() + 1).padStart(2, '0');
    const day = String(date.getUTCDate()).padStart(2, '0');
    return `${year}${month}${day}`;
  }
}

module.exports = { ReconMirrorManager };
