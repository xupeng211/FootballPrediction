/**
 * V178 宸ュ巶绾ч厤缃腑蹇?(缁堟瀬寮哄寲鐗?
 * ==============================================
 *
 * 鎵€鏈夋敹鍓茬郴缁熺殑榄旀湳鏁板瓧缁熶竴褰掑彛绠＄悊
 * 涓ョ鍦ㄤ笟鍔′唬鐮佷腑纭紪鐮佷换浣曞弬鏁? *
 * V178 鍗囩骇:
 * - 鐔旀柇鍣ㄩ厤缃崌绾? 5 娆″け璐ヨЕ鍙? 60 绉掑喎鍗? * - 鎸囨暟閫€閬夸紭鍖? 1s -> 2s -> 4s (甯?卤20% 鎶栧姩)
 *
 * @module config/factory_config
 * @version V178.0.0 (Ultimate Hardening Edition)
 */

'use strict';
// ============================================================================
// 模块导入
// ============================================================================

const path = require('path');
const { resolveProxyPoolConfig } = require('./proxy_pool');

// ============================================================================
// 鐜鍙橀噺浼樺厛绾?// ============================================================================

const ENV = process.env;
const proxyPoolConfig = resolveProxyPoolConfig(ENV);
const envProxyPorts = String(ENV.PROXY_PORTS || '')
    .split(',')
    .map(port => Number.parseInt(port.trim(), 10))
    .filter(Number.isInteger);
const resolvedProxyPorts = envProxyPorts.length > 0 ? envProxyPorts : [...proxyPoolConfig.ports];
const resolvedDefaultProxyPort = Number.parseInt(ENV.PROXY_PORT || '', 10) || proxyPoolConfig.defaultPort;
const resolvedProxyServerTemplate = ENV.PROXY_SERVER || proxyPoolConfig.serverTemplate;

// ============================================================================
// 璐ㄩ噺闂ㄧ閰嶇疆 (Quality Gate)
// ============================================================================

const QUALITY_GATE = {
    /** 鏈€灏忔湁鏁堟暟鎹綋绉?(bytes) - 灏忎簬姝ゅ€艰涓洪潪娉曟暟鎹?*/
    minSizeBytes: parseInt(ENV.MIN_SIZE_BYTES) || 5000,

    /** 鏈潵姣旇禌鏈€灏忔暟鎹綋绉?(bytes) - 瀵逛簬娌℃湁 stats 鐨勬瘮璧涗娇鐢ㄦ洿浣庨槇鍊?*/
    minSizeBytesFuture: parseInt(ENV.MIN_SIZE_BYTES_FUTURE) || 3000,

    /** 鏈€澶ф暟鎹綋绉?(bytes) - 鐢ㄤ簬寮傚父妫€娴?*/
    maxSizeBytes: parseInt(ENV.MAX_SIZE_BYTES) || 10 * 1024 * 1024,  // 10MB

    /** 蹇呴』鍖呭惈鐨?JSON 璺緞 */
    requiredPaths: ['content'],

    /** 绂佹鍖呭惈鐨勯敊璇叧閿瘝 - V173: 鍙娴嬫槑纭殑 API 閿欒鍝嶅簲 */
    errorKeywords: ['TURNSTILE_REQUIRED', 'Verification required', 'ACCESS_DENIED', 'CAPTCHA', 'cf-browser-verification', 'challenge-platform'],

    /**
     * 楠岃瘉鏁版嵁鏄惁鏈夋晥
     * V175: 瀵逛簬鏈潵姣旇禌锛堟病鏈?stats锛変娇鐢ㄦ洿浣庣殑闃堝€?     * @param {object} rawData - 鍘熷鏁版嵁
     * @returns {{valid: boolean, reason?: string, size?: number}}
     */
    isValid(rawData) {
        if (!rawData) return { valid: false, reason: 'NULL_DATA' };

        const jsonStr = JSON.stringify(rawData);
        const size = jsonStr.length;

        // V175: 妫€鏌ユ槸鍚︽湁 stats 鏁版嵁
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
        // 缁撴瀯妫€鏌?        for (const path of this.requiredPaths) {
            if (!rawData[path]) {
                return { valid: false, reason: `MISSING_${path.toUpperCase()}` };
            }
        }

        // V173: 鏅鸿兘閿欒鍏抽敭瀛楁鏌?
        // 鍙鏌ユ牳蹇冩暟鎹尯鍩燂紝蹇界暐缈昏瘧鏂囨湰锛坱ranslations锛?
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
// 寤舵椂閰嶇疆 (Timing)
// ============================================================================

const TIMING = {
    /** 鍗曞満鏀跺壊鏈€灏忓欢鏃?(ms) - V173: 榛樿 10s 娼滆棰戠巼 */
    minDelayMs: parseInt(ENV.MIN_DELAY_MS) || 1000,  // V4.46.3 HYPER-DRIVE: 超频模式 (原 10s)

    /** 鍗曞満鏀跺壊鏈€澶у欢鏃?(ms) - V173: 榛樿 15s 娼滆棰戠巼 */
    maxDelayMs: parseInt(ENV.MAX_DELAY_MS) || 3000,   // V4.46.3 HYPER-DRIVE: 超频模式 (原 15s)

    /** 棣栭〉棰勭儹寤舵椂鑼冨洿 [min, max] (ms) */
    preVisitDelay: [2000, 4000],  // V4.46.3: 压缩预热延迟

    /** 椤甸潰绛夊緟寤舵椂鑼冨洿 [min, max] (ms) */
    pageDelay: [2000, 5000],      // V4.46.3: 压缩页面延迟

    /** 闃呰寤舵椂鑼冨洿 [min, max] (ms) - 妯℃嫙鐪熶汉闃呰 */
    readDelay: [1500, 3500],      // V4.46.3: 压缩阅读延迟

    /** API 璇锋眰瓒呮椂 (ms) */
    apiTimeout: parseInt(ENV.API_TIMEOUT) || 30000,

    /** 椤甸潰鍔犺浇瓒呮椂 (ms) */
    pageTimeout: parseInt(ENV.PAGE_TIMEOUT) || 60000
};

// ============================================================================
// 閲嶈瘯閰嶇疆 (Retry)
// ============================================================================

const RETRY = {
    /** 鏈€澶ч噸璇曟鏁?*/
    maxAttempts: parseInt(ENV.MAX_RETRY_ATTEMPTS) || 3,

    /** 閲嶈瘯寤舵椂鑼冨洿 [min, max] (ms) */
    delayRange: [5000, 10000],

    /** 鎸囨暟閫€閬垮熀鏁?*/
    backoffBase: parseInt(ENV.BACKOFF_BASE) || 2,

    /** 鏈€澶ч€€閬挎椂闂?(ms) */
    maxBackoffMs: parseInt(ENV.MAX_BACKOFF_MS) || 60000,

    /** 鍙噸璇曠殑閿欒绫诲瀷 */
    retryableErrors: [
        'SIZE_TOO_SMALL',
        'TURNSTILE_REQUIRED',
        'NETWORK_ERROR',
        'TIMEOUT',
        'ECONNRESET',
        'ENOTFOUND',
        'NO_NEXT_DATA',
        'DATA_TRANSFORM_FAILED',
        'CF_BLOCK'  // V173: Cloudflare 鎷︽埅涔熷皾璇曢噸璇曪紙浼氳嚜鍔ㄥ垏鎹㈢鍙ｏ級
    ],

    /** 涓嶅彲閲嶈瘯鐨勯敊璇被鍨?(姘镐箙澶辫触) */
    nonRetryableErrors: [
        'MATCH_NOT_FOUND',
        'INVALID_ID',
        'ACCESS_DENIED'
    ],

    /**
     * 鍒ゆ柇閿欒鏄惁鍙噸璇?     * @param {string} errorType - 閿欒绫诲瀷
     * @returns {boolean}
     */
    isRetryable(errorType) {
        return this.retryableErrors.some(e =>
            errorType.includes(e) || e.includes(errorType)
        );
    }
};

// ============================================================================
// 骞跺彂閰嶇疆 (Concurrency)
// ============================================================================

const CONCURRENCY = {
    /** 鏈€澶?Worker 鏁伴噺 - V173: 榛樿 1 (鏈€绋虫ā寮? */
    maxWorkers: parseInt(ENV.MAX_WORKERS) || 1,

    /** 姣忔壒娆′换鍔℃暟 */
    batchSize: parseInt(ENV.BATCH_SIZE) || 50,

    /** Worker 閿欏嘲鍚姩闂撮殧 (ms) */
    staggerStartMs: parseInt(ENV.STAGGER_START_MS) || 5000,

    /** 鐩戞帶妫€鏌ラ棿闅?(ms) */
    monitorIntervalMs: parseInt(ENV.MONITOR_INTERVAL_MS) || 1000
};

// ============================================================================
// 浠ｇ悊閰嶇疆 (Proxy) - V173-OVERHAUL: 22 涓嫭绔?IP 鐏姏鍏ㄥ紑
// ============================================================================

const PROXY_CONFIG = {
    /**
     * V173-OVERHAUL: 22 涓嫭绔?IP 浠ｇ悊绔彛姹?     * 绔彛鑼冨洿来自共享 proxy_pool 配置
     * 姣忎釜绔彛瀵瑰簲涓€涓嫭绔?IP 鍦板潃
     */
    ports: [...resolvedProxyPorts],

    /** 榛樿浠ｇ悊绔彛 */
    defaultPort: resolvedDefaultProxyPort,

    /** 浠ｇ悊鏈嶅姟鍣ㄥ湴鍧€妯℃澘 - V174-TUNING: 浣跨敤鐩存帴 IP 鍦板潃鎻愰珮绋冲畾鎬?*/
    serverTemplate: resolvedProxyServerTemplate,

    /** 浠ｇ悊鍋ュ悍妫€鏌ヨ秴鏃?(ms) */
    healthCheckTimeout: parseInt(ENV.PROXY_HEALTH_TIMEOUT) || 10000,

    /**
     * 鑾峰彇浠ｇ悊鏈嶅姟鍣ㄥ湴鍧€
     * @param {number} port - 浠ｇ悊绔彛
     * @returns {string} 浠ｇ悊鏈嶅姟鍣ㄥ湴鍧€
     */
    getServer(port = this.defaultPort) {
        return this.serverTemplate.replace('{port}', port);
    },

    /**
     * V173-OVERHAUL: 鏍规嵁 Worker ID 瀹岀編鏄犲皠鍒?22 涓鍙?     * @param {number} workerId - Worker 缂栧彿 (1-based)
     * @returns {number} 浠ｇ悊绔彛
     */
    getPortByWorker(workerId) {
        // Worker ID 鏄?1-based锛岀鍙ｆ暟缁勬槸 0-based
        const index = (workerId - 1) % this.ports.length;
        return this.ports[index];
    },

    /**
     * V173-OVERHAUL: 鑾峰彇涓嬩竴涓彲鐢ㄧ鍙?(鐢ㄤ簬鏁呴殰鍒囨崲)
     * @param {number} currentPort - 褰撳墠绔彛
     * @returns {number} 涓嬩竴涓鍙?     */
    getNextPort(currentPort) {
        const currentIndex = this.ports.indexOf(currentPort);
        const nextIndex = (currentIndex + 1) % this.ports.length;
        return this.ports[nextIndex];
    },

    /**
     * V173-OVERHAUL: 鑾峰彇闅忔満绔彛 (鐢ㄤ簬鍒嗘暎鍘嬪姏)
     * @returns {number} 闅忔満绔彛
     */
    getRandomPort() {
        return this.ports[Math.floor(Math.random() * this.ports.length)];
    },

    /**
     * V172-STRENGTHEN: 鍔ㄦ€佹墿灞曠鍙ｆ睜
     * @param {number} count - 闇€瑕佺殑绔彛鏁伴噺
     */
    expandPorts(count) {
        const currentMax = Math.max(...this.ports);
        while (this.ports.length < count) {
            this.ports.push(currentMax + this.ports.length);
        }
    },

    /**
     * V173-OVERHAUL: 鎵撳嵃绔彛姹犵姸鎬?     */
    printStatus() {
        console.log(`馃摗 浠ｇ悊姹犵姸鎬? ${this.ports.length} 涓嫭绔?IP 灏辩华`);
        console.log(`   绔彛鑼冨洿: ${this.ports[0]} - ${this.ports[this.ports.length - 1]}`);
    }
};

// ============================================================================
// 鐔旀柇閰嶇疆 (Circuit Breaker) - V178: 5 娆?403/瓒呮椂瑙﹀彂, 60 绉掑喎鍗?// ============================================================================

const CIRCUIT_BREAKER = {
    /** 杩炵画澶辫触娆℃暟闃堝€?- V178: 浠?3 鎻愬崌鍒?5 */
    threshold: parseInt(ENV.CIRCUIT_BREAKER_THRESHOLD) || 5,

    /** Worker 閲嶅惎寤惰繜 (ms) */
    restartDelayMs: parseInt(ENV.WORKER_RESTART_DELAY_MS) || 30000,

    /** 鍐峰嵈鏈?(ms) - V178: 60 绉掑喎鍗?*/
    cooldownMs: parseInt(ENV.CIRCUIT_COOLDOWN) || 60000,

    /** 鍗婂紑鐘舵€佹祴璇曡姹傛暟 - V178: 浠?1 鎻愬崌鍒?3 */
    halfOpenRequests: 3,

    /** 鎴愬姛鎭㈠闃堝€?- V178: 鍗婂紑鐘舵€佹垚鍔?1 娆″嵆鎭㈠ */
    successThreshold: 1
};

// ============================================================================
// 鏁版嵁搴撻厤缃?(Database) - V174: 浼樺寲杩炴帴姹犳敮鎸侀珮骞跺彂
// ============================================================================

const DATABASE = {
    /** 杩炴帴瓒呮椂 (ms) */
    connectTimeout: parseInt(ENV.DB_CONNECT_TIMEOUT) || 10000,

    /** 鏌ヨ瓒呮椂 (ms) */
    queryTimeout: parseInt(ENV.DB_QUERY_TIMEOUT) || 30000,

    /** 杩炴帴姹犳渶澶ц繛鎺ユ暟 - V174: 20 鏀寔楂樺苟鍙?*/
    poolMax: parseInt(ENV.DB_POOL_MAX) || 20,

    /** 杩炴帴姹犳渶灏忚繛鎺ユ暟 */
    poolMin: parseInt(ENV.DB_POOL_MIN) || 5,

    /** 杩炴帴绌洪棽瓒呮椂 (ms) - V174: 30 绉?*/
    idleTimeoutMillis: parseInt(ENV.DB_IDLE_TIMEOUT) || 30000
};

// ============================================================================
// 娴忚鍣ㄩ厤缃?(Browser)
// ============================================================================

const BROWSER = {
    /** 娴忚鍣ㄩ厤缃枃浠惰矾寰?*/
    profilePath: ENV.BROWSER_PROFILE_PATH || path.join(process.cwd(), 'data/browser_profile'),

    /** 娴忚鍣ㄧ姸鎬佹枃浠跺悕 */
    stateFilename: 'browser_state.json',

    /** Cookie 淇濆瓨闂撮殧 (姣?N 鍦烘瘮璧涗繚瀛樹竴娆? */
    cookieSaveInterval: parseInt(ENV.COOKIE_SAVE_INTERVAL) || 3,

    /** 鏄惁鏃犲ご妯″紡 */
    headless: ENV.HEADLESS !== 'false',

    /** 娴忚鍣ㄥ惎鍔ㄥ弬鏁?*/
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
     * 鑾峰彇娴忚鍣ㄧ姸鎬佹枃浠跺畬鏁磋矾寰?     * @returns {string}
     */
    getStatePath() {
        const path = require('path');
        return path.join(this.profilePath, this.stateFilename);
    }
};

// ============================================================================
// 琛屼负妯℃嫙閰嶇疆 (Behavior Simulation)
// ============================================================================

const BEHAVIOR = {
    /** 婊氬姩娆℃暟鑼冨洿 [min, max] */
    scrollSteps: [2, 4],

    /** 榧犳爣绉诲姩娆℃暟鑼冨洿 [min, max] */
    mouseMoves: [3, 6],

    /** 榧犳爣绉诲姩姝ユ暟鑼冨洿 [min, max] */
    mouseSteps: [5, 15],

    /** 婊氬姩璺濈鑼冨洿 [min, max] (px) */
    scrollDistance: [100, 300],

    /** 婊氬姩闂撮殧鑼冨洿 [min, max] (ms) */
    scrollInterval: [500, 1500],

    /** 榧犳爣绉诲姩闂撮殧鑼冨洿 [min, max] (ms) */
    mouseInterval: [200, 800]
};

// ============================================================================
// 闈欐€佹寚绾归厤缃?(Fingerprint)
// ============================================================================

const FINGERPRINT = {
    /** 闈欐€佹寚绾?(涓庝細璇濋暅鍍忎竴鑷? */
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

    /** 闅忔満鎸囩汗姹?*/
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

    /** 璇█姹?*/
    languages: ['en-US,en;q=0.9', 'en-GB,en;q=0.9', 'en-US,en;q=0.9,en-GB;q=0.8'],

    /** 鏃跺尯姹?*/
    timezones: ['Europe/London', 'America/New_York', 'Europe/Paris'],

    /**
     * V173: 鍔ㄦ€?User-Agent 杞崲姹?(20 涓富娴?UA)
     * 鍖呭惈鏈€鏂扮殑妗岄潰绔拰绉诲姩绔祻瑙堝櫒鎸囩汗
     */
    uaPool: [
        // Chrome 妗岄潰绔?(Windows)
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
        // Chrome 妗岄潰绔?(macOS)
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        // Edge 妗岄潰绔?        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0',
        // Firefox 妗岄潰绔?        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:135.0) Gecko/20100101 Firefox/135.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 14.0; rv:134.0) Gecko/20100101 Firefox/134.0',
        // Safari 妗岄潰绔?(macOS)
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15',
        // Chrome 绉诲姩绔?(Android)
        'Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Mobile Safari/537.36',
        'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36',
        // Safari 绉诲姩绔?(iOS)
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
    ],

    /**
     * V173: 鑾峰彇闅忔満 User-Agent
     * @returns {string} 闅忔満 UA 瀛楃涓?     */
    getRandomUA() {
        return this.uaPool[Math.floor(Math.random() * this.uaPool.length)];
    },

    /**
     * V173: 鑾峰彇闅忔満瑙嗗彛灏哄
     * @returns {Object} 瑙嗗彛閰嶇疆
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
            { width: 1287, height: 1271 }  // 鍘熷浼氳瘽闀滃儚灏哄
        ];
        return viewports[Math.floor(Math.random() * viewports.length)];
    }
};

// ============================================================================
// V173: FotMob 娣卞害闈欓粯妯″紡閰嶇疆 (Cool Down)
// ============================================================================

const FOTMOB_COOL_DOWN = {
    /** 鏄惁鍚敤娣卞害闈欓粯妯″紡 */
    enabled: ENV.ENABLE_COOL_DOWN !== 'false',

    /** 瑙﹀彂鐔旀柇鐨勮繛缁け璐ユ鏁?*/
    triggerThreshold: parseInt(ENV.COOL_DOWN_THRESHOLD) || 3,

    /** 鍐峰嵈鏃堕棿 (姣) - 榛樿 30 鍒嗛挓 */
    durationMs: parseInt(ENV.COOL_DOWN_DURATION_MS) || 30 * 60 * 1000,

    /** 闇€瑕佽Е鍙戝喎鍗寸殑閿欒绫诲瀷 */
    triggerErrors: [
        'SIZE_TOO_SMALL',
        'TURNSTILE_REQUIRED',
        'CONTAINS_TURNSTILE',
        'BLOCKED',
        'CAPTCHA'
    ],

    /** 褰撳墠鍐峰嵈鐘舵€?(杩愯鏃? */
    _activeCoolDowns: new Map(),

    /**
     * 妫€鏌ユ槸鍚﹀簲璇ヨЕ鍙戝喎鍗?     * @param {string} errorType - 閿欒绫诲瀷
     * @param {number} consecutiveFailures - 杩炵画澶辫触娆℃暟
     * @returns {boolean}
     */
    shouldTrigger(errorType, consecutiveFailures) {
        const isErrorMatch = this.triggerErrors.some(e =>
            errorType.includes(e) || e.includes(errorType)
        );
        return isErrorMatch && consecutiveFailures >= this.triggerThreshold;
    },

    /**
     * 杩涘叆鍐峰嵈鐘舵€?     * @param {number} workerId - Worker ID
     */
    enterCoolDown(workerId) {
        const endTime = Date.now() + this.durationMs;
        this._activeCoolDowns.set(workerId, {
            startTime: Date.now(),
            endTime,
            duration: this.durationMs
        });
        const minutes = Math.round(this.durationMs / 60000);
        console.log(`鉂勶笍 Worker ${workerId} 杩涘叆娣卞害闈欓粯妯″紡锛屽喎鍗?${minutes} 鍒嗛挓`);
    },

    /**
     * 妫€鏌ユ槸鍚﹀湪鍐峰嵈涓?     * @param {number} workerId - Worker ID
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
     * 鑾峰彇鍓╀綑鍐峰嵈鏃堕棿 (姣)
     * @param {number} workerId - Worker ID
     * @returns {number} 鍓╀綑姣鏁帮紝0 琛ㄧず涓嶅湪鍐峰嵈涓?     */
    getRemainingTime(workerId) {
        const state = this._activeCoolDowns.get(workerId);
        if (!state) return 0;
        return Math.max(0, state.endTime - Date.now());
    }
};

// ============================================================================
// 璺緞閰嶇疆 (Paths)
// ============================================================================

const PATH_CONFIG = {
    /** 椤圭洰鏍圭洰褰?*/
    projectRoot: ENV.PROJECT_ROOT || '/app',

    /** 鏁版嵁搴撻厤缃矾寰?*/
    databaseConfig: path.join(process.cwd(), 'config/database'),

    /** 鏁版嵁鐩綍 */
    dataDir: ENV.DATA_DIR || path.join(process.cwd(), 'data'),

    /** 鏃ュ織鐩綍 */
    logDir: ENV.LOG_DIR || path.join(process.cwd(), 'logs'),

    /** Cookie 瀛樺偍璺緞 */
    cookiePath: path.join(process.cwd(), 'data/browser_profile/browser_state.json'),

    /** Worker 鑴氭湰璺緞 */
    workerScript: path.join(process.cwd(), 'scripts/ops/harvest_worker.js'),

    /** 鏍稿績寮曟搸璺緞 */
    enginePath: path.join(process.cwd(), 'src/domain/services/harvesting/MatchDetailEngine.js'),

    /** 娴忚鍣ㄩ厤缃洰褰?*/
    browserProfile: ENV.BROWSER_PROFILE_PATH || path.join(process.cwd(), 'data/browser_profile')
};

// ============================================================================
// 鏃ュ織閰嶇疆 (Logging)
// ============================================================================

const LOG_CONFIG = {
    /** 鏃ュ織绾у埆 */
    level: ENV.LOG_LEVEL || 'info',

    /** 鏃ュ織鏍煎紡 */
    format: 'timestamped',

    /** 鏄惁杈撳嚭鍒版枃浠?*/
    toFile: ENV.LOG_TO_FILE === 'true',

    /** 鏃ュ織鏂囦欢鏈€澶уぇ灏?(bytes) */
    maxFileSize: parseInt(ENV.LOG_MAX_SIZE) || 10 * 1024 * 1024,  // 10MB

    /** 鏃ュ織淇濈暀澶╂暟 */
    retentionDays: parseInt(ENV.LOG_RETENTION_DAYS) || 7
};

// ============================================================================
// 鍝ㄥ叺鐩戞帶閰嶇疆 (Sentinel)
// ============================================================================

const SENTINEL_CONFIG = {
    /** 鏈€澶уけ璐ョ巼闃堝€?*/
    maxFailureRate: parseFloat(ENV.MAX_FAILURE_RATE) || 0.10,

    /** 鏈€澶ц繛缁?403 閿欒娆℃暟 */
    maxConsecutive403: parseInt(ENV.MAX_CONSECUTIVE_403) || 5,

    /** 鍋ュ悍鎶ュ憡璺緞 */
    healthReportPath: ENV.HEALTH_REPORT_PATH || path.join(process.cwd(), 'logs/factory_health.json'),

    /** 鍛婅閭欢 (鍙€? */
    alertEmail: ENV.ALERT_EMAIL || null,

    /** Cookie 鏈€澶у勾榫?(姣) */
    cookieMaxAgeMs: parseInt(ENV.COOKIE_MAX_AGE_MS) || 24 * 60 * 60 * 1000  // 24 灏忔椂
};

// ============================================================================
// 澧為噺妯″紡閰嶇疆 (Incremental)
// ============================================================================

const INCREMENTAL_CONFIG = {
    /** 鍥炴函澶╂暟 */
    lookbackDays: parseInt(ENV.INCREMENTAL_LOOKBACK_DAYS) || 7,

    /** 鐩爣鐘舵€佸垪琛?*/
    targetStatuses: ['completed', 'finished'],

    /** 鎺掗櫎鐨勮仈璧?(鍙€? */
    excludedLeagues: (ENV.EXCLUDED_LEAGUES || '').split(',').filter(Boolean)
};

// ============================================================================
// 杩愯妯″紡 (Run Modes)
// ============================================================================

const RUN_MODES = {
    INCREMENTAL: 'incremental',
    REPAIR: 'repair',
    FULL: 'full'
};

// ============================================================================
// 杈呭姪鍑芥暟
// ============================================================================

/**
 * 鑾峰彇闅忔満寤舵椂 (姣)
 * @param {number[]} range - [min, max] 鑼冨洿
 * @returns {number} 闅忔満姣鏁? */
function getRandomDelay(range = [TIMING.minDelayMs, TIMING.maxDelayMs]) {
    return Math.floor(Math.random() * (range[1] - range[0] + 1)) + range[0];
}

/**
 * V178: 鑾峰彇鎸囨暟閫€閬垮欢鏃?(1s -> 2s -> 4s 甯︽姈鍔?
 * @param {number} attempt - 褰撳墠灏濊瘯娆℃暟 (1-based)
 * @returns {number} 閫€閬垮欢鏃?(ms)
 */
function getExponentialBackoff(attempt) {
    // V178: 鍥哄畾閫€閬垮簭鍒?1s -> 2s -> 4s
    const baseDelay = 1000 * Math.pow(2, attempt - 1);  // 1000, 2000, 4000
    const delay = Math.min(baseDelay, 4000);  // 涓婇檺 4 绉?
    // V178: 卤20% 鎶栧姩
    const jitter = delay * 0.2 * (Math.random() * 2 - 1);
    return Math.floor(delay + jitter);
}

/**
 * 闅忔満鏁扮敓鎴?(鑼冨洿)
 * @param {number} min - 鏈€灏忓€? * @param {number} max - 鏈€澶у€? * @returns {number}
 */
function randomInRange(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

/**
 * 闅忔満閫夋嫨鏁扮粍鍏冪礌
 * @param {Array} arr - 鏁扮粍
 * @returns {*}
 */
function randomChoice(arr) {
    return arr[Math.floor(Math.random() * arr.length)];
}

// ============================================================================
// 瀵煎嚭
// ============================================================================

module.exports = {
    // 閰嶇疆妯″潡
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

    // V173: 鏂板閰嶇疆
    FOTMOB_COOL_DOWN,

    // 杈呭姪鍑芥暟
    getRandomDelay,
    getExponentialBackoff,
    randomInRange,
    randomChoice,

    // 鐗堟湰淇℃伅
    VERSION: 'V178.0.0',
    BUILD_DATE: '2026-03-03'
};
