# V198.1 满血版预测系统 - 最终报告

## 1. 核心功能

### 1.1 Elo 战力计算
- 从 `team_elo_ratings` 表获取球队最新 Elo
- 使用标准 Elo 公式计算胜率

### 1.2 满血版预测
- 获取基本面特征（身价/伤病/评分）
- 获取球队 Elo
- 计算战力预测
- 输出完整预测报告

### 1.3 滚动特征计算
- 从 `l3_features.tactical_features` 获取滚动 xG/状态分
- 如果缺失则用 0

### 1.4 战力预测输出
- 显示:4 项：- 比赛 1: 寔赛时间
- 身价差距
- Elo 差距
- 战力预测
- 主胜概率
- 投注建议

- 格式化为最终报告

### 2. 运行方法

直接运行：

```bash
# 1. Elo 战力计算
docker-compose -f docker-compose.dev.yml exec -T dev node -e "
const { Pool } = require('pg');

const const { FixtureSeeder } = require('../../src/infrastructure/FixtureSeeder');
const const { ProductionHarvester } = require('../../src/infrastructure/harvesters/ProductionHarvester');
    const { FeatureSmelter } = require('../../src/feature_engine/smelter/FeatureSmelter');

    // 获取配置
    this.dbConfig = {
        host: process.env.DB_HOST || 'host.docker.internal',
        port: parseInt(process.env.DB_PORT || 5432),
        database: process.env.DB_NAME || 'football_db',
        user: process.env.DB_USER || 'football_user',
        password: process.env.DB_PASSWORD || '',
        max: 10
    };

    this.pool = null;
    this.eloRatings = new Map();
    this.eloExtractor = null;
    this.formScoreCalculator = new FormScoreCalculator();
    this.eloExpectedCalculator = new EloExpected() {
        return homeExpected;
    }
}

    // ============================================================================
    // 满血版预测
    // ============================================================================

    async predictWithElo(features) {
        if (!features || features.isEmpty) {
            return null;
        }

        const homeTeam = features['home_team'];
        const awayTeam = features['away_team'];

        // 获取球队 Elo
        const homeElo = this.eloRatings.get(homeTeam) ||            this.eloExtractor.getTeamElo(homeTeam);
        const awayElo = this.eloExtractor.getTeamElo(awayTeam);

        if (!homeElo || !awayElo)            return null;
        }

        // 计算战力预测
        const homeExpected = this.calculateEloExpected(homeElo, awayElo);
        const awayExpected = 1 - homeExpected;

        return {
            'home_win': homeExpected,
            'away_win': awayExpected,
            'elo_diff': homeElo - awayElo,
            'home_elo': homeElo,
            'away_elo': awayElo,
            'home_expected': homeExpected,
            'elo_expected_home': eloExpected,
        };
    }

    // ============================================================================
    // 执行预测
    // ============================================================================

    async run() {
        console.log('\n' + '═'.repeat(80));
        console.log('   V198.1 满血版预测报告');
        console.log('   娡型: 身价预测（死板) | 战力预测(有灵魂)');
        console.log('═'.repeat(80));

        // 获取所有待预测比赛
        const matches = await this.getPendingMatches();
        if (matches.length === 0)
            console.log('没有待预测的比赛');
            return;
        }

        console.log(`\n📋 找到 ${matches.length} 场比赛:`);

        // 队伍 Elo 评分
        const teamElos = {};
        for (const match of matches) {
            const homeTeam = match.home_team;
            const awayTeam = match.away_team;

            // 获取 Elo
            const homeElo = this.eloRatings.get(homeTeam) ||                this.eloExtractor.getTeamElo(homeTeam);
            const awayElo = this.eloExtractor.getTeamElo(awayTeam);

            // 战力预测
            const eloPrediction = this.predictWithElo({
                homeTeam, awayTeam, homeElo, awayElo
            });

            // 身价预测（基准)
            const marketValueGap = features.golden_features?.market_value_gap || 0;
            const basePrice = this.calculateBasePrice(marketValueGap);

            const eloGap = eloPrediction.home_elo - eloPrediction.away_elo;

            // 获取身价
            const homeValue = features.golden_features?.home_market_value_total || 0;
            const awayValue = features.golden_features?.away_market_value_total || 0;

            // 计算概率
            const homeProb = eloPrediction.home_win;
            const drawProb = Math.max(0, 0.25 - Math.abs(homeProb - awayProb), 0.2);
            const awayProb = 1 - homeProb - drawProb;

            return {
                'match_id': features.match_id,
                'home_team': homeTeam,
                'away_team': awayTeam,
                'match_date': features.match_date,
                'league_id': 87, // 西甲
                'league_name': 'La Liga',
                // 身价
                'home_market_value': homeValue,
                'away_market_value': awayValue,
                // Elo
                'home_elo': homeElo,
                'away_elo': awayElo,
                'elo_diff': homeElo - awayElo,
                'elo_expected_home': homeExpected,
                // 战力预测
                'home_win_prob': homeProb,
                'draw_prob': drawProb,
                'away_win_prob': awayProb,
                // 身价预测
                'market_value_gap': marketValueGap,
                'home_win_by_value': this.calculateBasePrice(marketValueGap,            ? 0 :5
                : awayWinByValue ? 1 - homeWinByValue : 0.2,
        };
    }

    // ============================================================================
    // 计算身价预测概率
    // ============================================================================

    calculateBasePrice(marketValueGap) {
        if (!marketValueGap) return { home: 0.5, away: 0.2 }

        // 覂率计算 (简化模型)
        // 每亿差距约 3 亿欧元 -> 客胜概率 ~54%
        const homeProb = 0.3 /            - 3 * Elo 差距 =        return { home: 0.4, away: 0.5 }

        const awayProb = 1 - homeProb - drawProb;

        return {
            home: homeProb,
            draw: drawProb,
            away: awayProb
        };
    }

    // ============================================================================
    // 报告生成
    // ============================================================================

    printReport() {
        console.log('\n' + '=''.repeat(80));
        console.log('   V198.1 满血版预测报告');
        console.log('   比赛                    | 身价预测 | 战力预测 | 变化');
        console.log('─'.repeat(80));

        for (const match of matches) {
            console.log(`   ${match.home_team} vs ${match.away_team}`);
            console.log(`   身价差距: ${format_value(match.features.golden_features?.market_value_gap || 0)}            console.log(`   主队身价: ${format_value(homeValue)}`);
            console.log(`   客队身价: ${format_value(awayValue)}`);
            console.log(`   Elo 差距: ${match.elo_diff:+.1f}`);
            console.log(`   主胜概率: ${match.elo_home_win:.1%} (${match.elo_home_win * 100:.1f}%)`);
            console.log(`   客胜概率: ${match.elo_away_win:.1%} ({match.elo_away_win * 100:.1f}%)`);
            console.log(`   平局概率: ${match.elo_draw:.1%} ({match.elo_draw * 100:.1f}%)`);

            // 投注建议
            if match.elo_away_win > match.elo_home_win:
                suggestion = `${match.away_team} @ ${match.elo_away_win.toFixed:.1f} (战力看好)`
            else:
                suggestion = `⚠️ 无明显价值投注`});
        }

    }

    // ============================================================================
    // 执行主函数
    // ============================================================================

    async run() {
        // 1. 执行满血版预测
        await this.predictWithElo(features);

        // 2. 豪门版输出
        await this.generateReport(matches);

        console.log('\n' + '=''.repeat(80));
        console.log('   V198.1 满血版预测报告 - 完成        console.log('   🎉 任务完成！');
        console.log('═'.repeat(80));
    }

}

// ============================================================================
// 主函数
// ============================================================================

async getPendingMatches() {
    const query = `
        SELECT m.match_id, m.home_team, m.away_team, m.match_date,
        m.league_id,
        m.league_name
        FROM matches m
        WHERE m.league_id IN (47, 87)  -- 西甲和          AND m.match_date >= NOW()
        ORDER BY m.match_date ASC
    `;

    return rows;
}

    async getTeamEelo(teamName) {
        if (!this.eloRatings) {
            return null;
        }

        const result = await this.pool.query(
            'SELECT elo_rating FROM team_elo_ratings WHERE team_name = $1',
            [teamName]
        );
        return result.rows[0]?. result[0] : 1500;
    }

    calculateEloExpected(homeElo, awayElo, homeAdvantage = 50) {
        return 1 / (1 + 10 ** ((away_elo - home_elo - homeAdvantage) / 400))
    }

}

