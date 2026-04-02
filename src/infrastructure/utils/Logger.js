/**
 * V186 Enterprise Logger - 工业级日志系统
 * ==============================================
 *
 * 全局单例日志器，支持：
 * - JSON 格式（生产环境）或彩色 Text（开发环境）
 * - 自动归档到 /app/logs/combined.log 和 error.log
 * - 元数据：时间戳、WorkerID、ProxyPort、MatchID
 * - 日志轮转：按日期自动归档
 * @module infrastructure/utils/Logger
 * @version V186.0.0
 */

'use strict';

const winston = require('winston');
const path = require('path');
const fs = require('fs');

// ============================================================================
// 环境配置
// ============================================================================

// V4.46-TITAN: 环境常量定义
const IS_PRODUCTION = process.env.NODE_ENV === 'production';
const IS_TEST_ENV = process.env.NODE_ENV === 'test' ||
    process.argv.includes('--test') ||
    process.argv.some(arg => /\.test\.js$/i.test(arg)) ||
    Boolean(process.env.NODE_TEST_CONTEXT);
const LOG_LEVEL = process.env.LOG_LEVEL || (IS_PRODUCTION ? 'info' : 'debug');

// ============================================================================
// V4.46-TITAN: 彻底解决 WSL/Windows 路径兼容性
// ============================================================================
const CWD = process.cwd();
// 检测是否处于 Windows 操作 WSL 的特殊路径
const IS_WSL_WINDOWS_PATH = CWD.includes('\\\\wsl.localhost\\') || CWD.includes('\\wsl$\\');

// 关键修复：如果是 WSL 路径，强制关闭文件日志存储，只保留控制台输出
const FILE_LOG_ENABLED = !IS_TEST_ENV && !IS_WSL_WINDOWS_PATH && process.env.DISABLE_FILE_LOG !== 'true';

const LOG_DIR = path.join(process.cwd(), 'logs');

// 仅在启用文件日志且目录不存在时尝试创建
if (FILE_LOG_ENABLED && !fs.existsSync(LOG_DIR)) {
    try {
        fs.mkdirSync(LOG_DIR, { recursive: true });
        console.log(`[Logger] 日志目录已创建: ${LOG_DIR}`);
    } catch (err) {
        console.warn(`[Logger] 目录创建跳过: ${err.message}`);
    }
}

// WSL 路径警告
if (IS_WSL_WINDOWS_PATH) {
    console.warn('[Logger] 检测到 WSL 路径，文件日志已禁用，仅输出到控制台');
}

// ============================================================================
// 自定义格式
// ============================================================================

/**
 * 开发环境：彩色文本格式
 */
const devFormat = winston.format.combine(
    winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss.SSS' }),
    winston.format.printf(({ level, message, timestamp, ...metadata }) => {
        // 颜色映射
        const colors = {
            error: '\x1b[31m',   // 红色
            warn: '\x1b[33m',    // 黄色
            info: '\x1b[36m',    // 青色
            debug: '\x1b[90m',   // 灰色
            verbose: '\x1b[35m'  // 紫色
        };
        const reset = '\x1b[0m';
        const color = colors[level] || '';

        // 构建元数据字符串
        let metaStr = '';
        if (Object.keys(metadata).length > 0) {
            const { workerId, proxyPort, matchId, attempt, oldPort, newPort, errorType } = metadata;
            const parts = [];
            if (workerId !== undefined) parts.push(`W${workerId}`);
            if (proxyPort !== undefined) parts.push(`P${proxyPort}`);
            if (matchId !== undefined) parts.push(`M:${matchId.slice(0, 8)}...`);
            if (attempt !== undefined) parts.push(`重试#${attempt}`);
            if (oldPort !== undefined && newPort !== undefined) parts.push(`${oldPort}→${newPort}`);
            if (errorType !== undefined) parts.push(`[${errorType}]`);
            if (parts.length > 0) {
                metaStr = ` [${parts.join(' | ')}]`;
            }
        }

        return `${timestamp} ${color}[${level.toUpperCase().padEnd(5)}]${reset}${metaStr} ${message}`;
    })
);

/**
 * 生产环境：JSON 格式
 */
const prodFormat = winston.format.combine(
    winston.format.timestamp({ format: 'YYYY-MM-DDTHH:mm:ss.SSSZ' }),
    winston.format.errors({ stack: true }),
    winston.format.json()
);

// ============================================================================
// 日志传输配置 (V4.46-TITAN: 支持 WSL 路径兼容)
// ============================================================================

/**
 * 构建传输列表 - 根据环境动态配置
 * @returns {Array} Winston 传输列表
 */
function buildTransports() {
    const transports = [];

    // 控制台输出 - 始终启用
    transports.push(new winston.transports.Console({
        format: IS_PRODUCTION ? prodFormat : devFormat,
        stderrLevels: ['error', 'warn']
    }));

    // 文件传输 - 仅在 FILE_LOG_ENABLED 时启用
    if (FILE_LOG_ENABLED) {
        const dailyRotateFile = require('winston-daily-rotate-file');

        transports.push(
            new dailyRotateFile({
                filename: path.join(LOG_DIR, 'combined-%DATE%.log'),
                datePattern: 'YYYY-MM-DD',
                zippedArchive: true,
                maxSize: '50m',
                maxFiles: '30d',
                format: IS_PRODUCTION ? prodFormat : devFormat
            }),
            new dailyRotateFile({
                filename: path.join(LOG_DIR, 'error-%DATE%.log'),
                datePattern: 'YYYY-MM-DD',
                zippedArchive: true,
                maxSize: '20m',
                maxFiles: '60d',
                level: 'error',
                format: IS_PRODUCTION ? prodFormat : devFormat
            })
        );
    }

    return transports;
}

/**
 * 构建异常处理器 - 根据环境动态配置
 * @returns {Array|undefined} Winston 异常处理器列表
 */
function buildExceptionHandlers() {
    if (!FILE_LOG_ENABLED) {
        return undefined;
    }

    const dailyRotateFile = require('winston-daily-rotate-file');

    return [
        new dailyRotateFile({
            filename: path.join(LOG_DIR, 'exceptions-%DATE%.log'),
            datePattern: 'YYYY-MM-DD',
            zippedArchive: true,
            maxSize: '20m',
            maxFiles: '30d'
        })
    ];
}

/**
 * 构建拒绝处理器 - 根据环境动态配置
 * @returns {Array|undefined} Winston 拒绝处理器列表
 */
function buildRejectionHandlers() {
    if (!FILE_LOG_ENABLED) {
        return undefined;
    }

    const dailyRotateFile = require('winston-daily-rotate-file');

    return [
        new dailyRotateFile({
            filename: path.join(LOG_DIR, 'rejections-%DATE%.log'),
            datePattern: 'YYYY-MM-DD',
            zippedArchive: true,
            maxSize: '20m',
            maxFiles: '30d'
        })
    ];
}

// ============================================================================
// 全局单例 Logger
// ============================================================================

/**
 * EnterpriseLogger - 企业级日志器单例
 */
class EnterpriseLogger {
    /**
     *
     */
    constructor() {
        if (EnterpriseLogger.instance) {
            return EnterpriseLogger.instance;
        }

        this.logger = winston.createLogger({
            level: LOG_LEVEL,
            defaultMeta: {
                service: 'FootballPrediction',
                version: 'V186.0.0',
                pid: process.pid
            },
            transports: buildTransports(),
            exceptionHandlers: buildExceptionHandlers(),
            rejectionHandlers: buildRejectionHandlers()
        });

        EnterpriseLogger.instance = this;
    }

    // ========================================================================
    // 基础日志方法
    // ========================================================================

    /**
     * 记录 INFO 级别日志
     * @param {string} message - 日志消息
     * @param {object} [meta] - 元数据
     */
    info(message, meta = {}) {
        this.logger.info(message, meta);
    }

    /**
     * 记录 WARN 级别日志
     * @param {string} message - 日志消息
     * @param {object} [meta] - 元数据
     */
    warn(message, meta = {}) {
        this.logger.warn(message, meta);
    }

    /**
     * 记录 ERROR 级别日志
     * @param {string} message - 日志消息
     * @param {Error | object} [error] - 错误对象或元数据
     * @param {object} [meta] - 额外元数据
     */
    error(message, error = {}, meta = {}) {
        if (error instanceof Error) {
            this.logger.error(message, {
                ...meta,
                errorName: error.name,
                errorMessage: error.message,
                stack: error.stack
            });
        } else {
            this.logger.error(message, { ...error, ...meta });
        }
    }

    /**
     * 记录 DEBUG 级别日志
     * @param {string} message - 日志消息
     * @param {object} [meta] - 元数据
     */
    debug(message, meta = {}) {
        this.logger.debug(message, meta);
    }

    /**
     * 记录 VERBOSE 级别日志
     * @param {string} message - 日志消息
     * @param {object} [meta] - 元数据
     */
    verbose(message, meta = {}) {
        this.logger.verbose(message, meta);
    }

    // ========================================================================
    // V186: 企业级专用日志方法
    // ========================================================================

    /**
     * 记录 Worker 启动日志
     * @param {number} workerId - Worker ID
     * @param {number} proxyPort - 代理端口
     * @param {object} [extra] - 额外信息
     */
    logWorkerStart(workerId, proxyPort, extra = {}) {
        this.info(`🚀 Worker ${workerId} 启动`, {
            workerId,
            proxyPort,
            event: 'WORKER_START',
            ...extra
        });
    }

    /**
     * 记录收割成功日志
     * @param {number} workerId - Worker ID
     * @param {string} matchId - 比赛 ID
     * @param {number} proxyPort - 代理端口
     * @param {object} [extra] - 额外信息
     */
    logHarvestSuccess(workerId, matchId, proxyPort, extra = {}) {
        this.info(`✅ Worker ${workerId} 收割成功: ${matchId}`, {
            workerId,
            matchId,
            proxyPort,
            event: 'HARVEST_SUCCESS',
            ...extra
        });
    }

    /**
     * V186: 记录重试日志（包含端口切换信息）
     * @param {number} workerId - Worker ID
     * @param {string} matchId - 比赛 ID
     * @param {number} attempt - 当前尝试次数
     * @param {number} oldPort - 旧端口
     * @param {number} newPort - 新端口
     * @param {string} errorType - 错误类型
     * @param {string} reason - 重试原因
     */
    logRetry(workerId, matchId, attempt, oldPort, newPort, errorType, reason) {
        this.warn(`🔄 Worker ${workerId} 重试 #${attempt}: ${reason}`, {
            workerId,
            matchId,
            attempt,
            oldPort,
            newPort,
            errorType,
            event: 'RETRY'
        });
    }

    /**
     * V186: 记录致命错误（程序必须退出）
     * @param {string} message - 错误消息
     * @param {Error} [error] - 错误对象
     * @param {object} [meta] - 元数据
     */
    logFatal(message, error = null, meta = {}) {
        const errorMeta = error instanceof Error ? {
            errorName: error.name,
            errorMessage: error.message,
            stack: error.stack
        } : error || {};

        this.logger.error(`💀 FATAL: ${message}`, {
            ...errorMeta,
            ...meta,
            severity: 'FATAL',
            event: 'FATAL_ERROR'
        });
    }

    /**
     * V186: 记录可重试错误
     * @param {number} workerId - Worker ID
     * @param {string} matchId - 比赛 ID
     * @param {string} errorType - 错误类型
     * @param {string} reason - 错误原因
     * @param {object} [meta] - 额外元数据
     */
    logRetryableError(workerId, matchId, errorType, reason, meta = {}) {
        this.warn(`⚠️ Worker ${workerId} 可重试错误: ${errorType} - ${reason}`, {
            workerId,
            matchId,
            errorType,
            reason,
            severity: 'RETRYABLE',
            event: 'RETRYABLE_ERROR',
            ...meta
        });
    }

    /**
     * 记录 WebGL 指纹随机化结果
     * @param {number} workerId - Worker ID
     * @param {string} webglRenderer - WebGL 渲染器
     * @param {object} [extra] - 额外信息
     */
    logWebGLFingerprint(workerId, webglRenderer, extra = {}) {
        this.debug(`🎨 Worker ${workerId} WebGL 指纹: ${webglRenderer.slice(0, 50)}...`, {
            workerId,
            webglRenderer,
            event: 'WEBGL_FINGERPRINT',
            ...extra
        });
    }

    /**
     * 记录优雅停机事件
     * @param {string} signal - 信号类型
     * @param {number} activeWorkers - 活跃 Worker 数量
     */
    logGracefulShutdown(signal, activeWorkers) {
        this.info(`🛑 收到 ${signal} 信号，开始优雅停机 (活跃 Worker: ${activeWorkers})`, {
            signal,
            activeWorkers,
            event: 'GRACEFUL_SHUTDOWN_START'
        });
    }

    /**
     * 记录停机完成
     * @param {number} durationMs - 停机耗时（毫秒）
     * @param {object} [stats] - 统计信息
     */
    logShutdownComplete(durationMs, stats = {}) {
        this.info(`✅ 优雅停机完成，耗时 ${durationMs}ms`, {
            durationMs,
            event: 'GRACEFUL_SHUTDOWN_COMPLETE',
            ...stats
        });
    }

    /**
     * 创建带 Worker 上下文的子日志器
     * @param {number} workerId - Worker ID
     * @param {number} proxyPort - 代理端口
     * @returns {object} 子日志器
     */
    createWorkerLogger(workerId, proxyPort) {
        const self = this;
        return {
            info: (msg, meta = {}) => self.info(msg, { workerId, proxyPort, ...meta }),
            warn: (msg, meta = {}) => self.warn(msg, { workerId, proxyPort, ...meta }),
            error: (msg, err = {}, meta = {}) => self.error(msg, err, { workerId, proxyPort, ...meta }),
            debug: (msg, meta = {}) => self.debug(msg, { workerId, proxyPort, ...meta }),
            logRetry: (matchId, attempt, newPort, errorType, reason) =>
                self.logRetry(workerId, matchId, attempt, proxyPort, newPort, errorType, reason),
            logSuccess: (matchId, extra = {}) =>
                self.logHarvestSuccess(workerId, matchId, proxyPort, extra),
            logWebGL: (webglRenderer) =>
                self.logWebGLFingerprint(workerId, webglRenderer)
        };
    }
}

// ============================================================================
// 导出单例
// ============================================================================

let loggerInstance = null;

/**
 * 获取全局 Logger 单例
 * @returns {EnterpriseLogger}
 */
function getLogger() {
    if (!loggerInstance) {
        loggerInstance = new EnterpriseLogger();
    }
    return loggerInstance;
}

// 默认导出单例
const logger = getLogger();

module.exports = {
    EnterpriseLogger,
    getLogger,
    logger
};
