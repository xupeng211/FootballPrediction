/**
 * ZombieKiller - 僵尸进程清理器 (V175 增强版)
 * ==============================================
 *
 * 在 Worker 启动前执行，确保没有残留的 Chrome/Chromium 进程
 * 防止资源泄漏和端口冲突
 *
 * V175 增强:
 * - defunct 进程检测 (真正意义上的僵尸)
 * - 超时进程清理 (运行超过 5 分钟的 Playwright 进程)
 * - 定期扫描模式
 * @module core/process/ZombieKiller
 * @version V175.0.0
 */

'use strict';

const { execSync } = require('child_process');

/**
 * ZombieKiller - 僵尸进程清理器
 */
class ZombieKiller {
    /**
     * @param {object} options - 配置选项
     * @param {number} options.timeout - 命令超时时间 (ms)
     * @param {string[]} options.targetProcesses - 目标进程名列表
     * @param {boolean} options.silent - 静默模式
     * @param {number} options.maxProcessAge - 进程最大存活时间 (ms)，超过则清理
     */
    constructor(options = {}) {
        this.timeout = options.timeout ?? 5000;
        this.targetProcesses = options.targetProcesses ?? ['chromium', 'chrome', 'playwright'];
        this.silent = options.silent ?? false;
        // V175: 进程最大存活时间 (5 分钟)
        this.maxProcessAge = options.maxProcessAge ?? 5 * 60 * 1000;
        this.lastCleanupStats = null;
        // V175: 定期扫描定时器
        this._scanInterval = null;
    }

    /**
     * 日志输出
     * @param level
     * @param msg
     * @private
     */
    _log(level, msg) {
        if (this.silent) return;
        const timestamp = new Date().toISOString().slice(0, 19).replace('T', ' ');
        const prefix = '[ZombieKiller]';
        console.log(`${timestamp} ${prefix} [${level.toUpperCase()}] ${msg}`);
    }

    /**
     * 查找僵尸进程 (常规)
     * @returns {string[]} 进程 PID 列表
     */
    findZombieProcesses() {
        const processPatterns = this.targetProcesses.join('|');
        const command = `pgrep -f "${processPatterns}" 2>/dev/null || true`;

        try {
            const output = execSync(command, {
                encoding: 'utf8',
                timeout: this.timeout
            }).trim();

            if (!output) {
                return [];
            }

            return output.split('\n').filter(pid => pid && /^\d+$/.test(pid));

        } catch (e) {
            this._log('warn', `查找进程失败: ${e.message}`);
            return [];
        }
    }

    /**
     * V175: 查找 defunct (僵尸) 进程
     * 真正的僵尸进程在 ps 中显示为 "Z" 或 "defunct"
     * @returns {Array<{pid: string, ppid: string, cmd: string}>}
     */
    findDefunctProcesses() {
        try {
            // 查找状态为 Z (zombie) 的进程
            const command = 'ps aux | grep -E "defunct|<defunct>" | grep -v grep || true';
            const output = execSync(command, {
                encoding: 'utf8',
                timeout: this.timeout
            }).trim();

            if (!output) {
                return [];
            }

            const zombies = [];
            const lines = output.split('\n');

            for (const line of lines) {
                const parts = line.trim().split(/\s+/);
                if (parts.length >= 11) {
                    zombies.push({
                        user: parts[0],
                        pid: parts[1],
                        ppid: parts[2],
                        stat: parts[7],
                        cmd: parts.slice(10).join(' ')
                    });
                }
            }

            return zombies;

        } catch (e) {
            this._log('warn', `查找 defunct 进程失败: ${e.message}`);
            return [];
        }
    }

    /**
     * V175: 查找超时进程
     * 查找运行时间超过阈值的 Playwright/Chrome 进程
     * @returns {Array<{pid: string, etime: string, cmd: string}>}
     */
    findStaleProcesses() {
        try {
            // 使用 ps 查找运行时间超过阈值的进程
            // etime 是进程运行时间 (elapsed time)
            const processPatterns = this.targetProcesses.join('|');
            const command = `ps -eo pid,etime,cmd | grep -E "${processPatterns}" | grep -v grep || true`;

            const output = execSync(command, {
                encoding: 'utf8',
                timeout: this.timeout
            }).trim();

            if (!output) {
                return [];
            }

            const stale = [];
            const lines = output.split('\n');

            for (const line of lines) {
                const parts = line.trim().split(/\s+/);
                if (parts.length >= 3) {
                    const pid = parts[0];
                    const etime = parts[1];
                    const cmd = parts.slice(2).join(' ');

                    // 解析运行时间 (格式可能是 00:05:00 或 5:00 或 00:05)
                    const ageMs = this._parseElapsedTime(etime);

                    if (ageMs > this.maxProcessAge) {
                        stale.push({ pid, etime, cmd, ageMs });
                    }
                }
            }

            return stale;

        } catch (e) {
            this._log('warn', `查找超时进程失败: ${e.message}`);
            return [];
        }
    }

    /**
     * 解析 ps etime 格式
     * @private
     * @param {string} etime - 格式如 "00:05:00", "5:00", "00:05"
     * @returns {number} 毫秒数
     */
    _parseElapsedTime(etime) {
        const parts = etime.split(':').map(Number);

        if (parts.length === 3) {
            // HH:MM:SS
            return (parts[0] * 3600 + parts[1] * 60 + parts[2]) * 1000;
        } else if (parts.length === 2) {
            // MM:SS
            return (parts[0] * 60 + parts[1]) * 1000;
        }

        return 0;
    }

    /**
     * 杀死指定进程
     * @param {string} pid - 进程 PID
     * @param {boolean} force - 是否强制杀死 (SIGKILL)
     * @returns {boolean} 是否成功
     */
    killProcess(pid, force = true) {
        const signal = force ? '-9' : '-15';
        const command = `kill ${signal} ${pid} 2>/dev/null || true`;

        try {
            execSync(command, { timeout: 1000 });
            return true;
        } catch (e) {
            return false;
        }
    }

    /**
     * V175: 杀死进程树 (包括所有子进程)
     * @param {string} pid - 进程 PID
     * @returns {number} 杀死的进程数
     */
    killProcessTree(pid) {
        let killed = 0;

        try {
            // 查找所有子进程
            const childrenCmd = `pgrep -P ${pid} 2>/dev/null || true`;
            const children = execSync(childrenCmd, {
                encoding: 'utf8',
                timeout: 2000
            }).trim().split('\n').filter(p => p);

            // 递归杀死子进程
            for (const childPid of children) {
                killed += this.killProcessTree(childPid);
            }

            // 杀死父进程
            if (this.killProcess(pid, true)) {
                killed++;
            }

        } catch (e) {
            // 忽略错误
        }

        return killed;
    }

    /**
     * 执行起飞前清理 (V175 增强)
     * 在 Worker 启动前执行，确保没有残留的 Chrome/Chromium 进程
     * @param {number} workerId - Worker ID (用于日志)
     * @returns {object} 清理统计 { found, killed, failed, defunct, stale }
     */
    preFlightCleanup(workerId = 0) {
        const stats = {
            found: 0,
            killed: 0,
            failed: 0,
            defunct: 0,
            stale: 0,
            pids: []
        };

        const workerPrefix = workerId ? `[W${workerId}]` : '';

        try {
            // 1. 清理常规僵尸进程
            const pids = this.findZombieProcesses();
            stats.found = pids.length;

            if (pids.length > 0) {
                this._log('info', `${workerPrefix} 发现 ${pids.length} 个进程，正在清理...`);

                for (const pid of pids) {
                    const killed = this.killProcessTree(pid);
                    if (killed > 0) {
                        stats.killed += killed;
                        stats.pids.push(pid);
                    } else {
                        stats.failed++;
                    }
                }
            }

            // 2. V175: 清理 defunct 进程
            const defunct = this.findDefunctProcesses();
            if (defunct.length > 0) {
                this._log('warn', `${workerPrefix} 发现 ${defunct.length} 个 defunct 僵尸进程`);
                stats.defunct = defunct.length;

                // defunct 进程无法直接杀死，需要杀死父进程
                for (const z of defunct) {
                    // 尝试杀死父进程 (如果父进程是 node/chromium)
                    if (z.ppid && z.ppid !== '1') {
                        this.killProcess(z.ppid, false);
                    }
                }
            }

            // 3. V175: 清理超时进程
            const stale = this.findStaleProcesses();
            if (stale.length > 0) {
                this._log('warn', `${workerPrefix} 发现 ${stale.length} 个超时进程 (>${this.maxProcessAge / 60000}分钟)`);
                stats.stale = stale.length;

                for (const s of stale) {
                    const killed = this.killProcessTree(s.pid);
                    stats.killed += killed;
                    this._log('debug', `${workerPrefix} 清理超时进程 PID ${s.pid} (运行 ${s.etime})`);
                }
            }

            // 汇总日志
            if (stats.killed > 0 || stats.defunct > 0 || stats.stale > 0) {
                this._log('info', `${workerPrefix} 清理完成: ${stats.killed} 已杀死, ${stats.defunct} defunct, ${stats.stale} 超时`);
            } else if (stats.found === 0) {
                this._log('debug', `${workerPrefix} 环境干净`);
            }

        } catch (e) {
            this._log('warn', `${workerPrefix} 清理检查失败: ${e.message}`);
        }

        this.lastCleanupStats = stats;
        return stats;
    }

    /**
     * V175: 启动定期扫描
     * 每 30 秒扫描一次，清理僵尸进程
     * @param {number} interval - 扫描间隔 (ms)，默认 30 秒
     */
    startPeriodicScan(interval = 30000) {
        if (this._scanInterval) {
            this.stopPeriodicScan();
        }

        this._log('info', `启动定期僵尸扫描 (间隔 ${interval / 1000}s)`);

        this._scanInterval = setInterval(() => {
            const stats = this.preFlightCleanup(0);

            // 如果发现大量僵尸，发出警告
            if (stats.defunct > 5) {
                this._log('warn', `⚠️ 检测到 ${stats.defunct} 个 defunct 进程，可能需要重启容器`);
            }
        }, interval);
    }

    /**
     * V175: 停止定期扫描
     */
    stopPeriodicScan() {
        if (this._scanInterval) {
            clearInterval(this._scanInterval);
            this._scanInterval = null;
            this._log('info', '定期僵尸扫描已停止');
        }
    }

    /**
     * 强制杀死浏览器进程
     * 确保即使手动停止脚本，所有浏览器进程也必须被物理强制杀死
     * @param {number} workerId - Worker ID
     * @returns {object} 清理统计
     */
    forceKillBrowser(workerId = 0) {
        const stats = {
            found: 0,
            killed: 0,
            pids: []
        };

        try {
            // 查找当前进程相关的 chrome 进程
            // $$ 是当前 shell 的 PID，-P 查找子进程
            const command = 'pgrep -P $$ 2>/dev/null || true';

            const output = execSync(command, {
                encoding: 'utf8',
                timeout: 2000
            }).trim();

            if (output) {
                const pids = output.split('\n').filter(p => p);
                stats.found = pids.length;

                for (const pid of pids) {
                    const killed = this.killProcessTree(pid);
                    stats.killed += killed;
                    stats.pids.push(pid);
                }

                if (!this.silent && stats.killed > 0) {
                    const workerPrefix = workerId ? `[W${workerId}]` : '';
                    this._log('debug', `${workerPrefix} 已强制清理 ${stats.killed} 个子进程`);
                }
            }

        } catch (e) {
            // 忽略清理错误
        }

        return stats;
    }

    /**
     * 检查是否有残留进程
     * @returns {boolean} 是否有残留进程
     */
    hasZombieProcesses() {
        return this.findZombieProcesses().length > 0;
    }

    /**
     * V175: 检查是否有 defunct 进程
     * @returns {boolean}
     */
    hasDefunctProcesses() {
        return this.findDefunctProcesses().length > 0;
    }

    /**
     * V175: 获取僵尸进程统计
     * @returns {object}
     */
    getZombieStats() {
        return {
            regular: this.findZombieProcesses().length,
            defunct: this.findDefunctProcesses().length,
            stale: this.findStaleProcesses().length
        };
    }

    /**
     * 获取上次清理统计
     * @returns {object | null}
     */
    getLastStats() {
        return this.lastCleanupStats;
    }

    /**
     * 静态方法：快速清理
     * @param {number} workerId - Worker ID
     * @returns {object} 清理统计
     */
    static quickClean(workerId = 0) {
        const killer = new ZombieKiller();
        return killer.preFlightCleanup(workerId);
    }

    /**
     * 静态方法：强制杀死浏览器
     * @param {number} workerId - Worker ID
     * @returns {object} 清理统计
     */
    static forceKillBrowser(workerId = 0) {
        const killer = new ZombieKiller();
        return killer.forceKillBrowser(workerId);
    }

    /**
     * V175: 静态方法：获取僵尸统计
     * @returns {object}
     */
    static getStats() {
        const killer = new ZombieKiller({ silent: true });
        return killer.getZombieStats();
    }
}

/**
 * 便捷函数：起飞前清理
 * @param {number} workerId - Worker ID
 * @returns {object} 清理统计
 */
function preFlightCleanup(workerId = 0) {
    return ZombieKiller.quickClean(workerId);
}

/**
 * 便捷函数：强制杀死浏览器
 * @param {number} workerId - Worker ID
 * @returns {object} 清理统计
 */
function forceKillBrowser(workerId = 0) {
    return ZombieKiller.forceKillBrowser(workerId);
}

/**
 * V175: 便捷函数：获取僵尸统计
 * @returns {object}
 */
function getZombieStats() {
    return ZombieKiller.getStats();
}

module.exports = {
    ZombieKiller,
    preFlightCleanup,
    forceKillBrowser,
    getZombieStats
};
