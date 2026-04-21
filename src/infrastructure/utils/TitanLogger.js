/**
 * TitanLogger - 工业级结构化日志系统
 * ====================================
 *
 * 职责: 统一日志接口，强制结构化输出
 * - JSON 格式日志
 * - 强制 traceId 传播
 * - 日志级别控制
 *
 * @module infrastructure/logger/TitanLogger
 * @version V11.6-INDUSTRIAL
 */

'use strict';

const winston = require('winston');
const path = require('path');
const { randomUUID } = require('crypto');

class TitanLogger {
  constructor(options = {}) {
    this.serviceName = options.serviceName || 'titan';
    this.defaultTraceId = options.traceId || null;
    this.logLevel = options.logLevel || process.env.LOG_LEVEL || 'info';
    this.logDir = options.logDir || process.env.LOG_DIR || path.join(process.cwd(), 'logs');

    this.logger = winston.createLogger({
      level: this.logLevel,
      format: winston.format.combine(
        winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss.SSS' }),
        winston.format.errors({ stack: true }),
        winston.format.json()
      ),
      defaultMeta: {
        service: this.serviceName,
        pid: process.pid,
        hostname: require('os').hostname()
      },
      transports: [
        new winston.transports.Console({
          format: winston.format.combine(
            winston.format.colorize(),
            winston.format.printf(({ timestamp, level, message, traceId, ...meta }) => {
              const trace = traceId ? `[${traceId.slice(0, 8)}]` : '[--------]';
              const metaStr = Object.keys(meta).length > 0 ? ` ${JSON.stringify(meta)}` : '';
              return `${timestamp} ${level} ${trace} ${message}${metaStr}`;
            })
          )
        })
      ]
    });

    if (options.enableFileLogging !== false) {
      const DailyRotateFile = require('winston-daily-rotate-file');
      this.logger.add(
        new DailyRotateFile({
          dirname: this.logDir,
          filename: `${this.serviceName}-%DATE%.log`,
          datePattern: 'YYYY-MM-DD',
          maxSize: '100m',
          maxFiles: '14d',
          format: winston.format.json()
        })
      );
    }
  }

  _log(level, message, context = {}) {
    const traceId = context.traceId || this.defaultTraceId || 'NO_TRACE';
    const meta = { ...context, traceId };
    delete meta.message;

    this.logger.log(level, message, meta);
  }

  debug(message, context = {}) {
    this._log('debug', message, context);
  }

  info(message, context = {}) {
    this._log('info', message, context);
  }

  warn(message, context = {}) {
    this._log('warn', message, context);
  }

  error(message, context = {}) {
    if (context instanceof Error) {
      context = {
        error: context.message,
        stack: context.stack,
        code: context.code
      };
    } else if (context.error instanceof Error) {
      context.stack = context.error.stack;
      context.error = context.error.message;
    }

    this._log('error', message, context);
  }

  child(childContext = {}) {
    const childLogger = new TitanLogger({
      serviceName: this.serviceName,
      traceId: childContext.traceId || this.defaultTraceId,
      logLevel: this.logLevel,
      logDir: this.logDir,
      enableFileLogging: false
    });

    childLogger.logger = this.logger.child(childContext);
    return childLogger;
  }

  static createTraceId() {
    return randomUUID();
  }

  setTraceId(traceId) {
    this.defaultTraceId = traceId;
  }

  getTraceId() {
    return this.defaultTraceId;
  }
}

const defaultLogger = new TitanLogger({ serviceName: 'titan-default' });

module.exports = {
  TitanLogger,
  logger: defaultLogger,
  createLogger: (options) => new TitanLogger(options),
  createTraceId: TitanLogger.createTraceId
};
