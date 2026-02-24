/**
 * V171.002 Real URL Hash Extractor - Node.js 版本
 * =================================================
 *
 * 从 OddsPortal 抓取真实的 URL hash 值
 */

'use strict';

const { chromium } = require('playwright');
const { Client } = require('pg');

// 8 字符 hash 正则表达式
const HASH_PATTERN = /[A-Za-z0-9]{8}\/?$/;

// 联赛 URL
const LEAGUE_URLS = {
    'Premier League': 'https://www.oddsportal.com/football/england/premier-league/',
    'La Liga': 'https://www.oddsportal.com/football/spain/laliga/',
    'Bundesliga': 'https://www.oddsportal.com/football/germany/bundesliga/',
    'Serie A': 'https://www.oddsportal.com/football/italy/serie-a/',
    'Ligue 1': 'https://www.oddsportal.com/football/france/ligue-1/'
};

async function extractRealUrls(league, limit = 20) {
    console.log('');
    console.log('═'.repeat(65));
    console.log('  V171.002 真实 URL Hash 提取器');
    console.log('═'.repeat(65));
    console.log('');
    console.log(`🌐 联赛: ${league}`);
    console.log(`📋 限制: ${limit}`);
    console.log('');

    const url = LEAGUE_URLS[league];
    if (!url) {
        console.error('❌ 未知联赛');
        return [];
    }

    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();

    console.log(`🔗 访问: ${url}`);
    await page.goto(url, { timeout: 30000, waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);

    // 提取带 hash 的链接
    const links = await page.evaluate(() => {
        const results = [];
        const links = document.querySelectorAll('a[href*="/football/"]');

        links.forEach(link => {
            const href = link.getAttribute('href');
            if (href && href.match(/[A-Za-z0-9]{8}\/?$/)) {
                results.push({ href, text: link.innerText });
            }
        });

        return results;
    });

    console.log(`   找到 ${links.length} 个带 hash 的链接`);
    console.log('');

    const matches = [];

    for (const link of links.slice(0, limit)) {
        const href = link.href;
        const text = link.text;

        // 提取 hash
        const hashMatch = href.match(HASH_PATTERN);
        if (hashMatch) {
            const urlHash = hashMatch[0].replace('/', '');
            const fullUrl = href.startsWith('http') ? href : `https://www.oddsportal.com${href}`;

            // 解析队名
            const teams = parseTeamsFromUrl(href, text);

            if (teams) {
                matches.push({
                    home: teams.home,
                    away: teams.away,
                    hash: urlHash,
                    url: fullUrl
                });

                console.log(`   ✅ ${teams.home} vs ${teams.away}`);
                console.log(`      Hash: ${urlHash}`);
                console.log(`      URL:  ${fullUrl}`);
                console.log('');
            }
        }
    }

    await browser.close();

    console.log('═'.repeat(65));
    console.log(`  提取完成: ${matches.length} 个真实 URL`);
    console.log('═'.repeat(65));

    return matches;
}

function parseTeamsFromUrl(url, text) {
    // 提取联赛后的部分
    const match = url.match(/\/premier-league\/([^/]+)\/?$/);
    if (!match) return null;

    const teamsPart = match[1];
    const parts = teamsPart.split('-');

    // 找到 hash 位置
    let hashIdx = -1;
    for (let i = 0; i < parts.length; i++) {
        if (parts[i].length === 8 && (/[A-Z]/.test(parts[i]) || /[0-9]/.test(parts[i]))) {
            hashIdx = i;
            break;
        }
    }

    if (hashIdx < 2) return null;

    const teamParts = parts.slice(0, hashIdx);

    // 智能分割
    const knownTeams = [
        'manchester', 'united', 'city', 'liverpool', 'chelsea', 'arsenal',
        'tottenham', 'hotspur', 'newcastle', 'brighton', 'west', 'ham',
        'wolves', 'wolverhampton', 'aston', 'villa', 'everton', 'fulham',
        'crystal', 'palace', 'brentford', 'nottingham', 'forest', 'bournemouth',
        'southampton', 'leeds', 'leicester'
    ];

    // 尝试找到分割点
    for (let i = 1; i < teamParts.length; i++) {
        const homeParts = teamParts.slice(0, i);
        const awayParts = teamParts.slice(i);

        const home = homeParts.map(p => p.charAt(0).toUpperCase() + p.slice(1)).join(' ');
        const away = awayParts.map(p => p.charAt(0).toUpperCase() + p.slice(1)).join(' ');

        // 简单验证
        if (home.length < 30 && away.length < 30) {
            return { home, away };
        }
    }

    return null;
}

async function updateDatabase(matches) {
    const client = new Client({
        host: process.env.DB_HOST || 'db',
        database: process.env.DB_NAME || 'football_db',
        user: process.env.DB_USER || 'football_user',
        password: process.env.DB_PASSWORD || 'your_secure_password_here'
    });

    await client.connect();
    let updated = 0;

    for (const match of matches) {
        // 查找匹配的比赛
        const result = await client.query(`
            SELECT match_id FROM matches
            WHERE (home_team ILIKE $1 AND away_team ILIKE $2)
               OR (home_team ILIKE $3 AND away_team ILIKE $4)
            LIMIT 1
        `, [`%${match.home}%`, `%${match.away}%`, `%${match.away}%`, `%${match.home}%`]);

        if (result.rows.length > 0) {
            const matchId = result.rows[0].match_id;

            await client.query(`
                UPDATE matches SET external_id = $1, updated_at = NOW()
                WHERE match_id = $2
            `, [match.url, matchId]);

            console.log(`   💾 更新: ${matchId} → ${match.hash}`);
            updated++;
        }
    }

    await client.end();
    return updated;
}

async function main() {
    const args = process.argv.slice(2);
    const limitIndex = args.indexOf('--limit');
    const limit = limitIndex > -1 ? parseInt(args[limitIndex + 1]) || 20 : 20;
    const updateDb = args.includes('--update-db');

    const matches = await extractRealUrls('Premier League', limit);

    if (updateDb && matches.length > 0) {
        console.log('');
        console.log('─'.repeat(65));
        console.log('💾 更新数据库...');
        const updated = await updateDatabase(matches);
        console.log(`   更新了 ${updated} 条记录`);
    }
}

main().catch(e => {
    console.error('Fatal:', e.message);
    process.exit(1);
});
