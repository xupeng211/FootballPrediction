/**
 * AbstractFileSystem - V1.1.0 [Genesis.Standardization] Dependency Injection Adapter
 * ================================================================================
 *
 * 文件系统抽象层 - 实现依赖注入（DI）原则，解耦核心逻辑与具体文件系统实现。
 *
 * 设计原则:
 * - 面向接口编程，而非实现
 * - 支持内存文件系统（测试场景）
 * - 支持原子写入操作
 * - 统一错误处理
 *
 * @module network/core/AbstractFileSystem
 * @version V1.1.0
 * @since 2026-02-03
 * @author [Genesis.Standardization]
 */

'use strict';

const { filesystemError, safeExecuteSync } = require('./NetworkShieldError');

// ============================================================================
// ABSTRACT FILE SYSTEM INTERFACE
// ============================================================================

/**
 * @interface IFileSystem
 * 文件系统抽象接口
 *
 * @description
 * 所有文件系统操作必须实现此接口。这允许在不同环境（测试、生产）
 * 中使用不同的实现，而无需修改核心业务逻辑。
 */
class IFileSystem {
    /**
     * 读取文件内容
     * @abstract
     * @param {string} filePath - 文件路径
     * @param {Object} [options] - 选项
     * @returns {string} 文件内容
     * @throws {NetworkShieldError}
     */
    readFile(filePath, options = {}) {
        throw new Error('Not implemented');
    }

    /**
     * 写入文件内容（原子操作）
     * @abstract
     * @param {string} filePath - 文件路径
     * @param {string} content - 文件内容
     * @param {Object} [options] - 选项
     * @throws {NetworkShieldError}
     */
    writeFile(filePath, content, options = {}) {
        throw new Error('Not implemented');
    }

    /**
     * 检查文件是否存在
     * @abstract
     * @param {string} filePath - 文件路径
     * @returns {boolean}
     */
    exists(filePath) {
        throw new Error('Not implemented');
    }

    /**
     * 删除文件
     * @abstract
     * @param {string} filePath - 文件路径
     * @throws {NetworkShieldError}
     */
    unlink(filePath) {
        throw new Error('Not implemented');
    }

    /**
     * 复制文件
     * @abstract
     * @param {string} srcPath - 源文件路径
     * @param {string} destPath - 目标文件路径
     * @throws {NetworkShieldError}
     */
    copyFile(srcPath, destPath) {
        throw new Error('Not implemented');
    }

    /**
     * 创建目录（递归）
     * @abstract
     * @param {string} dirPath - 目录路径
     * @throws {NetworkShieldError}
     */
    mkdirRecursive(dirPath) {
        throw new Error('Not implemented');
    }

    /**
     * 获取文件统计信息
     * @abstract
     * @param {string} filePath - 文件路径
     * @returns {{size: number, mtime: Date}}
     */
    stat(filePath) {
        throw new Error('Not implemented');
    }

    /**
     * 原子写入（先写临时文件，再重命名）
     * @abstract
     * @param {string} filePath - 目标文件路径
     * @param {string} content - 文件内容
     * @throws {NetworkShieldError}
     */
    atomicWrite(filePath, content) {
        throw new Error('Not implemented');
    }

    /**
     * 尝试获取文件锁（用于并发控制）
     * @abstract
     * @param {string} lockPath - 锁文件路径
     * @param {number} timeoutMs - 超时时间（毫秒）
     * @returns {Promise<boolean>} 是否成功获取锁
     */
    async acquireLock(lockPath, timeoutMs) {
        throw new Error('Not implemented');
    }

    /**
     * 释放文件锁
     * @abstract
     * @param {string} lockPath - 锁文件路径
     */
    releaseLock(lockPath) {
        throw new Error('Not implemented');
    }
}

// ============================================================================
// NODE FILESYSTEM IMPLEMENTATION
// ============================================================================

const fs = require('fs');
const path = require('path');
const os = require('os');

class NodeFileSystem extends IFileSystem {
    constructor() {
        super();
        this._fs = fs;
    }

    /**
     * @inheritdoc
     */
    readFile(filePath, options = {}) {
        return safeExecuteSync(() => {
            const encoding = options.encoding || 'utf8';
            return this._fs.readFileSync(filePath, encoding);
        }, 'NS_FILESYSTEM_ERROR');
    }

    /**
     * @inheritdoc
     */
    writeFile(filePath, content, options = {}) {
        return safeExecuteSync(() => {
            const encoding = options.encoding || 'utf8';
            this._fs.writeFileSync(filePath, content, encoding);
        }, 'NS_FILESYSTEM_ERROR');
    }

    /**
     * @inheritdoc
     */
    exists(filePath) {
        try {
            return this._fs.existsSync(filePath);
        } catch {
            return false;
        }
    }

    /**
     * @inheritdoc
     */
    unlink(filePath) {
        return safeExecuteSync(() => {
            if (this.exists(filePath)) {
                this._fs.unlinkSync(filePath);
            }
        }, 'NS_FILESYSTEM_ERROR');
    }

    /**
     * @inheritdoc
     */
    copyFile(srcPath, destPath) {
        return safeExecuteSync(() => {
            this._fs.copyFileSync(srcPath, destPath);
        }, 'NS_FILESYSTEM_ERROR');
    }

    /**
     * @inheritdoc
     */
    mkdirRecursive(dirPath) {
        return safeExecuteSync(() => {
            this._fs.mkdirSync(dirPath, { recursive: true });
        }, 'NS_FILESYSTEM_ERROR');
    }

    /**
     * @inheritdoc
     */
    stat(filePath) {
        return safeExecuteSync(() => {
            const stats = this._fs.statSync(filePath);
            return {
                size: stats.size,
                mtime: stats.mtime,
                mode: stats.mode,
                isFile: stats.isFile(),
                isDirectory: stats.isDirectory()
            };
        }, 'NS_FILESYSTEM_ERROR');
    }

    /**
     * @inheritdoc
     */
    atomicWrite(filePath, content) {
        return safeExecuteSync(() => {
            // 创建临时文件
            const tempPath = `${filePath}.${process.pid}.${Date.now()}.tmp`;

            try {
                // 写入临时文件
                this._fs.writeFileSync(tempPath, content, 'utf8');

                // 原子重命名（在 POSIX 和 Windows 上都是原子的）
                this._fs.renameSync(tempPath, filePath);
            } catch (error) {
                // 清理临时文件
                if (this.exists(tempPath)) {
                    try {
                        this._fs.unlinkSync(tempPath);
                    } catch {
                        // 忽略清理错误
                    }
                }
                throw error;
            }
        }, 'NS_FILESYSTEM_ERROR');
    }

    /**
     * @inheritdoc
     */
    async acquireLock(lockPath, timeoutMs = 5000) {
        const startTime = Date.now();
        const pollInterval = 50;

        while (Date.now() - startTime < timeoutMs) {
            try {
                // 使用 O_CREAT | O_EXCL | O_WRONLY 标志创建锁文件
                const fd = this._fs.openSync(lockPath, 'wx');
                this._fs.writeSync(fd, process.pid.toString());
                this._fs.closeSync(fd);
                return true;
            } catch (error) {
                if (error.code === 'EEXIST') {
                    // 锁文件已存在，等待后重试
                    await new Promise(resolve => { setTimeout(resolve, pollInterval); });
                } else {
                    // 其他错误，抛出
                    throw filesystemError('acquireLock', lockPath, error);
                }
            }
        }

        return false;
    }

    /**
     * @inheritdoc
     */
    releaseLock(lockPath) {
        return safeExecuteSync(() => {
            if (this.exists(lockPath)) {
                this._fs.unlinkSync(lockPath);
            }
        }, 'NS_FILESYSTEM_ERROR');
    }
}

// ============================================================================
// MEMORY FILESYSTEM (FOR TESTING)
// ============================================================================

class MemoryFileSystem extends IFileSystem {
    constructor() {
        super();
        /** @type {Map<string, {content: string, mtime: Date}>} */
        this._files = new Map();
        /** @type {Set<string>} */
        this._locks = new Set();
    }

    /**
     * @inheritdoc
     */
    readFile(filePath, options = {}) {
        const encoding = options.encoding || 'utf8';
        const normalizedPath = this._normalizePath(filePath);

        if (!this._files.has(normalizedPath)) {
            throw filesystemError('readFile', filePath, new Error('File not found'));
        }

        return this._files.get(normalizedPath).content;
    }

    /**
     * @inheritdoc
     */
    writeFile(filePath, content, options = {}) {
        const normalizedPath = this._normalizePath(filePath);
        this._files.set(normalizedPath, {
            content,
            mtime: new Date()
        });
    }

    /**
     * @inheritdoc
     */
    exists(filePath) {
        return this._files.has(this._normalizePath(filePath));
    }

    /**
     * @inheritdoc
     */
    unlink(filePath) {
        this._files.delete(this._normalizePath(filePath));
    }

    /**
     * @inheritdoc
     */
    copyFile(srcPath, destPath) {
        const srcNormalized = this._normalizePath(srcPath);
        const destNormalized = this._normalizePath(destPath);

        if (!this._files.has(srcNormalized)) {
            throw filesystemError('copyFile', srcPath, new Error('Source file not found'));
        }

        this._files.set(destNormalized, { ...this._files.get(srcNormalized) });
    }

    /**
     * @inheritdoc
     */
    mkdirRecursive(dirPath) {
        // 内存文件系统不需要创建目录
    }

    /**
     * @inheritdoc
     */
    stat(filePath) {
        const normalizedPath = this._normalizePath(filePath);

        if (!this._files.has(normalizedPath)) {
            throw filesystemError('stat', filePath, new Error('File not found'));
        }

        const file = this._files.get(normalizedPath);
        return {
            size: file.content.length,
            mtime: file.mtime,
            isFile: true,
            isDirectory: false
        };
    }

    /**
     * @inheritdoc
     */
    atomicWrite(filePath, content) {
        this.writeFile(filePath, content);
    }

    /**
     * @inheritdoc
     */
    async acquireLock(lockPath, timeoutMs = 5000) {
        const normalizedPath = this._normalizePath(lockPath);
        const startTime = Date.now();
        const pollInterval = 10;

        while (Date.now() - startTime < timeoutMs) {
            if (!this._locks.has(normalizedPath)) {
                this._locks.add(normalizedPath);
                return true;
            }
            await new Promise(resolve => { setTimeout(resolve, pollInterval); });
        }

        return false;
    }

    /**
     * @inheritdoc
     */
    releaseLock(lockPath) {
        this._locks.delete(this._normalizePath(lockPath));
    }

    /**
     * 规范化路径
     * @private
     * @param {string} filePath - 文件路径
     * @returns {string}
     */
    _normalizePath(filePath) {
        return path.normalize(filePath);
    }

    /**
     * 清空所有文件（用于测试）
     */
    clear() {
        this._files.clear();
        this._locks.clear();
    }

    /**
     * 获取所有文件路径
     * @returns {string[]}
     */
    getFiles() {
        return Array.from(this._files.keys());
    }
}

// ============================================================================
// FILE SYSTEM PROVIDER
// ============================================================================

/**
 * 文件系统提供者 - 根据环境选择合适的实现
 */
class FileSystemProvider {
    /**
     * 获取默认文件系统实现
     * @param {Object} [options] - 选项
     * @param {boolean} [options.memory] - 是否使用内存文件系统
     * @returns {IFileSystem}
     */
    static getFileSystem(options = {}) {
        if (options.memory || process.env.NODE_ENV === 'test') {
            return new MemoryFileSystem();
        }
        return new NodeFileSystem();
    }

    /**
     * 创建文件系统实例
     * @param {string} type - 文件系统类型 ('node' | 'memory')
     * @returns {IFileSystem}
     */
    static create(type) {
        switch (type) {
            case 'memory':
                return new MemoryFileSystem();
            case 'node':
            default:
                return new NodeFileSystem();
        }
    }
}

module.exports = {
    IFileSystem,
    NodeFileSystem,
    MemoryFileSystem,
    FileSystemProvider
};
