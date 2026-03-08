/**
 * PathResolver - V4.46 统一路径管理器
 * ================================
 *
 * 集中管理所有文件系统路径，支持容器/本地环境自动适配
 * 为"绞杀者模式"重构提供路径解耦基础
 *
 * @module infrastructure/utils/PathResolver
 * @version V4.46.0
 */

'use strict';

const path = require('path');
const fs = require('fs');

/**
 * PathResolver - 统一路径解析器
 *
 * 功能:
 * 1. 自动检测运行环境 (容器/本地)
 * 2. 统一管理所有路径常量
 * 3. 提供路径验证和创建功能
 */
class PathResolver {
    /**
     * @param {Object} options - 配置选项
     * @param {string} [options.appRoot] - 应用根目录 (默认自动检测)
     * @param {boolean} [options.isContainer] - 是否容器环境 (默认自动检测)
     */
    constructor(options = {}) {
        // 自动检测环境
        this.isContainer = options.isContainer ?? this._detectContainer();
        this.appRoot = options.appRoot || (this.isContainer ? '/app' : this._findProjectRoot());

        // 初始化路径映射
        this._initPaths();
    }

    /**
     * 检测是否在容器中运行
     * @private
     * @returns {boolean}
     */
    _detectContainer() {
        // 检查常见容器标识
        const containerIndicators = [
            fs.existsSync('/.dockerenv'),
            fs.existsSync('/app/package.json') && !fs.existsSync('./package.json'),
            process.env.KUBERNETES_SERVICE_HOST !== undefined,
            process.env.DOCKER_CONTAINER !== undefined
        ];

        return containerIndicators.some(Boolean);
    }

    /**
     * 查找项目根目录
     * @private
     * @returns {string}
     */
    _findProjectRoot() {
        let currentDir = process.cwd();

        // 向上查找直到找到 package.json
        while (currentDir !== path.dirname(currentDir)) {
            if (fs.existsSync(path.join(currentDir, 'package.json'))) {
                return currentDir;
            }
            currentDir = path.dirname(currentDir);
        }

        // 回退到 cwd
        return process.cwd();
    }

    /**
     * 初始化路径映射
     * @private
     */
    _initPaths() {
        // 基础路径
        this.paths = {
            // 数据目录
            data: path.join(this.appRoot, 'data'),
            dataBrowserProfile: path.join(this.appRoot, 'data/browser_profile'),
            dataNetwork: path.join(this.appRoot, 'data/network'),
            dataRegistry: path.join(this.appRoot, 'data/registry'),
            dataSessions: path.join(this.appRoot, 'data/sessions'),
            dataRegression: path.join(this.appRoot, 'data/regression'),
            dataLogs: path.join(this.appRoot, 'data/logs'),

            // 配置目录
            config: path.join(this.appRoot, 'config'),

            // 日志目录
            logs: path.join(this.appRoot, 'logs'),

            // 特定文件
            browserState: path.join(this.appRoot, 'data/browser_profile/browser_state.json'),
            registryLock: path.join(this.appRoot, 'config/.registry.lock')
        };

        // 锁文件目录列表 (用于清理)
        this.lockDirs = [
            this.paths.dataNetwork,
            this.paths.dataRegistry,
            this.paths.config
        ];

        // 特定锁文件路径
        this.lockFiles = [
            this.paths.registryLock
        ];
    }

    // ========================================================================
    // 公开 API - 路径获取
    // ========================================================================

    /**
     * 获取浏览器状态文件路径
     * @returns {string}
     */
    getBrowserStatePath() {
        return this.paths.browserState;
    }

    /**
     * 获取会话目录路径
     * @returns {string}
     */
    getSessionsPath() {
        return this.paths.dataSessions;
    }

    /**
     * 获取网络数据目录
     * @returns {string}
     */
    getNetworkPath() {
        return this.paths.dataNetwork;
    }

    /**
     * 获取注册表目录
     * @returns {string}
     */
    getRegistryPath() {
        return this.paths.dataRegistry;
    }

    /**
     * 获取配置目录
     * @returns {string}
     */
    getConfigPath() {
        return this.paths.config;
    }

    /**
     * 获取注册表锁文件路径
     * @returns {string}
     */
    getRegistryLockPath() {
        return this.paths.registryLock;
    }

    /**
     * 获取所有锁文件目录
     * @returns {string[]}
     */
    getLockDirs() {
        return [...this.lockDirs];
    }

    /**
     * 获取所有特定锁文件路径
     * @returns {string[]}
     */
    getLockFiles() {
        return [...this.lockFiles];
    }

    /**
     * 获取日志目录
     * @returns {string}
     */
    getLogsPath() {
        return this.paths.logs;
    }

    /**
     * 获取回归测试数据目录
     * @returns {string}
     */
    getRegressionPath() {
        return this.paths.dataRegression;
    }

    /**
     * 解析相对路径为绝对路径
     * @param {string} relativePath - 相对路径 (相对于 appRoot)
     * @returns {string} 绝对路径
     */
    resolve(relativePath) {
        // 处理已 /app/ 开头的路径
        if (relativePath.startsWith('/app/')) {
            return path.join(this.appRoot, relativePath.slice(5));
        }
        return path.join(this.appRoot, relativePath);
    }

    // ========================================================================
    // 公开 API - 路径操作
    // ========================================================================

    /**
     * 确保目录存在
     * @param {string} dirPath - 目录路径
     * @returns {boolean} 是否成功创建
     */
    ensureDir(dirPath) {
        try {
            if (!fs.existsSync(dirPath)) {
                fs.mkdirSync(dirPath, { recursive: true });
            }
            return true;
        } catch (error) {
            console.error(`PathResolver: 创建目录失败 ${dirPath}: ${error.message}`);
            return false;
        }
    }

    /**
     * 确保所有必要目录存在
     */
    ensureAllDirs() {
        const dirs = [
            this.paths.data,
            this.paths.dataBrowserProfile,
            this.paths.dataNetwork,
            this.paths.dataRegistry,
            this.paths.dataSessions,
            this.paths.dataRegression,
            this.paths.dataLogs,
            this.paths.config
        ];

        for (const dir of dirs) {
            this.ensureDir(dir);
        }
    }

    /**
     * 检查文件是否存在
     * @param {string} filePath - 文件路径
     * @returns {boolean}
     */
    exists(filePath) {
        return fs.existsSync(filePath);
    }

    /**
     * 获取路径信息摘要
     * @returns {Object}
     */
    getSummary() {
        return {
            isContainer: this.isContainer,
            appRoot: this.appRoot,
            paths: { ...this.paths },
            environment: {
                nodeEnv: process.env.NODE_ENV,
                cwd: process.cwd()
            }
        };
    }
}

// ============================================================================
// 单例导出
// ============================================================================

let instance = null;

/**
 * 获取 PathResolver 单例
 * @param {Object} [options] - 配置选项
 * @returns {PathResolver}
 */
function getPathResolver(options) {
    if (!instance) {
        instance = new PathResolver(options);
    }
    return instance;
}

/**
 * 重置单例 (用于测试)
 */
function resetPathResolver() {
    instance = null;
}

module.exports = {
    PathResolver,
    getPathResolver,
    resetPathResolver
};
