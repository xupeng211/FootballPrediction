/**
 * WebSocket服务 - 管理实时质量监控的WebSocket连接
 * WebSocket Service - Manage real-time quality monitoring connection
 */

import { useState, useEffect, useRef, useCallback } from 'react';

const CONNECTION_STATES = {
  Connecting: 'Connecting',
  Open: 'Connected',
  Closing: 'Closing',
  Closed: 'Disconnected'
};

export const useWebSocket = (url) => {
  const [connectionStatus, setConnectionStatus] = useState('Connecting');
  const [lastMessage, setLastMessage] = useState(null);
  const [error, setError] = useState(null);
  const websocket = useRef(null);
  const reconnectTimer = useRef(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;
  const reconnectDelay = 3000; // 3秒

  const connect = useCallback(() => {
    try {
      // 清理之前的连接
      if (websocket.current) {
        websocket.current.close();
      }

      setConnectionStatus('Connecting');
      setError(null);

      websocket.current = new WebSocket(url);

      websocket.current.onopen = () => {
        console.log('WebSocket连接已建立');
        setConnectionStatus('Connected');
        reconnectAttempts.current = 0;

        // 发送初始请求
        if (websocket.current) {
          websocket.current.send(JSON.stringify({
            type: 'request_metrics'
          }));
        }
      };

      websocket.current.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          setLastMessage({
            data: event.data,
            timestamp: new Date(),
            parsed: message
          });
        } catch (parseError) {
          console.error('解析WebSocket消息失败:', parseError);
          setLastMessage({
            data: event.data,
            timestamp: new Date(),
            parsed: null,
            error: parseError.message
          });
        }
      };

      websocket.current.onclose = (event) => {
        console.log('WebSocket连接已关闭:', event.code, event.reason);
        setConnectionStatus('Disconnected');

        // 自动重连逻辑
        if (reconnectAttempts.current < maxReconnectAttempts && event.code !== 1000) {
          reconnectAttempts.current++;
          console.log(`尝试重连 (${reconnectAttempts.current}/${maxReconnectAttempts})...`);

          reconnectTimer.current = setTimeout(() => {
            connect();
          }, reconnectDelay * reconnectAttempts.current);
        } else if (reconnectAttempts.current >= maxReconnectAttempts) {
          setError('WebSocket连接失败，已达到最大重试次数');
        }
      };

      websocket.current.onerror = (event) => {
        console.error('WebSocket错误:', event);
        setError('WebSocket连接错误');
        setConnectionStatus('Error');
      };

    } catch (connectionError) {
      console.error('创建WebSocket连接失败:', connectionError);
      setError(connectionError.message);
      setConnectionStatus('Error');
    }
  }, [url]);

  useEffect(() => {
    connect();

    return () => {
      // 清理连接和定时器
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current);
      }
      if (websocket.current) {
        websocket.current.close(1000, 'Component unmounted');
      }
    };
  }, [connect]);

  const sendMessage = useCallback((message) => {
    if (websocket.current && websocket.current.readyState === WebSocket.OPEN) {
      try {
        const messageStr = typeof message === 'string' ? message : JSON.stringify(message);
        websocket.current.send(messageStr);
        return true;
      } catch (error) {
        console.error('发送WebSocket消息失败:', error);
        setError(error.message);
        return false;
      }
    } else {
      console.warn('WebSocket未连接，无法发送消息');
      return false;
    }
  }, []);

  const ping = useCallback(() => {
    return sendMessage({ type: 'ping' });
  }, [sendMessage]);

  const requestMetrics = useCallback(() => {
    return sendMessage({ type: 'request_metrics' });
  }, [sendMessage]);

  // 心跳检测
  useEffect(() => {
    if (connectionStatus === 'Connected') {
      const pingInterval = setInterval(() => {
        ping();
      }, 30000); // 每30秒发送一次心跳

      return () => clearInterval(pingInterval);
    }
  }, [connectionStatus, ping]);

  return {
    connectionStatus,
    lastMessage,
    error,
    sendMessage,
    ping,
    requestMetrics,
    reconnect: connect,
    isConnected: connectionStatus === 'Connected'
  };
};

export class WebSocketManager {
  constructor(url) {
    this.url = url;
    this.callbacks = new Map();
    this.websocket = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 3000;
  }

  connect() {
    return new Promise((resolve, reject) => {
      try {
        this.websocket = new WebSocket(this.url);

        this.websocket.onopen = () => {
          console.log('WebSocket管理器连接已建立');
          this.reconnectAttempts = 0;
          this.emit('connected');
          resolve();
        };

        this.websocket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            this.emit('message', data);
          } catch (error) {
            console.error('解析消息失败:', error);
            this.emit('error', error);
          }
        };

        this.websocket.onclose = () => {
          console.log('WebSocket连接已关闭');
          this.emit('disconnected');
          this.attemptReconnect();
        };

        this.websocket.onerror = (error) => {
          console.error('WebSocket错误:', error);
          this.emit('error', error);
          reject(error);
        };

      } catch (error) {
        reject(error);
      }
    });
  }

  disconnect() {
    if (this.websocket) {
      this.websocket.close(1000, 'Manual disconnect');
      this.websocket = null;
    }
  }

  send(message) {
    if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
      const messageStr = typeof message === 'string' ? message : JSON.stringify(message);
      this.websocket.send(messageStr);
      return true;
    }
    return false;
  }

  on(event, callback) {
    if (!this.callbacks.has(event)) {
      this.callbacks.set(event, []);
    }
    this.callbacks.get(event).push(callback);
  }

  off(event, callback) {
    if (this.callbacks.has(event)) {
      const callbacks = this.callbacks.get(event);
      const index = callbacks.indexOf(callback);
      if (index > -1) {
        callbacks.splice(index, 1);
      }
    }
  }

  emit(event, data) {
    if (this.callbacks.has(event)) {
      this.callbacks.get(event).forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error(`执行回调函数失败 (${event}):`, error);
        }
      });
    }
  }

  attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);

      setTimeout(() => {
        this.connect().catch(error => {
          console.error('重连失败:', error);
        });
      }, this.reconnectDelay * this.reconnectAttempts);
    } else {
      console.error('已达到最大重试次数，停止重连');
      this.emit('maxReconnectAttemptsReached');
    }
  }

  getConnectionState() {
    if (!this.websocket) return 'Disconnected';
    switch (this.websocket.readyState) {
      case WebSocket.CONNECTING: return 'Connecting';
      case WebSocket.OPEN: return 'Connected';
      case WebSocket.CLOSING: return 'Closing';
      case WebSocket.CLOSED: return 'Disconnected';
      default: return 'Unknown';
    }
  }

  isConnected() {
    return this.getConnectionState() === 'Connected';
  }
}

export default { useWebSocket, WebSocketManager, CONNECTION_STATES };