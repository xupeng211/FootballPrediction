'use strict';

function toMillis(value) {
  if (!value) {
    return Number.NEGATIVE_INFINITY;
  }

  const parsed = new Date(value).getTime();
  return Number.isFinite(parsed) ? parsed : Number.NEGATIVE_INFINITY;
}

function compareRowsForDeduplication(left, right) {
  const updatedDelta = toMillis(right.updated_at) - toMillis(left.updated_at);
  if (updatedDelta !== 0) {
    return updatedDelta;
  }

  const createdDelta = toMillis(right.created_at) - toMillis(left.created_at);
  if (createdDelta !== 0) {
    return createdDelta;
  }

  return String(right.match_id).localeCompare(String(left.match_id));
}

function buildDeduplicationPlan(rows = []) {
  const grouped = new Map();

  for (const row of rows) {
    const season = String(row.season);
    const oddsportalHash = String(row.oddsportal_hash);
    const key = `${season}::${oddsportalHash}`;

    if (!grouped.has(key)) {
      grouped.set(key, []);
    }
    grouped.get(key).push(row);
  }

  return [...grouped.entries()]
    .map(([key, groupRows]) => {
      if (groupRows.length <= 1) {
        return null;
      }

      const [season, oddsportalHash] = key.split('::');
      const ordered = [...groupRows].sort(compareRowsForDeduplication);
      const kept = ordered[0];
      const removed = ordered.slice(1);

      return {
        season,
        oddsportal_hash: oddsportalHash,
        kept_match_id: String(kept.match_id),
        removed_match_ids: removed
          .map((row) => String(row.match_id))
          .sort((left, right) => left.localeCompare(right)),
        removed_count: removed.length
      };
    })
    .filter(Boolean)
    .sort((left, right) => {
      const seasonDelta = left.season.localeCompare(right.season);
      if (seasonDelta !== 0) {
        return seasonDelta;
      }
      return left.oddsportal_hash.localeCompare(right.oddsportal_hash);
    });
}

async function findDuplicateSeasonHashGroups(queryable) {
  const result = await queryable.query(`
    SELECT season, oddsportal_hash, match_id, updated_at, created_at
    FROM matches_oddsportal_mapping
    WHERE (season, oddsportal_hash) IN (
      SELECT season, oddsportal_hash
      FROM matches_oddsportal_mapping
      WHERE oddsportal_hash IS NOT NULL
      GROUP BY season, oddsportal_hash
      HAVING COUNT(*) > 1
    )
      AND oddsportal_hash IS NOT NULL
  `);

  return buildDeduplicationPlan(result.rows || []);
}

async function dedupeMappings({ queryable, logger = { info() {} }, groups = null } = {}) {
  if (!queryable || typeof queryable.query !== 'function') {
    throw new TypeError('dedupeMappings requires a queryable with query(sql, params)');
  }

  const duplicateGroups = Array.isArray(groups)
    ? groups
    : await findDuplicateSeasonHashGroups(queryable);

  let deletedCount = 0;

  for (const group of duplicateGroups) {
    if (!Array.isArray(group.removed_match_ids) || group.removed_match_ids.length === 0) {
      continue;
    }

    const result = await queryable.query(`
      DELETE FROM matches_oddsportal_mapping
      WHERE season = $1
        AND oddsportal_hash = $2
        AND match_id = ANY($3::text[])
    `, [group.season, group.oddsportal_hash, group.removed_match_ids]);

    deletedCount += result.rowCount || 0;
    logger.info('[Repository][DEDUPE] 已清理历史 season/hash 重复映射', {
      season: group.season,
      oddsportal_hash: group.oddsportal_hash,
      kept_match_id: group.kept_match_id,
      removed_match_ids: group.removed_match_ids
    });
  }

  return {
    deletedCount,
    groupCount: duplicateGroups.length,
    groups: duplicateGroups
  };
}

module.exports = {
  buildDeduplicationPlan,
  dedupeMappings,
  findDuplicateSeasonHashGroups
};
