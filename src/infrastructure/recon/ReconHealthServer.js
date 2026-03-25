/**
 * ReconHealthServer - 健康检查服务器
 * ==================================
 *
 * 职责: 暴露 HTTP 健康检查端点供 Kubernetes/Docker 使用
 * 端点:
 * - GET /health/live: Liveness Probe - 进程存活检查
 * - GET /health/ready: Readiness Probe - 依赖就绪检查
 * - GET /metrics: Prometheus 指标导出
 *
 * @module infrastructure/recon/ReconHealthServer
 * @version V6.7-OBSERVABILITY
 * @date 2026-03-22
 */

'use strict';

const http = require('http');
const url = require('url');

/**
 * 健康检查服务器类
 * @class ReconHealthServer
 */
class ReconHealthServer {
  /**
   * 创建健康检查服务器
   * @param {Object} options - 配置选项
   * @param {number} options.port - 监听端口 (默认: 8080)
   * @param {Object} options.metrics - ReconMetrics 实例
   * @param {Object} options.logger - 结构化日志器
   */
  constructor(options = {}) {
    this.port = options.port || 8080;
    this.metrics = options.metrics;
    this.logger = options.logger || console;

    this.checks = new Map();
    this.server = null;
    this.isRunning = false;

    // 注册默认检查
    this.registerDefaultChecks();

    this.logger.info('health_server_initialized', { port: this.port });
  }

  /**
   * 注册默认健康检查
   * @private
   */
  registerDefaultChecks() {
    // 基础存活检查
    this.registerCheck('liveness', async () => ({
      ready: true,
      pid: process.pid,
      uptime: process.uptime(),
      memory: process.memoryUsage()
    }));
  }

  /**
   * 注册自定义健康检查
   * @param {string} name - 检查名称
   * @param {Function} fn - 检查函数，返回 Promise<{ ready: boolean, ... }>
   */
  registerCheck(name, fn) {
    this.checks.set(name, fn);
    this.logger.debug('health_check_registered', { name });
  }

  /**
   * 移除健康检查
   * @param {string} name - 检查名称
   */
  unregisterCheck(name) {
    this.checks.delete(name);
    this.logger.debug('health_check_unregistered', { name });
  }

  /**
   * 启动健康检查服务器
   * @returns {Promise<void>}
   */
  async start() {
    if (this.isRunning) {
      this.logger.warn('health_server_already_running');
      return;
    }

    this.server = http.createServer((req, res) => {
      this.handleRequest(req, res);
    });

    return new Promise((resolve, reject) => {
      this.server.listen(this.port, (err) => {
        if (err) {
          this.logger.error('health_server_start_failed', { error: err.message });
          reject(err);
          return;
        }

        this.isRunning = true;
        this.logger.info('health_server_started', { port: this.port });
        resolve();
      });
    });
  }

  /**
   * 停止健康检查服务器
   * @returns {Promise<void>}
   */
  async stop() {
    if (!this.isRunning || !this.server) {
      return;
    }

    return new Promise((resolve) => {
      this.server.close(() => {
        this.isRunning = false;
        this.logger.info('health_server_stopped');
        resolve();
      });
    });
  }

  /**
   * 处理 HTTP 请求
   * @param {http.IncomingMessage} req - 请求对象
   * @param {http.ServerResponse} res - 响应对象
   * @private
   */
  async handleRequest(req, res) {
    const parsedUrl = url.parse(req.url, true);
    const pathname = parsedUrl.pathname;

    // 设置 CORS 头
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
    res.setHeader('Content-Type', 'application/json');

    if (req.method === 'OPTIONS') {
      res.writeHead(200);
      res.end();
      return;
    }

    try {
      switch (pathname) {
        case '/health/live':
          await this.handleLiveness(req, res);
          break;
        case '/health/ready':
          await this.handleReadiness(req, res);
          break;
        case '/metrics':
          await this.handleMetrics(req, res);
          break;
        case '/health':
          await this.handleHealth(req, res);
          break;
        default:
          this.handleNotFound(req, res);
      }
    } catch (e) {
      this.logger.error('health_request_error', {
        path: pathname,
        error: e.message
      });

      res.writeHead(500);
      res.end(JSON.stringify({
        status: 'error',
        message: e.message
      }));
    }
  }

  /**
   * 处理存活检查 (Liveness Probe)
   * @param {http.IncomingMessage} req - 请求对象
   * @param {http.ServerResponse} res - 响应对象
   * @private
   */
  async handleLiveness(req, res) {
    const check = this.checks.get('liveness');
    let result = { ready: true, pid: process.pid };

    if (check) {
      try {
        result = await check();
      } catch (e) {
        result = { ready: false, error: e.message };
      }
    }

    const statusCode = result.ready ? 200 : 503;

    res.writeHead(statusCode);
    res.end(JSON.stringify({
      status: result.ready ? 'ok' : 'error',
      timestamp: new Date().toISOString(),
      ...result
    }));
  }

  /**
   * 处理就绪检查 (Readiness Probe)
   * @param {http.IncomingMessage} req - 请求对象
   * @param {http.ServerResponse} res - 响应对象
   * @private
   */
  async handleReadiness(req, res) {
    const results = [];
    let allReady = true;

    for (const [name, check] of this.checks) {
      if (name === 'liveness') continue; // 跳过存活检查

      try {
        const result = await check();
        results.push({ name, ...result });
        if (!result.ready) {
          allReady = false;
        }
      } catch (e) {
        results.push({ name, ready: false, error: e.message });
        allReady = false;
      }
    }

    const statusCode = allReady ? 200 : 503;

    res.writeHead(statusCode);
    res.end(JSON.stringify({
      status: allReady ? 'ready' : 'not_ready',
      timestamp: new Date().toISOString(),
      checks: results
    }));
  }

  /**
   * 处理指标导出
   * @param {http.IncomingMessage} req - 请求对象
   * @param {http.ServerResponse} res - 响应对象
   * @private
   */
  async handleMetrics(req, res) {
    if (!this.metrics) {
      res.writeHead(503);
      res.end(JSON.stringify({
        status: 'error',
        message: 'Metrics not available'
      }));
      return;
    }

    try {
      const metricsData = await this.metrics.getMetrics();

      res.setHeader('Content-Type', 'text/plain');
      res.writeHead(200);
      res.end(metricsData);
    } catch (e) {
      res.writeHead(500);
      res.end(JSON.stringify({
        status: 'error',
        message: e.message
      }));
    }
  }

  /**
   * 处理综合健康检查
   * @param {http.IncomingMessage} req - 请求对象
   * @param {http.ServerResponse} res - 响应对象
   * @private
   */
  async handleHealth(req, res) {
    const liveness = await this.checks.get('liveness')?.().catch(() => ({ ready: false }));

    const readinessResults = [];
    let ready = true;

    for (const [name, check] of this.checks) {
      if (name === 'liveness') continue;

      try {
        const result = await check();
        readinessResults.push({ name, ...result });
        if (!result.ready) ready = false;
      } catch (e) {
        readinessResults.push({ name, ready: false, error: e.message });
        ready = false;
      }
    }

    const statusCode = liveness?.ready ? 200 : 503;

    res.writeHead(statusCode);
    res.end(JSON.stringify({
      status: liveness?.ready ? (ready ? 'healthy' : 'degraded') : 'unhealthy',
      timestamp: new Date().toISOString(),
      liveness: liveness?.ready,
      readiness: ready,
      checks: readinessResults
    }));
  }

  /**
   * 处理 404
   * @param {http.IncomingMessage} req - 请求对象
   * @param {http.ServerResponse} res - 响应对象
   * @private
   */
  handleNotFound(req, res) {
    res.writeHead(404);
    res.end(JSON.stringify({
      status: 'not_found',
      message: `Path ${req.url} not found`,
      available_endpoints: [
        '/health/live',
        '/health/ready',
        '/health',
        '/metrics'
      ]
    }));
  }

  /**
   * 注册数据库健康检查
   * @param {Object} repository - Repository 实例
   */
  registerDatabaseCheck(repository) {
    this.registerCheck('database', async () => {
      try {
        const start = Date.now();
        // 尝试执行简单查询
        if (repository.dbPool) {
          const client = await repository.dbPool.connect();
          await client.query('SELECT 1');
          client.release();
        }
        const latency = Date.now() - start;

        return {
          ready: true,
          latency: `${latency}ms`
        };
      } catch (e) {
        return {
          ready: false,
          error: e.message
        };
      }
    });

    this.logger.info('database_health_check_registered');
  }

  /**
   * 注册 Redis 健康检查
   * @param {Object} redisClient - Redis 客户端
   */
  registerRedisCheck(redisClient) {
    this.registerCheck('redis', async () => {
      try {
        const start = Date.now();
        await redisClient.ping();
        const latency = Date.now() - start;

        return {
          ready: true,
          latency: `${latency}ms`
        };
      } catch (e) {
        return {
          ready: false,
          error: e.message
        };
      }
    });

    this.logger.info('redis_health_check_registered');
  }

  /**
   * 注册代理池健康检查
   * @param {Object} proxyRotator - ProxyRotator 实例
   */
  registerProxyPoolCheck(proxyRotator) {
    this.registerCheck('proxy_pool', async () => {
      try {
        const stats = proxyRotator.getStats ? proxyRotator.getStats() : { healthy: 0, total: 0 };

        return {
          ready: stats.healthy > 0,
          healthy: stats.healthy,
          total: stats.total,
          ratio: stats.total > 0 ? (stats.healthy / stats.total).toFixed(2) : '0.00'
        };
      } catch (e) {
        return {
          ready: false,
          error: e.message
        };
      }
    });

    this.logger.info('proxy_pool_health_check_registered');
  }

  /**
   * 获取服务器状态
   * @returns {Object} 状态信息
   */
  getStatus() {
    return {
      isRunning: this.isRunning,
      port: this.port,
      checkCount: this.checks.size,
      checks: Array.from(this.checks.keys())
    };
  }
}

module.exports = { ReconHealthServer };
