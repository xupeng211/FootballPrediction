/**
 * TitanConfig - 工业级配置中控面板
 * ===================================
 *
 * 职责: 集中管理所有环境变量，提供启动时验证
 * - 统一配置访问接口
 * - 必要环境变量校验
 * - 类型安全的配置读取
 *
 * @module infrastructure/config/TitanConfig
 * @version V11.6-INDUSTRIAL
 */

'use strict';

const path = require('path');

class TitanConfig {
  constructor() {
    this._config = null;
    this._validated = false;
  }

  _loadProxyConfig() {
    try {
      const { resolveProxyPoolConfig } = require('../../../config/proxy_pool');
      const pool = resolveProxyPoolConfig();
      return {
        host: pool.host,
        ports: pool.ports,
        portStart: pool.ports[0] || 0,
        portEnd: pool.ports[pool.ports.length - 1] || 0,
        protocol: pool.protocol
      };
    } catch (error) {
      return this._getFallbackProxyConfig();
    }
  }

  _getFallbackProxyConfig() {
    return {
      host: process.env.PROXY_HOST || process.env.WSL2_PROXY_HOST || 'localhost',
      ports: [],
      portStart: 0,
      portEnd: 0,
      protocol: process.env.PROXY_PROTOCOL || 'http'
    };
  }

  _loadDatabaseConfig() {
    return {
      host: process.env.DB_HOST || 'localhost',
      port: parseInt(process.env.DB_PORT || '5432', 10),
      name: process.env.DB_NAME || 'football_db',
      user: process.env.DB_USER || 'football_user',
      password: process.env.DB_PASSWORD || '',
      maxConnections: parseInt(process.env.DB_MAX_CONNECTIONS || '20', 10)
    };
  }

  _loadRedisConfig() {
    return {
      host: process.env.REDIS_HOST || 'localhost',
      port: parseInt(process.env.REDIS_PORT || '6379', 10),
      password: process.env.REDIS_PASSWORD || '',
      db: parseInt(process.env.REDIS_DB || '0', 10)
    };
  }

  _loadBrowserConfig() {
    return {
      profilePath: process.env.BROWSER_PROFILE_PATH || path.join(process.cwd(), 'data/browser_profile'),
      headless: process.env.BROWSER_HEADLESS !== 'false',
      launchTimeout: parseInt(process.env.BROWSER_LAUNCH_TIMEOUT || '30000', 10)
    };
  }

  _loadHarvesterConfig() {
    return {
      maxWorkers: parseInt(process.env.MAX_WORKERS || '1', 10),
      minDelayMs: parseInt(process.env.MIN_DELAY_MS || '10000', 10),
      maxDelayMs: parseInt(process.env.MAX_DELAY_MS || '15000', 10),
      batchSize: parseInt(process.env.BATCH_SIZE || '50', 10)
    };
  }

  _loadLoggingConfig() {
    return {
      level: process.env.LOG_LEVEL || 'info',
      dir: process.env.LOG_DIR || path.join(process.cwd(), 'logs')
    };
  }

  _loadEnvironmentConfig() {
    return {
      nodeEnv: process.env.NODE_ENV || 'development',
      dockerEnv: process.env.DOCKER_ENV === 'true',
      isProduction: process.env.NODE_ENV === 'production'
    };
  }

  _loadEnv() {
    if (this._config) return this._config;

    try {
      require('dotenv').config();
    } catch (error) {
      console.warn('[TitanConfig] dotenv 未安装，跳过 .env 加载');
    }

    this._config = {
      database: this._loadDatabaseConfig(),
      redis: this._loadRedisConfig(),
      proxy: this._loadProxyConfig(),
      browser: this._loadBrowserConfig(),
      harvester: this._loadHarvesterConfig(),
      logging: this._loadLoggingConfig(),
      environment: this._loadEnvironmentConfig()
    };

    return this._config;
  }

  validateConfig() {
    const config = this._loadEnv();
    const errors = [];

    if (!config.database.password) {
      errors.push('DB_PASSWORD 未设置（必填）');
    }

    if (config.database.port < 1 || config.database.port > 65535) {
      errors.push(`DB_PORT 无效: ${config.database.port}`);
    }

    if (config.harvester.maxWorkers < 1) {
      errors.push(`MAX_WORKERS 必须 >= 1，当前: ${config.harvester.maxWorkers}`);
    }

    if (config.harvester.minDelayMs >= config.harvester.maxDelayMs) {
      errors.push('MIN_DELAY_MS 必须小于 MAX_DELAY_MS');
    }

    if (errors.length > 0) {
      const errorMsg = `[TitanConfig] 配置验证失败:\n  - ${errors.join('\n  - ')}`;
      throw new Error(errorMsg);
    }

    this._validated = true;
    return true;
  }

  get(path) {
    const config = this._loadEnv();
    const keys = path.split('.');
    let value = config;

    for (const key of keys) {
      if (value && typeof value === 'object' && key in value) {
        value = value[key];
      } else {
        return undefined;
      }
    }

    return value;
  }

  getDatabase() {
    return this._loadEnv().database;
  }

  getRedis() {
    return this._loadEnv().redis;
  }

  getProxy() {
    return this._loadEnv().proxy;
  }

  getBrowser() {
    return this._loadEnv().browser;
  }

  getHarvester() {
    return this._loadEnv().harvester;
  }

  getLogging() {
    return this._loadEnv().logging;
  }

  getEnvironment() {
    return this._loadEnv().environment;
  }

  isProduction() {
    return this.getEnvironment().isProduction;
  }

  isDevelopment() {
    return !this.isProduction();
  }

  isDocker() {
    return this.getEnvironment().dockerEnv;
  }

  toJSON() {
    const config = this._loadEnv();
    const sanitized = JSON.parse(JSON.stringify(config));

    if (sanitized.database?.password) {
      sanitized.database.password = '***';
    }
    if (sanitized.redis?.password) {
      sanitized.redis.password = '***';
    }

    return sanitized;
  }
}

const instance = new TitanConfig();

module.exports = {
  TitanConfig,
  titanConfig: instance,
  validateConfig: () => instance.validateConfig(),
  getConfig: (path) => instance.get(path),
  getDatabase: () => instance.getDatabase(),
  getRedis: () => instance.getRedis(),
  getProxy: () => instance.getProxy(),
  getBrowser: () => instance.getBrowser(),
  getHarvester: () => instance.getHarvester(),
  getLogging: () => instance.getLogging(),
  getEnvironment: () => instance.getEnvironment()
};
