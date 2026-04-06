'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');

const { ReconEngine } = require('../../src/infrastructure/recon/ReconEngine');

describe('Recon League Dictionary Flow', () => {
  it('应在 runReconMatrix 前预热联赛字典并将短名 h2h 候选洗白后提升为 RECON_LINKED', async () => {
    const savedMappings = [];

    const engine = new ReconEngine({
      configManager: {
        getActiveLeagues() {
          return [
            { id: 140, name: 'Segunda División', country: 'spain', slug: 'segunda-division', enabled: true }
          ];
        }
      },
      repository: {
        async getReconEligibleMatches() {
          return [
            {
              match_id: '140_20252026_4837844',
              home_team: 'Sporting Gijon',
              away_team: 'Deportivo La Coruna',
              league_name: 'Segunda División',
              season: '2025/2026',
              pipeline_status: 'harvested',
              match_date: '2026-04-05T18:00:00.000Z'
            }
          ];
        },
        async getLeagueDictionaryEntries() {
          return [
            {
              league_id: 140,
              remote_name: 'Gijon',
              local_team_id: '9869',
              local_team_name: 'Sporting Gijon'
            },
            {
              league_id: 140,
              remote_name: 'Dep La Coruna',
              local_team_id: '9783',
              local_team_name: 'Deportivo La Coruna'
            }
          ];
        },
        async batchSaveOddsPortalMappings(mappings) {
          savedMappings.push(...mappings);
          return { success: true, inserted: mappings.length, updated: 0 };
        },
        async batchUpdateMatchPipelineStatus(matchIds) {
          return { updated: matchIds.length };
        },
        async batchSaveMismatchEvidence() {
          return { success: true, saved: 0 };
        }
      },
      navigator: {
        async protocolArchiveExtract() {
          return {
            matches: [
              {
                hash: '23spHYrm',
                url: 'https://www.oddsportal.com/football/h2h/gijon-69w4Rb2d/dep-la-coruna-Q51ZzMS6/#23spHYrm',
                homeTeam: 'Gijon',
                awayTeam: 'Dep La Coruna',
                matchDate: '2026-01-01T00:00:00.000Z'
              }
            ],
            pagesScanned: 1,
            totalCandidates: 1
          };
        }
      },
      parser: {
        calculateSimilarity(left, right) {
          return String(left || '').toLowerCase().trim() === String(right || '').toLowerCase().trim() ? 1 : 0;
        }
      },
      logger: { info() {}, warn() {}, error() {} },
      baseUrl: 'oddsportal://root'
    });

    const result = await engine.runReconMatrix({
      season: '2025-2026',
      confidenceThreshold: 0.75,
      concurrency: 1
    });

    assert.equal(result.success, true);
    assert.equal(result.linked, 1);
    assert.equal(result.mismatched, 0);
    assert.equal(savedMappings.length, 1);
    assert.equal(savedMappings[0].match_id, '140_20252026_4837844');
    assert.equal(savedMappings[0].oddsportal_hash, '23spHYrm');
    assert.equal(savedMappings[0].match_confidence, 1);
    assert.doesNotMatch(savedMappings[0].full_url, /\/h2h\//);
    assert.match(savedMappings[0].full_url, /-23spHYrm\/$/);
  });

  it('SOURCE_EMPTY 且仅剩 RECON_MISMATCH 时也应先回源一次，再走本地字典自愈', async () => {
    const savedMappings = [];
    let navigatorCalls = 0;

    const engine = new ReconEngine({
      configManager: {
        getActiveLeagues() {
          return [
            { id: 140, name: 'Segunda División', country: 'spain', slug: 'segunda-division', enabled: true }
          ];
        }
      },
      repository: {
        async getReconEligibleMatches() {
          return [
            {
              match_id: '140_20252026_4837532',
              home_team: 'Deportivo La Coruna',
              away_team: 'Sporting Gijon',
              league_name: 'Segunda División',
              season: '2025/2026',
              pipeline_status: 'RECON_MISMATCH',
              match_date: '2026-04-05T18:00:00.000Z'
            }
          ];
        },
        async getLeagueDictionaryEntries() {
          return [
            {
              league_id: 140,
              remote_name: 'DEP LA Coruna',
              local_team_id: '9783',
              local_team_name: 'Deportivo La Coruna'
            },
            {
              league_id: 140,
              remote_name: 'Gijon',
              local_team_id: '9869',
              local_team_name: 'Sporting Gijon'
            }
          ];
        },
        async batchSaveOddsPortalMappings(mappings) {
          savedMappings.push(...mappings);
          return { success: true, inserted: mappings.length, updated: 0 };
        },
        async batchUpdateMatchPipelineStatus(matchIds) {
          return { updated: matchIds.length };
        },
        async batchSaveMismatchEvidence() {
          return { success: true, saved: 0 };
        }
      },
      navigator: {
        async protocolArchiveExtract() {
          navigatorCalls++;
          return {
            matches: [],
            pagesScanned: 0,
            totalCandidates: 0,
            sourceState: 'SOURCE_EMPTY'
          };
        }
      },
      parser: {
        calculateSimilarity(left, right) {
          return String(left || '').toLowerCase().trim() === String(right || '').toLowerCase().trim() ? 1 : 0;
        }
      },
      logger: { info() {}, warn() {}, error() {} },
      baseUrl: 'oddsportal://root'
    });

    const result = await engine.runReconMatrix({
      season: '2025-2026',
      confidenceThreshold: 0.75,
      concurrency: 1
    });

    assert.equal(result.success, true);
    assert.equal(result.linked, 1);
    assert.equal(result.mismatched, 0);
    assert.equal(navigatorCalls, 1);
    assert.equal(savedMappings.length, 1);
    assert.equal(savedMappings[0].mapping_method, 'dictionary');
    assert.equal(savedMappings[0].match_confidence, 1);
    assert.match(savedMappings[0].oddsportal_hash, /^~/);
    assert.match(savedMappings[0].full_url, /^dictionary:\/\/recon\/140\/2025%2F2026\//);
  });

  it('应支持组合对阵与占位赛程在先回源后通过本地字典候选完成自愈', async () => {
    const savedMappings = [];
    let navigatorCalls = 0;

    const engine = new ReconEngine({
      configManager: {
        getActiveLeagues() {
          return [
            { id: 42, name: 'Champions League', country: 'europe', slug: 'champions-league', enabled: true }
          ];
        }
      },
      repository: {
        async getReconEligibleMatches() {
          return [
            {
              match_id: '42_20252026_5205814',
              home_team: 'Sporting Cp Arsenal',
              away_team: 'Barcelona Atletico Madrid',
              league_name: 'Champions League',
              season: '2025/2026',
              pipeline_status: 'RECON_MISMATCH',
              match_date: '2026-04-05T18:00:00.000Z'
            },
            {
              match_id: '42_20252026_5205834',
              home_team: 'Winner SF 1',
              away_team: 'Winner SF 2',
              league_name: 'Champions League',
              season: '2025/2026',
              pipeline_status: 'RECON_MISMATCH',
              match_date: '2026-05-10T18:00:00.000Z'
            }
          ];
        },
        async getLeagueDictionaryEntries() {
          return [
            {
              league_id: 42,
              remote_name: 'Sporting CP',
              local_team_id: '9768',
              local_team_name: 'Sporting CP'
            },
            {
              league_id: 42,
              remote_name: 'Arsenal',
              local_team_id: '9825',
              local_team_name: 'Arsenal'
            },
            {
              league_id: 42,
              remote_name: 'Barcelona',
              local_team_id: '8634',
              local_team_name: 'Barcelona'
            },
            {
              league_id: 42,
              remote_name: 'ATL Madrid',
              local_team_id: '9906',
              local_team_name: 'Atletico Madrid'
            }
          ];
        },
        async batchSaveOddsPortalMappings(mappings) {
          savedMappings.push(...mappings);
          return { success: true, inserted: mappings.length, updated: 0 };
        },
        async batchUpdateMatchPipelineStatus(matchIds) {
          return { updated: matchIds.length };
        },
        async batchSaveMismatchEvidence() {
          return { success: true, saved: 0 };
        }
      },
      navigator: {
        async protocolArchiveExtract() {
          navigatorCalls++;
          return {
            matches: [],
            pagesScanned: 0,
            totalCandidates: 0,
            sourceState: 'SOURCE_EMPTY'
          };
        }
      },
      parser: {
        calculateSimilarity(left, right) {
          return String(left || '').toLowerCase().trim() === String(right || '').toLowerCase().trim() ? 1 : 0;
        }
      },
      logger: { info() {}, warn() {}, error() {} },
      baseUrl: 'oddsportal://root'
    });

    const result = await engine.runReconMatrix({
      season: '2025-2026',
      confidenceThreshold: 0.75,
      concurrency: 1
    });

    assert.equal(result.success, true);
    assert.equal(result.linked, 2);
    assert.equal(result.mismatched, 0);
    assert.equal(navigatorCalls, 1);
    assert.equal(savedMappings.length, 2);
    assert.equal(savedMappings[0].mapping_method, 'dictionary');
    assert.equal(savedMappings[0].match_confidence, 1);
    assert.equal(savedMappings[1].mapping_method, 'exact');
    assert.equal(savedMappings[1].match_confidence, 1);
  });
});
