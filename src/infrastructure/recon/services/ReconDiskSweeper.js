'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

class ReconDiskSweeper {
  constructor(options = {}) {
    this.logger = options.logger || console;
    this.traceId = options.traceId || 'trace-unknown';
    this.rootDir = String(options.rootDir || os.tmpdir());
    this.profilePrefix = String(options.profilePrefix || 'playwright_profile_');
    this.maxAgeMs = Math.max(0, Number(options.maxAgeMs ?? 60 * 60 * 1000));
    this.enabled = options.enabled !== false;
  }

  async sweep() {
    if (!this.enabled) {
      return {
        scanned: 0,
        removed: 0,
        reclaimedBytes: 0,
        rootDir: this.rootDir
      };
    }

    let entries = [];
    try {
      entries = await fs.promises.readdir(this.rootDir, { withFileTypes: true });
    } catch (error) {
      this.logger.warn('recon_disk_sweeper_root_unavailable', {
        traceId: this.traceId,
        rootDir: this.rootDir,
        error: error.message
      });
      return {
        scanned: 0,
        removed: 0,
        reclaimedBytes: 0,
        rootDir: this.rootDir
      };
    }

    const cutoff = Date.now() - this.maxAgeMs;
    let scanned = 0;
    let removed = 0;
    let reclaimedBytes = 0;

    for (const entry of entries) {
      if (!entry.isDirectory() || !entry.name.startsWith(this.profilePrefix)) {
        continue;
      }

      scanned += 1;
      const targetPath = path.join(this.rootDir, entry.name);

      try {
        const stat = await fs.promises.stat(targetPath);
        if (stat.mtimeMs >= cutoff) {
          continue;
        }

        const sizeBytes = await this._estimateDirectorySize(targetPath);
        await fs.promises.rm(targetPath, { recursive: true, force: true });
        removed += 1;
        reclaimedBytes += sizeBytes;
      } catch (error) {
        this.logger.warn('recon_disk_sweeper_remove_failed', {
          traceId: this.traceId,
          targetPath,
          error: error.message
        });
      }
    }

    const summary = {
      scanned,
      removed,
      reclaimedBytes,
      rootDir: this.rootDir,
      maxAgeMs: this.maxAgeMs
    };
    this.logger.info('recon_disk_sweeper_complete', {
      traceId: this.traceId,
      ...summary
    });
    return summary;
  }

  async _estimateDirectorySize(targetPath) {
    const stack = [targetPath];
    let total = 0;

    while (stack.length > 0) {
      const currentPath = stack.pop();
      let entries = [];

      try {
        entries = await fs.promises.readdir(currentPath, { withFileTypes: true });
      } catch (_error) {
        continue;
      }

      for (const entry of entries) {
        const fullPath = path.join(currentPath, entry.name);
        if (entry.isDirectory()) {
          stack.push(fullPath);
          continue;
        }

        try {
          const stat = await fs.promises.stat(fullPath);
          total += stat.size;
        } catch (_error) {
          continue;
        }
      }
    }

    return total;
  }
}

module.exports = {
  ReconDiskSweeper
};
