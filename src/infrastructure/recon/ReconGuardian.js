/**
 * ReconGuardian - 僵尸进程守护进程
 * ================================
 *
 * 职责: 定时巡检系统进程树，清理残留的浏览器僵尸进程
 * 核心要求:
 * - 每 60 秒巡检一次
 * - 识别父进程已退出的 chromium/playwright 进程
 * - 强制执行 SIGKILL 确保资源 100% 回收
 *
 * @module infrastructure/recon/ReconGuardian
 * @version V6.7-OBSERVABILITY
 * @date 2026-03-22
 */

'use strict';

const { exec } = require('child_process');
const util = require('util');
const execAsync = util.promisify(exec);

/**
 * Guardian 守护进程类
 * @class ReconGuardian
 */
class ReconGuardian {
  /**
   * 创建 Guardian 实例
   * @param {Object} options - 配置选项
   * @param {Object} options.metrics - ReconMetrics 实例
   * @param {Object} options.logger - 结构化日志器
   * @param {number} options.intervalMs - 巡检间隔 ms (默认: 60000)
   * @param {Array<string>} options.targetProcesses - 目标进程名列表
   */
  constructor(options = {}) {
    this.metrics = options.metrics;
    this.logger = options.logger || console;
    this.intervalMs = options.intervalMs || 60000;
    this.targetProcesses = options.targetProcesses || ['chromium', 'chrome', 'playwright'];
    this.killResourceHogs = options.killResourceHogs === true;
    this.cpuThreshold = Number(options.cpuThreshold || 50);
    this.memThreshold = Number(options.memThreshold || 20);
    this.orphanGraceSeconds = Number(options.orphanGraceSeconds || 1800);
    this.managedProfileMarker = String(options.managedProfileMarker || 'playwright_profile_');

    this.interval = null;
    this.isRunning = false;
    this.zombiesKilled = 0;
    this.lastScanTime = null;
    this.scanCount = 0;

    this.logger.info('guardian_initialized', {
      intervalMs: this.intervalMs,
      targets: this.targetProcesses,
      killResourceHogs: this.killResourceHogs
    });
  }

  /**
   * 启动 Guardian 巡检
   */
  start() {
    if (this.isRunning) {
      this.logger.warn('guardian_already_running');
      return;
    }

    this.isRunning = true;
    this.logger.info('guardian_started');

    if (this.metrics) {
      this.metrics.setGuardianRunning(true);
    }

    // 立即执行一次巡检
    this.checkZombies().catch(e => {
      this.logger.error('guardian_initial_scan_error', { error: e.message });
    });

    // 定时巡检
    this.interval = setInterval(() => {
      this.checkZombies().catch(e => {
        this.logger.error('guardian_scan_error', { error: e.message });
      });
    }, this.intervalMs);

    // 确保 interval 不会阻止进程退出
    if (this.interval.unref) {
      this.interval.unref();
    }
  }

  /**
   * 停止 Guardian 巡检
   */
  stop() {
    if (!this.isRunning) {
      return;
    }

    if (this.interval) {
      clearInterval(this.interval);
      this.interval = null;
    }

    this.isRunning = false;
    this.logger.info('guardian_stopped', {
      totalZombiesKilled: this.zombiesKilled,
      totalScans: this.scanCount
    });

    if (this.metrics) {
      this.metrics.setGuardianRunning(false);
    }
  }

  /**
   * 执行僵尸进程巡检
   * @returns {Promise<number>} 清理的僵尸进程数
   */
  async checkZombies() {
    const startTime = Date.now();
    this.scanCount++;

    try {
      this.logger.debug('guardian_scan_start', { scanNumber: this.scanCount });

      const zombies = await this.findZombieProcesses();
      let killed = 0;

      for (const zombie of zombies) {
        const success = await this.killZombie(zombie);
        if (success) {
          killed++;
        }
      }

      const duration = Date.now() - startTime;
      this.lastScanTime = new Date();

      this.logger.info('guardian_scan_complete', {
        scanNumber: this.scanCount,
        zombiesFound: zombies.length,
        zombiesKilled: killed,
        durationMs: duration
      });

      return killed;
    } catch (e) {
      this.logger.error('guardian_scan_failed', {
        error: e.message,
        stack: e.stack
      });
      throw e;
    }
  }

  /**
   * 查找僵尸进程
   * @returns {Promise<Array<Object>>} 僵尸进程列表 [{ pid, ppid, name, cpu, mem }]
   * @private
   */
  async findZombieProcesses() {
    try {
      const { stdout } = await execAsync('ps -eo pid=,ppid=,pcpu=,pmem=,etimes=,stat=,args=');
      if (!stdout.trim()) {
        return [];
      }

      return stdout.trim().split('\n')
        .map((line) => this._buildCollectableProcess(line))
        .filter(Boolean);
    } catch (e) {
      this.logger.debug('process_check_error', { error: e.message });
      return [];
    }
  }

  _buildCollectableProcess(line) {
    const parts = line.trim().match(/^(\d+)\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+(\d+)\s+(\S+)\s+(.+)$/);
    if (!parts) {
      return null;
    }

    const [, pidStr, ppidStr, cpu, mem, elapsedStr, stat, cmd] = parts;
    const processName = this.targetProcesses.find((name) => cmd.toLowerCase().includes(name.toLowerCase()));
    const pid = parseInt(pidStr, 10);
    const ppid = parseInt(ppidStr, 10);
    if (!processName || isNaN(pid) || isNaN(ppid)) {
      return null;
    }

    const cpuUsage = parseFloat(cpu) || 0;
    const memUsage = parseFloat(mem) || 0;
    const flags = {
      isZombie: stat === 'Z' || stat === 'Z+',
      isOrphan: ppid === 1,
      isManagedProfile: this._isManagedBrowserProcess(cmd),
      isResourceHog: cpuUsage > this.cpuThreshold || memUsage > this.memThreshold
    };
    flags.isOrphanPastGrace = flags.isOrphan && (parseInt(elapsedStr, 10) || 0) >= this.orphanGraceSeconds;
    if (!this._shouldCollectProcess(flags)) {
      return null;
    }

    return {
      pid,
      ppid,
      name: processName,
      cpu: cpuUsage,
      mem: memUsage,
      stat,
      cmd: cmd.substring(0, 100),
      ...flags
    };
  }

  /**
   * 判断进程是否应被视为可清理目标
   * @param {Object} flags
   * @returns {boolean}
   * @private
   */
  _shouldCollectProcess(flags = {}) {
    const {
      isZombie = false,
      isOrphan = false,
      isOrphanPastGrace = false,
      isManagedProfile = false,
      isResourceHog = false
    } = flags;

    if (isZombie) {
      return true;
    }

    if (isOrphan && isOrphanPastGrace && !isManagedProfile) {
      return true;
    }

    return this.killResourceHogs && isResourceHog;
  }

  _isManagedBrowserProcess(cmd = '') {
    const raw = String(cmd || '');
    return Boolean(this.managedProfileMarker && raw.includes(this.managedProfileMarker));
  }

  /**
   * 终止僵尸进程
   * @param {Object} zombie - 僵尸进程信息
   * @returns {Promise<boolean>} 是否成功终止
   * @private
   */
  async killZombie(zombie) {
    const { pid, name, isZombie, isOrphan } = zombie;

    this.logger.warn('killing_zombie', {
      pid,
      name,
      reason: isZombie ? 'zombie' : isOrphan ? 'orphan' : 'resource_hog',
      cpu: zombie.cpu,
      mem: zombie.mem
    });

    try {
      // 先尝试优雅终止 (SIGTERM)
      await execAsync(`kill -15 ${pid} 2>/dev/null || true`);

      // 等待短暂时间
      await this.sleep(1000);

      // 检查进程是否仍在运行
      const isStillRunning = await this.isProcessRunning(pid);

      if (isStillRunning) {
        // 强制终止 (SIGKILL)
        await execAsync(`kill -9 ${pid} 2>/dev/null || true`);
      }

      // 验证终止结果
      const isDead = !(await this.isProcessRunning(pid));

      if (isDead) {
        this.zombiesKilled++;

        if (this.metrics) {
          this.metrics.recordZombieKilled(name);
        }

        this.logger.info('zombie_killed', {
          pid,
          name,
          totalKilled: this.zombiesKilled
        });

        return true;
      } else {
        this.logger.error('zombie_kill_failed', { pid, name });
        return false;
      }
    } catch (e) {
      this.logger.error('zombie_kill_error', {
        pid,
        name,
        error: e.message
      });
      return false;
    }
  }

  /**
   * 检查进程是否仍在运行
   * @param {number} pid - 进程 ID
   * @returns {Promise<boolean>} 是否运行中
   * @private
   */
  async isProcessRunning(pid) {
    try {
      await execAsync(`kill -0 ${pid} 2>/dev/null`);
      return true;
    } catch (e) {
      return false;
    }
  }

  /**
   * 休眠
   * @param {number} ms - 毫秒数
   * @returns {Promise<void>}
   * @private
   */
  sleep(ms) {
    return new Promise((resolve) => {
      setTimeout(resolve, ms);
    });
  }

  /**
   * 获取 Guardian 统计信息
   * @returns {Object} 统计信息
   */
  getStats() {
    return {
      isRunning: this.isRunning,
      intervalMs: this.intervalMs,
      scanCount: this.scanCount,
      zombiesKilled: this.zombiesKilled,
      lastScanTime: this.lastScanTime,
      targetProcesses: this.targetProcesses
    };
  }

  /**
   * 立即执行一次巡检 (用于手动触发)
   * @returns {Promise<number>} 清理的僵尸进程数
   */
  async scanNow() {
    return this.checkZombies();
  }
}

module.exports = { ReconGuardian };
