/**
 * ProductionHarvester - 精简版收割指挥部
 * =======================================
 *
 * TITAN-DECOUPLING-STAGE 重构结果：
 * - 从 1309 行缩减至 ~250 行
 * - 基于 AbstractHarvester 基类
 * - 使用 Strategy 模式动态加载收割策略
 * - 零 CSS/API 硬编码，纯协调逻辑
 *
 * @module infrastructure/harvesters/ProductionHarvester
 * @version V4.46-TITAN
 */

'use strict';

const { AbstractHarvester } = require('./base/AbstractHarvester');
const { FotMobStrategy } = require('./strategies/FotMobStrategy');

// ============================================================================
// Strategy 工厂
// ============================================================================

/**
 * 策略工厂 - 根据联赛名称返回对应策略
 * @param {string} league - 联赛名称
 * @param {Object} config - 配置选项
 * @returns {Object} 收割策略实例
 */
function createStrategy(league, config = {}) {
    // 当前仅支持 FotMob 策略
    // 未来可扩展：BundesligaStrategy, PremierLeagueStrategy 等
    return new FotMobStrategy(config);
}

// ============================================================================
// ProductionHarvester 类
// ============================================================================

class ProductionHarvester extends AbstractHarvester {
    /**
     * 创建 ProductionHarvester 实例
     * @param {Object} [config={}] - 配置选项
     */
    constructor(config = {}) {
        super(config);

        // 初始化策略
        this.strategy = createStrategy(this.config.leagueFilter, {
            verboseLogging: this.config.verboseLogging
        });

        // 请求拦截数据存储
        this._interceptionData = null;
    }

    /**
     * 抽象方法实现：获取目标 URL
     * 委托给 Strategy
     * @param {Object} match - 比赛信息
     * @returns {string} 目标 URL
     */
    getTargetUrl(match) {
        return this.strategy.getTargetUrl(match);
    }

    /**
     * 抽象方法实现：数据提取逻辑
     * 委托给 Strategy 处理页面数据提取
     * @param {import('playwright').Page} page - Playwright Page 对象
     * @param {Object} match - 比赛信息
     * @returns {Promise<Object>} 提取的数据
     */
    async extractData(page, match) {
        return this.strategy.extractData(page, match, this._interceptionData);
    }

    /**
     * 抽象方法实现：数据保存
     * @param {string} matchId - 比赛 ID
     * @param {Object} rawData - 原始数据对象
     */
    async saveData(matchId, rawData) {
        const client = await this.pool.connect();
        try {
            const query = `
                INSERT INTO raw_match_data (match_id, raw_data, collected_at)
                VALUES ($1, $2, NOW())
                ON CONFLICT (match_id)
                DO UPDATE SET raw_data = EXCLUDED.raw_data, collected_at = NOW()
            `;
            await client.query(query, [matchId, JSON.stringify(rawData)]);
        } finally {
            client.release();
        }
    }

    /**
     * 获取待收割的比赛列表
     * @returns {Promise<Array>} 比赛列表
     */
    async getPendingMatches() {
        const serieAPilot = process.env.SERIE_A_PILOT === 'true';

        let query, params;

        if (serieAPilot) {
            query = `
                SELECT
                    m.match_id,
                    m.external_id,
                    m.home_team,
                    m.away_team,
                    m.match_date
                FROM matches m
                LEFT JOIN raw_match_data r ON m.match_id = r.match_id
                WHERE r.match_id IS NULL
                    AND m.league_name = 'Serie A'
                    AND m.status = 'FINISHED'
                ORDER BY m.match_date DESC
                LIMIT 10
            `;
            params = [];
            console.log('🇮🇹 SERIE-A-PILOT 模式: 只收割意甲最近 10 场已结束比赛');
        } else {
            query = `
                SELECT
                    m.match_id,
                    m.external_id,
                    m.home_team,
                    m.away_team,
                    m.match_date
                FROM matches m
                LEFT JOIN raw_match_data r ON m.match_id = r.match_id
                WHERE r.match_id IS NULL
                ORDER BY m.match_date DESC
                LIMIT $1
            `;
            params = [this.config.batchSize || 500];
        }

        const result = await this.pool.query(query, params);
        return result.rows;
    }

    /**
     * 设置请求拦截
     * 在单场收割前调用，初始化拦截器
     * @param {import('playwright').Page} page - Playwright Page 对象
     */
    async _setupInterception(page) {
        this._interceptionData = await this.strategy.setupRequestInterception(page);
    }

    /**
     * 重写单场收割，添加请求拦截设置
     * @param {Object} match - 比赛信息
     * @param {number} index - 任务索引
     * @param {number} attempt - 当前尝试次数
     * @returns {Promise<Object>} 收割结果
     * @private
     */
    async _harvestSingleMatch(match, index, attempt = 1) {
        const { match_id, home_team, away_team } = match;
        const workerId = (index % this.config.maxWorkers) + 1;
        const isRetry = attempt > 1;

        // 随机延迟
        const baseDelay = isRetry ? 3000 : this.config.minDelayMs;
        const maxDelay = isRetry ? 6000 : this.config.maxDelayMs;
        const delay = baseDelay + Math.random() * (maxDelay - baseDelay);
        await this._delay(delay);

        // 获取 Worker 身份
        const identity = await this.networkManager.assignWorkerIdentity(workerId);

        // 代理配置
        const disableProxy = process.env.DISABLE_PROXY === 'true';
        const proxyConfig = disableProxy ? undefined : { server: identity.proxy.url };

        // 创建浏览器上下文
        const context = await this.browser.newContext({
            viewport: identity.stealth.viewport,
            userAgent: identity.stealth.userAgent,
            extraHTTPHeaders: identity.stealth.extraHTTPHeaders,
            proxy: proxyConfig,
            deviceScaleFactor: identity.stealth.deviceScaleFactor || 1,
            locale: identity.stealth.locale || 'en-US',
            timezoneId: identity.stealth.timezoneId || 'Europe/London'
        });

        // Cookie 热加载
        let cookieLoaded = false;
        if (this.networkManager) {
            cookieLoaded = await this.networkManager.loadSessionToContext(context, identity.proxy.port);
        }
        if (!cookieLoaded) {
            cookieLoaded = await this._loadBrowserStateCookies(context);
        }

        const page = await context.newPage();
        await this._injectStealthScripts(page);

        // 设置请求拦截
        await this._setupInterception(page);

        const logPrefix = isRetry ? `[W${workerId}-R${attempt}]` : `[W${workerId}]`;

        try {
            // 首页预热
            const warmupConfig = isRetry ? { scrollMore: true, randomScrolls: true } : { scrollMore: false, randomScrolls: false };
            await this._warmupHomepage(page, warmupConfig);

            // 导航到目标页面
            const targetUrl = this.getTargetUrl(match);
            await page.goto(targetUrl, {
                waitUntil: 'domcontentloaded',
                timeout: 60000
            });

            // 行为模拟
            if (!isRetry) {
                await this._simulateHumanBehavior(page);
            } else {
                const moves = this._randomInRange(3, 5);
                for (let i = 0; i < moves; i++) {
                    await page.mouse.move(
                        this._randomInRange(100, 1800),
                        this._randomInRange(100, 900),
                        { steps: 5 }
                    );
                    await this._delay(200);
                }
            }

            await page.waitForTimeout(isRetry ? 3000 : 5000);

            // 提取数据（委托给 Strategy）
            const capturedData = await this.extractData(page, match);

            // 验证数据
            if (!capturedData) {
                throw new Error('NO_DATA:无法获取数据');
            }

            const size = JSON.stringify(capturedData).length;
            if (size < 1000) {
                throw new Error(`SIZE_TOO_SMALL:${size}`);
            }

            // 标记代理成功
            await this.networkManager.markProxySuccess(workerId);

            // 保存数据
            if (!this.config.dryRun) {
                await this.saveData(match_id, capturedData);
            }

            console.log(`✅ ${logPrefix} ${home_team} vs ${away_team} | ${size} bytes | Port ${identity.proxy.port}`);

            return { success: true, match_id, size, workerId, port: identity.proxy.port, attempt };

        } catch (error) {
            await this.networkManager.markProxyFailed(workerId, error.message);

            if (attempt >= 3 || !this._isRetryableError(error)) {
                console.error(`❌ ${logPrefix} ${home_team} vs ${away_team}: ${error.message}`);
            }

            return { success: false, match_id, error: error.message, workerId, attempt };
        } finally {
            await page.close();
            await context.close();
            // 重置拦截数据
            this._interceptionData = null;
        }
    }

    /**
     * 执行多轮收割直到 100% 成功率
     * @param {Object} [options={}] - 收割选项
     * @param {string} [options.matchId] - 单场比赛 ID
     * @param {boolean} [options.force=false] - 强制收割已收割的比赛
     * @returns {Promise<Object>} 收割结果
     */
    async run(options = {}) {
        const { matchId, force = false } = options;

        if (matchId) {
            return this._runSingleMatch(matchId, force);
        }

        return this._runBatch();
    }

    /**
     * 批量收割模式
     * @returns {Promise<Object>} 收割结果
     * @private
     */
    async _runBatch() {
        this.startTime = Date.now();

        console.log('═══════════════════════════════════════════════════════════════');
        console.log(`  V4.46-TITAN 无人值守收割引擎`);
        console.log('  策略模式 | 22 节点代理池 | 6 Worker 集群 | 弹性重试');
        console.log('═══════════════════════════════════════════════════════════════');

        while (true) {
            this.stats.sweepRounds++;
            const matches = await this.getPendingMatches();
            this.stats.total = matches.length;

            if (matches.length === 0) {
                console.log('🎉 所有比赛收割完成！');
                break;
            }

            console.log(`📋 第 ${this.stats.sweepRounds} 轮: 待收割 ${matches.length} 场`);

            if (this.config.dryRun) {
                console.log('⚠️ DRY RUN 模式 - 不会写入数据库');
            }

            // 使用 WorkerPool 进行并发收割
            const results = await this.workerPool.executeAll(
                matches,
                (match, index) => this.harvestWithRetry(match, index)
            );

            // 统计本轮结果
            let roundSuccess = 0;
            let roundFailed = 0;
            for (const result of results) {
                this.stats.processed++;
                if (result.success) {
                    this.stats.success++;
                    roundSuccess++;
                } else {
                    this.stats.failed++;
                    roundFailed++;
                }
            }

            const roundRate = matches.length > 0
                ? ((roundSuccess / matches.length) * 100).toFixed(1)
                : '0.0';

            console.log(`📊 第 ${this.stats.sweepRounds} 轮: 成功 ${roundSuccess}/${matches.length} (${roundRate}%)`);

            if (roundFailed === 0) {
                console.log('✅ 本轮 100% 成功，收割完成');
                break;
            }

            console.log(`🔄 检测到 ${roundFailed} 场失败，准备下一轮扫尾...`);
            await this._delay(5000);
        }

        this.printReport();
        return {
            total: this.stats.total,
            success: this.stats.success,
            failed: this.stats.failed
        };
    }

    /**
     * 单场比赛收割模式
     * @param {string} matchId - 比赛 ID 或 external_id
     * @param {boolean} [force=false] - 强制收割已收割的比赛
     * @returns {Promise<Object>} 收割结果
     * @private
     */
    async _runSingleMatch(matchId, force = false) {
        this.startTime = Date.now();
        this.stats.sweepRounds = 1;

        console.log('═══════════════════════════════════════════════════════════════');
        console.log(`  V4.46-TITAN 单场比赛收割模式`);
        console.log(`  MatchID: ${matchId} | Force: ${force}`);
        console.log('═══════════════════════════════════════════════════════════════');

        // 查询比赛信息
        let query = `
            SELECT
                m.match_id,
                m.external_id,
                m.home_team,
                m.away_team,
                m.match_date
            FROM matches m
            WHERE m.match_id = $1 OR m.external_id = $1
        `;

        if (!force) {
            query = `
                SELECT
                    m.match_id,
                    m.external_id,
                    m.home_team,
                    m.away_team,
                    m.match_date
                FROM matches m
                LEFT JOIN raw_match_data r ON m.match_id = r.match_id
                WHERE (m.match_id = $1 OR m.external_id = $1)
                    AND r.match_id IS NULL
            `;
        }

        const result = await this.pool.query(query, [matchId]);

        let match;
        if (result.rows.length === 0) {
            // 直接收割模式 - 比赛不在数据库中
            console.log(`📡 比赛不在数据库中，启用直接收割模式...`);

            let externalId;
            if (/^\d+$/.test(matchId)) {
                externalId = matchId;
            } else if (matchId.includes('_')) {
                const parts = matchId.split('_');
                externalId = parts[parts.length - 1];
            } else {
                externalId = matchId;
            }

            match = {
                match_id: matchId,
                external_id: externalId,
                home_team: 'Unknown',
                away_team: 'Unknown',
                match_date: new Date()
            };

            console.log(`📋 比赛: External ID ${match.external_id}`);
        } else {
            match = result.rows[0];
            console.log(`📋 比赛: ${match.home_team} vs ${match.away_team}`);
        }

        this.stats.total = 1;

        // 执行收割
        const harvestResult = await this.harvestWithRetry(match, 0, this.config.maxRetries);

        if (harvestResult.success) {
            this.stats.success = 1;
            this.stats.processed = 1;
            console.log(`✅ 收割成功: ${match.home_team} vs ${match.away_team}`);
        } else {
            this.stats.failed = 1;
            this.stats.processed = 1;
            console.error(`❌ 收割失败: ${harvestResult.error}`);
        }

        this.printReport();

        return {
            total: 1,
            success: this.stats.success,
            failed: this.stats.failed,
            matchId,
            error: harvestResult.success ? null : harvestResult.error
        };
    }
}

// ============================================================================
// CLI 启动逻辑
// ============================================================================

if (require.main === module) {
    const args = process.argv.slice(2);
    const options = {
        matchId: null,
        force: false,
        verbose: false
    };

    for (const arg of args) {
        if (arg.startsWith('--matchId=')) {
            options.matchId = arg.split('=')[1];
        } else if (arg === '--force' || arg === '-f') {
            options.force = true;
        } else if (arg === '--verbose' || arg === '-v') {
            options.verbose = true;
        }
    }

    console.log('🚀 [IGNITION] Starting ProductionHarvester V4.46-TITAN...');
    console.log('📊 Options:', JSON.stringify(options, null, 2));

    (async () => {
        const harvester = new ProductionHarvester({
            verboseLogging: options.verbose
        });

        try {
            console.log('🔧 [IGNITION] 初始化收割器...');
            await harvester.init();

            console.log('🔥 [IGNITION] 开始收割...');
            const result = await harvester.run({
                matchId: options.matchId,
                force: options.force
            });

            console.log('✅ [IGNITION] Harvest completed!');
            console.log('📊 Result:', JSON.stringify(result, null, 2));

            await harvester.cleanup();
            process.exit(0);
        } catch (err) {
            console.error('💥 [IGNITION] Fatal error:', err);
            console.error('📊 Stack:', err.stack);
            process.exit(1);
        }
    })();
}

module.exports = { ProductionHarvester, createStrategy };