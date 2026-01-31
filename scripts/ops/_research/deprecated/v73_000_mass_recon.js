/**
 * V73.000 - Mass Hash Reconnaissance
 * =====================================
 *
 * 直接在 matches 和 matches_mapping 表之间进行模糊匹配，
 * 通过队名相似度发现缺失的映射。
 *
 * @file v73_000_mass_recon.js
 * @version V73.000
 * @since 2026-01-25
 */

'use strict';

const { Pool } = require('pg');
const path = require('path');

// ============================================================================
// CONFIGURATION
// ============================================================================

const RECON_CONFIG = {
    fuzzyThreshold: 70.0,  // 进一步降低阈值（75% -> 70%）
    batchSize: 100,

    // 队名标准化映射（处理常见别名）
    teamNormalizations: {
        // 英超
        'Man Utd': 'Manchester United',
        'Man United': 'Manchester United',
        'Man City': 'Manchester City',
        'Wolves': 'Wolverhampton Wanderers',
        'Spurs': 'Tottenham Hotspur',
        'Newcastle': 'Newcastle United',
        'West Ham': 'West Ham United',
        'Brighton': 'Brighton & Hove Albion',
        'Leicester': 'Leicester City',
        'Leeds': 'Leeds United',
        'Norwich': 'Norwich City',
        'Burnley': 'Burnley',
        'Watford': 'Watford',
        'Brentford': 'Brentford',
        'Fulham': 'Fulham',
        'Aston Villa': 'Aston Villa',
        'Crystal Palace': 'Crystal Palace',
        'Everton': 'Everton',
        'Southampton': 'Southampton',
        'Bournemouth': 'AFC Bournemouth',
        'Nottm Forest': 'Nottingham Forest',
        'Luton': 'Luton Town',
        'Sheffield Utd': 'Sheffield United',
        // 西甲
        'Real Madrid': 'Real Madrid',
        'Barcelona': 'Barcelona',
        'Atletico': 'Atletico Madrid',
        'Atleti': 'Atletico Madrid',
        'Sevilla': 'Sevilla',
        'Real Betis': 'Real Betis',
        'Real Sociedad': 'Real Sociedad',
        'Athletic Club': 'Athletic Bilbao',
        'Valencia': 'Valencia',
        'Villarreal': 'Villarreal',
        'Real Valladolid': 'Real Valladolid',
        'Celta Vigo': 'Celta Vigo',
        'Osasuna': 'Osasuna',
        'Getafe': 'Getafe',
        'Alaves': 'Deportivo Alaves',
        'Espanyol': 'Espanyol',
        'Elche': 'Elche',
        'Cadiz': 'Cadiz',
        'Mallorca': 'Mallorca',
        'Rayo': 'Rayo Vallecano',
        'Almeria': 'Almeria',
        'Las Palmas': 'Las Palmas',
        'Girona': 'Girona',
        'Leganes': 'Leganes',
        'Huesca': 'Huesca',
        // 意甲
        'Juventus': 'Juventus',
        'Juve': 'Juventus',
        'Inter': 'Inter Milan',
        'Milan': 'AC Milan',
        'Napoli': 'Napoli',
        'Roma': 'AS Roma',
        'Lazio': 'Lazio',
        'Atalanta': 'Atalanta',
        'Fiorentina': 'Fiorentina',
        'Torino': 'Torino',
        'Bologna': 'Bologna',
        'Sassuolo': 'Sassuolo',
        'Udinese': 'Udinese',
        'Sampdoria': 'Sampdoria',
        'Genoa': 'Genoa',
        'Cagliari': 'Cagliari',
        'Verona': 'Hellas Verona',
        'Parma': 'Parma',
        'Benevento': 'Benevento',
        'Salernitana': 'Salernitana',
        'Venezia': 'Venezia',
        'Empoli': 'Empoli',
        'Lecce': 'Lecce',
        'Monza': 'Monza',
        'Cremonese': 'Cremonese',
        // 德甲
        'Bayern Munich': 'Bayern Munich',
        'Bayern': 'Bayern Munich',
        'Dortmund': 'Borussia Dortmund',
        'Leverkusen': 'Bayer Leverkusen',
        'RB Leipzig': 'RB Leipzig',
        'Frankfurt': 'Eintracht Frankfurt',
        'Wolfsburg': 'VfL Wolfsburg',
        'Freiburg': 'Freiburg',
        'Mainz': 'Mainz',
        'Borussia M': 'Borussia Monchengladbach',
        "Gladbach": 'Borussia Monchengladbach',
        'Union Berlin': 'Union Berlin',
        'Koln': 'FC Cologne',
        'Hoffenheim': 'Hoffenheim',
        'Stuttgart': 'Stuttgart',
        'Augsburg': 'Augsburg',
        'Bielefeld': 'Arminia Bielefeld',
        'Greuther Furth': 'Greuther Furth',
        'Hertha': 'Hertha Berlin',
        'Darmstadt': 'Darmstadt',
        'Heidenheim': 'Heidenheim',
        'Bochum': 'Bochum',
        // 法甲
        'PSG': 'Paris Saint-Germain',
        'Paris': 'Paris Saint-Germain',
        'Monaco': 'Monaco',
        'Lyon': 'Lyon',
        'Marseille': 'Marseille',
        'Lille': 'Lille',
        'Lens': 'Lens',
        'Nice': 'Nice',
        'Rennes': 'Rennes',
        'Strasbourg': 'Strasbourg',
        'Toulouse': 'Toulouse',
        'Nantes': 'Nantes',
        'Montpellier': 'Montpellier',
        'Brest': 'Brest',
        'Reims': 'Reims',
        'Lorient': 'Lorient',
        'Clermont': 'Clermont',
        'Troyes': 'Troyes',
        'Ajaccio': 'Ajaccio',
        'Le Havre': 'Le Havre',
        'Metz': 'Metz',
    },

    db: {
        host: process.env.DB_HOST || '172.25.16.1',
        port: parseInt(process.env.DB_PORT) || 5432,
        database: process.env.DB_NAME || 'football_db',
        user: process.env.DB_USER || 'football_user',
        password: process.env.DB_PASSWORD || 'football_pass',
        max: 20
    }
};

// ============================================================================
// LEVENSHTEIN DISTANCE
// ============================================================================

/**
 * 标准化队名（处理常见别名）
 * @param {string} teamName - 原始队名
 * @returns {string} - 标准化后的队名
 */
function normalizeTeamName(teamName) {
    if (!teamName) return '';
    const normalized = teamName.trim();
    return RECON_CONFIG.teamNormalizations[normalized] || normalized;
}

function levenshtein(a, b) {
    const matrix = [];
    for (let i = 0; i <= b.length; i++) matrix[i] = [i];
    for (let j = 0; j <= a.length; j++) matrix[0][j] = j;

    for (let i = 1; i <= b.length; i++) {
        for (let j = 1; j <= a.length; j++) {
            if (b.charAt(i - 1) === a.charAt(j - 1)) {
                matrix[i][j] = matrix[i - 1][j - 1];
            } else {
                matrix[i][j] = Math.min(
                    matrix[i - 1][j - 1] + 1,
                    matrix[i][j - 1] + 1,
                    matrix[i - 1][j] + 1
                );
            }
        }
    }
    return matrix[b.length][a.length];
}

function similarity(str1, str2) {
    // 容错处理：处理 null/undefined/空字符串
    if (!str1 || !str2) return 0;
    const s1 = String(str1).trim();
    const s2 = String(str2).trim();
    if (s1.length === 0 || s2.length === 0) return 0;

    const maxLen = Math.max(s1.length, s2.length);
    if (maxLen === 0) return 100;
    const distance = levenshtein(s1.toLowerCase(), s2.toLowerCase());
    return ((maxLen - distance) / maxLen) * 100;
}

// ============================================================================
// RECONNAISSANCE SERVICE
// ============================================================================

class ReconService {
    constructor(db) {
        this.db = db;
    }

    /**
     * 扫描需要映射的比赛（英超优先策略）
     */
    async scan(limit = 100) {
        const client = await this.db.connect();
        try {
            // 策略 1: 优先扫描英超 2020-2022（唯一有充足历史映射的区域）
            const premierLeagueQuery = `
                SELECT m.match_id, m.league_name, m.home_team, m.away_team, m.match_date
                FROM matches m
                LEFT JOIN matches_mapping mm ON m.match_id = mm.fotmob_id
                WHERE mm.fotmob_id IS NULL
                  AND m.l2_raw_json IS NOT NULL
                  AND m.league_name = 'Premier League'
                  AND m.match_date >= '2020-08-01'
                  AND m.match_date < '2023-01-01'
                ORDER BY m.match_date DESC
                LIMIT $1
            `;

            const eplResult = await client.query(premierLeagueQuery, [limit]);

            if (eplResult.rows.length > 0) {
                console.log(`[V73.000] 扫描到 ${eplResult.rows.length} 场英超 2020-2022 待映射比赛`);
                return eplResult.rows;
            }

            // 策略 2: 英雄其他联赛（如果英超已处理完）
            const otherLeaguesQuery = `
                SELECT m.match_id, m.league_name, m.home_team, m.away_team, m.match_date
                FROM matches m
                LEFT JOIN matches_mapping mm ON m.match_id = mm.fotmob_id
                WHERE mm.fotmob_id IS NULL
                  AND m.l2_raw_json IS NOT NULL
                  AND m.league_name IN ('La Liga', 'Serie A', 'Bundesliga', 'Ligue 1')
                  AND m.match_date >= '2020-08-01'
                ORDER BY m.league_name, m.match_date DESC
                LIMIT $1
            `;

            const otherResult = await client.query(otherLeaguesQuery, [limit]);
            console.log(`[V73.000] 扫描到 ${otherResult.rows.length} 场其他联赛待映射比赛`);
            return otherResult.rows;

        } finally {
            client.release();
        }
    }

    /**
     * 从已有映射中查找最佳匹配
     */
    async findBestMatch(matchData) {
        const client = await this.db.connect();
        try {
            // 查询已有映射，使用队名匹配（跨赛季）
            const query = `
                SELECT fotmob_id, oddsportal_url, home_team, away_team, league_name, match_date
                FROM matches_mapping
                WHERE COALESCE(league_name, '') = $1
                  AND oddsportal_url IS NOT NULL
                  AND home_team IS NOT NULL AND away_team IS NOT NULL
                ORDER BY match_date DESC
                LIMIT 50
            `;

            const result = await client.query(query, [matchData.league_name]);

            if (result.rows.length === 0) {
                return null;
            }

            // 计算相似度（使用标准化队名）
            let bestMatch = null;
            let bestScore = 0;

            // 标准化待匹配比赛的队名
            const normalizedHome = normalizeTeamName(matchData.home_team);
            const normalizedAway = normalizeTeamName(matchData.away_team);

            for (const row of result.rows) {
                // 跳过空队名
                if (!row.home_team || !row.away_team) continue;

                // 标准化参考数据的队名
                const refHome = normalizeTeamName(row.home_team);
                const refAway = normalizeTeamName(row.away_team);

                const sim1 = similarity(normalizedHome, refHome);
                const sim2 = similarity(normalizedAway, refAway);
                const avgSimilarity = (sim1 + sim2) / 2;

                if (avgSimilarity > bestScore && avgSimilarity >= RECON_CONFIG.fuzzyThreshold) {
                    bestScore = avgSimilarity;
                    bestMatch = {
                        fotmob_id: row.fotmob_id,
                        url: row.oddsportal_url,
                        similarity: avgSimilarity,
                        confidence: avgSimilarity / 100
                    };
                }
            }

            return bestMatch;

        } finally {
            client.release();
        }
    }

    /**
     * 使用 URL 模式推断映射
     */
    async inferMappingFromPattern(matchData) {
        const client = await this.db.connect();
        try {
            // 从已有的同联赛映射中提取 URL 模式
            const query = `
                SELECT oddsportal_url
                FROM matches_mapping
                WHERE league_name = $1
                  AND oddsportal_url IS NOT NULL
                  AND season = $2
                LIMIT 1
            `;

            const result = await client.query(query, [matchData.league_name, this.extractSeason(matchData.match_date)]);

            if (result.rows.length === 0) {
                return null;
            }

            const templateUrl = result.rows[0].oddsportal_url;

            // 提取基础 URL 模式
            const baseUrlMatch = templateUrl.match(/^(https:\/\/www\.oddsportal\.com\/football\/[^\/]+\/[^\/]+\/)/);
            if (!baseUrlMatch) {
                return null;
            }

            const baseUrl = baseUrlMatch[1];

            // 构造新的 URL（使用队名转小写并用连字符连接）
            const homeSlug = matchData.home_team.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '');
            const awaySlug = matchData.away_team.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '');

            return {
                url: `${baseUrl}${homeSlug}-${awaySlug}-INFERRED/`,
                method: 'pattern_inference',
                confidence: 0.6
            };

        } finally {
            client.release();
        }
    }

    extractSeason(dateStr) {
        const date = new Date(dateStr);
        const year = date.getFullYear();
        const month = date.getMonth() + 1;

        if (month >= 8) {
            return `${year}-${year + 1}`;
        } else {
            return `${year - 1}-${year}`;
        }
    }

    /**
     * 保存映射
     */
    async saveMapping(matchData, mappingResult) {
        const client = await this.db.connect();
        try {
            const insertQuery = `
                INSERT INTO matches_mapping (
                    fotmob_id, oddsportal_url, confidence, mapping_method,
                    review_status, match_date, home_team, away_team, league_name
                )
                VALUES ($1, $2, $3, 'fuzzy_match', 'pending', $4, $5, $6, $7)
                ON CONFLICT (fotmob_id)
                DO UPDATE SET
                    oddsportal_url = EXCLUDED.oddsportal_url,
                    confidence = EXCLUDED.confidence,
                    updated_at = NOW()
            `;

            await client.query(insertQuery, [
                matchData.match_id,
                mappingResult.url,
                mappingResult.confidence,
                matchData.match_date,
                matchData.home_team,
                matchData.away_team,
                matchData.league_name
            ]);

            console.log(`[V73.000] ✅ 保存映射: ${matchData.match_id} (confidence: ${mappingResult.confidence.toFixed(2)})`);

        } finally {
            client.release();
        }
    }

    /**
     * 执行侦察
     */
    async execute(limit = 100) {
        console.log(`[V73.000] 开始哈希侦察 (limit: ${limit})`);

        const matches = await this.scan(limit);

        if (matches.length === 0) {
            console.log('[V73.000] 没有待映射的比赛');
            return { processed: 0, mapped: 0, failed: 0 };
        }

        let mapped = 0;
        let failed = 0;

        for (const match of matches) {
            try {
                // 策略 1: 库内模糊匹配
                const bestMatch = await this.findBestMatch(match);

                if (bestMatch) {
                    await this.saveMapping(match, bestMatch);
                    mapped++;
                    continue;
                }

                // 策略 2: URL 模式推断
                const inferred = await this.inferMappingFromPattern(match);
                if (inferred) {
                    await this.saveMapping(match, inferred);
                    mapped++;
                } else {
                    failed++;
                    console.log(`[V73.000] ⚠️ 无法推断映射: ${match.match_id} (${match.home_team} vs ${match.away_team})`);
                }

            } catch (error) {
                failed++;
                console.error(`[V73.000] ❌ 错误: ${match.match_id} - ${error.message}`);
                console.error(`[V73.000] Stack: ${error.stack}`);
            }
        }

        console.log(`[V73.000] 侦察完成: 处理 ${matches.length} 场, 成功 ${mapped} 场, 失败 ${failed} 场, 成功率 ${(mapped / matches.length * 100).toFixed(2)}%`);

        return {
            processed: matches.length,
            mapped,
            failed,
            success_rate: (mapped / matches.length * 100).toFixed(2) + '%'
        };
    }
}

// ============================================================================
// MAIN
// ============================================================================

async function main() {
    const service = new ReconService(new Pool(RECON_CONFIG.db));

    try {
        const limit = parseInt(process.argv[2]) || 100;
        const result = await service.execute(limit);
        console.log(JSON.stringify(result, null, 2));
        return result.mapped > 0 ? 0 : 1;

    } catch (error) {
        console.error(`[V73.000] 致命错误: ${error.message}`);
        console.error(error.stack);
        return 1;
    } finally {
        await service.db.end();
    }
}

if (require.main === module) {
    main();
}

module.exports = { ReconService, RECON_CONFIG };
