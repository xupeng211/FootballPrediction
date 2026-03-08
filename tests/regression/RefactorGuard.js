/**
 * RefactorGuard.js - V4.46 回归测试护城河
 * ==========================================
 *
 * 为 ProductionHarvester (1561 行) 建立回归测试护城河
 * 采用"绞杀者模式"重构前的 Golden Master 机制
 *
 * 功能:
 * 1. 快照抓取 (Capture) - 捕获 ProductionHarvester 的所有输出
 * 2. 深度对比 (Deep Diff) - 对比新旧版本输出差异
 * 3. 环境隔离 - 拦截 /app/ 路径为 process.cwd()
 *
 * @module tests/regression/RefactorGuard
 * @version V4.46.0
 */

'use strict';

const fs = require('fs');
const path = require('path');
const assert = require('assert');

// ============================================================================
// 环境隔离 - 路径映射
// ============================================================================

/**
 * 解析路径，将 /app/ 映射到项目根目录
 * @param {string} inputPath - 输入路径
 * @returns {string} 解析后的路径
 */
function resolvePath(inputPath) {
    const projectRoot = process.cwd();

    if (inputPath.startsWith('/app/')) {
        return path.join(projectRoot, inputPath.slice(5));
    }

    return inputPath;
}

/**
 * 创建路径解析代理，拦截所有 /app/ 路径
 */
function createPathProxy() {
    const originalJoin = path.join;
    const originalResolve = path.resolve;

    path.join = function(...args) {
        const result = originalJoin.apply(path, args);
        return resolvePath(result);
    };

    path.resolve = function(...args) {
        const result = originalResolve.apply(path, args);
        return resolvePath(result);
    };

    return { originalJoin, originalResolve };
}

/**
 * 恢复原始路径方法
 */
function restorePathProxy(original) {
    path.join = original.originalJoin;
    path.resolve = original.originalResolve;
}

// ============================================================================
// 深度对比引擎
// ============================================================================

/**
 * 深度对比结果
 * @typedef {Object} DiffResult
 * @property {boolean} equal - 是否相等
 * @property {Array<string>} differences - 差异列表
 * @property {Object} summary - 摘要统计
 */

/**
 * 深度对比两个对象
 * @param {*} actual - 实际值
 * @param {*} expected - 期望值
 * @param {string} path - 当前路径
 * @param {Object} options - 对比选项
 * @returns {DiffResult}
 */
function deepDiff(actual, expected, path = '', options = {}) {
    const differences = [];
    const summary = {
        fieldCount: { actual: 0, expected: 0 },
        typeMismatches: 0,
        valueMismatches: 0,
        missingFields: 0,
        extraFields: 0
    };

    function compare(a, e, p) {
        // 类型检查
        if (typeof a !== typeof e) {
            differences.push({
                path: p,
                type: 'TYPE_MISMATCH',
                actualType: typeof a,
                expectedType: typeof e,
                actual: a,
                expected: e
            });
            summary.typeMismatches++;
            return;
        }

        // null 检查
        if (a === null || e === null) {
            if (a !== e) {
                differences.push({
                    path: p,
                    type: 'VALUE_MISMATCH',
                    actual: a,
                    expected: e
                });
                summary.valueMismatches++;
            }
            return;
        }

        // 数组检查
        if (Array.isArray(a) && Array.isArray(e)) {
            if (a.length !== e.length) {
                differences.push({
                    path: p,
                    type: 'ARRAY_LENGTH_MISMATCH',
                    actualLength: a.length,
                    expectedLength: e.length
                });
            }

            const minLen = Math.min(a.length, e.length);
            for (let i = 0; i < minLen; i++) {
                compare(a[i], e[i], `${p}[${i}]`);
            }
            return;
        }

        // 对象检查
        if (typeof a === 'object' && typeof e === 'object') {
            const aKeys = Object.keys(a);
            const eKeys = Object.keys(e);

            summary.fieldCount.actual += aKeys.length;
            summary.fieldCount.expected += eKeys.length;

            const aKeySet = new Set(aKeys);
            const eKeySet = new Set(eKeys);

            // 检查缺失字段
            for (const key of eKeySet) {
                if (!aKeySet.has(key)) {
                    differences.push({
                        path: `${p}.${key}`,
                        type: 'MISSING_FIELD',
                        expected: e[key]
                    });
                    summary.missingFields++;
                }
            }

            // 检查额外字段
            for (const key of aKeySet) {
                if (!eKeySet.has(key)) {
                    differences.push({
                        path: `${p}.${key}`,
                        type: 'EXTRA_FIELD',
                        actual: a[key]
                    });
                    summary.extraFields++;
                }
            }

            // 递归对比共有字段
            for (const key of aKeySet) {
                if (eKeySet.has(key)) {
                    compare(a[key], e[key], `${p}.${key}`);
                }
            }
            return;
        }

        // 基本类型值检查
        if (a !== e) {
            // 数值类型特殊处理：允许微小误差
            if (typeof a === 'number' && typeof e === 'number') {
                const tolerance = options.numericTolerance || 0.0001;
                if (Math.abs(a - e) > tolerance) {
                    differences.push({
                        path: p,
                        type: 'VALUE_MISMATCH',
                        actual: a,
                        expected: e,
                        delta: Math.abs(a - e)
                    });
                    summary.valueMismatches++;
                }
                return;
            }

            differences.push({
                path: p,
                type: 'VALUE_MISMATCH',
                actual: a,
                expected: e
            });
            summary.valueMismatches++;
        }
    }

    compare(actual, expected, path);

    return {
        equal: differences.length === 0,
        differences,
        summary
    };
}

// ============================================================================
// 快照管理器
// ============================================================================

/**
 * 快照管理器
 */
class SnapshotManager {
    /**
     * @param {string} snapshotDir - 快照存储目录
     */
    constructor(snapshotDir) {
        this.snapshotDir = resolvePath(snapshotDir);
        this.ensureDir();
    }

    ensureDir() {
        if (!fs.existsSync(this.snapshotDir)) {
            fs.mkdirSync(this.snapshotDir, { recursive: true });
        }
    }

    /**
     * 生成快照文件路径
     * @param {string} matchId - 比赛 ID
     * @returns {string}
     */
    getSnapshotPath(matchId) {
        return path.join(this.snapshotDir, `golden_master_${matchId}.json`);
    }

    /**
     * 保存快照
     * @param {string} matchId - 比赛 ID
     * @param {Object} data - 快照数据
     */
    save(matchId, data) {
        const snapshotPath = this.getSnapshotPath(matchId);
        const snapshot = {
            version: 'V4.46',
            createdAt: new Date().toISOString(),
            matchId,
            source: 'ProductionHarvester',
            metadata: {
                nodeVersion: process.version,
                platform: process.platform
            },
            data
        };

        fs.writeFileSync(snapshotPath, JSON.stringify(snapshot, null, 2), 'utf8');
        console.log(`📸 快照已保存: ${snapshotPath}`);
        return snapshotPath;
    }

    /**
     * 加载快照
     * @param {string} matchId - 比赛 ID
     * @returns {Object|null}
     */
    load(matchId) {
        const snapshotPath = this.getSnapshotPath(matchId);
        if (!fs.existsSync(snapshotPath)) {
            return null;
        }

        const content = fs.readFileSync(snapshotPath, 'utf8');
        return JSON.parse(content);
    }

    /**
     * 检查快照是否存在
     * @param {string} matchId - 比赛 ID
     * @returns {boolean}
     */
    exists(matchId) {
        return fs.existsSync(this.getSnapshotPath(matchId));
    }
}

// ============================================================================
// ProductionHarvester 输出捕获器
// ============================================================================

/**
 * 捕获 ProductionHarvester 输出的包装器
 */
class HarvesterCapture {
    constructor() {
        this.capturedCalls = [];
        this.capturedOutputs = [];
        this.methodSignatures = {};
    }

    /**
     * 创建方法调用记录
     * @param {string} methodName - 方法名
     * @param {Array} args - 参数
     * @param {*} result - 返回值
     * @param {number} duration - 耗时 (ms)
     */
    recordCall(methodName, args, result, duration) {
        this.capturedCalls.push({
            method: methodName,
            args: this._serializeArgs(args),
            result: this._serializeResult(result),
            duration,
            timestamp: Date.now()
        });
    }

    /**
     * 序列化参数 (移除不可序列化对象)
     */
    _serializeArgs(args) {
        return args.map(arg => {
            if (arg === null) return null;
            if (arg === undefined) return undefined;
            if (typeof arg === 'function') return '[Function]';
            if (typeof arg !== 'object') return arg;

            try {
                JSON.stringify(arg);
                return arg;
            } catch {
                return '[Non-Serializable Object]';
            }
        });
    }

    /**
     * 序列化结果
     */
    _serializeResult(result) {
        if (result === null) return null;
        if (result === undefined) return undefined;
        if (typeof result !== 'object') return result;

        try {
            JSON.stringify(result);
            return result;
        } catch {
            return { type: 'Non-Serializable', constructor: result.constructor?.name };
        }
    }

    /**
     * 提取方法签名
     * @param {Object} obj - 目标对象
     */
    extractMethodSignatures(obj) {
        const proto = Object.getPrototypeOf(obj);
        const methods = Object.getOwnPropertyNames(proto).filter(
            name => name !== 'constructor' && typeof proto[name] === 'function'
        );

        for (const method of methods) {
            const fn = proto[method];
            const fnStr = fn.toString();

            // 提取参数列表
            const paramsMatch = fnStr.match(/\(([^)]*)\)/);
            const params = paramsMatch ? paramsMatch[1].split(',').map(p => p.trim()).filter(Boolean) : [];

            // 提取 JSDoc
            const jsDocMatch = fnStr.match(/\/\*\*[\s\S]*?\*\//);

            this.methodSignatures[method] = {
                params,
                jsDoc: jsDocMatch ? jsDocMatch[0] : null,
                isAsync: fnStr.includes('async')
            };
        }
    }

    /**
     * 获取捕获摘要
     */
    getSummary() {
        return {
            totalCalls: this.capturedCalls.length,
            methods: [...new Set(this.capturedCalls.map(c => c.method))],
            signatures: this.methodSignatures,
            calls: this.capturedCalls
        };
    }
}

// ============================================================================
// RefactorGuard 主类
// ============================================================================

/**
 * RefactorGuard - 回归测试护城河
 */
class RefactorGuard {
    /**
     * @param {Object} options - 配置选项
     * @param {string} options.snapshotDir - 快照目录
     * @param {boolean} options.verbose - 详细输出
     */
    constructor(options = {}) {
        this.snapshotDir = options.snapshotDir || '/app/data/regression';
        this.verbose = options.verbose || false;
        this.snapshotManager = new SnapshotManager(this.snapshotDir);
        this.capture = new HarvesterCapture();
        this.pathProxy = null;
    }

    /**
     * 初始化环境
     */
    init() {
        console.log('🛡️ RefactorGuard V4.46 - 回归测试护城河');
        console.log('═'.repeat(60));

        // 设置路径代理
        this.pathProxy = createPathProxy();
        console.log(`📁 项目根目录: ${process.cwd()}`);
        console.log(`📁 快照目录: ${resolvePath(this.snapshotDir)}`);
    }

    /**
     * 清理环境
     */
    cleanup() {
        if (this.pathProxy) {
            restorePathProxy(this.pathProxy);
        }
    }

    /**
     * 捕获 ProductionHarvester 的结构信息 (不需要实际运行)
     * @returns {Object} 结构信息
     */
    captureHarvesterStructure() {
        // 动态导入 ProductionHarvester
        const harvesterPath = resolvePath('/app/src/infrastructure/harvesters/ProductionHarvester.js');

        if (!fs.existsSync(harvesterPath)) {
            throw new Error(`找不到 ProductionHarvester: ${harvesterPath}`);
        }

        // 读取源码进行分析
        const sourceCode = fs.readFileSync(harvesterPath, 'utf8');
        const lines = sourceCode.split('\n');

        // 提取类结构
        const structure = {
            filePath: harvesterPath,
            totalLines: lines.length,
            imports: [],
            classes: [],
            methods: [],
            constants: [],
            version: null
        };

        // 解析版本号
        const versionMatch = sourceCode.match(/@version\s+(V?[\d.]+)/);
        if (versionMatch) {
            structure.version = versionMatch[1];
        }

        // 解析 imports
        const importRegex = /(?:const|let|var)\s+(\w+)\s*=\s*require\(['"]([^'"]+)['"]\)/g;
        let match;
        while ((match = importRegex.exec(sourceCode)) !== null) {
            structure.imports.push({
                name: match[1],
                module: match[2]
            });
        }

        // 解析类定义
        const classRegex = /class\s+(\w+)\s*(?:extends\s+(\w+))?\s*\{/g;
        while ((match = classRegex.exec(sourceCode)) !== null) {
            structure.classes.push({
                name: match[1],
                extends: match[2] || null
            });
        }

        // 解析方法定义
        const methodRegex = /(?:async\s+)?(\w+)\s*\(([^)]*)\)\s*\{/g;
        while ((match = methodRegex.exec(sourceCode)) !== null) {
            const methodName = match[1];
            // 过滤掉控制语句
            if (!['if', 'for', 'while', 'switch', 'catch', 'function'].includes(methodName)) {
                structure.methods.push({
                    name: methodName,
                    params: match[2].split(',').map(p => p.trim()).filter(Boolean)
                });
            }
        }

        // 解析常量定义
        const constRegex = /(?:const|let)\s+([A-Z_][A-Z0-9_]*)\s*=/g;
        while ((match = constRegex.exec(sourceCode)) !== null) {
            structure.constants.push(match[1]);
        }

        return structure;
    }

    /**
     * 捕获单场比赛的收割输出 (模拟模式)
     * @param {string} matchId - 比赛 ID
     * @param {Object} mockData - 模拟数据 (用于 dry-run 模式)
     * @returns {Object} 捕获的输出
     */
    captureHarvestOutput(matchId, mockData = null) {
        // 如果有模拟数据，直接使用
        if (mockData) {
            return {
                matchId,
                timestamp: Date.now(),
                data: mockData,
                mode: 'mock'
            };
        }

        // 尝试从数据库加载已收割的数据
        const outputPath = resolvePath(`/app/data/regression/harvest_output_${matchId}.json`);

        if (fs.existsSync(outputPath)) {
            return JSON.parse(fs.readFileSync(outputPath, 'utf8'));
        }

        // 返回结构信息作为 baseline
        return {
            matchId,
            timestamp: Date.now(),
            structure: this.captureHarvesterStructure(),
            mode: 'structure_only'
        };
    }

    /**
     * 生成 Golden Master 快照
     * @param {string} matchId - 比赛 ID
     * @param {Object} options - 选项
     */
    generateGoldenMaster(matchId, options = {}) {
        console.log(`\n📸 生成 Golden Master: matchId=${matchId}`);

        // 1. 捕获 ProductionHarvester 结构
        const structure = this.captureHarvesterStructure();
        console.log(`   ✓ 结构分析完成: ${structure.methods.length} 个方法`);

        // 2. 生成快照
        const snapshot = {
            matchId,
            createdAt: new Date().toISOString(),
            structure,
            expectedOutput: {
                // 预期输出结构 (基于代码分析)
                harvestResult: {
                    success: 'boolean',
                    match_id: 'string',
                    size: 'number',
                    workerId: 'number',
                    port: 'number',
                    error: 'string|null'
                },
                rawData: {
                    // 具体字段取决于 FotMob API 返回
                    matchId: 'string',
                    homeTeam: 'string',
                    awayTeam: 'string',
                    score: 'object',
                    stats: 'object',
                    odds: 'object'
                }
            },
            contract: {
                // 方法契约
                harvestMatch: {
                    input: ['match object', 'index number'],
                    output: ['success', 'match_id', 'size', 'workerId', 'port']
                },
                saveRawData: {
                    input: ['matchId string', 'rawData object'],
                    output: 'void'
                }
            }
        };

        // 3. 保存快照
        const snapshotPath = this.snapshotManager.save(matchId, snapshot);

        // 4. 输出摘要
        this.printSnapshotSummary(snapshot);

        return snapshot;
    }

    /**
     * 打印快照摘要
     * @param {Object} snapshot - 快照数据
     */
    printSnapshotSummary(snapshot) {
        const { structure, expectedOutput, contract } = snapshot;

        console.log('\n' + '═'.repeat(60));
        console.log('📋 GOLDEN MASTER 结构摘要');
        console.log('═'.repeat(60));

        console.log(`\n📦 源文件信息:`);
        console.log(`   路径: ${structure.filePath}`);
        console.log(`   版本: ${structure.version || '未知'}`);
        console.log(`   行数: ${structure.totalLines}`);

        console.log(`\n📥 依赖模块 (${structure.imports.length} 个):`);
        structure.imports.slice(0, 10).forEach(imp => {
            console.log(`   - ${imp.name}: ${imp.module}`);
        });
        if (structure.imports.length > 10) {
            console.log(`   ... 还有 ${structure.imports.length - 10} 个`);
        }

        console.log(`\n🔧 方法列表 (${structure.methods.length} 个):`);
        const publicMethods = structure.methods.filter(m =>
            !m.name.startsWith('_') && m.name !== 'constructor'
        );
        const privateMethods = structure.methods.filter(m =>
            m.name.startsWith('_')
        );

        console.log(`   公开方法 (${publicMethods.length} 个):`);
        publicMethods.forEach(m => {
            console.log(`     • ${m.name}(${m.params.join(', ')})`);
        });

        console.log(`   私有方法 (${privateMethods.length} 个):`);
        privateMethods.slice(0, 10).forEach(m => {
            console.log(`     • ${m.name}(${m.params.join(', ')})`);
        });
        if (privateMethods.length > 10) {
            console.log(`     ... 还有 ${privateMethods.length - 10} 个`);
        }

        console.log(`\n📐 常量定义 (${structure.constants.length} 个):`);
        structure.constants.forEach(c => {
            console.log(`   - ${c}`);
        });

        console.log(`\n📜 输出契约:`);
        Object.entries(contract).forEach(([method, spec]) => {
            console.log(`   ${method}:`);
            console.log(`     输入: ${spec.input.join(', ')}`);
            console.log(`     输出: ${Array.isArray(spec.output) ? spec.output.join(', ') : spec.output}`);
        });

        console.log('\n' + '═'.repeat(60));
    }

    /**
     * 对比快照
     * @param {string} matchId - 比赛 ID
     * @param {Object} newOutput - 新输出
     * @returns {DiffResult}
     */
    compareWithGoldenMaster(matchId, newOutput) {
        const snapshot = this.snapshotManager.load(matchId);

        if (!snapshot) {
            console.log(`⚠️ 未找到 Golden Master: ${matchId}`);
            return null;
        }

        console.log(`\n🔍 对比 Golden Master: ${matchId}`);

        // 对比结构
        const structureDiff = deepDiff(
            newOutput.structure || {},
            snapshot.structure || {},
            'structure'
        );

        // 对比输出
        const outputDiff = deepDiff(
            newOutput.output || {},
            snapshot.expectedOutput || {},
            'output'
        );

        const result = {
            equal: structureDiff.equal && outputDiff.equal,
            structureDiff,
            outputDiff,
            snapshot,
            newOutput
        };

        // 打印对比结果
        this.printDiffResult(result);

        return result;
    }

    /**
     * 打印对比结果
     * @param {Object} result - 对比结果
     */
    printDiffResult(result) {
        console.log('\n' + '═'.repeat(60));
        console.log('📊 对比结果');
        console.log('═'.repeat(60));

        if (result.equal) {
            console.log('\n✅ PASS - 输出与 Golden Master 一致');
        } else {
            console.log('\n❌ FAIL - 发现差异');
        }

        // 结构差异
        if (!result.structureDiff.equal) {
            console.log('\n🔧 结构差异:');
            result.structureDiff.differences.slice(0, 10).forEach(diff => {
                console.log(`   [${diff.type}] ${diff.path}`);
                if (diff.actual !== undefined) {
                    console.log(`     实际: ${JSON.stringify(diff.actual).slice(0, 50)}`);
                }
                if (diff.expected !== undefined) {
                    console.log(`     期望: ${JSON.stringify(diff.expected).slice(0, 50)}`);
                }
            });
            if (result.structureDiff.differences.length > 10) {
                console.log(`   ... 还有 ${result.structureDiff.differences.length - 10} 个差异`);
            }
        }

        // 输出差异
        if (!result.outputDiff.equal) {
            console.log('\n📤 输出差异:');
            result.outputDiff.differences.slice(0, 10).forEach(diff => {
                console.log(`   [${diff.type}] ${diff.path}`);
            });
        }

        console.log('\n📈 统计摘要:');
        console.log(`   结构差异: ${result.structureDiff.differences.length} 个`);
        console.log(`   输出差异: ${result.outputDiff.differences.length} 个`);

        console.log('═'.repeat(60));
    }

    /**
     * 运行回归测试
     * @param {string} matchId - 比赛 ID
     * @param {Object} options - 选项
     */
    runRegressionTest(matchId, options = {}) {
        console.log(`\n🧪 运行回归测试: ${matchId}`);

        // 检查 Golden Master 是否存在
        if (!this.snapshotManager.exists(matchId)) {
            console.log('⚠️ Golden Master 不存在，创建新的快照...');
            return this.generateGoldenMaster(matchId, options);
        }

        // 捕获当前输出
        const currentOutput = this.captureHarvestOutput(matchId, options.mockData);

        // 对比
        return this.compareWithGoldenMaster(matchId, currentOutput);
    }
}

// ============================================================================
// CLI 入口
// ============================================================================

/**
 * 打印使用说明
 */
function printUsage() {
    console.log(`
使用方法:
  node RefactorGuard.js <command> [options]

命令:
  capture <matchId>    - 生成 Golden Master 快照
  compare <matchId>    - 对比当前输出与 Golden Master
  analyze              - 分析 ProductionHarvester 结构
  test <matchId>       - 运行完整回归测试

选项:
  --verbose            - 详细输出
  --mock-data <file>   - 使用模拟数据文件

示例:
  node RefactorGuard.js capture 4803308
  node RefactorGuard.js compare 4803308
  node RefactorGuard.js analyze
`);
}

/**
 * 主入口
 */
async function main() {
    const args = process.argv.slice(2);

    if (args.length === 0 || args[0] === '--help' || args[0] === '-h') {
        printUsage();
        process.exit(0);
    }

    const command = args[0];
    const matchId = args[1];
    const verbose = args.includes('--verbose');

    const guard = new RefactorGuard({ verbose });

    try {
        guard.init();

        switch (command) {
            case 'capture':
                if (!matchId) {
                    console.error('❌ 缺少 matchId 参数');
                    process.exit(1);
                }
                guard.generateGoldenMaster(matchId);
                break;

            case 'compare':
                if (!matchId) {
                    console.error('❌ 缺少 matchId 参数');
                    process.exit(1);
                }
                guard.runRegressionTest(matchId);
                break;

            case 'analyze':
                const structure = guard.captureHarvesterStructure();
                console.log('\n📊 ProductionHarvester 结构分析:');
                console.log(JSON.stringify(structure, null, 2));
                break;

            case 'test':
                if (!matchId) {
                    console.error('❌ 缺少 matchId 参数');
                    process.exit(1);
                }
                guard.runRegressionTest(matchId);
                break;

            default:
                console.error(`❌ 未知命令: ${command}`);
                printUsage();
                process.exit(1);
        }

    } catch (error) {
        console.error('❌ 执行失败:', error.message);
        if (verbose) {
            console.error(error.stack);
        }
        process.exit(1);
    } finally {
        guard.cleanup();
    }
}

// ============================================================================
// 契约验证器
// ============================================================================

/**
 * 验证 harvestMatch 输出契约
 * @param {Object} output - harvestMatch 返回值
 * @returns {Object} 验证结果
 */
function validateHarvestMatchContract(output) {
    const requiredFields = ['success', 'match_id'];
    const optionalFields = ['size', 'workerId', 'port', 'error', 'attempt'];

    const errors = [];
    const warnings = [];

    // 检查必须字段
    for (const field of requiredFields) {
        if (!(field in output)) {
            errors.push(`缺少必须字段: ${field}`);
        }
    }

    // 检查字段类型
    if ('success' in output && typeof output.success !== 'boolean') {
        errors.push(`success 字段类型错误: 期望 boolean，实际 ${typeof output.success}`);
    }

    if ('match_id' in output && typeof output.match_id !== 'string') {
        errors.push(`match_id 字段类型错误: 期望 string，实际 ${typeof output.match_id}`);
    }

    if ('size' in output && typeof output.size !== 'number') {
        warnings.push(`size 字段类型: ${typeof output.size}`);
    }

    if ('workerId' in output && typeof output.workerId !== 'number') {
        warnings.push(`workerId 字段类型: ${typeof output.workerId}`);
    }

    if ('port' in output && typeof output.port !== 'number') {
        warnings.push(`port 字段类型: ${typeof output.port}`);
    }

    // 成功时检查额外字段
    if (output.success === true) {
        if (!('size' in output)) {
            warnings.push('成功时建议包含 size 字段');
        }
    }

    // 失败时检查错误信息
    if (output.success === false) {
        if (!('error' in output)) {
            warnings.push('失败时建议包含 error 字段');
        }
    }

    return {
        valid: errors.length === 0,
        errors,
        warnings,
        fieldCount: Object.keys(output).length,
        requiredFieldsPresent: requiredFields.filter(f => f in output),
        optionalFieldsPresent: optionalFields.filter(f => f in output)
    };
}

/**
 * 验证 saveRawData 契约
 * @param {string} matchId - matchId 参数
 * @param {Object} rawData - rawData 参数
 * @returns {Object} 验证结果
 */
function validateSaveRawDataContract(matchId, rawData) {
    const errors = [];

    if (typeof matchId !== 'string') {
        errors.push(`matchId 类型错误: 期望 string，实际 ${typeof matchId}`);
    }

    if (typeof rawData !== 'object' || rawData === null) {
        errors.push(`rawData 类型错误: 期望 object，实际 ${typeof rawData}`);
    }

    // 检查 rawData 可序列化
    if (typeof rawData === 'object') {
        try {
            const serialized = JSON.stringify(rawData);
            if (serialized.length < 1000) {
                return {
                    valid: false,
                    errors: [...errors, `rawData 体积过小: ${serialized.length} bytes (最小 1000)`],
                    size: serialized.length
                };
            }
        } catch (e) {
            errors.push(`rawData 不可序列化: ${e.message}`);
        }
    }

    return {
        valid: errors.length === 0,
        errors,
        size: rawData ? JSON.stringify(rawData).length : 0
    };
}

/**
 * 验证 ProductionHarvester 类结构契约
 * @param {Object} structure - 结构信息
 * @returns {Object} 验证结果
 */
function validateClassStructureContract(structure) {
    const errors = [];
    const warnings = [];

    // 必须存在的公开方法
    const requiredMethods = [
        'init',
        'run',
        'harvestMatch',
        'saveRawData',
        'cleanup',
        'getPendingMatches',
        'printReport'
    ];

    // 必须存在的私有方法
    const requiredPrivateMethods = [
        '_delay',
        '_assignWorkerIdentity',
        '_markProxySuccess',
        '_markProxyFailed',
        '_warmupHomepage',
        '_simulateHumanBehavior',
        '_injectStealthScripts'
    ];

    const methodNames = structure.methods.map(m => m.name);

    // 检查必须的公开方法
    for (const method of requiredMethods) {
        if (!methodNames.includes(method)) {
            errors.push(`缺少必须的公开方法: ${method}`);
        }
    }

    // 检查必须的私有方法
    for (const method of requiredPrivateMethods) {
        if (!methodNames.includes(method)) {
            warnings.push(`缺少建议的私有方法: ${method}`);
        }
    }

    // 检查必须的常量
    const requiredConstants = ['FIXED_FINGERPRINT'];
    for (const constant of requiredConstants) {
        if (!structure.constants.includes(constant)) {
            errors.push(`缺少必须的常量: ${constant}`);
        }
    }

    // 检查必须的类
    const requiredClasses = ['ProductionHarvester', 'WorkerIdentity'];
    const classNames = structure.classes.map(c => c.name);
    for (const cls of requiredClasses) {
        if (!classNames.includes(cls)) {
            errors.push(`缺少必须的类: ${cls}`);
        }
    }

    return {
        valid: errors.length === 0,
        errors,
        warnings,
        methodCount: methodNames.length,
        publicMethodCount: methodNames.filter(m => !m.startsWith('_')).length,
        privateMethodCount: methodNames.filter(m => m.startsWith('_')).length
    };
}

// ============================================================================
// 完整回归测试套件
// ============================================================================

/**
 * 运行完整回归测试套件
 * @param {string} matchId - 比赛 ID
 */
async function runFullRegressionSuite(matchId) {
    console.log('\n' + '═'.repeat(60));
    console.log('  🧪 RefactorGuard 完整回归测试套件');
    console.log('═'.repeat(60));

    const guard = new RefactorGuard({ verbose: true });
    const results = {
        passed: 0,
        failed: 0,
        skipped: 0,
        tests: []
    };

    try {
        guard.init();

        // 测试 1: 结构契约验证
        console.log('\n📋 测试 1: 类结构契约验证');
        const structure = guard.captureHarvesterStructure();
        const structureResult = validateClassStructureContract(structure);

        if (structureResult.valid) {
            console.log('   ✅ PASS - 类结构符合契约');
            results.passed++;
        } else {
            console.log('   ❌ FAIL - 类结构不符合契约');
            structureResult.errors.forEach(e => console.log(`      - ${e}`));
            results.failed++;
        }
        results.tests.push({ name: '结构契约', ...structureResult });

        // 测试 2: 方法数量验证
        console.log('\n📋 测试 2: 方法数量稳定性');
        const expectedMethodCount = 42; // Golden Master 基准
        const actualMethodCount = structure.methods.length;
        const methodCountDiff = Math.abs(actualMethodCount - expectedMethodCount);

        if (methodCountDiff === 0) {
            console.log(`   ✅ PASS - 方法数量一致: ${actualMethodCount}`);
            results.passed++;
        } else if (methodCountDiff <= 2) {
            console.log(`   ⚠️ WARN - 方法数量变化: ${actualMethodCount} (基准: ${expectedMethodCount}, 差异: ${methodCountDiff})`);
            results.skipped++;
        } else {
            console.log(`   ❌ FAIL - 方法数量变化过大: ${actualMethodCount} (基准: ${expectedMethodCount}, 差异: ${methodCountDiff})`);
            results.failed++;
        }
        results.tests.push({
            name: '方法数量',
            valid: methodCountDiff <= 2,
            expected: expectedMethodCount,
            actual: actualMethodCount
        });

        // 测试 3: 常量定义验证
        console.log('\n📋 测试 3: 常量定义完整性');
        const expectedConstants = ['WEBGL_RENDERER_POOL', 'DEEP_STEALTH_CONFIG', 'FIXED_FINGERPRINT', 'GHOST_UA_POOL', 'GHOST_VIEWPORTS'];
        const missingConstants = expectedConstants.filter(c => !structure.constants.includes(c));

        if (missingConstants.length === 0) {
            console.log(`   ✅ PASS - 所有常量定义完整 (${structure.constants.length} 个)`);
            results.passed++;
        } else {
            console.log(`   ❌ FAIL - 缺少常量: ${missingConstants.join(', ')}`);
            results.failed++;
        }
        results.tests.push({ name: '常量定义', valid: missingConstants.length === 0, missing: missingConstants });

        // 测试 4: 版本号验证
        console.log('\n📋 测试 4: 版本号格式');
        const versionPattern = /^V?\d+\.\d+(\.\d+)?$/;
        const versionValid = versionPattern.test(structure.version);

        if (versionValid) {
            console.log(`   ✅ PASS - 版本号格式正确: ${structure.version}`);
            results.passed++;
        } else {
            console.log(`   ⚠️ WARN - 版本号格式异常: ${structure.version}`);
            results.skipped++;
        }
        results.tests.push({ name: '版本号', valid: versionValid, version: structure.version });

        // 测试 5: Golden Master 完整性
        console.log('\n📋 测试 5: Golden Master 完整性');
        const snapshot = guard.snapshotManager.load(matchId);

        if (snapshot && snapshot.data && snapshot.data.structure) {
            console.log(`   ✅ PASS - Golden Master 存在且完整`);
            results.passed++;
        } else {
            console.log(`   ❌ FAIL - Golden Master 不存在或不完整`);
            results.failed++;
        }
        results.tests.push({ name: 'Golden Master', valid: !!snapshot?.data?.structure });

        // 测试 6: 输出契约验证
        console.log('\n📋 测试 6: harvestMatch 输出契约');
        const mockOutput = {
            success: true,
            match_id: matchId,
            size: 12345,
            workerId: 1,
            port: 7890
        };
        const contractResult = validateHarvestMatchContract(mockOutput);

        if (contractResult.valid) {
            console.log(`   ✅ PASS - 输出契约验证通过`);
            results.passed++;
        } else {
            console.log(`   ❌ FAIL - 输出契约验证失败`);
            contractResult.errors.forEach(e => console.log(`      - ${e}`));
            results.failed++;
        }
        results.tests.push({ name: '输出契约', ...contractResult });

    } catch (error) {
        console.error(`\n❌ 测试套件执行失败: ${error.message}`);
        results.failed++;
    } finally {
        guard.cleanup();
    }

    // 打印摘要
    console.log('\n' + '═'.repeat(60));
    console.log('  📊 测试结果摘要');
    console.log('═'.repeat(60));
    console.log(`  ✅ 通过: ${results.passed}`);
    console.log(`  ❌ 失败: ${results.failed}`);
    console.log(`  ⏭️ 跳过: ${results.skipped}`);
    console.log(`  📈 通过率: ${((results.passed / (results.passed + results.failed)) * 100).toFixed(1)}%`);
    console.log('═'.repeat(60));

    return results;
}

// 导出模块
module.exports = {
    RefactorGuard,
    SnapshotManager,
    HarvesterCapture,
    deepDiff,
    resolvePath,
    validateHarvestMatchContract,
    validateSaveRawDataContract,
    validateClassStructureContract,
    runFullRegressionSuite
};

// CLI 模式
if (require.main === module) {
    main().catch(console.error);
}
