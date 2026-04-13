'use strict';

function splitCandidateNamePair(candidateName) {
  const cleanValue = String(candidateName || '').trim();
  if (!cleanValue) {
    return null;
  }

  const parts = cleanValue.split(/\s+vs\s+/i).map((item) => item.trim()).filter(Boolean);
  if (parts.length !== 2) {
    return null;
  }

  return {
    left: parts[0],
    right: parts[1]
  };
}

function decodeSlugName(slug) {
  return String(slug || '')
    .split('-')
    .filter(Boolean)
    .map((part) => (/^[a-z]{1,3}$/i.test(part) ? part.toUpperCase() : `${part.charAt(0).toUpperCase()}${part.slice(1)}`))
    .join(' ')
    .trim();
}

function decodeRemoteTeamSegment(segment, fallbackName = null) {
  const cleanSegment = String(segment || '').trim();
  if (!cleanSegment) {
    return null;
  }

  const match = cleanSegment.match(/^(.*)-([A-Za-z0-9]{8})$/);
  if (!match) {
    return null;
  }

  return {
    remoteHash: match[2],
    remoteName: String(fallbackName || decodeSlugName(match[1])).trim(),
    remoteSegment: cleanSegment
  };
}

function buildRemoteEvidenceKey(remoteEntry, parser) {
  const normalizedRemoteName = parser?.normalizeTeamName?.(remoteEntry?.remoteName || '')
    || String(remoteEntry?.remoteName || '').trim();
  if (!normalizedRemoteName) {
    return remoteEntry?.remoteHash ? String(remoteEntry.remoteHash).trim().toLowerCase() : null;
  }

  return normalizedRemoteName.toLowerCase();
}

function upsertRemoteEvidence(map, remoteEntry, evidenceUrl, parser) {
  if (!remoteEntry?.remoteName) {
    return;
  }

  const remoteKey = buildRemoteEvidenceKey(remoteEntry, parser);
  if (!remoteKey) {
    return;
  }

  const existing = map.get(remoteKey);
  if (!existing) {
    map.set(remoteKey, {
      remoteHash: remoteEntry.remoteHash,
      remoteName: remoteEntry.remoteName,
      remoteSegment: remoteEntry.remoteSegment,
      evidenceUrl: evidenceUrl || null,
      source: 'mapping_candidates'
    });
    return;
  }

  if (remoteEntry.remoteName.length > existing.remoteName.length) {
    existing.remoteName = remoteEntry.remoteName;
  }
  if (!existing.evidenceUrl && evidenceUrl) {
    existing.evidenceUrl = evidenceUrl;
  }
}

function findBestLocalTeamMatch(remoteName, localTeams, parser) {
  let bestMatch = null;

  for (const localTeam of Array.isArray(localTeams) ? localTeams : []) {
    const score = Number(parser.calculateSimilarity(remoteName, localTeam.team_name) || 0);
    if (!bestMatch || score > bestMatch.score) {
      bestMatch = {
        teamId: String(localTeam.team_id),
        teamName: String(localTeam.team_name),
        score
      };
    }
  }

  return bestMatch;
}

function buildSplitCandidate(parts, index, localTeams, parser) {
  const leftRemoteName = decodeSlugName(parts.slice(0, index).join('-'));
  const rightRemoteName = decodeSlugName(parts.slice(index).join('-'));
  const leftMatch = findBestLocalTeamMatch(leftRemoteName, localTeams, parser);
  const rightMatch = findBestLocalTeamMatch(rightRemoteName, localTeams, parser);
  if (!leftMatch || !rightMatch || leftMatch.teamId === rightMatch.teamId) {
    return null;
  }

  const exactBonus = (
    parser.normalizeTeamName(leftRemoteName) === parser.normalizeTeamName(leftMatch.teamName) ? 0.05 : 0
  ) + (
    parser.normalizeTeamName(rightRemoteName) === parser.normalizeTeamName(rightMatch.teamName) ? 0.05 : 0
  );
  const averageScore = (leftMatch.score + rightMatch.score) / 2;
  return {
    averageScore,
    minScore: Math.min(leftMatch.score, rightMatch.score),
    totalScore: averageScore + exactBonus,
    leftRemoteName,
    rightRemoteName
  };
}

function findBestStandardUrlSplit(matchSlug, localTeams, parser) {
  const parts = String(matchSlug || '').split('-').filter(Boolean);
  if (parts.length < 2) {
    return null;
  }

  let bestSplit = null;
  for (let index = 1; index < parts.length; index++) {
    const splitCandidate = buildSplitCandidate(parts, index, localTeams, parser);
    if (!splitCandidate) {
      continue;
    }

    if (
      !bestSplit
      || splitCandidate.totalScore > bestSplit.totalScore
      || (splitCandidate.totalScore === bestSplit.totalScore && splitCandidate.minScore > bestSplit.minScore)
    ) {
      bestSplit = splitCandidate;
    }
  }

  if (!bestSplit || bestSplit.averageScore < 0.78 || bestSplit.minScore < 0.65) {
    return null;
  }

  return bestSplit;
}

function appendParsedUrlNames(names, url, parser, localTeams) {
  const parsedUrl = parser?.parseMatchUrl?.(url) || {};
  if (!parsedUrl.homeTeam || parsedUrl.homeTeam === 'Unknown' || !parsedUrl.awayTeam || parsedUrl.awayTeam === 'Unknown') {
    return;
  }

  const parsedAverage = (
    Number(parser.calculateSimilarity(parsedUrl.homeTeam, findBestLocalTeamMatch(parsedUrl.homeTeam, localTeams, parser)?.teamName || '') || 0)
    + Number(parser.calculateSimilarity(parsedUrl.awayTeam, findBestLocalTeamMatch(parsedUrl.awayTeam, localTeams, parser)?.teamName || '') || 0)
  ) / 2;
  if (parsedAverage >= 0.85) {
    names.push(parsedUrl.homeTeam, parsedUrl.awayTeam);
  }
}

function dedupeRemoteNames(names, parser) {
  const dedupedNames = [];
  const seen = new Set();
  for (const rawName of names) {
    const cleanName = String(rawName || '').trim();
    if (!cleanName) {
      continue;
    }

    const dedupeKey = String(parser?.normalizeTeamName?.(cleanName) || cleanName).toLowerCase();
    if (!dedupeKey || seen.has(dedupeKey)) {
      continue;
    }

    seen.add(dedupeKey);
    dedupedNames.push(cleanName);
  }

  return dedupedNames;
}

function parseStandardMatchUrlEvidence(url, candidateName, parser, localTeams) {
  const path = (() => {
    try {
      return new URL(url).pathname;
    } catch {
      return '';
    }
  })();
  if (!path || /\/football\/h2h\//i.test(path)) {
    return [];
  }

  const lastSegment = String(path).replace(/\/+$/, '').split('/').filter(Boolean).pop() || '';
  const match = lastSegment.match(/^(.*)-([A-Za-z0-9]{8})$/);
  if (!match) {
    return [];
  }

  const names = [];
  const pair = splitCandidateNamePair(candidateName);
  if (pair?.left && pair?.right) {
    names.push(pair.left, pair.right);
  }

  const bestSplit = findBestStandardUrlSplit(match[1], localTeams, parser);
  if (bestSplit?.leftRemoteName && bestSplit?.rightRemoteName) {
    names.push(bestSplit.leftRemoteName, bestSplit.rightRemoteName);
  } else {
    appendParsedUrlNames(names, url, parser, localTeams);
  }

  return dedupeRemoteNames(names, parser).map((remoteName) => ({
    remoteHash: null,
    remoteName,
    remoteSegment: lastSegment
  }));
}

function mergeStandardUrlEvidence(teamsByHash, row, parser, localTeams) {
  const standardTeams = parseStandardMatchUrlEvidence(row.full_url, row.candidate_name, parser, localTeams);
  for (const remoteEntry of standardTeams) {
    upsertRemoteEvidence(teamsByHash, remoteEntry, row.full_url, parser);
  }
}

async function loadRemoteTeamsFromMappingEvidence(pool, leagueId, season, parser, localTeams) {
  const matchIdPrefix = `${Number(leagueId)}_%`;
  const result = await pool.query(`
    SELECT full_url, candidate_name, match_confidence
    FROM matches_oddsportal_mapping
    WHERE match_id LIKE $1
      AND season = $2
      AND full_url LIKE 'https://www.oddsportal.com/football/%'
    ORDER BY match_confidence DESC NULLS LAST, updated_at DESC NULLS LAST, created_at DESC NULLS LAST
  `, [matchIdPrefix, season]);

  const teamsByHash = new Map();
  for (const row of result.rows || []) {
    const url = String(row.full_url || '').trim();
    const path = (() => {
      try {
        return new URL(url).pathname;
      } catch {
        return '';
      }
    })();
    const match = path.match(/\/football\/h2h\/([^/]+)\/([^/]+)\/?$/i);
    if (!match) {
      mergeStandardUrlEvidence(teamsByHash, row, parser, localTeams);
      continue;
    }

    const pair = splitCandidateNamePair(row.candidate_name);
    upsertRemoteEvidence(teamsByHash, decodeRemoteTeamSegment(match[1], pair?.left || null), url, parser);
    upsertRemoteEvidence(teamsByHash, decodeRemoteTeamSegment(match[2], pair?.right || null), url, parser);
  }

  return [...teamsByHash.values()].sort((left, right) => left.remoteName.localeCompare(right.remoteName));
}

function buildClosedSpaceAssignments(remoteTeams, localTeams, parser, threshold) {
  const candidatePairs = [];

  for (const remote of remoteTeams) {
    for (const local of localTeams) {
      const score = Number(parser.calculateSimilarity(remote.remoteName, local.team_name) || 0);
      if (score >= threshold) {
        candidatePairs.push({
          remoteHash: remote.remoteHash || null,
          remoteName: remote.remoteName,
          remoteSegment: remote.remoteSegment || null,
          evidenceUrl: remote.evidenceUrl || remote.teamUrl || null,
          localTeamId: String(local.team_id),
          localTeamName: local.team_name,
          score
        });
      }
    }
  }

  candidatePairs.sort((left, right) => (
    right.score - left.score
    || left.remoteName.localeCompare(right.remoteName)
    || left.localTeamName.localeCompare(right.localTeamName)
  ));

  const usedRemote = new Set();
  const usedLocal = new Set();
  const assignments = [];
  for (const candidate of candidatePairs) {
    const remoteKey = String(candidate.remoteHash || candidate.remoteName).toLowerCase();
    const localKey = String(candidate.localTeamId);
    if (usedRemote.has(remoteKey) || usedLocal.has(localKey)) {
      continue;
    }

    usedRemote.add(remoteKey);
    usedLocal.add(localKey);
    assignments.push(candidate);
  }

  return {
    assignments,
    unresolvedRemote: remoteTeams.filter((remote) => !usedRemote.has(String(remote.remoteHash || remote.remoteName).toLowerCase())),
    unresolvedLocal: localTeams.filter((local) => !usedLocal.has(String(local.team_id)))
  };
}

function printAssignments(assignments) {
  console.log('\n[字典预览]');
  for (const item of assignments) {
    console.log(
      `- ${item.remoteName.padEnd(24)} -> ${String(item.localTeamName).padEnd(24)} ` +
      `(team_id=${item.localTeamId}, score=${item.score.toFixed(2)}, hash=${item.remoteHash || 'n/a'})`
    );
  }
}

module.exports = {
  loadRemoteTeamsFromMappingEvidence,
  buildClosedSpaceAssignments,
  printAssignments
};
