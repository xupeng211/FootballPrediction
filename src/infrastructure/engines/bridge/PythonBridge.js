/**
 * PythonBridge - V171.000 [Integration.Alpha]
 * =================================================
 *
 * Node.js → Python 桥接器
 *
 * Core Features:
 * - spawn Python 子进程
 * - 调用 GoldenDataMerger.merge_match()
 * - 调用 MultiModelValidator 并发预测
 * - JSON 序列化通信
 * - 错误处理和超时管理
 *
 * Usage:
 *   const bridge = new PythonBridge();
 *   const result = await bridge.callMerger({
 *     match_id: '12345',
 *     league_name: 'Premier League',
 *     season: '2024-2025'
 *   });
 *
 * @module engines/bridge/PythonBridge
 * @version V171.000
 * @since 2026-02-23
 */

'use strict';

const { spawn } = require('child_process');
const path = require('path');

// ============================================================================
// PYTHON BRIDGE
// ============================================================================

class PythonBridge {
    /**
     * 创建 Python 桥接器实例
     * @param {Object} options - 配置选项
     * @param {string} options.pythonPath - Python 可执行文件路径
     * @param {number} options.timeout - 超时时间（毫秒）
     * @param {string} options.logLevel - 日志级别
     */
    constructor(options = {}) {
        this.pythonPath = options.pythonPath || 'python3';
        this.timeout = options.timeout || 120000; // 默认 2 分钟
        this.logLevel = options.logLevel || 'info';
        // V171.000: 修正路径计算 - bridge 目录在 src/infrastructure/engines/bridge/
        // 需要向上 4 级到达项目根目录
        // __dirname = /app/src/infrastructure/engines/bridge
        // 向上 4 级 = /app
        this.projectRoot = path.resolve(__dirname, '..', '..', '..', '..');

        // 日志辅助函数
        this._log = (level, message) => {
            if (this._shouldLog(level)) {
                const timestamp = new Date().toISOString();
                console.log(`[${timestamp}] [PythonBridge] [${level.toUpperCase()}] ${message}`);
            }
        };

        this._shouldLog = (level) => {
            const levels = ['debug', 'info', 'warn', 'error'];
            return levels.indexOf(level) >= levels.indexOf(this.logLevel);
        };
    }

    /**
     * 调用 GoldenDataMerger.merge_match()
     * @param {Object} params - 参数
     * @param {string} params.match_id - 比赛 ID
     * @param {string} params.league_name - 联赛名称
     * @param {string} params.season - 赛季
     * @param {boolean} params.force - 强制重新执行
     * @param {boolean} params.skip_l2 - 跳过 L2
     * @param {boolean} params.skip_l3 - 跳过 L3
     * @returns {Promise<Object>} 融合结果
     */
    async callMerger(params) {
        this._log('info', `Calling GoldenDataMerger for match: ${params.match_id}`);

        const script = this._buildMergerScript(params);
        return this._executePython(script, params.match_id);
    }

    /**
     * 调用 MultiModelValidator 执行多模型预测
     * @param {Object} params - 参数
     * @param {string} params.match_id - 比赛 ID
     * @param {string} params.league_name - 联赛名称（可选）
     * @returns {Promise<Object>} 预测结果
     */
    async callValidator(params) {
        this._log('info', `Calling MultiModelValidator for match: ${params.match_id}`);

        const script = this._buildValidatorScript(params);
        return this._executePython(script, `validator_${params.match_id}`);
    }

    /**
     * 构建 GoldenDataMerger 调用脚本
     * @private
     */
    _buildMergerScript(params) {
        return `
import asyncio
import json
import sys
import os

# 确保项目根目录在 Python 路径中
sys.path.insert(0, '${this.projectRoot.replace(/\\/g, '/')}')

from src.infrastructure.merger.GoldenDataMerger import GoldenDataMerger

async def main():
    try:
        merger = GoldenDataMerger()
        result = await merger.merge_match(
            match_id='${params.match_id}',
            league_name=${params.league_name ? `'${params.league_name}'` : 'None'},
            season=${params.season ? `'${params.season}'` : 'None'},
            force=${params.force || false},
            skip_l2=${params.skip_l2 || false},
            skip_l3=${params.skip_l3 || false}
        )

        # 转换为可序列化字典
        output = {
            'match_id': result.match_id,
            'is_complete_success': result.is_complete_success,
            'total_latency_ms': result.total_latency_ms,
            'l1_status': result.l1_result.status.value if result.l1_result else None,
            'l2_status': result.l2_result.status.value if result.l2_result else None,
            'l3_status': result.l3_result.status.value if result.l3_result else None,
            'completed_at': result.completed_at
        }

        print(json.dumps({'success': True, 'data': output}))
        merger.close()

    except Exception as e:
        print(json.dumps({'success': False, 'error': str(e)}))
        sys.exit(1)

asyncio.run(main())
`.trim();
    }

    /**
     * 构建 MultiModelValidator 调用脚本
     * @private
     */
    _buildValidatorScript(params) {
        return `
import asyncio
import json
import sys
import os

# 确保项目根目录在 Python 路径中
sys.path.insert(0, '${this.projectRoot.replace(/\\/g, '/')}')

from src.ml.inference.multi_model_validator import MultiModelValidator

def result_to_dict(result):
    """将 ConsensusResult 转换为可序列化字典"""
    return {
        'match_id': result.match_id,
        'final_prediction': result.final_prediction,
        'final_confidence': result.final_confidence,
        'consensus_level': result.consensus_level.value,
        'agreement_ratio': result.agreement_ratio,
        'models_count': result.models_count,
        'voting_breakdown': result.voting_breakdown,
        'recommended_bet': result.recommended_bet,
        'is_reliable': result.is_reliable,
        'model_predictions': [
            {
                'model_type': p.model_type,
                'prediction': p.prediction,
                'confidence': p.confidence,
                'latency_ms': p.latency_ms
            }
            for p in result.model_predictions
        ]
    }

async def main():
    try:
        validator = MultiModelValidator()
        result = await validator.validate_match(
            match_id='${params.match_id}',
            league_name=${params.league_name ? `'${params.league_name}'` : 'None'}
        )
        validator.close()

        print(json.dumps({'success': True, 'data': result_to_dict(result)}))
    except Exception as e:
        print(json.dumps({'success': False, 'error': str(e)}))
        sys.exit(1)

asyncio.run(main())
`.trim();
    }

    /**
     * 执行 Python 脚本
     * @private
     */
    _executePython(script, taskId) {
        return new Promise((resolve, reject) => {
            const timeoutId = setTimeout(() => {
                reject(new Error(`Python process timeout after ${this.timeout}ms for task: ${taskId}`));
            }, this.timeout);

            const env = {
                ...process.env,
                PYTHONIOENCODING: 'utf-8',
                PYTHONUNBUFFERED: '1'
            };

            this._log('debug', `Spawning Python process for: ${taskId}`);

            const python = spawn(this.pythonPath, ['-c', script], {
                cwd: this.projectRoot,
                env: env
            });

            let stdout = '';
            let stderr = '';

            python.stdout.on('data', (data) => {
                stdout += data.toString();
            });

            python.stderr.on('data', (data) => {
                stderr += data.toString();
                this._log('debug', `Python stderr: ${data.toString()}`);
            });

            python.on('close', (code) => {
                clearTimeout(timeoutId);

                if (code !== 0) {
                    this._log('error', `Python process exited with code ${code}`);
                    this._log('error', `stderr: ${stderr}`);
                    reject(new Error(`Python process failed with code ${code}: ${stderr}`));
                    return;
                }

                try {
                    // 尝试解析 JSON 输出
                    const lines = stdout.trim().split('\n');
                    const lastLine = lines[lines.length - 1];

                    const result = JSON.parse(lastLine);

                    if (result.success) {
                        this._log('info', `Python task completed: ${taskId}`);
                        resolve(result.data);
                    } else {
                        this._log('error', `Python task failed: ${result.error}`);
                        reject(new Error(result.error));
                    }
                } catch (parseError) {
                    this._log('error', `Failed to parse Python output: ${parseError.message}`);
                    this._log('error', `Raw output: ${stdout}`);
                    reject(new Error(`Failed to parse Python output: ${parseError.message}`));
                }
            });

            python.on('error', (err) => {
                clearTimeout(timeoutId);
                this._log('error', `Failed to spawn Python process: ${err.message}`);
                reject(new Error(`Failed to spawn Python process: ${err.message}`));
            });
        });
    }

    /**
     * 测试 Python 环境和依赖
     * @returns {Promise<Object>} 测试结果
     */
    async testEnvironment() {
        this._log('info', 'Testing Python environment...');

        const script = `
import sys
import json

result = {
    'python_version': sys.version,
    'python_path': sys.executable
}

try:
    import psycopg2
    result['psycopg2'] = 'available'
except ImportError:
    result['psycopg2'] = 'missing'

try:
    import xgboost
    result['xgboost'] = 'available'
except ImportError:
    result['xgboost'] = 'missing'

try:
    import joblib
    result['joblib'] = 'available'
except ImportError:
    result['joblib'] = 'missing'

try:
    import pandas
    result['pandas'] = 'available'
except ImportError:
    result['pandas'] = 'missing'

# V171.000: 包装为标准格式
print(json.dumps({'success': True, 'data': result}))
`.trim();

        try {
            const result = await this._executePython(script, 'environment_test');
            this._log('info', `Python environment: ${JSON.stringify(result)}`);
            return { success: true, environment: result };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }
}

// ============================================================================
// MODULE EXPORTS
// ============================================================================

module.exports = { PythonBridge };

// ============================================================================
// CLI TEST ENTRY
// ============================================================================

if (require.main === module) {
    const bridge = new PythonBridge({ logLevel: 'debug' });

    // 测试环境
    bridge.testEnvironment()
        .then(result => {
            console.log('\n=== Environment Test ===');
            console.log(JSON.stringify(result, null, 2));
        })
        .catch(err => {
            console.error('Test failed:', err.message);
            process.exit(1);
        });
}
