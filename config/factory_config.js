/**
 * V178 工厂级配置中心 (终极强化版)
 * ==============================================
 *
 * 所有收割系统的魔术数字统一归口管理
 * 严禁在业务代码中硬编码任何参数
 *
 * V178 升级:
 * - 熔断器配置升级: 5 次失败触发, 60 秒冷却
 * - 指数退避优化: 1s -> 2s -> 4s (带 ±20% 抖动)
 *
 * @module config/factory_config
 * @version V178.0.0 (Ultimate Hardening Edition)
 */

'use strict';

// ============================================================================
// 环境变量优先级
// ============================================================================

const ENV = process.env;

// ============================================================================
// 质量门禁配置 (Quality Gate)
// ============================================================================

const QUALITY_GATE = {
    /** 最小有效数据体积 (bytes) - 小于此值视为非法数据 */
    minSizeBytes: parseInt(ENV.MIN_SIZE_BYTES) || 5000,

    /** 未来比赛最小数据体积 (bytes) - 对于没有 stats 的比赛使用更低阈值 */
    minSizeBytesFuture: parseInt(ENV.MIN_SIZE_BYTES_FUTURE) || 3000,

    /** 最大数据体积 (bytes) - 用于异常检测 */
    maxSizeBytes: parseInt(ENV.MAX_SIZE_BYTES) || 10 * 1024 * 1024,  // 10MB

    /** 必须包含的 JSON 路径 */
    requiredPaths: ['content'],

    /** 禁止包含的错误关键词 - V173: 只检测明确的 API 错误响应 */
    errorKeywords: ['TURNSTILE_REQUIRED', 'Verification required', 'ACCESS_DENIED', 'CAPTCHA', 'cf-browser-verification', 'challenge-platform'],

    /**
     * 验证数据是否有效
     * V175: 对于未来比赛（没有 stats）使用更低的阈值
     * @param {object} rawData - 原始数据
     * @returns {{valid: boolean, reason?: string, size?: number}}
     */
    isValid(rawData) {
        if (!rawData) return { valid: false, reason: 'NULL_DATA' };

        const jsonStr = JSON.stringify(rawData);
        const size = jsonStr.length;

        // V175: 检查是否有 stats 数据
        const hasStats = rawData.content &&
            rawData.content.stats &&
            Object.keys(rawData.content.stats).length > 0;

        // 根据是否有 stats 选择不同的阈值
        const minSize = hasStats ? this.minSizeBytes : this.minSizeBytesFuture;

        // 体积检查
        if (size < minSize) {
            return { valid: false, reason: 'SIZE_TOO_SMALL', size, hasStats };
        }

        // 结构检查
        for (const path of this.requiredPaths) {
            if (!rawData[path]) {
                return { valid: false, reason: `MISSING_${path.toUpperCase()}` };
            }
        }

        // V173: 智能错误关键字检查
        // 只检查核心数据区域，忽略翻译文本（translations）
        const coreData = {
            content: rawData.content,
            general: rawData.general,
            header: rawData.header
        };
        const coreStr = JSON.stringify(coreData).toLowerCase();

        for (const keyword of this.errorKeywords) {
            if (coreStr.includes(keyword.toLowerCase())) {
                return { valid: false, reason: `CONTAINS_${keyword.toUpperCase()}` };
            }
        }

        return { valid: true, size, hasStats };
    }
};

// ============================================================================
// 延时配置 (Timing)
// ============================================================================

const TIMING = {
    /** 单场收割最小延时 (ms) - V173: 默认 10s 潜行频率 */
    minDelayMs: parseInt(ENV.MIN_DELAY_MS) || 10000,

    /** 单场收割最大延时 (ms) - V173: 默认 15s 潜行频率 */
    maxDelayMs: parseInt(ENV.MAX_DELAY_MS) || 15000,

    /** 首页预热延时范围 [min, max] (ms) */
    preVisitDelay: [3000, 6000],

    /** 页面等待延时范围 [min, max] (ms) */
    pageDelay: [5000, 10000],

    /** 阅读延时范围 [min, max] (ms) - 模拟真人阅读 */
    readDelay: [3000, 7000],

    /** API 请求超时 (ms) */
    apiTimeout: parseInt(ENV.API_TIMEOUT) || 30000,

    /** 页面加载超时 (ms) */
    pageTimeout: parseInt(ENV.PAGE_TIMEOUT) || 60000
};

// ============================================================================
// 重试配置 (Retry)
// ============================================================================

const RETRY = {
    /** 最大重试次数 */
    maxAttempts: parseInt(ENV.MAX_RETRY_ATTEMPTS) || 3,

    /** 重试延时范围 [min, max] (ms) */
    delayRange: [5000, 10000],

    /** 指数退避基数 */
    backoffBase: parseInt(ENV.BACKOFF_BASE) || 2,

    /** 最大退避时间 (ms) */
    maxBackoffMs: parseInt(ENV.MAX_BACKOFF_MS) || 60000,

    /** 可重试的错误类型 */
    retryableErrors: [
        'SIZE_TOO_SMALL',
        'TURNSTILE_REQUIRED',
        'NETWORK_ERROR',
        'TIMEOUT',
        'ECONNRESET',
        'ENOTFOUND',
        'NO_NEXT_DATA',
        'DATA_TRANSFORM_FAILED',
        'CF_BLOCK'  // V173: Cloudflare 拦截也尝试重试（会自动切换端口）
    ],

    /** 不可重试的错误类型 (永久失败) */
    nonRetryableErrors: [
        'MATCH_NOT_FOUND',
        'INVALID_ID',
        'ACCESS_DENIED'
    ],

    /**
     * 判断错误是否可重试
     * @param {string} errorType - 错误类型
     * @returns {boolean}
     */
    isRetryable(errorType) {
        return this.retryableErrors.some(e =>
            errorType.includes(e) || e.includes(errorType)
        );
    }
};

// ============================================================================
// 并发配置 (Concurrency)
// ============================================================================

const CONCURRENCY = {
    /** 最大 Worker 数量 - V173: 默认 1 (最稳模式) */
    maxWorkers: parseInt(ENV.MAX_WORKERS) || 1,

    /** 每批次任务数 */
    batchSize: parseInt(ENV.BATCH_SIZE) || 50,

    /** Worker 错峰启动间隔 (ms) */
    staggerStartMs: parseInt(ENV.STAGGER_START_MS) || 5000,

    /** 监控检查间隔 (ms) */
    monitorIntervalMs: parseInt(ENV.MONITOR_INTERVAL_MS) || 1000
};

// ============================================================================
// 代理配置 (Proxy) - V173-OVERHAUL: 22 个独立 IP 火力全开
// ============================================================================

const PROXY_CONFIG = {
    /**
     * V173-OVERHAUL: 22 个独立 IP 代理端口池
     * 端口范围: 7890 - 7911 (共 22 个)
     * 每个端口对应一个独立 IP 地址
     */
    ports: (() => {
        // 优先使用环境变量
        if (ENV.PROXY_PORTS) {
            return ENV.PROXY_PORTS.split(',')
                .map(p => parseInt(p.trim()))
                .filter(p => !isNaN(p));
        }
        // V173: 默认 22 个端口，火力全开！
        return Array.from({ length: 22 }, (_, i) => 7890 + i);
    })(),

    /** 默认代理端口 */
    defaultPort: parseInt(ENV.PROXY_PORT) || 7890,

    /** 代理服务器地址模板 - V174-TUNING: 使用直接 IP 地址提高稳定性 */
    serverTemplate: ENV.PROXY_SERVER || 'http://172.25.16.1:{port}',

    /** 代理健康检查超时 (ms) */
    healthCheckTimeout: parseInt(ENV.PROXY_HEALTH_TIMEOUT) || 10000,

    /**
     * 获取代理服务器地址
     * @param {number} port - 代理端口
     * @returns {string} 代理服务器地址
     */
    getServer(port = this.defaultPort) {
        return this.serverTemplate.replace('{port}', port);
    },

    /**
     * V173-OVERHAUL: 根据 Worker ID 完美映射到 22 个端口
     * @param {number} workerId - Worker 编号 (1-based)
     * @returns {number} 代理端口
     */
    getPortByWorker(workerId) {
        // Worker ID 是 1-based，端口数组是 0-based
        const index = (workerId - 1) % this.ports.length;
        return this.ports[index];
    },

    /**
     * V173-OVERHAUL: 获取下一个可用端口 (用于故障切换)
     * @param {number} currentPort - 当前端口
     * @returns {number} 下一个端口
     */
    getNextPort(currentPort) {
        const currentIndex = this.ports.indexOf(currentPort);
        const nextIndex = (currentIndex + 1) % this.ports.length;
        return this.ports[nextIndex];
    },

    /**
     * V173-OVERHAUL: 获取随机端口 (用于分散压力)
     * @returns {number} 随机端口
     */
    getRandomPort() {
        return this.ports[Math.floor(Math.random() * this.ports.length)];
    },

    /**
     * V172-STRENGTHEN: 动态扩展端口池
     * @param {number} count - 需要的端口数量
     */
    expandPorts(count) {
        const currentMax = Math.max(...this.ports);
        while (this.ports.length < count) {
            this.ports.push(currentMax + this.ports.length);
        }
    },

    /**
     * V173-OVERHAUL: 打印端口池状态
     */
    printStatus() {
        console.log(`📡 代理池状态: ${this.ports.length} 个独立 IP 就绪`);
        console.log(`   端口范围: ${this.ports[0]} - ${this.ports[this.ports.length - 1]}`);
    }
};

// ============================================================================
// 熔断配置 (Circuit Breaker) - V178: 5 次 403/超时触发, 60 秒冷却
// ============================================================================

const CIRCUIT_BREAKER = {
    /** 连续失败次数阈值 - V178: 从 3 提升到 5 */
    threshold: parseInt(ENV.CIRCUIT_BREAKER_THRESHOLD) || 5,

    /** Worker 重启延迟 (ms) */
    restartDelayMs: parseInt(ENV.WORKER_RESTART_DELAY_MS) || 30000,

    /** 冷却期 (ms) - V178: 60 秒冷却 */
    cooldownMs: parseInt(ENV.CIRCUIT_COOLDOWN) || 60000,

    /** 半开状态测试请求数 - V178: 从 1 提升到 3 */
    halfOpenRequests: 3,

    /** 成功恢复阈值 - V178: 半开状态成功 1 次即恢复 */
    successThreshold: 1
};

// ============================================================================
// 数据库配置 (Database) - V174: 优化连接池支持高并发
// ============================================================================

const DATABASE = {
    /** 连接超时 (ms) */
    connectTimeout: parseInt(ENV.DB_CONNECT_TIMEOUT) || 10000,

    /** 查询超时 (ms) */
    queryTimeout: parseInt(ENV.DB_QUERY_TIMEOUT) || 30000,

    /** 连接池最大连接数 - V174: 20 支持高并发 */
    poolMax: parseInt(ENV.DB_POOL_MAX) || 20,

    /** 连接池最小连接数 */
    poolMin: parseInt(ENV.DB_POOL_MIN) || 5,

    /** 连接空闲超时 (ms) - V174: 30 秒 */
    idleTimeoutMillis: parseInt(ENV.DB_IDLE_TIMEOUT) || 30000
};

// ============================================================================
// 浏览器配置 (Browser)
// ============================================================================

const BROWSER = {
    /** 浏览器配置文件路径 */
    profilePath: ENV.BROWSER_PROFILE_PATH || '/app/data/browser_profile',

    /** 浏览器状态文件名 */
    stateFilename: 'browser_state.json',

    /** Cookie 保存间隔 (每 N 场比赛保存一次) */
    cookieSaveInterval: parseInt(ENV.COOKIE_SAVE_INTERVAL) || 3,

    /** 是否无头模式 */
    headless: ENV.HEADLESS !== 'false',

    /** 浏览器启动参数 */
    launchArgs: [
        '--disable-blink-features=AutomationControlled',
        '--disable-dev-shm-usage',
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-web-security',
        '--disable-features=IsolateOrigins,site-per-process',
        '--disable-infobars',
        '--disable-breakpad',
        '--disable-component-update',
        '--disable-default-apps'
    ],

    /**
     * 获取浏览器状态文件完整路径
     * @returns {string}
     */
    getStatePath() {
        const path = require('path');
        return path.join(this.profilePath, this.stateFilename);
    }
};

// ============================================================================
// 行为模拟配置 (Behavior Simulation)
// ============================================================================

const BEHAVIOR = {
    /** 滚动次数范围 [min, max] */
    scrollSteps: [2, 4],

    /** 鼠标移动次数范围 [min, max] */
    mouseMoves: [3, 6],

    /** 鼠标移动步数范围 [min, max] */
    mouseSteps: [5, 15],

    /** 滚动距离范围 [min, max] (px) */
    scrollDistance: [100, 300],

    /** 滚动间隔范围 [min, max] (ms) */
    scrollInterval: [500, 1500],

    /** 鼠标移动间隔范围 [min, max] (ms) */
    mouseInterval: [200, 800]
};

// ============================================================================
// 静态指纹配置 (Fingerprint)
// ============================================================================

const FINGERPRINT = {
    /** 静态指纹 (与会话镜像一致) */
    static: {
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36',
        viewport: { width: 1287, height: 1271 },
        deviceScaleFactor: 1,
        locale: 'zh-CN',
        timezoneId: 'Asia/Shanghai',
        platform: 'Win32',
        hardwareConcurrency: 24,
        deviceMemory: 8,
        webgl: {
            vendor: 'Google Inc. (AMD)',
            renderer: 'ANGLE (AMD, AMD Radeon(TM) Graphics (0x000013C0) Direct3D11 vs_5_0 ps_5_0, D3D11)'
        }
    },

    /** 随机指纹池 */
    pool: [
        {
            userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            viewport: { width: 1920, height: 1080 },
            deviceScaleFactor: 1,
            platform: 'Win32'
        },
        {
            userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
            viewport: { width: 1366, height: 768 },
            deviceScaleFactor: 1,
            platform: 'Win32'
        },
        {
            userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            viewport: { width: 1440, height: 900 },
            deviceScaleFactor: 2,
            platform: 'MacIntel'
        }
    ],

    /** 语言池 */
    languages: ['en-US,en;q=0.9', 'en-GB,en;q=0.9', 'en-US,en;q=0.9,en-GB;q=0.8'],

    /** 时区池 */
    timezones: ['Europe/London', 'America/New_York', 'Europe/Paris'],

    /**
     * V173: 动态 User-Agent 轮换池 (20 个主流 UA)
     * 包含最新的桌面端和移动端浏览器指纹
     */
    uaPool: [
        // Chrome 桌面端 (Windows)
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
        // Chrome 桌面端 (macOS)
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        // Edge 桌面端
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0',
        // Firefox 桌面端
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:135.0) Gecko/20100101 Firefox/135.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 14.0; rv:134.0) Gecko/20100101 Firefox/134.0',
        // Safari 桌面端 (macOS)
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15',
        // Chrome 移动端 (Android)
        'Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Mobile Safari/537.36',
        'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36',
        // Safari 移动端 (iOS)
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
    ],

    /**
     * V173: 获取随机 User-Agent
     * @returns {string} 随机 UA 字符串
     */
    getRandomUA() {
        return this.uaPool[Math.floor(Math.random() * this.uaPool.length)];
    },

    /**
     * V173: 获取随机视口尺寸
     * @returns {Object} 视口配置
     */
    getRandomViewport() {
        const viewports = [
            { width: 1920, height: 1080 },
            { width: 1366, height: 768 },
            { width: 1440, height: 900 },
            { width: 1536, height: 864 },
            { width: 1280, height: 720 },
            { width: 1600, height: 900 },
            { width: 2560, height: 1440 },
            { width: 1287, height: 1271 }  // 原始会话镜像尺寸
        ];
        return viewports[Math.floor(Math.random() * viewports.length)];
    }
};

// ============================================================================
// V173: FotMob 深度静默模式配置 (Cool Down)
// ============================================================================

const FOTMOB_COOL_DOWN = {
    /** 是否启用深度静默模式 */
    enabled: ENV.ENABLE_COOL_DOWN !== 'false',

    /** 触发熔断的连续失败次数 */
    triggerThreshold: parseInt(ENV.COOL_DOWN_THRESHOLD) || 3,

    /** 冷却时间 (毫秒) - 默认 30 分钟 */
    durationMs: parseInt(ENV.COOL_DOWN_DURATION_MS) || 30 * 60 * 1000,

    /** 需要触发冷却的错误类型 */
    triggerErrors: [
        'SIZE_TOO_SMALL',
        'TURNSTILE_REQUIRED',
        'CONTAINS_TURNSTILE',
        'BLOCKED',
        'CAPTCHA'
    ],

    /** 当前冷却状态 (运行时) */
    _activeCoolDowns: new Map(),

    /**
     * 检查是否应该触发冷却
     * @param {string} errorType - 错误类型
     * @param {number} consecutiveFailures - 连续失败次数
     * @returns {boolean}
     */
    shouldTrigger(errorType, consecutiveFailures) {
        const isErrorMatch = this.triggerErrors.some(e =>
            errorType.includes(e) || e.includes(errorType)
        );
        return isErrorMatch && consecutiveFailures >= this.triggerThreshold;
    },

    /**
     * 进入冷却状态
     * @param {number} workerId - Worker ID
     */
    enterCoolDown(workerId) {
        const endTime = Date.now() + this.durationMs;
        this._activeCoolDowns.set(workerId, {
            startTime: Date.now(),
            endTime,
            duration: this.durationMs
        });
        const minutes = Math.round(this.durationMs / 60000);
        console.log(`❄️ Worker ${workerId} 进入深度静默模式，冷却 ${minutes} 分钟`);
    },

    /**
     * 检查是否在冷却中
     * @param {number} workerId - Worker ID
     * @returns {boolean}
     */
    isInCoolDown(workerId) {
        const state = this._activeCoolDowns.get(workerId);
        if (!state) return false;

        if (Date.now() >= state.endTime) {
            this._activeCoolDowns.delete(workerId);
            return false;
        }
        return true;
    },

    /**
     * 获取剩余冷却时间 (毫秒)
     * @param {number} workerId - Worker ID
     * @returns {number} 剩余毫秒数，0 表示不在冷却中
     */
    getRemainingTime(workerId) {
        const state = this._activeCoolDowns.get(workerId);
        if (!state) return 0;
        return Math.max(0, state.endTime - Date.now());
    }
};

// ============================================================================
// 路径配置 (Paths)
// ============================================================================

const PATH_CONFIG = {
    /** 项目根目录 */
    projectRoot: ENV.PROJECT_ROOT || '/app',

    /** 数据库配置路径 */
    databaseConfig: '/app/config/database',

    /** 数据目录 */
    dataDir: ENV.DATA_DIR || '/app/data',

    /** 日志目录 */
    logDir: ENV.LOG_DIR || '/app/logs',

    /** Cookie 存储路径 */
    cookiePath: '/app/data/browser_profile/browser_state.json',

    /** Worker 脚本路径 */
    workerScript: '/app/scripts/ops/harvest_worker.js',

    /** 核心引擎路径 */
    enginePath: '/app/src/domain/services/harvesting/MatchDetailEngine.js',

    /** 浏览器配置目录 */
    browserProfile: ENV.BROWSER_PROFILE_PATH || '/app/data/browser_profile'
};

// ============================================================================
// 日志配置 (Logging)
// ============================================================================

const LOG_CONFIG = {
    /** 日志级别 */
    level: ENV.LOG_LEVEL || 'info',

    /** 日志格式 */
    format: 'timestamped',

    /** 是否输出到文件 */
    toFile: ENV.LOG_TO_FILE === 'true',

    /** 日志文件最大大小 (bytes) */
    maxFileSize: parseInt(ENV.LOG_MAX_SIZE) || 10 * 1024 * 1024,  // 10MB

    /** 日志保留天数 */
    retentionDays: parseInt(ENV.LOG_RETENTION_DAYS) || 7
};

// ============================================================================
// 哨兵监控配置 (Sentinel)
// ============================================================================

const SENTINEL_CONFIG = {
    /** 最大失败率阈值 */
    maxFailureRate: parseFloat(ENV.MAX_FAILURE_RATE) || 0.10,

    /** 最大连续 403 错误次数 */
    maxConsecutive403: parseInt(ENV.MAX_CONSECUTIVE_403) || 5,

    /** 健康报告路径 */
    healthReportPath: ENV.HEALTH_REPORT_PATH || '/app/logs/factory_health.json',

    /** 告警邮件 (可选) */
    alertEmail: ENV.ALERT_EMAIL || null,

    /** Cookie 最大年龄 (毫秒) */
    cookieMaxAgeMs: parseInt(ENV.COOKIE_MAX_AGE_MS) || 24 * 60 * 60 * 1000  // 24 小时
};

// ============================================================================
// 增量模式配置 (Incremental)
// ============================================================================

const INCREMENTAL_CONFIG = {
    /** 回溯天数 */
    lookbackDays: parseInt(ENV.INCREMENTAL_LOOKBACK_DAYS) || 7,

    /** 目标状态列表 */
    targetStatuses: ['completed', 'finished'],

    /** 排除的联赛 (可选) */
    excludedLeagues: (ENV.EXCLUDED_LEAGUES || '').split(',').filter(Boolean)
};

// ============================================================================
// 运行模式 (Run Modes)
// ============================================================================

const RUN_MODES = {
    INCREMENTAL: 'incremental',
    REPAIR: 'repair',
    FULL: 'full'
};

// ============================================================================
// 辅助函数
// ============================================================================

/**
 * 获取随机延时 (毫秒)
 * @param {number[]} range - [min, max] 范围
 * @returns {number} 随机毫秒数
 */
function getRandomDelay(range = [TIMING.minDelayMs, TIMING.maxDelayMs]) {
    return Math.floor(Math.random() * (range[1] - range[0] + 1)) + range[0];
}

/**
 * V178: 获取指数退避延时 (1s -> 2s -> 4s 带抖动)
 * @param {number} attempt - 当前尝试次数 (1-based)
 * @returns {number} 退避延时 (ms)
 */
function getExponentialBackoff(attempt) {
    // V178: 固定退避序列 1s -> 2s -> 4s
    const baseDelay = 1000 * Math.pow(2, attempt - 1);  // 1000, 2000, 4000
    const delay = Math.min(baseDelay, 4000);  // 上限 4 秒

    // V178: ±20% 抖动
    const jitter = delay * 0.2 * (Math.random() * 2 - 1);
    return Math.floor(delay + jitter);
}

/**
 * 随机数生成 (范围)
 * @param {number} min - 最小值
 * @param {number} max - 最大值
 * @returns {number}
 */
function randomInRange(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

/**
 * 随机选择数组元素
 * @param {Array} arr - 数组
 * @returns {*}
 */
function randomChoice(arr) {
    return arr[Math.floor(Math.random() * arr.length)];
}

// ============================================================================
// 导出
// ============================================================================

module.exports = {
    // 配置模块
    QUALITY_GATE,
    TIMING,
    RETRY,
    CONCURRENCY,
    PROXY_CONFIG,
    CIRCUIT_BREAKER,
    DATABASE,
    BROWSER,
    BEHAVIOR,
    FINGERPRINT,
    PATH_CONFIG,
    LOG_CONFIG,
    SENTINEL_CONFIG,
    INCREMENTAL_CONFIG,
    RUN_MODES,

    // V173: 新增配置
    FOTMOB_COOL_DOWN,

    // 辅助函数
    getRandomDelay,
    getExponentialBackoff,
    randomInRange,
    randomChoice,

    // 版本信息
    VERSION: 'V178.0.0',
    BUILD_DATE: '2026-03-03'
};
