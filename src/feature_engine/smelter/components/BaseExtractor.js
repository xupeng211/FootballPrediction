/**
 * BaseExtractor - V4.0 特征提取器抽象基类
 * ========================================
 *
 * 建立特征提取的"行业标准"，强制规范所有特征维度的开发协议。
 * 所有具体提取器必须继承此类并实现抽象方法。
 *
 * @module feature_engine/smelter/components/BaseExtractor
 * @version V4.0.0-MODULAR
 * @since 2026-03-14
 */

'use strict';

// ============================================================================
// 提取器异常类
// ============================================================================

/**
 * 提取器异常
 */
class ExtractorError extends Error {
    /**
     * @param {string} message - 错误信息
     * @param {string} code - 错误代码
     * @param {*} context - 上下文数据
     */
    constructor(message, code = 'EXTRACTOR_ERROR', context = null) {
        super(message);
        this.name = 'ExtractorError';
        this.code = code;
        this.context = context;
        this.timestamp = new Date().toISOString();
    }
}

/**
 * 验证错误
 */
class ValidationError extends ExtractorError {
    constructor(message, missingFields = [], context = null) {
        super(message, 'VALIDATION_ERROR', context);
        this.name = 'ValidationError';
        this.missingFields = missingFields;
    }
}

/**
 * 提取错误
 */
class ExtractionError extends ExtractorError {
    constructor(message, extractPhase = 'unknown', context = null) {
        super(message, 'EXTRACTION_ERROR', context);
        this.name = 'ExtractionError';
        this.extractPhase = extractPhase;
    }
}

// ============================================================================
// 抽象基类
// ============================================================================

/**
 * 特征提取器抽象基类
 * 所有具体提取器必须继承并实现抽象方法
 */
class BaseExtractor {
    /**
     * @param {object} options - 配置选项
     * @param {string} options.name - 提取器名称（必填）
     * @param {string} options.version - 版本号
     * @param {Array<string>} options.requiredFields - 必需字段路径列表
     * @param {object} options.config - 提取器特定配置
     */
    constructor(options = {}) {
        // 验证名称（子类必须提供）
        if (!options.name) {
            throw new ExtractorError(
                '提取器名称必填',
                'MISSING_NAME',
                { options }
            );
        }

        this.name = options.name;
        this.version = options.version || 'V4.0.0';
        this.requiredFields = options.requiredFields || [];
        this.config = { ...this.getDefaultConfig(), ...(options.config || {}) };

        // 统计数据
        this.stats = {
            totalCalls: 0,
            successfulCalls: 0,
            failedCalls: 0,
            validationFailures: 0,
            lastCalledAt: null,
            avgExecutionTimeMs: 0
        };

        // 初始化钩子
        this.onInitialize();
    }

    // ========================================================================
    // 抽象方法（子类必须实现）
    // ========================================================================

    /**
     * 执行特征提取（抽象方法，子类必须实现）
     * @abstract
     * @param {object} rawData - 原始数据
     * @param {object} context - 上下文信息
     * @returns {object} 提取的特征
     * @throws {ExtractionError} 提取失败时抛出
     */
    extract(rawData, context = {}) {
        throw new ExtractorError(
            `提取器 ${this.name} 必须实现 extract 方法`,
            'ABSTRACT_METHOD_NOT_IMPLEMENTED',
            { extractor: this.name }
        );
    }

    /**
     * 获取该提取器产出的特征字段名清单（抽象方法）
     * @abstract
     * @returns {Array<string>} 特征字段名数组
     */
    getFeatureNames() {
        throw new ExtractorError(
            `提取器 ${this.name} 必须实现 getFeatureNames 方法`,
            'ABSTRACT_METHOD_NOT_IMPLEMENTED',
            { extractor: this.name }
        );
    }

    /**
     * 获取默认配置（子类可覆盖）
     * @returns {object} 默认配置对象
     */
    getDefaultConfig() {
        return {};
    }

    // ========================================================================
    // 通用逻辑（子类可直接使用）
    // ========================================================================

    /**
     * 验证原始数据是否具备提取所需的最小字段集
     * @param {object} rawData - 原始数据
     * @param {Array<string>} [additionalFields] - 额外需要验证的字段
     * @returns {object} 验证结果 { valid: boolean, missing: Array<string>, present: Array<string> }
     */
    validate(rawData, additionalFields = []) {
        const fieldsToCheck = [...this.requiredFields, ...additionalFields];
        const missing = [];
        const present = [];

        if (!rawData || typeof rawData !== 'object') {
            return {
                valid: false,
                missing: fieldsToCheck,
                present: [],
                error: '原始数据为空或非对象类型'
            };
        }

        for (const fieldPath of fieldsToCheck) {
            if (this._hasPath(rawData, fieldPath)) {
                present.push(fieldPath);
            } else {
                missing.push(fieldPath);
            }
        }

        const valid = missing.length === 0;

        return {
            valid,
            missing,
            present,
            completeness: fieldsToCheck.length > 0
                ? present.length / fieldsToCheck.length
                : 1.0
        };
    }

    /**
     * 严格验证（验证失败时抛出异常）
     * @param {object} rawData - 原始数据
     * @param {Array<string>} [additionalFields] - 额外需要验证的字段
     * @throws {ValidationError} 验证失败时抛出
     */
    validateStrict(rawData, additionalFields = []) {
        const result = this.validate(rawData, additionalFields);

        if (!result.valid) {
            this.stats.validationFailures++;
            throw new ValidationError(
                `数据验证失败: 缺少必需字段 [${result.missing.join(', ')}]`,
                result.missing,
                { data: rawData, extractor: this.name }
            );
        }

        return result;
    }

    /**
     * 执行提取（带验证、统计、错误处理）
     * @param {object} rawData - 原始数据
     * @param {object} context - 上下文信息
     * @returns {object} 提取的特征
     */
    async extractSafe(rawData, context = {}) {
        const startTime = Date.now();
        this.stats.totalCalls++;
        this.stats.lastCalledAt = new Date().toISOString();

        try {
            // 验证数据
            const validation = this.validate(rawData);
            if (!validation.valid && this.config.strictMode) {
                this.validateStrict(rawData);
            }

            // 执行提取
            const features = await this.extract(rawData, context);

            // 添加元数据
            const result = {
                ...features,
                _extractor: this.name,
                _version: this.version,
                _extractedAt: new Date().toISOString(),
                _validation: {
                    valid: validation.valid,
                    completeness: validation.completeness
                }
            };

            // 更新统计
            this.stats.successfulCalls++;
            const executionTime = Date.now() - startTime;
            this._updateAvgExecutionTime(executionTime);

            return result;

        } catch (error) {
            this.stats.failedCalls++;

            if (error instanceof ExtractorError) {
                throw error;
            }

            throw new ExtractionError(
                `提取失败: ${error.message}`,
                'extract',
                { originalError: error.message, extractor: this.name }
            );
        }
    }

    /**
     * 同步版本提取（用于简单场景）
     * @param {object} rawData - 原始数据
     * @param {object} context - 上下文信息
     * @returns {object} 提取的特征
     */
    extractSync(rawData, context = {}) {
        const startTime = Date.now();
        this.stats.totalCalls++;
        this.stats.lastCalledAt = new Date().toISOString();

        try {
            // 验证数据（严格模式下会抛出异常）
            const validation = this.config.strictMode
                ? this.validateStrict(rawData)
                : this.validate(rawData);

            // 执行提取
            const features = this.extract(rawData, context);

            // 添加元数据
            const result = {
                ...features,
                _extractor: this.name,
                _version: this.version,
                _extractedAt: new Date().toISOString(),
                _validation: {
                    valid: validation.valid,
                    completeness: validation.completeness
                }
            };

            // 更新统计
            this.stats.successfulCalls++;
            const executionTime = Date.now() - startTime;
            this._updateAvgExecutionTime(executionTime);

            return result;

        } catch (error) {
            this.stats.failedCalls++;

            if (error instanceof ExtractorError) {
                throw error;
            }

            throw new ExtractionError(
                `提取失败: ${error.message}`,
                'extract',
                { originalError: error.message, extractor: this.name }
            );
        }
    }

    // ========================================================================
    // 工具方法（子类可使用）
    // ========================================================================

    /**
     * 安全获取对象属性
     * @param {object} obj - 源对象
     * @param {string} path - 属性路径 (如 'a.b.c')
     * @param {*} defaultValue - 默认值
     * @returns {*}
     */
    safeGet(obj, path, defaultValue = undefined) {
        if (!obj || typeof obj !== 'object') {
            return defaultValue;
        }

        const keys = path.split('.');
        let current = obj;

        for (const key of keys) {
            if (current === null || current === undefined) {
                return defaultValue;
            }
            if (typeof current !== 'object') {
                return defaultValue;
            }
            current = current[key];
        }

        return current !== undefined && current !== null ? current : defaultValue;
    }

    /**
     * 检查对象是否有指定路径
     * @param {object} obj - 源对象
     * @param {string} path - 属性路径
     * @returns {boolean}
     */
    _hasPath(obj, path) {
        if (!obj || typeof obj !== 'object') {
            return false;
        }

        const keys = path.split('.');
        let current = obj;

        for (const key of keys) {
            if (current === null || current === undefined || typeof current !== 'object') {
                return false;
            }
            current = current[key];
        }

        return current !== undefined;
    }

    /**
     * 检查是否为有效数字
     * @param {*} value - 待检查值
     * @returns {boolean}
     */
    isValidNumber(value) {
        return typeof value === 'number' && !isNaN(value) && isFinite(value);
    }

    /**
     * 检查是否为有效对象
     * @param {*} value - 待检查值
     * @returns {boolean}
     */
    isValidObject(value) {
        return value !== null && typeof value === 'object' && !Array.isArray(value);
    }

    /**
     * 创建空特征对象（带错误信息）
     * @param {string} reason - 原因说明
     * @param {object} defaults - 默认字段值
     * @returns {object}
     */
    createEmptyFeatures(reason = 'No valid data', defaults = {}) {
        const featureNames = this.getFeatureNames();
        const emptyFeatures = {};

        // 为所有特征字段设置默认值 0
        for (const name of featureNames) {
            emptyFeatures[name] = defaults[name] || 0;
        }

        return {
            ...emptyFeatures,
            _error: reason,
            _extractor: this.name,
            _version: this.version,
            _extractedAt: new Date().toISOString()
        };
    }

    /**
     * 获取统计信息
     * @returns {object}
     */
    getStats() {
        return {
            ...this.stats,
            name: this.name,
            version: this.version,
            successRate: this.stats.totalCalls > 0
                ? (this.stats.successfulCalls / this.stats.totalCalls * 100).toFixed(2) + '%'
                : 'N/A'
        };
    }

    /**
     * 重置统计
     */
    resetStats() {
        this.stats = {
            totalCalls: 0,
            successfulCalls: 0,
            failedCalls: 0,
            validationFailures: 0,
            lastCalledAt: null,
            avgExecutionTimeMs: 0
        };
    }

    // ========================================================================
    // 生命周期钩子（子类可覆盖）
    // ========================================================================

    /**
     * 初始化钩子
     */
    onInitialize() {
        // 子类可覆盖
    }

    /**
     * 关闭钩子
     */
    onClose() {
        // 子类可覆盖
    }

    // ========================================================================
    // 私有方法
    // ========================================================================

    /**
     * 更新平均执行时间
     * @private
     * @param {number} executionTime - 本次执行时间
     */
    _updateAvgExecutionTime(executionTime) {
        const { successfulCalls, avgExecutionTimeMs } = this.stats;
        if (successfulCalls === 1) {
            this.stats.avgExecutionTimeMs = executionTime;
        } else {
            // 移动平均
            this.stats.avgExecutionTimeMs =
                (avgExecutionTimeMs * (successfulCalls - 1) + executionTime) / successfulCalls;
        }
    }
}

// ============================================================================
// 导出
// ============================================================================
module.exports = {
    BaseExtractor,
    ExtractorError,
    ValidationError,
    ExtractionError
};
