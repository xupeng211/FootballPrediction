'use strict';

const { Pool } = require('pg');

const POOL_CONFIG = {
  host: process.env.DB_HOST || 'host.docker.internal',
  port: parseInt(process.env.DB_PORT || '5432', 10),
  database: process.env.DB_NAME || 'football_db',
  user: process.env.DB_USER || 'football_user',
  password: process.env.DB_PASSWORD || 'football_pass'
};

const TARGET_SEASON = '2025/2026';
const MIN_CONFIDENCE = parseFloat(process.env.MIN_CONFIDENCE || '0.20');

async function promoteEvidence() {
  const pool = new Pool(POOL_CONFIG);
  try {
    await pool.query('BEGIN');
    const { rows } = await pool.query(`
      SELECT match_id
      FROM matches_oddsportal_mapping
      WHERE season = $1
        AND COALESCE(is_evidence_only, FALSE) = TRUE
        AND match_confidence >= $2
    `, [TARGET_SEASON, MIN_CONFIDENCE]);

    const matchIds = rows.map((row) => row.match_id);
    if (matchIds.length === 0) {
      console.log('promote_recon_evidence: 0 场 evidence 可转正');
      await pool.query('ROLLBACK');
      return;
    }

    await pool.query(`
      UPDATE matches_oddsportal_mapping
      SET is_evidence_only = FALSE,
          status = 'pending',
          updated_at = NOW()
      WHERE match_id = ANY($1)
        AND season = $2
    `, [matchIds, TARGET_SEASON]);

    await pool.query(`
      UPDATE matches
      SET pipeline_status = 'RECON_LINKED',
          updated_at = NOW()
      WHERE match_id = ANY($1)
        AND season = $2
    `, [matchIds, TARGET_SEASON]);

    await pool.query('COMMIT');
    console.log(`promote_recon_evidence: ${matchIds.length} 场 evidence 转正`);
  } catch (error) {
    await pool.query('ROLLBACK');
    console.error('promote_recon_evidence: 失败', error.message);
    process.exitCode = 1;
  } finally {
    await pool.end();
  }
}

void promoteEvidence();
