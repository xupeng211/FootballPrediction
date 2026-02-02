/**
 * EngineConfig - V167.000 Central Configuration Authority
 * =========================================================
 *
 * [Genesis.Reconstruction] 中央配置管理
 *
 * 统一管理所有 Timeout、Titan IDs、Selector 和其他配置项。
 * 彻底弃用硬编码，实现配置集中化管理。
 *
 * @module config/EngineConfig
 * @version V167.000
 * @since 2026-02-02
 * @author [Genesis.Reconstruction]
 */

'use strict';

/**
 * V167.000: Titan ID 映射表
 * 用于识别赔率提供商数据，l3_odds_hash 计算的核心标识
 */
const TITAN_ID_MAPPING = {
    PINNACLE: '18',
    WILLIAM_HILL: '32',
    BET365: '2',
    ONE_X_BET: '25679340',
    UNIBET: '25',
    LADBROKES: '16',
    BWIN: '1'
};

/**
 * V167.000: 标准提供商名称映射
 * 用于反向查询 Titan ID
 */
const STANDARD_PROVIDER_NAMES = {
    '18': 'Entity_P',
    '32': 'Entity_WH',
    '2': 'Entity_B365',
    '25679340': 'Entity_1XBT',
    '25': 'Entity_UNIBET',
    '16': 'Entity_LADB',
    '1': 'Entity_BWIN'
};

/**
 * V167.000: 超时配置常量
 * 统一管理所有超时设置，支持环境变量覆盖
 */
const TIMEOUT_CONFIG = {
    // 内存钩子超时
    MEMORY_HOOK_TIMEOUT: parseInt(process.env.MEMORY_HOOK_TIMEOUT) || 12000,
    MEMORY_HOOK_POLL_INTERVAL: parseInt(process.env.MEMORY_HOOK_POLL_INTERVAL) || 100,

    // DOM 回退超时
    DOM_FALLBACK_TIMEOUT: parseInt(process.env.DOM_FALLBACK_TIMEOUT) || 5000,

    // 页面导航超时
    PAGE_NAVIGATION_TIMEOUT: parseInt(process.env.PAGE_NAVIGATION_TIMEOUT) || 60000,
    NETWORK_IDLE_TIMEOUT: parseInt(process.env.NETWORK_IDLE_TIMEOUT) || 30000,

    // Hover 相关超时
    HOVER_WAIT_TIMEOUT: parseInt(process.env.HOVER_WAIT_TIMEOUT) || 1500,
    HOVER_RETRY_DELAY: parseInt(process.env.HOVER_RETRY_DELAY) || 200,
    HOVER_MAX_RETRIES: parseInt(process.env.HOVER_MAX_RETRIES) || 2,

    // React 渲染超时
    REACT_RENDER_TIMEOUT: parseInt(process.env.REACT_RENDER_TIMEOUT) || 10000,
    SCROLL_SETTLE_DELAY: parseInt(process.env.SCROLL_SETTLE_DELAY) || 800,

    // 滚动激活超时
    SCROLL_CHUNK_DELAY: parseInt(process.env.SCROLL_CHUNK_DELAY) || 200,
    SCROLL_FINAL_WAIT: parseInt(process.env.SCROLL_FINAL_WAIT) || 3000,

    // 语义提取超时
    SEMANTIC_RENDER_WINDOW: parseInt(process.env.SEMANTIC_RENDER_WINDOW) || 15000,

    // 拦截窗口
    INTERCEPT_WINDOW: parseInt(process.env.INTERCEPT_WINDOW) || 12000,

    // 资源清理超时
    RESOURCE_CLEANUP_TIMEOUT: parseInt(process.env.RESOURCE_CLEANUP_TIMEOUT) || 5000
};

/**
 * V167.000: 轴向映射配置
 * 用于三维数据（Home/Draw/Away）映射到维度标识
 */
const AXIS_MAPPING = {
    HOME: { name: 'home', dimension: 'A', typeId: '1' },
    DRAW: { name: 'draw', dimension: 'B', typeId: '2' },
    AWAY: { name: 'away', dimension: 'C', typeId: '3' }
};

/**
 * V167.000: 数据质量评分阈值
 * 用于 Golden Shield 数据质量评级
 */
const QUALITY_THRESHOLDS = {
    EXCELLENT: { minFeatures: 100, minCoreMetrics: 4 },
    GOOD: { minFeatures: 80, minCoreMetrics: 3 },
    FAIR: { minFeatures: 50, minCoreMetrics: 2 },
    POOR: { minFeatures: 0, minCoreMetrics: 0 }
};

/**
 * V167.000: Payout 计算配置
 * 统一的返还率计算标准
 */
const PAYOUT_CONFIG = {
    // 返还率计算公式: 1 / (1/H + 1/D + 1/A)
    CALCULATION_METHOD: 'harmonic_mean_inverse',

    // 有效赔率范围
    MIN_VALID_ODDS: 1.01,
    MAX_VALID_ODDS: 500.0,

    // 有效返还率范围
    MIN_VALID_PAYOUT: 85.0,   // 85% (正常市场)
    MAX_VALID_PAYOUT: 105.0,   // 105% (允许小幅误差)

    // 精度配置
    PAYOUT_DECIMAL_PLACES: 2
};

/**
 * V167.000: 内存保护配置
 * 防止内存溢出的保护阈值
 */
const MEMORY_PROTECTION = {
    MAX_RESPONSE_SIZE: 200 * 1024,   // 200KB 最大响应大小
    MIN_RESPONSE_SIZE: 100,           // 100 bytes 最小响应大小
    MAX_CAPTURED_RESPONSES: 50,       // 最大捕获响应数量
    MAX_MEMORY_STREAMS: 10,           // 最大内存流数量
    MEMORY_CLEANUP_THRESHOLD: 0.8     // 80% 堆内存使用率触发清理
};

/**
 * V167.000: 并发配置
 * 用于控制浏览器实例和并发数量
 *
 * V168.001: 生产参数固化 - 默认并发降至 10（工业级稳定性）
 */
const CONCURRENCY_CONFIG = {
    MAX_CONCURRENT_BROWSERS: parseInt(process.env.MAX_CONCURRENT_BROWSERS) || 10,  // V168.001: 15 → 10
    MAX_CONCURRENT_CONTEXTS: parseInt(process.env.MAX_CONCURRENT_CONTEXTS) || 3,
    MAX_CONCURRENT_PAGES: parseInt(process.env.MAX_CONCURRENT_PAGES) || 5,
    BROWSER_POOL_SIZE: parseInt(process.env.BROWSER_POOL_SIZE) || 5
};

/**
 * V168.000: 收割策略配置
 * [Genesis.Solidify] 固化实战收割参数
 *
 * V168.001: 生产参数固化 - 渲染窗口提升至 75s（适应动态加载）
 */
const HARVEST_CONFIG = {
    // 默认门槛：至少需要 1 家提供商才算有效
    MIN_PROVIDERS: parseInt(process.env.MIN_PROVIDERS) || 1,  // V168.001: 固化为 1

    // 渲染窗口：提升至 75s 以适应动态加载（生产级稳定性）
    RENDER_WINDOW: parseInt(process.env.RENDER_WINDOW) || 75000,  // V168.001: 60s → 75s

    // 激活姿态：强制开启深度滚动
    DEEP_SCROLL_ACTIVATION: process.env.DEEP_SCROLL_ACTIVATION !== 'false', // Default true

    // 快速判死时间
    FAST_FAIL_TIMEOUT: parseInt(process.env.FAST_FAIL_TIMEOUT) || 30000
};

/**
 * V167.000: 日志级别配置
 */
const LOG_LEVELS = {
    DEBUG: 0,
    INFO: 1,
    WARN: 2,
    ERROR: 3,
    SILENT: 4
};

/**
 * EngineConfig - 中央配置管理类
 *
 * 统一管理所有引擎配置，支持环境变量覆盖
 */
class EngineConfig {
    /**
     * @param {Object} overrides - 配置覆盖选项
     */
    constructor(overrides = {}) {
        // 超时配置
        this.timeouts = { ...TIMEOUT_CONFIG, ...(overrides.timeouts || {}) };

        // Titan ID 映射
        this.titanIds = { ...TITAN_ID_MAPPING, ...(overrides.titanIds || {}) };
        this.standardNames = { ...STANDARD_PROVIDER_NAMES, ...(overrides.standardNames || {}) };

        // 轴向映射
        this.axes = { ...AXIS_MAPPING, ...(overrides.axes || {}) };

        // 质量阈值
        this.qualityThresholds = { ...QUALITY_THRESHOLDS, ...(overrides.qualityThresholds || {}) };

        // Payout 配置
        this.payout = { ...PAYOUT_CONFIG, ...(overrides.payout || {}) };

        // 内存保护
        this.memoryProtection = { ...MEMORY_PROTECTION, ...(overrides.memoryProtection || {}) };

        // 并发配置
        this.concurrency = { ...CONCURRENCY_CONFIG, ...(overrides.concurrency || {}) };

        // [V168.000] 收割策略配置
        this.harvest = { ...HARVEST_CONFIG, ...(overrides.harvest || {}) };

        // 日志配置
        this.logLevel = overrides.logLevel || (process.env.LOG_LEVEL || 'INFO');
        this._logLevelValue = LOG_LEVELS[this.logLevel] || LOG_LEVELS.INFO;

        // V168.001: 代理配置 - 移除硬编码默认值，强制使用环境变量
        const proxyHost = overrides.proxy?.host || process.env.PROXY_HOST || process.env.WSL2_PROXY_HOST;
        const proxyPort = overrides.proxy?.port || process.env.PROXY_PORT || process.env.DEFAULT_PROXY_PORT;

        this.proxy = {
            host: proxyHost || null,
            port: proxyPort || null,
            enabled: overrides.proxy?.enabled !== undefined
                ? overrides.proxy.enabled
                : (process.env.PROXY_ENABLED === 'true')
        };

        // V168.001: 如果启用了代理但配置不完整，发出警告
        if (this.proxy.enabled && (!this.proxy.host || !this.proxy.port)) {
            console.warn('[EngineConfig] ⚠️ Proxy enabled but configuration incomplete (host or port missing)');
            console.warn('[EngineConfig] Required env vars: PROXY_HOST, PROXY_PORT');
            this.proxy.enabled = false;
        }
    }

    /**
     * V167.000: 获取超时配置
     * @param {string} key - 超时配置键名
     * @returns {number} 超时值（毫秒）
     */
    getTimeout(key) {
        const timeout = this.timeouts[key.toUpperCase()];
        if (timeout === undefined) {
            console.warn(`[EngineConfig] Unknown timeout key: ${key}, using default 5000ms`);
            return 5000;
        }
        return timeout;
    }

    /**
     * V167.000: 获取 Titan ID
     * @param {string} providerName - 提供商名称
     * @returns {string|null} Titan ID
     */
    getTitanId(providerName) {
        return this.titanIds[providerName.toUpperCase()] || null;
    }

    /**
     * V167.000: 获取标准提供商名称
     * @param {string} titanId - Titan ID
     * @returns {string|null} 标准名称
     */
    getStandardName(titanId) {
        return this.standardNames[titanId] || null;
    }

    /**
     * V167.000: 获取轴向配置
     * @param {string} axisName - 轴向名称 (home/draw/away)
     * @returns {Object|null} 轴向配置
     */
    getAxis(axisName) {
        return this.axes[axisName.toUpperCase()] || null;
    }

    /**
     * V167.000: 获取所有 Titan ID 签名
     * @returns {string[]} Titan ID 数组
     */
    getTitanIdSignatures() {
        return Object.values(this.titanIds);
    }

    /**
     * V167.000: 日志级别检查
     * @param {string} level - 日志级别
     * @returns {boolean} 是否应该记录该级别的日志
     */
    shouldLog(level) {
        return (LOG_LEVELS[level] || 0) >= this._logLevelValue;
    }

    /**
     * V167.000: 生成代理 URL
     * @returns {string} 代理 URL
     */
    getProxyUrl() {
        if (!this.proxy.enabled) {
            return null;
        }
        return `http://${this.proxy.host}:${this.proxy.port}`;
    }

    /**
     * V167.000: 导出为 page.evaluate() 可用的配置对象
     * 用于在浏览器上下文中访问配置
     *
     * @returns {Object} 可序列化的配置对象
     */
    toSerializable() {
        return {
            titanIds: this.titanIds,
            axes: this.axes,
            qualityThresholds: this.qualityThresholds,
            payout: this.payout,
            timeouts: {
                hoverWait: this.timeouts.HOVER_WAIT_TIMEOUT,
                scrollSettle: this.timeouts.SCROLL_SETTLE_DELAY,
                reactRender: this.timeouts.REACT_RENDER_TIMEOUT
            }
        };
    }

    /**
     * V167.000: 创建默认配置实例
     * @returns {EngineConfig} 默认配置实例
     */
    static createDefault() {
        return new EngineConfig();
    }

    /**
     * V167.000: 从环境变量创建配置
     * @returns {EngineConfig} 基于环境变量的配置实例
     */
    static fromEnv() {
        return new EngineConfig({
            timeouts: TIMEOUT_CONFIG,
            concurrency: CONCURRENCY_CONFIG,
            logLevel: process.env.LOG_LEVEL
        });
    }
}

/**
 * V167.000: 导出常量和类
 */
module.exports = {
    // 配置常量
    TITAN_ID_MAPPING,
    STANDARD_PROVIDER_NAMES,
    TIMEOUT_CONFIG,
    AXIS_MAPPING,
    QUALITY_THRESHOLDS,
    PAYOUT_CONFIG,
    MEMORY_PROTECTION,
    CONCURRENCY_CONFIG,
    HARVEST_CONFIG,
    LOG_LEVELS,

    // 配置类
    EngineConfig
};
