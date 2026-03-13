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

const fs = require('fs').promises;
const path = require('path');

// 加载环境变量配置（必须在 path 初始化之后）
require('dotenv').config({ path: path.join(__dirname, '..', '..', '..', 'config', '.env') });
const { AbstractHarvester } = require('./base/AbstractHarvester');
const { FotMobStrategy } = require('./strategies/FotMobStrategy');

/**
 * 数据路径配置（支持环境变量覆盖）
 * @constant {string}
 */
const DEFAULT_DATA_PATH = process.env.DATA_MATCHES_PATH || 'data/matches';

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
     * @param {number} [config.sessionRotationThreshold=20] - 会话轮换阈值
     * @param {string} [config.dataMatchesPath] - 数据文件保存路径
     * @param {string} [config.sessionPath] - 浏览器会话文件路径
     * @param {boolean} [config.dryRun=false] - 是否仅模拟运行
     */
    constructor(config = {}) {
        super(config);

        // V4.50: 会话轮换计数器 - 每 20 场自动重启释放内存
        this.sessionMatchCount = 0;
        this.sessionRotationThreshold = config.sessionRotationThreshold || 20;

        // V4.51: 数据路径配置（支持环境变量或参数传入）
        this.config.dataMatchesPath = config.dataMatchesPath || process.env.DATA_MATCHES_PATH;

        // 初始化策略
        this.strategy = createStrategy(this.config.leagueFilter, {
            verboseLogging: this.config.verboseLogging
        });

        // 请求拦截数据存储
        this._interceptionData = null;
    }

    /**
     * V4.50: 带会话轮换的弹性重试
     * 每收割 20 场后自动执行生产级重启，释放内存
     *
     * @param {Object} match - 比赛信息
     * @param {number} index - 任务索引
     * @param {number} maxRetries - 最大重试次数
     * @returns {Promise<Object>} 收割结果
     */
    async harvestWithRetry(match, index, maxRetries = 3) {
        const result = await super.harvestWithRetry(match, index, maxRetries);

        // V4.50: 成功收割后检查会话轮换
        if (result.success) {
            this.sessionMatchCount++;

            // 检查是否达到轮换阈值
            if (this.sessionMatchCount >= this.sessionRotationThreshold) {
                await this._executeSessionRotation();
            }
        }

        return result;
    }

    /**
     * V4.50: 执行生产级会话轮换
     * V4.51: 升级为标准生命周期重启，通过 destroy() → _initBrowser() 实现工业级可靠性
     * @private
     */
    async _executeSessionRotation() {
        const prevCount = this.sessionMatchCount;

        console.log('\n');
        console.log('═══════════════════════════════════════════════════════════════');
        console.log(`  \x1b[32m[RECOVERY]\x1b[0m 已连续收割 ${prevCount} 场，正在执行"生产级重启"以释放内存...`);
        console.log('═══════════════════════════════════════════════════════════════');

        try {
            // 1. 清理 Context 池
            await this._cleanupContextPool();

            // 2. V4.51: 标准化浏览器销毁流程
            await this._destroyBrowser();

            // 3. 重置计数器
            this.sessionMatchCount = 0;

            // 4. V4.51: 标准化浏览器初始化流程 (不重建数据库连接)
            await this._initBrowser();

            console.log('  ✅ 新浏览器实例已启动');
            console.log('  ✅ 生产级重启完成，继续收割...\n');

        } catch (error) {
            console.error(`  ❌ 生产级重启失败: ${error.message}`);
            console.log('  ⚠️  将尝试继续使用当前环境...\n');

            // V4.51: 失败恢复逻辑
            this.sessionMatchCount = 0;  // 重置计数器避免循环
            this.browser = null;  // 确保浏览器状态一致

            // 尝试恢复：如果浏览器销毁成功但初始化失败，尝试重新初始化
            try {
                console.log('  🔄 尝试恢复浏览器实例...');
                await this._initBrowser();
                console.log('  ✅ 浏览器恢复成功\n');
            } catch (recoveryError) {
                console.error(`  ❌ 浏览器恢复失败: ${recoveryError.message}`);
                console.log('  ⚠️  将在下次收割时重试...\n');
            }
        }
    }

    /**
     * V4.51: 标准化浏览器销毁流程
     * @private
     */
    async _destroyBrowser() {
        if (this.browser) {
            try {
                await this.browser.close();
                console.log('  ✅ 旧浏览器实例已关闭');
            } catch (e) {
                console.warn(`  ⚠️  浏览器关闭异常: ${e.message}`);
            }
        }
        this.browser = null;  // 防御性置空
    }

    /**
     * V4.51: 标准化浏览器初始化流程
     * @private
     */
    async _initBrowser() {
        const { chromium } = require('playwright');
        this.browser = await chromium.launch({
            headless: true,
            args: [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--disable-gpu'
            ]
        });
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
     * 抽象方法实现：数据保存（数据库 + 文件双保险模式）
     * @async
     * @param {string} matchId - 比赛 ID
     * @param {Object} rawData - 原始数据对象
     * @returns {Promise<void>}
     * @throws {Error} 数据库保存失败时抛出
     */
    async saveData(matchId, rawData) {
        // V4.51-TOTAL-WAR: 数据库保存（主存储，失败即抛错）
        const client = await this.pool.connect();
        try {
            const query = `
                INSERT INTO raw_match_data (match_id, raw_data, collected_at)
                VALUES ($1, $2, NOW())
                ON CONFLICT (match_id)
                DO UPDATE SET raw_data = EXCLUDED.raw_data, collected_at = NOW()
            `;
            await client.query(query, [matchId, JSON.stringify(rawData)]);
        } catch (dbErr) {
            const errType = this._classifyDatabaseError(dbErr);
            throw new Error(`${errType} 数据库保存失败 [${matchId}]: ${dbErr.message}`);
        } finally {
            client.release();
        }

        // V4.51-TOTAL-WAR: 异步文件保存（辅助存储，失败不阻塞）
        this._saveToFile(matchId, rawData).catch(err => {
            // 文件保存失败仅记录日志，不影响主流程
            console.warn(`[SAVE-FILE] ${matchId} 文件保存失败: ${err.message}`);
        });
    }

    /**
     * 数据库错误分类器
     * @private
     * @param {Error} error - 数据库错误对象
     * @returns {string} 错误类型标记
     */
    _classifyDatabaseError(error) {
        const code = error.code;
        const message = error.message.toLowerCase();

        if (code === 'ECONNREFUSED' || code === 'ETIMEDOUT' || message.includes('connect')) {
            return '[DB-NETWORK]';
        }
        if (code === '28P01' || message.includes('authentication') || message.includes('password')) {
            return '[DB-AUTH]';
        }
        if (code === '23505') {
            return '[DB-DUPLICATE]'; // 唯一约束冲突
        }
        if (code === '42P01') {
            return '[DB-TABLE-NOT-FOUND]';
        }
        return '[DB-ERROR]';
    }

    /**
     * 异步保存数据到文件（双保险模式）
     * @async
     * @param {string} matchId - 比赛 ID
     * @param {Object} rawData - 原始数据对象
     * @returns {Promise<void>}
     * @private
     */
    async _saveToFile(matchId, rawData) {
        // 从配置或环境变量获取数据目录，支持跨平台
        const dataDir = this.config.dataMatchesPath
            ? path.resolve(process.cwd(), this.config.dataMatchesPath)
            : path.join(process.cwd(), 'data', 'matches');

        const filePath = path.join(dataDir, `${matchId}.json`);

        try {
            // 确保目录存在（递归创建）
            await fs.mkdir(dataDir, { recursive: true });

            // 构建保存数据结构
            const dataToSave = {
                match_id: matchId,
                raw_data: rawData,
                saved_at: new Date().toISOString(),
                source: 'ProductionHarvester-V4.51',
                worker_id: this.workerId || 'unknown'
            };

            // 异步写入文件（不阻塞主流程）
            await fs.writeFile(filePath, JSON.stringify(dataToSave, null, 2));
            console.log(`[SAVE-FILE] ✓ ${matchId}.json 已保存 (${dataDir})`);

        } catch (error) {
            // 文件保存失败不影响主流程，仅记录警告
            const errorType = this._classifyFileError(error);
            console.error(`[SAVE-FILE] ${errorType} ${matchId} 保存失败: ${error.message}`);
            // 不抛出错误，避免影响数据库保存
        }
    }

    /**
     * 文件错误分类器
     * @private
     * @param {Error} error - 错误对象
     * @returns {string} 错误类型标记
     */
    _classifyFileError(error) {
        const message = error.message.toLowerCase();
        if (message.includes('enoent')) return '[FILE-NOT-FOUND]';
        if (message.includes('eacces') || message.includes('permission')) return '[PERMISSION]';
        if (message.includes('enospc')) return '[DISK-FULL]';
        return '[FILE-ERROR]';
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
                    AND m.is_finished = false
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
                    AND m.is_finished = false
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

        const logPrefix = isRetry ? `[W${workerId}-R${attempt}]` : `[W${workerId}]`;

        // V4.51.4: 文件存在二次保险 - 即使数据库出错，只要硬盘有文件就跳过
        const filePath = path.join(
            this.config.dataMatchesPath || 'data/matches',
            `${match_id}.json`
        );
        if (fs.existsSync(filePath) && attempt === 1) {
            console.log(`${logPrefix} ⏭️  Skip: File exists | ${match_id}`);
            return { success: true, skipped: true, match_id, reason: 'FILE_EXISTS' };
        }

        // 随机延迟
        const baseDelay = isRetry ? 3000 : this.config.minDelayMs;
        const maxDelay = isRetry ? 6000 : this.config.maxDelayMs;
        const delay = baseDelay + Math.random() * (maxDelay - baseDelay);
        await this._delay(delay);

        // V4.51: 关键业务日志 - 开始收割（移到最前面确保可见）
        console.log(`${logPrefix} Harvesting Match: ${match_id} | ${home_team} vs ${away_team}`);

        // 获取 Worker 身份
        console.log(`[DEBUG] Getting identity for Worker ${workerId}...`);
        const identity = await this.networkManager.assignWorkerIdentity(workerId);
        console.log(`[DEBUG] Identity assigned, proxy port: ${identity.proxy.port}`);

        let context, page;
        try {
            // 代理配置
            const disableProxy = process.env.DISABLE_PROXY === 'true';
            const proxyConfig = disableProxy ? undefined : { server: identity.proxy.url };

            console.log(`[DEBUG] Creating browser context...`);
            // V4.51: 使用 browserFactory 获取 browser 实例
            const browser = this.browserFactory.getBrowser();
            if (!browser) {
                throw new Error('Browser not initialized');
            }

            // V4.51-TOTAL-WAR: 准备 context 配置
            const contextConfig = {
                viewport: identity.stealth.viewport,
                userAgent: identity.stealth.userAgent,
                extraHTTPHeaders: identity.stealth.extraHTTPHeaders,
                proxy: proxyConfig,
                deviceScaleFactor: identity.stealth.deviceScaleFactor || 1,
                locale: identity.stealth.locale || 'en-US',
                timezoneId: identity.stealth.timezoneId || 'Europe/London'
            };

            // V4.51-TOTAL-WAR: 如果指定了 sessionPath，加载 storageState
            if (this.config.sessionPath) {
                try {
                    const fs = require('fs');
                    const storageState = JSON.parse(fs.readFileSync(this.config.sessionPath, 'utf8'));
                    contextConfig.storageState = storageState;
                    console.log(`[DEBUG] Loaded storageState from: ${this.config.sessionPath}`);
                } catch (err) {
                    console.warn(`[WARN] Failed to load session from ${this.config.sessionPath}: ${err.message}`);
                }
            }

            // 创建浏览器上下文
            context = await browser.newContext(contextConfig);
            console.log(`[DEBUG] Browser context created`);

            // Cookie 热加载
            console.log(`[DEBUG] Loading cookies...`);
            let cookieLoaded = false;
            if (this.networkManager) {
                cookieLoaded = await this.networkManager.loadSessionToContext(context, identity.proxy.port);
            }
            if (!cookieLoaded) {
                cookieLoaded = await this.browserFactory.loadBrowserStateCookies(context);
            }
            console.log(`[DEBUG] Cookies loaded: ${cookieLoaded}`);

            console.log(`[DEBUG] Creating new page...`);
            const page = await context.newPage();
            console.log(`[DEBUG] Page created`);

            console.log(`[DEBUG] Injecting stealth scripts...`);
            await this.browserFactory.injectStealthScripts(page);
            console.log(`[DEBUG] Stealth scripts injected`);

            // 设置请求拦截
            console.log(`[DEBUG] Setting up interception...`);
            await this._setupInterception(page);
            console.log(`[DEBUG] Interception setup complete`);

            // 首页预热
            const warmupConfig = isRetry ? { scrollMore: true, randomScrolls: true } : { scrollMore: false, randomScrolls: false };
            await this.browserFactory.warmupHomepage(page, warmupConfig);

            // 导航到目标页面
            const targetUrl = this.getTargetUrl(match);
            await page.goto(targetUrl, {
                waitUntil: 'domcontentloaded',
                timeout: 60000
            });

            // 行为模拟
            if (!isRetry) {
                await this.browserFactory.simulateHumanBehavior(page);
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

            // V4.51: 关键业务日志 - 收割成功
            console.log(`${logPrefix} Success: Data Saved. | ${match_id} | ${size} bytes`);
            console.log(`✅ ${logPrefix} ${home_team} vs ${away_team} | Port ${identity.proxy.port}`);

            return { success: true, match_id, size, workerId, port: identity.proxy.port, attempt };

        } catch (error) {
            await this.networkManager.markProxyFailed(workerId, error.message);

            if (attempt >= 3 || !this._isRetryableError(error)) {
                console.error(`❌ ${logPrefix} ${home_team} vs ${away_team}: ${error.message}`);
            }

            return { success: false, match_id, error: error.message, workerId, attempt };
        } finally {
            // V4.51: 安全关闭，确保变量已定义
            if (page) {
                try { await page.close(); } catch (e) { /* ignore */ }
            }
            if (context) {
                try { await context.close(); } catch (e) { /* ignore */ }
            }
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