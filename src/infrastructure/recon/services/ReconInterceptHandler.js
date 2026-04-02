'use strict';

const reconInterceptHandler = {
  attach(page) {
    const targetPage = page || this.page;
    if (!targetPage || typeof targetPage.on !== 'function') {
      return;
    }

    this.detach();
    this.page = targetPage;
    this._responseHandler = async (response) => this.handleResponse(response);
    this._attachedPage = targetPage;
    targetPage.on('response', this._responseHandler);
  },

  detach(page = null) {
    const targetPage = page || this._attachedPage || this.page;
    if (!targetPage || !this._responseHandler) {
      this._responseHandler = null;
      this._attachedPage = null;
      return;
    }

    if (typeof targetPage.off === 'function') {
      try {
        targetPage.off('response', this._responseHandler);
      } catch (_error) {
        // 避免关闭路径抛出二次异常
      }
    }

    this._responseHandler = null;
    this._attachedPage = null;
  },

  async handleResponse(response) {
    try {
      const url = response.url();
      if (!this.isPotentialMatchApi(url)) {
        return;
      }

      this.stats.requestsTotal++;
      this.apiEndpoints.add(url);

      let body;
      try {
        body = await response.text();
      } catch (error) {
        this.logger.warn('[ReconNetworkMonitor] 读取响应体失败', {
          traceId: this.traceId,
          url: url.substring(0, 60),
          error: error.message
        });
        this.stats.requestsFailed++;
        return;
      }

      let data;
      try {
        data = await this.parseApiResponse(body, url);
      } catch (error) {
        this.logger.warn('[ReconNetworkMonitor] 解析响应失败', {
          traceId: this.traceId,
          url: url.substring(0, 60),
          error: error.message
        });
        this.stats.requestsFailed++;
        return;
      }

      if (data && data.length > 0) {
        this.interceptedData.push(...data);
        this.stats.requestsSuccess++;
        this.logger.info('[ReconNetworkMonitor] 数据拦截成功', {
          traceId: this.traceId,
          url: url.substring(0, 60),
          count: data.length
        });
      }
    } catch (error) {
      this.logger.error('[ReconNetworkMonitor] 响应处理异常', {
        traceId: this.traceId,
        error: error.message,
        stack: error.stack?.substring(0, 200)
      });
      this.stats.requestsFailed++;
    }
  },

  isPotentialMatchApi(url) {
    return this.matchApiPatterns.some((pattern) => pattern.test(url));
  }
};

module.exports = { reconInterceptHandler };
