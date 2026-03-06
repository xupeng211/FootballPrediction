/**
 * V197 统一注册中心 (Unified Registry)
 * ==============================================
 *
 * 【一处修改，全局生效】
 * 所有硬编码值的唯一真实来源 (Single Source of Truth)
 *
 * 设计原则:
 * - 数据库表名集中管理
 * - API URL 集中管理
 * - 代理配置集中管理
 * - 联赛 ID 映射集中管理
 * - 硬件指纹池集中管理
 *
 * 使用方法:
 * ```javascript
 * const Registry = require('../config/registry');
 *
 * // 获取表名
 * const matchesTable = Registry.TABLES.MATCHES;
 *
 * // 获取 API URL
 * const fotmobUrl = Registry.APIS.FOTMOB.leagues(47, '20242025');
 * ```
 *
 * @module config/registry
 * @version V197.0.0
 * @since V196-TECH-DEBT-001
 */

'use strict';

const ENV = process.env;

// ============================================================================
// 数据库表名注册 (Database Tables)
// ============================================================================

/**
 * 数据库表名注册表
 * 所有 SQL 查询必须使用此处的常量
 */
const TABLES = Object.freeze({
    /** L1: 比赛基础信息 */
    MATCHES: 'matches',

    /** L2: 原始比赛数据 (FotMob/OddsPortal) */
    RAW_MATCH_DATA: 'raw_match_data',

    /** L3: 特征向量 */
    L3_FEATURES: 'l3_features',

    /** L2: 赔率数据 */
    L2_MATCH_DATA: 'l2_match_data',

    /** 预测结果 */
    PREDICTIONS: 'predictions',

    /** 基本面数据 */
    FUNDAMENTALS: 'fundamentals',

    /** 队名映射表 */
    MATCHES_MAPPING: 'matches_mapping',

    /** 会话缓存表 (可选) */
    SESSIONS_CACHE: 'sessions_cache',

    /**
     * 获取所有表名
     * @returns {string[]} 表名数组
     */
    all() {
        return [
            this.MATCHES,
            this.RAW_MATCH_DATA,
            this.L3_FEATURES,
            this.L2_MATCH_DATA,
            this.PREDICTIONS,
            this.FUNDAMENTALS,
            this.MATCHES_MAPPING
        ];
    },

    /**
     * 验证表名是否有效
     * @param {string} tableName - 表名
     * @returns {boolean}
     */
    isValid(tableName) {
        return this.all().includes(tableName);
    }
});

// ============================================================================
// API URL 注册 (API Endpoints)
// ============================================================================

/**
 * API 端点注册表
 * 所有外部 API 调用必须使用此处的配置
 */
const APIS = Object.freeze({
    /** FotMob API 配置 */
    FOTMOB: Object.freeze({
        /** 基础域名 */
        BASE_URL: ENV.FOTMOB_BASE_URL || 'https://www.fotmob.com',

        /** API 基础路径 */
        API_BASE: ENV.FOTMOB_API_BASE || 'https://www.fotmob.com/api',

        /** 超时时间 (ms) */
        TIMEOUT: parseInt(ENV.FOTMOB_TIMEOUT) || 20000,

        /**
         * 联赛赛程端点
         * @param {number} leagueId - 联赛 ID
         * @param {string} season - 赛季 (格式: 20242025)
         * @returns {string} 完整 URL
         */
        leagues(leagueId, season) {
            return `${this.API_BASE}/leagues?id=${leagueId}&season=${season}`;
        },

        /**
         * 比赛详情端点
         * @param {string} matchId - 比赛 ID
         * @returns {string} 完整 URL
         */
        matchDetails(matchId) {
            return `${this.API_BASE}/matchDetails?matchId=${matchId}`;
        },

        /**
         * 比赛详情页面 URL
         * @param {string} externalId - 外部比赛 ID
         * @returns {string} 完整页面 URL
         */
        matchPage(externalId) {
            return `${this.BASE_URL}/match/${externalId}`;
        },

        /**
         * 按日期获取比赛
         * @param {string} date - 日期 (格式: YYYYMMDD)
         * @returns {string} 完整 URL
         */
        matchesByDate(date) {
            return `${this.API_BASE}/matchesByDate?date=${date}`;
        },

        /** 端点列表 (用于 ApiSniffer) */
        ENDPOINTS: Object.freeze({
            MATCH_DETAILS: 'matchDetails',
            LEGACY_MATCH_DETAILS: 'data/matchDetails',
            MATCHES_BY_DATE: 'matchesByDate',
            LEAGUES: 'leagues'
        })
    }),

    /** OddsPortal 配置 */
    ODDSPORTAL: Object.freeze({
        /** 基础域名 */
        BASE_URL: ENV.ODDSPORTAL_BASE_URL || 'https://www.oddsportal.com',

        /** 超时时间 (ms) */
        TIMEOUT: parseInt(ENV.ODDSPORTAL_TIMEOUT) || 30000,

        /**
         * 比赛页面 URL
         * @param {string} slug - URL slug (如 "man-city-liverpool")
         * @returns {string} 完整页面 URL
         */
        matchPage(slug) {
            return `${this.BASE_URL}/football/${slug}/`;
        }
    }),

    /** HTTPBin 测试端点 (用于代理测试) */
    HTTPBIN: Object.freeze({
        BASE_URL: 'https://httpbin.org',

        /**
         * IP 检测端点
         * @returns {string} 完整 URL
         */
        ip() {
            return `${this.BASE_URL}/ip`;
        }
    })
});

// ============================================================================
// 代理配置注册 (Proxy Configuration)
// ============================================================================

/**
 * 代理配置注册表
 * 与 factory_config.js 的 PROXY_CONFIG 保持同步
 */
const PROXY = Object.freeze({
    /** 代理服务器主机 */
    HOST: ENV.PROXY_HOST || '172.25.16.1',

    /** 默认端口 */
    DEFAULT_PORT: parseInt(ENV.PROXY_PORT) || 7890,

    /** 端口范围 */
    PORT_RANGE: Object.freeze({
        START: 7890,
        END: 7911
    }),

    /** 总端口数 */
    TOTAL_PORTS: 22,

    /**
     * 获取所有端口
     * @returns {number[]} 端口数组
     */
    getAllPorts() {
        return Array.from(
            { length: this.PORT_RANGE.END - this.PORT_RANGE.START + 1 },
            (_, i) => this.PORT_RANGE.START + i
        );
    },

    /**
     * 根据 Worker ID 获取端口
     * @param {number} workerId - Worker 编号 (1-based)
     * @returns {number} 代理端口
     */
    getPortByWorker(workerId) {
        const ports = this.getAllPorts();
        const index = (workerId - 1) % ports.length;
        return ports[index];
    },

    /**
     * 获取代理服务器 URL
     * @param {number} port - 代理端口
     * @returns {string} 代理 URL
     */
    getServerUrl(port = this.DEFAULT_PORT) {
        return `http://${this.HOST}:${port}`;
    },

    /**
     * 健康检查配置
     */
    HEALTH_CHECK: Object.freeze({
        TIMEOUT: parseInt(ENV.PROXY_HEALTH_TIMEOUT) || 10000,
        MAX_FAILURES: 3,
        COOLDOWN_MINUTES: 5
    })
});

// ============================================================================
// 联赛 ID 注册 (League Registry)
// ============================================================================

/**
 * 联赛 ID 注册表
 * FotMob 联赛 ID 与名称的双向映射
 */
const LEAGUES = Object.freeze({
    /** ID 到名称的映射 */
    BY_ID: Object.freeze({
        47: 'Premier League',
        54: 'Bundesliga',
        55: 'Serie A',  // 意甲 (从 config/leagues.json 加载)
        61: 'Ligue 1',
        135: 'Serie A',
        73: 'Eredivisie',
        87: 'La Liga',  // 西甲 (从 config/leagues.json 加载)
        94: 'Scottish Premiership',
        148: 'Premier League (Russia)',
        234: 'Championship',
        242: 'Champions League',
        277: 'Europa League',
        638: 'Conference League'
    }),

    /** 名称到 ID 的映射 (小写) */
    BY_NAME: Object.freeze({
        'premier league': 47,
        'english premier league': 47,
        'epl': 47,
        'bundesliga': 54,
        'german bundesliga': 54,
        'la liga': 87,
        'primera división': 87,
        'ligue 1': 61,
        'french ligue 1': 61,
        'serie a': 135,
        'italian serie a': 135,
        'eredivisie': 73,
        'primeira liga': 87,
        'scottish premiership': 94,
        'championship': 234,
        'champions league': 242,
        'europa league': 277,
        'conference league': 638
    }),

    /**
     * 根据名称获取联赛 ID
     * @param {string} name - 联赛名称
     * @returns {number|null} 联赛 ID
     */
    getIdByName(name) {
        if (!name) return null;
        return this.BY_NAME[name.toLowerCase().trim()] || null;
    },

    /**
     * 根据 ID 获取联赛名称
     * @param {number} id - 联赛 ID
     * @returns {string|null} 联赛名称
     */
    getNameById(id) {
        return this.BY_ID[id] || null;
    },

    /**
     * 获取所有活跃联赛 ID
     * @returns {number[]}
     */
    getActiveIds() {
        return Object.keys(this.BY_ID).map(Number);
    }
});

// ============================================================================
// 硬件指纹池注册 (Fingerprint Pool)
// ============================================================================

/**
 * 浏览器指纹池
 * 用于反爬虫检测规避
 */
const FINGERPRINTS = Object.freeze({
    /** WebGL 渲染器池 */
    WEBGL_RENDERERS: Object.freeze([
        'ANGLE (AMD, AMD Radeon(TM) Graphics (0x000013C0) Direct3D11 vs_5_0 ps_5_0, D3D11)',
        'ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 (0x00002183) Direct3D11 vs_5_0 ps_5_0, D3D11)',
        'ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 (0x00002503) Direct3D11 vs_5_0 ps_5_0, D3D11)',
        'ANGLE (NVIDIA, NVIDIA GeForce RTX 3070 (0x00002484) Direct3D11 vs_5_0 ps_5_0, D3D11)',
        'ANGLE (NVIDIA, NVIDIA GeForce GTX 1080 (0x00001B80) Direct3D11 vs_5_0 ps_5_0, D3D11)',
        'ANGLE (Intel, Intel(R) UHD Graphics 630 (0x00003E9B) Direct3D11 vs_5_0 ps_5_0, D3D11)',
        'ANGLE (Intel, Intel(R) Iris(R) Xe Graphics (0x000049A5) Direct3D11 vs_5_0 ps_5_0, D3D11)',
        'ANGLE (AMD, AMD Radeon RX 580 Series (0x000067DF) Direct3D11 vs_5_0 ps_5_0, D3D11)'
    ]),

    /** User-Agent 池 */
    USER_AGENTS: Object.freeze([
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15'
    ]),

    /** 视口尺寸池 */
    VIEWPORTS: Object.freeze([
        { width: 1920, height: 1080 },
        { width: 1366, height: 768 },
        { width: 1440, height: 900 },
        { width: 1536, height: 864 },
        { width: 1280, height: 720 },
        { width: 1600, height: 900 },
        { width: 2560, height: 1440 }
    ]),

    /**
     * 根据 seed 获取确定性 WebGL 渲染器
     * @param {number} seed - 随机种子
     * @returns {string} WebGL 渲染器字符串
     */
    getWebGLRenderer(seed) {
        return this.WEBGL_RENDERERS[seed % this.WEBGL_RENDERERS.length];
    },

    /**
     * 根据 seed 获取确定性 User-Agent
     * @param {number} seed - 随机种子
     * @returns {string} User-Agent 字符串
     */
    getUserAgent(seed) {
        return this.USER_AGENTS[seed % this.USER_AGENTS.length];
    },

    /**
     * 根据 seed 获取确定性视口
     * @param {number} seed - 随机种子
     * @returns {{width: number, height: number}} 视口配置
     */
    getViewport(seed) {
        return this.VIEWPORTS[seed % this.VIEWPORTS.length];
    }
});

// ============================================================================
// 数据质量门禁 (Quality Gates)
// ============================================================================

/**
 * 数据质量阈值
 * 用于验证采集的数据是否有效
 */
const QUALITY_GATES = Object.freeze({
    /** 最小数据体积 (bytes) */
    MIN_SIZE_BYTES: parseInt(ENV.MIN_SIZE_BYTES) || 5000,

    /** 未来比赛最小数据体积 (bytes) */
    MIN_SIZE_BYTES_FUTURE: parseInt(ENV.MIN_SIZE_BYTES_FUTURE) || 3000,

    /** 最大数据体积 (bytes) */
    MAX_SIZE_BYTES: parseInt(ENV.MAX_SIZE_BYTES) || 10 * 1024 * 1024,

    /** 必须包含的 JSON 路径 */
    REQUIRED_PATHS: Object.freeze(['content']),

    /** 错误关键词 */
    ERROR_KEYWORDS: Object.freeze([
        'TURNSTILE_REQUIRED',
        'Verification required',
        'ACCESS_DENIED',
        'CAPTCHA',
        'cf-browser-verification',
        'challenge-platform'
    ])
});

// ============================================================================
// 路径配置 (Path Configuration)
// ============================================================================

/**
 * 文件系统路径配置
 */
const PATHS = Object.freeze({
    /** 项目根目录 */
    PROJECT_ROOT: ENV.PROJECT_ROOT || '/app',

    /** 数据目录 */
    DATA_DIR: ENV.DATA_DIR || '/app/data',

    /** 日志目录 */
    LOG_DIR: ENV.LOG_DIR || '/app/logs',

    /** 浏览器配置目录 */
    BROWSER_PROFILE: ENV.BROWSER_PROFILE_PATH || '/app/data/browser_profile',

    /** 会话存储目录 */
    SESSIONS_DIR: ENV.SESSIONS_DIR || '/app/data/sessions',

    /** 模型存储目录 */
    MODEL_ZOO: ENV.MODEL_ZOO || 'model_zoo',

    /**
     * 获取浏览器状态文件路径
     * @returns {string}
     */
    browserStatePath() {
        const path = require('path');
        return path.join(this.BROWSER_PROFILE, 'browser_state.json');
    },

    /**
     * 获取会话文件路径
     * @param {number} port - 代理端口
     * @returns {string}
     */
    sessionPath(port) {
        const path = require('path');
        return path.join(this.SESSIONS_DIR, `session_port_${port}.json`);
    }
});

// ============================================================================
// 比赛状态映射 (Match Status Mapping)
// ============================================================================

/**
 * 比赛状态常量
 */
const MATCH_STATUS = Object.freeze({
    /** 已安排 */
    SCHEDULED: 'scheduled',

    /** 进行中 */
    LIVE: 'live',

    /** 已结束 */
    FINISHED: 'finished',

    /** 已取消 */
    CANCELLED: 'cancelled',

    /** 已判给 */
    AWARDED: 'awarded',

    /**
     * 从 FotMob 状态对象判断状态
     * @param {Object} status - FotMob 状态对象
     * @param {number|null} homeScore - 主队得分
     * @param {number|null} awayScore - 客队得分
     * @returns {string} 状态常量
     */
    fromFotMob(status, homeScore, awayScore) {
        if (typeof status === 'object' && status !== null) {
            if (status.cancelled) return this.CANCELLED;
            if (status.awarded) return this.AWARDED;
            if (status.finished) return this.FINISHED;
            if (status.started) return this.LIVE;
        }

        if (homeScore !== null && awayScore !== null) {
            return this.FINISHED;
        }

        return this.SCHEDULED;
    }
});

// ============================================================================
// 数据源标识 (Data Source Identifiers)
// ============================================================================

/**
 * 数据来源标识
 */
const DATA_SOURCES = Object.freeze({
    FOTMOB: 'FotMob',
    ODDSPORTAL: 'OddsPortal',

    /**
     * 所有数据源
     * @returns {string[]}
     */
    all() {
        return [this.FOTMOB, this.ODDSPORTAL];
    },

    /**
     * 验证数据源是否有效
     * @param {string} source - 数据源标识
     * @returns {boolean}
     */
    isValid(source) {
        return this.all().includes(source);
    }
});

// ============================================================================
// 版本信息 (Version Information)
// ============================================================================

const VERSION = Object.freeze({
    REGISTRY: 'V197.0.0',
    BUILD_DATE: '2026-03-05',
    DESCRIPTION: 'Unified Registry - Single Source of Truth'
});

// ============================================================================
// 导出
// ============================================================================

module.exports = Object.freeze({
    // 核心注册表
    TABLES,
    APIS,
    PROXY,
    LEAGUES,
    FINGERPRINTS,
    QUALITY_GATES,
    PATHS,
    MATCH_STATUS,
    DATA_SOURCES,

    // 版本信息
    VERSION,

    // 便捷方法
    /**
     * 获取注册表摘要
     * @returns {Object}
     */
    getSummary() {
        return {
            version: VERSION.REGISTRY,
            tables: TABLES.all().length,
            apis: ['FOTMOB', 'ODDSPORTAL', 'HTTPBIN'],
            proxyPorts: PROXY.TOTAL_PORTS,
            leagues: Object.keys(LEAGUES.BY_ID).length,
            fingerprints: {
                webgl: FINGERPRINTS.WEBGL_RENDERERS.length,
                ua: FINGERPRINTS.USER_AGENTS.length,
                viewports: FINGERPRINTS.VIEWPORTS.length
            }
        };
    },

    /**
     * 验证注册表完整性
     * @returns {{valid: boolean, errors: string[]}}
     */
    validate() {
        const errors = [];

        // 检查表名
        if (!TABLES.isValid(TABLES.MATCHES)) {
            errors.push('TABLES.MATCHES is invalid');
        }

        // 检查端口范围
        const ports = PROXY.getAllPorts();
        if (ports.length !== PROXY.TOTAL_PORTS) {
            errors.push(`PROXY port count mismatch: ${ports.length} vs ${PROXY.TOTAL_PORTS}`);
        }

        // 检查联赛映射
        if (Object.keys(LEAGUES.BY_ID).length === 0) {
            errors.push('LEAGUES.BY_ID is empty');
        }

        return {
            valid: errors.length === 0,
            errors
        };
    }
});
