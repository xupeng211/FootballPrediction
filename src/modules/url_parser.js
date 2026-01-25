/**
 * V70.100 - OddsPortal URL Parser
 * ===============================
 *
 * Robust URL parser for extracting team names from OddsPortal match URLs.
 *
 * Handles complex URL patterns:
 * - .../premier-league-2024-2025-manchester-city-tottenham-12345678/
 * - .../laliga-2024-2025-real-madrid-barcelona-abcdefgh/
 * - .../bundesliga-bayern-munich-dortmund-87654321/
 *
 * @file url_parser.js
 * @version V70.100
 * @since 2026-01-25
 */

'use strict';

// ============================================================================
// CONFIGURATION
// ============================================================================

const URL_PARSER_CONFIG = {
    // Common league name patterns (lowercase, hyphenated)
    leaguePatterns: [
        'premier-league',
        'laliga',
        'la-liga',
        'primera-division',
        'bundesliga',
        '1-bundesliga',
        '2-bundesliga',
        'serie-a',
        'serie-b',
        'ligue-1',
        'ligue-2',
        'eredivisie',
        'primeira-liga',
        'championship',
        'premiership',
        'scottish-premiership',
        'scottish-premier-league'
    ],

    // Season patterns (e.g., 2024-2025, 2023-2024)
    seasonPattern: /\d{4}-\d{4}/,

    // Hash pattern (7-8 character alphanumeric at end, case-insensitive)
    hashPattern: /-[a-zA-Z0-9]{7,8}\/?$/,

    // Known multi-word team names (for proper reconstruction)
    multiWordTeams: [
        'manchester-city', 'manchester-united', 'manchester',
        'tottenham-hotspur', 'tottenham',
        'west-ham-united', 'west-ham',
        'newcastle-united', 'newcastle',
        'nottingham-forest',
        'leeds-united', 'leeds',
        'sheffield-united',
        'luton-town', 'luton',
        'brentford',
        'real-madrid', 'real-betis', 'real-sociedad', 'real-valladolid',
        'atletico-madrid',
        'athletic-bilbao',
        'fc-barcelona', 'barcelona',
        'bayern-munich', 'bayern',
        'borussia-dortmund', 'dortmund',
        'borussia-monchengladbach',
        'eintracht-frankfurt',
        'vfl-wolfsburg',
        'rb-leipzig',
        'inter-milan', 'inter',
        'ac-milan', 'milan',
        'juventus',
        'napoli',
        'as-roma', 'roma',
        'lazio-rome',
        'paris-saint-germain', 'psg', 'paris',
        'olympique-marseille', 'marseille',
        'olympique-lyonnais', 'lyon',
        'celtic',
        'rangers',
        'ajax',
        'feyenoord',
        'psv-eindhoven', 'psv',
        'benfica',
        'sporting-lisbon', 'sporting',
        'porto',
        'galatasaray',
        'fenerbahce',
        'besiktas',
        'shakhtar-donetsk',
        'dynamo-kiev',
        'red-star-belgrade',
        'salzburg',
        'lask',
        'brugge',
        'club-brugge',
        'gent',
        'anderlecht',
        'shanghai-sipg',
        'guangzhou-evergrande'
    ]
};

// ============================================================================
// URL PARSER CLASS
// ============================================================================

class OddsPortalUrlParser {
    constructor(config = URL_PARSER_CONFIG) {
        this.config = config;
    }

    /**
     * Extract team names from OddsPortal URL
     *
     * @param {string} url - Full OddsPortal URL
     * @returns {Object|null} - {homeTeam, awayTeam, hash, league, season} or null
     */
    parseUrlTeams(url) {
        if (!url || typeof url !== 'string') {
            return null;
        }

        // Step 1: Extract the filename/last segment
        const segments = url.split('/').filter(s => s.length > 0);
        const filename = segments[segments.length - 1].replace(/\/$/, '');

        if (!filename) {
            return null;
        }

        // Step 2: Extract the hash (last 7-8 alphanumeric chars, case-insensitive)
        const hashMatch = filename.match(/-([a-zA-Z0-9]{7,8})\/?$/);
        const hash = hashMatch ? hashMatch[1] : null;

        // Step 3: Remove hash from filename (case-insensitive)
        let withoutHash = filename.replace(/-[a-zA-Z0-9]{7,8}\/?$/, '');

        // Step 4: Remove season year pattern (e.g., 2024-2025)
        const seasonMatch = withoutHash.match(/(\d{4}-\d{4})-/);
        const season = seasonMatch ? seasonMatch[1] : null;
        withoutHash = withoutHash.replace(/\d{4}-\d{4}-/, '');

        // Step 5: Identify and remove league name
        const { league, remaining } = this.extractLeague(withoutHash);

        // Step 6: Extract team names from remaining segments
        const teamNames = this.extractTeamNames(remaining);

        return {
            homeTeam: teamNames.home,
            awayTeam: teamNames.away,
            hash,
            league,
            season
        };
    }

    /**
     * Extract league name from URL segment
     * @param {string} segment - URL segment after season removal
     * @returns {Object} - {league, remaining}
     */
    extractLeague(segment) {
        const parts = segment.split('-');
        let league = null;
        let startIndex = 0;

        // Check for league pattern at the beginning
        for (let i = 0; i < Math.min(3, parts.length); i++) {
            const candidate = parts.slice(0, i + 1).join('-');
            if (this.config.leaguePatterns.includes(candidate)) {
                league = candidate;
                startIndex = i + 1;
                break;
            }
        }

        const remaining = startIndex > 0 ? parts.slice(startIndex).join('-') : segment;

        return { league, remaining };
    }

    /**
     * Extract team names from remaining URL segment
     * @param {string} segment - URL segment after league/season removal
     * @returns {Object} - {home, away}
     */
    extractTeamNames(segment) {
        const parts = segment.split('-').filter(p => p.length > 0);

        if (parts.length < 2) {
            return { home: '', away: '' };
        }

        // Strategy: Find the split point between two teams
        // Known multi-word teams help us identify boundaries
        const splitIndex = this.findTeamSplitIndex(parts);

        const homeParts = parts.slice(0, splitIndex);
        const awayParts = parts.slice(splitIndex);

        return {
            home: this.reconstructTeamName(homeParts),
            away: this.reconstructTeamName(awayParts)
        };
    }

    /**
     * Find the split index between home and away team
     * @param {Array} parts - URL parts (hyphen-split)
     * @returns {number} - Split index
     */
    findTeamSplitIndex(parts) {
        const n = parts.length;

        // Strategy 1: Try to find a perfect split where both parts are known teams
        // Check all possible split positions (from 1 to n-1)
        for (let i = 1; i <= n - 1; i++) {
            const firstTeam = parts.slice(0, i).join('-');
            const secondTeam = parts.slice(i).join('-');

            // Both parts must be known teams
            if (this.isKnownTeam(firstTeam) && this.isKnownTeam(secondTeam)) {
                // Prefer exact matches over partial matches
                if (this.isExactKnownTeam(firstTeam) && this.isExactKnownTeam(secondTeam)) {
                    return i;
                }
            }
        }

        // Strategy 2: Check for a known multi-word team at the end (suffix)
        // Look for luton-town in brentford-luton-town
        for (let i = Math.min(4, n - 1); i >= 2; i--) {
            const lastTeam = parts.slice(n - i).join('-');
            if (this.isExactKnownTeam(lastTeam)) {
                // Make sure preceding parts form a valid team
                if (n - i >= 1) {
                    return n - i;
                }
            }
        }

        // Strategy 3: Check for a known multi-word team at the beginning (prefix)
        for (let i = Math.min(4, n - 1); i >= 2; i--) {
            const firstTeam = parts.slice(0, i).join('-');
            if (this.isExactKnownTeam(firstTeam)) {
                // Make sure remaining parts form a valid team
                if (n - i >= 1) {
                    return i;
                }
            }
        }

        // Strategy 4: Default split roughly in the middle
        // Prefer first team being slightly longer (common pattern)
        return Math.floor(n / 2) + (n % 2);
    }

    /**
     * Check if a name is an EXACT known team (not a partial match)
     * @param {string} name - Hyphenated team name
     * @returns {boolean}
     */
    isExactKnownTeam(name) {
        const normalizedName = name.toLowerCase().replace(/-/g, '-');
        return this.config.multiWordTeams.includes(normalizedName);
    }

    /**
     * Check if a name is a known multi-word team
     * @param {string} name - Hyphenated team name
     * @returns {boolean}
     */
    isKnownTeam(name) {
        const normalizedName = name.toLowerCase().replace(/-/g, '-');
        return this.config.multiWordTeams.some(team => {
            // Exact match
            if (team === normalizedName) {
                return true;
            }
            // Only use includes for multi-word known teams (contains hyphen)
            // This prevents 'brentford' from matching 'brentford-luton-town'
            if (team.includes('-') && (normalizedName + '-').startsWith(team + '-') || ('-' + normalizedName).endsWith('-' + team)) {
                return true;
            }
            return false;
        });
    }

    /**
     * Reconstruct team name from parts
     * @param {Array} parts - URL parts
     * @returns {string} - Reconstructed team name
     */
    reconstructTeamName(parts) {
        if (parts.length === 0) return '';

        // Join with hyphens and convert to title case
        const name = parts.join('-');

        // Special case mappings for common abbreviations
        const specialCases = {
            'fc': '',  // Remove FC prefix/suffix
            'afc': '',
            'bc': ''
        };

        return name
            .split('-')
            .filter(part => !specialCases[part.toLowerCase()])
            .map(word => this.capitalizeWord(word))
            .join(' ')
            .trim();
    }

    /**
     * Capitalize a word (handles special cases)
     * @param {string} word - Word to capitalize
     * @returns {string}
     */
    capitalizeWord(word) {
        const lower = word.toLowerCase();

        // Special cases
        const specialCases = {
            'fc': 'FC',
            'afc': 'AFC',
            'bc': 'BC',
            'united': 'United',
            'city': 'City',
            'town': 'Town',
            'athletic': 'Athletic',
            'hotspur': 'Hotspur',
            'forest': 'Forest',
            'albion': 'Albion',
            'rovers': 'Rovers',
            'rangers': 'Rangers',
            'celtic': 'Celtic',
            'real': 'Real',
            'atletico': 'Atletico',
            'betis': 'Betis',
            'sociedad': 'Sociedad',
            'bilbao': 'Bilbao',
            'bayern': 'Bayern',
            'borussia': 'Borussia',
            'eintracht': 'Eintracht',
            'vfl': 'VfL',
            'rb': 'RB',
            'inter': 'Inter',
            'milan': 'Milan',
            'juventus': 'Juventus',
            'napoli': 'Napoli',
            'roma': 'Roma',
            'lazio': 'Lazio',
            'olympique': 'Olympique',
            'saint-germain': 'Saint-Germain',
            'marseille': 'Marseille',
            'lyonnais': 'Lyon',
            'sporting': 'Sporting',
            'shakhtar': 'Shakhtar',
            'dynamo': 'Dynamo',
            'salzburg': 'Salzburg'
        };

        if (specialCases[lower]) {
            return specialCases[lower];
        }

        // Default: capitalize first letter
        return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
    }
}

// ============================================================================
// CONVENIENCE FUNCTIONS
// ============================================================================

/**
 * Parse OddsPortal URL and extract team names
 * @param {string} url - OddsPortal match URL
 * @returns {Object|null} - {homeTeam, awayTeam, hash, league, season}
 */
function parseUrlTeams(url) {
    const parser = new OddsPortalUrlParser();
    return parser.parseUrlTeams(url);
}

/**
 * Extract just the team names (for backward compatibility)
 * @param {string} url - OddsPortal match URL
 * @returns {Object} - {home, away}
 */
function extractTeams(url) {
    const result = parseUrlTeams(url);
    if (!result) {
        return { home: '', away: '' };
    }
    return {
        home: result.homeTeam,
        away: result.awayTeam
    };
}

// ============================================================================
// EXPORTS
// ============================================================================

module.exports = {
    OddsPortalUrlParser,
    parseUrlTeams,
    extractTeams,
    URL_PARSER_CONFIG
};

// ============================================================================
// CLI TEST INTERFACE
// ============================================================================

if (require.main === module) {
    // Test cases
    const testUrls = [
        'https://www.oddsportal.com/football/spain/laliga-2024-2025-real-madrid-barcelona-abcdefgh/',
        'https://www.oddsportal.com/football/england/premier-league-2024-2025-manchester-city-tottenham-12345678/',
        'https://www.oddsportal.com/football/germany/bundesliga-bayern-munich-dortmund-87654321/',
        'https://www.oddsportal.com/football/england/premier-league-2024-2025-brentford-luton-town-4a0b8c12/',
        'https://www.oddsportal.com/football/england/premier-league-2024-2025-arsenal-chelsea-7f8a9b2/',
        'https://www.oddsportal.com/football/italy/serie-a-2024-2025-inter-milan-jventus-abc12345/',
        'https://www.oddsportal.com/football/france/ligue-1-2024-2025-psg-marseille-def67890/'
    ];

    console.log('=== V70.100 URL Parser Test ===\n');

    for (const url of testUrls) {
        const result = parseUrlTeams(url);
        console.log('URL:', url.substring(url.lastIndexOf('/', url.lastIndexOf('/') - 1) + 1));
        console.log('Result:', JSON.stringify(result, null, 2));
        console.log('---');
    }
}
