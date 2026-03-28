'use strict';

const { spawn } = require('child_process');

class ProcessSupervisor {
  constructor(options = {}) {
    this.logger = options.logger || { info() {}, warn() {}, error() {} };
    this.defaultMaxRuntimeMs = Math.max(0, Number(options.maxRuntimeMs || 0));
    this.defaultKillGraceMs = Math.max(0, Number(options.killGraceMs || 5000));
    this.spawnImpl = options.spawnImpl || spawn;
    this._setTimeout = options.setTimeout || setTimeout;
    this._clearTimeout = options.clearTimeout || clearTimeout;
  }

  spawnChild(command, args = [], spawnOptions = {}) {
    return this.spawnImpl(command, args, spawnOptions);
  }

  _detachCloseListener(child, onClose) {
    if (!child || typeof onClose !== 'function') {
      return;
    }

    if (typeof child.off === 'function') {
      child.off('close', onClose);
    } else if (typeof child.removeListener === 'function') {
      child.removeListener('close', onClose);
    }
  }

  _sendSignal(child, signal, failureEvent) {
    try {
      child.kill(signal);
      return true;
    } catch (error) {
      this.logger.error(failureEvent, {
        pid: child?.pid || null,
        error: error.message
      });
      return false;
    }
  }

  terminateChild(child, options = {}) {
    if (!child || typeof child.kill !== 'function' || typeof child.on !== 'function') {
      return Promise.resolve({ terminated: false, forced: false });
    }

    const killGraceMs = Math.max(0, Number(options.killGraceMs ?? this.defaultKillGraceMs));

    return new Promise((resolve) => {
      let settled = false;
      let killTimer = null;

      const finish = (forced = false) => {
        if (settled) {
          return;
        }

        settled = true;
        if (killTimer) {
          this._clearTimeout(killTimer);
          killTimer = null;
        }
        this._detachCloseListener(child, onClose);
        resolve({ terminated: true, forced });
      };

      const onClose = () => {
        finish(false);
      };

      child.on('close', onClose);

      this._sendSignal(child, 'SIGTERM', 'child_sigterm_failed');

      if (killGraceMs > 0) {
        killTimer = this._setTimeout(() => {
          if (settled) {
            return;
          }

          this.logger.warn('child_force_kill', {
            pid: child.pid || null,
            killGraceMs
          });
          this._sendSignal(child, 'SIGKILL', 'child_sigkill_failed');
          finish(true);
        }, killGraceMs);
      } else {
        finish(false);
      }
    });
  }

  monitorChild(child, options = {}) {
    if (!child || typeof child.on !== 'function') {
      return { cancel() {} };
    }

    const maxRuntimeMs = Math.max(0, Number(options.maxRuntimeMs ?? this.defaultMaxRuntimeMs));
    const killGraceMs = Math.max(0, Number(options.killGraceMs ?? this.defaultKillGraceMs));

    let closed = false;
    let termTimer = null;
    let killTimer = null;

    const clearTimers = () => {
      if (termTimer) {
        this._clearTimeout(termTimer);
        termTimer = null;
      }
      if (killTimer) {
        this._clearTimeout(killTimer);
        killTimer = null;
      }
    };

    const detach = () => {
      this._detachCloseListener(child, onClose);
    };

    const onClose = () => {
      closed = true;
      clearTimers();
      detach();
    };

    child.on('close', onClose);

    if (maxRuntimeMs > 0 && typeof child.kill === 'function') {
      termTimer = this._setTimeout(() => {
        if (closed) {
          return;
        }

        this.logger.warn('child_runtime_exceeded', {
          pid: child.pid || null,
          maxRuntimeMs
        });

        this._sendSignal(child, 'SIGTERM', 'child_sigterm_failed');

        if (killGraceMs > 0) {
          killTimer = this._setTimeout(() => {
            if (closed) {
              return;
            }

            this.logger.warn('child_force_kill', {
              pid: child.pid || null,
              killGraceMs
            });

            this._sendSignal(child, 'SIGKILL', 'child_sigkill_failed');
          }, killGraceMs);
        }
      }, maxRuntimeMs);
    }

    return {
      cancel: () => {
        closed = true;
        clearTimers();
        detach();
      }
    };
  }
}

module.exports = { ProcessSupervisor };
