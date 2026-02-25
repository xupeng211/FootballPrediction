/**
 * L1 Discovery Test Script - V171.001
 * ================================
 *
 * 测试 L1 比赛发现能力：从 OddsPortal 英超页面自动发现下周比赛
 *
 * 执行流程:
 * 1. 访问 OddsPortal 英超联赛页面
 * 2. 提取所有未开赛的比赛链接
 * 3. 解析比赛信息（主队、客队、比赛时间）
 * 4. 存入 matches 表（状态: pending）
 *
 * Usage:
 *   node scripts/ops/test_l1_discovery.js --limit 10
 *
 * @module scripts/ops/test_l1_discovery
 * @version V171.001
 */

'use strict';

const { chromium } = require('playwright');
const { Client } = require('pg');
const path = require('path');

// 项目根目录
const PROJECT_ROOT = path.resolve(__dirname, '../..');

// 导入选择器
let OddsPortalSelectors;
try {
    OddsPortalSelectors = require(path.join(PROJECT_ROOT, 'src/infrastructure/engines/selectors/OddsPortalSelectors')).OddsPortalSelectors;
} catch (e) {
    console.warn('⚠️ OddsPortalSelectors not found, using fallback selectors');
    OddsPortalSelectors = null;
}

// ============================================================================
// CONFIGURATION
// ============================================================================

const CONFIG = {
    // OddsPortal 联赛页面
    leagues: [
        {
            name: 'Premier League',
            url: 'https://www.oddsportal.com/football/england/premier-league/',
            country: 'england',
            league_code: 'EPL'
        },
        {
            name: 'La Liga',
            url: 'https://www.oddsportal.com/football/spain/laliga/',
            country: 'spain',
            league_code: 'LALIGA'
        },
        {
            name: 'Bundesliga',
            url: 'https://www.oddsportal.com/football/germany/bundesliga/',
            country: 'germany',
            league_code: 'BL'
        },
        {
            name: 'Serie A',
            url: 'https://www.oddsportal.com/football/italy/serie-a/',
            country: 'italy',
            league_code: 'SA'
        },
        {
            name: 'Ligue 1',
            url: 'https://www.oddsportal.com/football/france/ligue-1/',
            country: 'france',
            league_code: 'L1'
        }
    ],

    // 选择器配置
    selectors: {
        // 比赛链接选择器（多种模式）
        matchLinks: [
            'a[href*="/match/"]',
            'a[href*="-vs-"]',
            'tr[class*="match"] a',
            'div[class*="match"] a',
            'table tbody tr a'
        ],
        // 比赛行选择器
        matchRows: [
            'tr[class*="deactivate"]',
            'tr[id*="match"]',
            'tbody tr'
        ],
        // 时间选择器
        timeCells: [
            'td[class*="time"]',
            'span[class*="time"]',
            '[class*="date"]'
        ],
        // 球队名称选择器
        teamNames: [
            'td[class*="name"]',
            'a[class*="name"]',
            'span[class*="team"]'
        ]
    },

    // 浏览器配置
    browser: {
        headless: true,
        timeout: 30000
    }
};

// ============================================================================
// L1 DISCOVERY ENGINE
// ============================================================================

class L1DiscoveryEngine {
    constructor(options = {}) {
        this.limit = options.limit || 10;
        this.leagues = options.leagues || CONFIG.leagues.slice(0, 1); // 默认只测试英超
        this.dryRun = options.dryRun || false;
        this.browser = null;
        this.dbClient = null;

        this.stats = {
            discovered: 0,
            inserted: 0,
            skipped: 0,
            errors: 0
        };

        this.discoveredMatches = [];
    }

    /**
     * 初始化
     */
    async init() {
        console.log('');
        console.log('╔════════════════════════════════════════════════════════════════╗');
        console.log('║     L1 DISCOVERY ENGINE - V171.001                            ║');
        console.log('╚════════════════════════════════════════════════════════════════╝');
        console.log('');

        // 初始化数据库连接
        if (!this.dryRun) {
            this.dbClient = new Client({
                host: process.env.DB_HOST || 'localhost',
                port: parseInt(process.env.DB_PORT) || 5432,
                database: process.env.DB_NAME || 'football_db',
                user: process.env.DB_USER || 'football_user',
                password: process.env.DB_PASSWORD || 'your_secure_password_here'
            });

            await this.dbClient.connect();
            console.log('✅ 数据库连接成功');
        } else {
            console.log('⚠️ DRY RUN MODE - 不写入数据库');
        }

        // 启动浏览器
        this.browser = await chromium.launch({
            headless: CONFIG.browser.headless
        });
        console.log('✅ 浏览器启动成功');
        console.log('');
    }

    /**
     * 关闭资源
     */
    async close() {
        if (this.browser) {
            await this.browser.close();
        }
        if (this.dbClient) {
            await this.dbClient.end();
        }
    }

    /**
     * 执行发现
     */
    async discover() {
        console.log(`🎯 开始发现比赛 (限制: ${this.limit} 场)`);
        console.log('');

        for (const league of this.leagues) {
            if (this.stats.discovered >= this.limit) {
                console.log(`\n✅ 已达到限制 (${this.limit} 场)，停止发现`);
                break;
            }

            console.log(`\n📍 扫描联赛: ${league.name}`);
            console.log(`   URL: ${league.url}`);

            try {
                const matches = await this.discoverLeague(league);
                this.discoveredMatches.push(...matches);
                this.stats.discovered += matches.length;

                console.log(`   ✅ 发现 ${matches.length} 场比赛`);

                // 写入数据库
                if (!this.dryRun) {
                    await this.insertMatches(matches, league);
                }

            } catch (error) {
                console.error(`   ❌ 发现失败: ${error.message}`);
                this.stats.errors++;
            }
        }

        // 输出结果
        this.printSummary();

        return this.discoveredMatches;
    }

    /**
     * 发现单个联赛的比赛
     */
    async discoverLeague(league) {
        const matches = [];
        const page = await this.browser.newPage();

        try {
            // 导航到联赛页面
            await page.goto(league.url, {
                timeout: CONFIG.browser.timeout,
                waitUntil: 'networkidle'
            });

            console.log('   📄 页面加载完成');

            // 移除覆盖层
            await this.removeOverlays(page);

            // 等待比赛列表加载
            await page.waitForSelector('table, tbody, [class*="match"]', {
                timeout: 10000
            }).catch(() => {
                console.log('   ⚠️ 未找到比赛列表容器，尝试直接提取');
            });

            // 提取比赛链接
            const matchLinks = await this.extractMatchLinks(page, league);
            console.log(`   🔗 提取到 ${matchLinks.length} 个比赛链接`);

            // 过滤未开赛的比赛
            for (const match of matchLinks) {
                if (matches.length >= this.limit - this.stats.discovered) {
                    break;
                }

                // 检查比赛是否未开始（通过时间判断）
                if (this.isUpcomingMatch(match)) {
                    matches.push(match);
                }
            }

        } finally {
            await page.close();
        }

        return matches;
    }

    /**
     * 移除覆盖层
     */
    async removeOverlays(page) {
        if (OddsPortalSelectors) {
            await page.evaluate(OddsPortalSelectors.generatePurgeScript());
        } else {
            // 基础覆盖层移除
            await page.evaluate(() => {
                const selectors = [
                    '#onetrust-consent-sdk',
                    '#onetrust-banner-sdk',
                    '.cookie-consent',
                    '[class*="overlay"]'
                ];
                selectors.forEach(sel => {
                    document.querySelectorAll(sel).forEach(el => el.remove());
                });
            });
        }
    }

    /**
     * 提取比赛链接
     */
    async extractMatchLinks(page, league) {
        const matches = [];

        // 方法1: 从表格行提取
        const tableMatches = await this.extractFromTable(page, league);
        matches.push(...tableMatches);

        // 方法2: 从链接直接提取（备选）
        if (matches.length === 0) {
            const linkMatches = await this.extractFromLinks(page, league);
            matches.push(...linkMatches);
        }

        return matches;
    }

    /**
     * 从表格提取比赛
     */
    async extractFromTable(page, league) {
        const matches = [];

        try {
            const rows = await page.$$('table tbody tr, [class*="match-row"], tr[class*="deactivate"]');
            console.log(`   📊 找到 ${rows.length} 行数据`);

            for (const row of rows) {
                try {
                    // 提取链接
                    const link = await row.$('a[href*="/match/"], a[href*="-vs-"]');
                    if (!link) continue;

                    const href = await link.getAttribute('href');
                    if (!href) continue;

                    // 提取球队名称
                    const text = await row.innerText();
                    const teams = this.parseTeamNames(text);

                    if (!teams.home || !teams.away) continue;

                    // 生成 match_id
                    const matchId = this.generateMatchId(teams, league);

                    matches.push({
                        match_id: matchId,
                        home_team: teams.home,
                        away_team: teams.away,
                        oddsportal_url: href.startsWith('http') ? href : `https://www.oddsportal.com${href}`,
                        league_name: league.name,
                        league_code: league.league_code,
                        discovered_at: new Date().toISOString()
                    });

                } catch (e) {
                    continue;
                }
            }

        } catch (error) {
            console.log(`   ⚠️ 表格提取失败: ${error.message}`);
        }

        return matches;
    }

    /**
     * 从链接直接提取
     */
    async extractFromLinks(page, league) {
        const matches = [];

        try {
            const links = await page.$$('a[href*="/match/"]');

            for (const link of links) {
                const href = await link.getAttribute('href');
                if (!href) continue;

                // 从 URL 解析球队名称
                const teams = this.parseTeamsFromUrl(href);
                if (!teams.home || !teams.away) continue;

                const matchId = this.generateMatchId(teams, league);

                matches.push({
                    match_id: matchId,
                    home_team: teams.home,
                    away_team: teams.away,
                    oddsportal_url: href.startsWith('http') ? href : `https://www.oddsportal.com${href}`,
                    league_name: league.name,
                    league_code: league.league_code,
                    discovered_at: new Date().toISOString()
                });
            }

        } catch (error) {
            console.log(`   ⚠️ 链接提取失败: ${error.message}`);
        }

        return matches;
    }

    /**
     * 解析球队名称（从文本）
     */
    parseTeamNames(text) {
        // 常见的分隔符模式
        const patterns = [
            /(.+?)\s*-\s*(.+)/,
            /(.+?)\s+vs\.?\s+(.+)/i,
            /(.+?)\s+v\s+(.+)/i
        ];

        for (const pattern of patterns) {
            const match = text.match(pattern);
            if (match) {
                return {
                    home: match[1].trim(),
                    away: match[2].trim()
                };
            }
        }

        return { home: null, away: null };
    }

    /**
     * 从 URL 解析球队名称
     */
    parseTeamsFromUrl(url) {
        // URL 格式: /match/team1-vs-team2-hash/
        // 或: /football/country/league/team1-vs-team2-hash/
        const match = url.match(/\/([a-z0-9-]+)-vs-([a-z0-9-]+)-/i);

        if (match) {
            return {
                home: this.formatTeamName(match[1]),
                away: this.formatTeamName(match[2])
            };
        }

        return { home: null, away: null };
    }

    /**
     * 格式化球队名称
     */
    formatTeamName(name) {
        return name
            .split('-')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
    }

    /**
     * 生成 match_id
     */
    generateMatchId(teams, league) {
        const date = new Date();
        const dateStr = date.toISOString().slice(0, 10).replace(/-/g, '');
        const homeCode = teams.home.substring(0, 3).toUpperCase();
        const awayCode = teams.away.substring(0, 3).toUpperCase();

        return `${league.league_code}_${dateStr}_${homeCode}_${awayCode}`;
    }

    /**
     * 判断是否为未开始的比赛
     */
    isUpcomingMatch(match) {
        // 简单判断：所有发现的比赛都视为未开始
        // 实际应用中可以检查比赛时间
        return true;
    }

    /**
     * 写入数据库
     */
    async insertMatches(matches, league) {
        for (const match of matches) {
            try {
                // 检查是否已存在
                const checkResult = await this.dbClient.query(
                    'SELECT match_id FROM matches WHERE match_id = $1',
                    [match.match_id]
                );

                if (checkResult.rows.length > 0) {
                    console.log(`   ⏭️ 跳过已存在: ${match.home_team} vs ${match.away_team}`);
                    this.stats.skipped++;
                    continue;
                }

                // 插入新记录
                await this.dbClient.query(`
                    INSERT INTO matches (
                        match_id, home_team, away_team,
                        league_name, season, match_date,
                        technical_features
                    ) VALUES ($1, $2, $3, $4, $5, NOW(), $6)
                `, [
                    match.match_id,
                    match.home_team,
                    match.away_team,
                    league.name,
                    '2025-2026',
                    JSON.stringify({
                        oddsportal_url: match.oddsportal_url,
                        discovered_at: match.discovered_at,
                        status: 'pending',
                        source: 'L1_discovery'
                    })
                ]);

                console.log(`   ✅ 入库: ${match.home_team} vs ${match.away_team}`);
                this.stats.inserted++;

            } catch (error) {
                console.error(`   ❌ 入库失败: ${error.message}`);
                this.stats.errors++;
            }
        }
    }

    /**
     * 打印摘要
     */
    printSummary() {
        console.log('');
        console.log('╔════════════════════════════════════════════════════════════════╗');
        console.log('║                    L1 DISCOVERY SUMMARY                       ║');
        console.log('╠════════════════════════════════════════════════════════════════╣');
        console.log(`║  发现比赛: ${this.stats.discovered.toString().padEnd(48)}║`);
        console.log(`║  成功入库: ${this.stats.inserted.toString().padEnd(48)}║`);
        console.log(`║  跳过重复: ${this.stats.skipped.toString().padEnd(48)}║`);
        console.log(`║  错误数量: ${this.stats.errors.toString().padEnd(48)}║`);
        console.log('╚════════════════════════════════════════════════════════════════╝');

        if (this.discoveredMatches.length > 0) {
            console.log('');
            console.log('📋 发现的比赛列表:');
            this.discoveredMatches.slice(0, 10).forEach((m, i) => {
                console.log(`   ${i + 1}. ${m.home_team} vs ${m.away_team} (${m.league_name})`);
            });
            if (this.discoveredMatches.length > 10) {
                console.log(`   ... 还有 ${this.discoveredMatches.length - 10} 场比赛`);
            }
        }
    }
}

// ============================================================================
// MAIN
// ============================================================================

async function main() {
    // 解析命令行参数
    const args = process.argv.slice(2);
    const limitIndex = args.indexOf('--limit');
    const limit = limitIndex > -1 ? parseInt(args[limitIndex + 1]) || 10 : 10;
    const dryRun = args.includes('--dry-run');

    const engine = new L1DiscoveryEngine({
        limit,
        dryRun,
        leagues: CONFIG.leagues.slice(0, 1) // 只测试英超
    });

    try {
        await engine.init();
        await engine.discover();
    } catch (error) {
        console.error('\n❌ FATAL ERROR:', error.message);
        console.error(error.stack);
        process.exit(1);
    } finally {
        await engine.close();
    }

    console.log('\n✅ L1 Discovery 测试完成!');
}

// 运行
main();
