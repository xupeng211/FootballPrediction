/**
 * WebSocket服务 - 足球预测系统实时通信
 *
 * WebSocket Service - Football Prediction System Real-time Communication
 *
 * 提供完整的WebSocket客户端功能，包括：
 * 连接管理、事件订阅、消息处理、重连机制
 */

export interface WebSocketConfig {
  url: string;
  userId?: string;
  sessionId?: string;
  token?: string;
  protocols?: string[];
  reconnectAttempts?: number;
  reconnectInterval?: number;
  heartbeatInterval?: number;
}

export interface SubscriptionRequest {
  type: 'subscribe';
  data: {
    subscription_type?: string;
    event_types: string[];
    filters?: Record<string, any>;
  };
}

export interface UnsubscribeRequest {
  type: 'unsubscribe';
  data: {
    event_types: string[];
  };
}

export interface HeartbeatRequest {
  type: 'heartbeat';
}

export interface GetStatsRequest {
  type: 'get_stats';
}

export interface GetSubscriptionsRequest {
  type: 'get_subscriptions';
}

export type WebSocketMessage =
  | SubscriptionRequest
  | UnsubscribeRequest
  | HeartbeatRequest
  | GetStatsRequest
  | GetSubscriptionsRequest;

export interface RealtimeEvent {
  event_type: string;
  data: Record<string, any>;
  timestamp: string;
  source?: string;
  correlation_id?: string;
}

export interface ConnectionStatus {
  status: 'connected' | 'disconnected' | 'connecting' | 'error';
  connectionId?: string;
  userId?: string;
  message?: string;
  timestamp: string;
}

export interface WebSocketStats {
  total_connections: number;
  total_users: number;
  total_rooms: number;
  total_subscriptions: number;
  connections_by_room: Record<string, number>;
  users_by_connection_count: Record<string, number>;
}

export type EventHandler = (event: RealtimeEvent) => void;
export type ConnectionStatusHandler = (status: ConnectionStatus) => void;
export type ErrorHandler = (error: Error) => void;

export class WebSocketService {
  private ws: WebSocket | null = null;
  private config: WebSocketConfig;
  private reconnectAttempts = 0;
  private maxReconnectAttempts: number;
  private reconnectInterval: number;
  private heartbeatInterval: number;
  private heartbeatTimer?: NodeJS.Timeout;
  private reconnectTimer?: NodeJS.Timeout;

  private eventHandlers: Map<string, Set<EventHandler>> = new Map();
  private connectionStatusHandlers: Set<ConnectionStatusHandler> = new Set();
  private errorHandlers: Set<ErrorHandler> = new Set();

  private isManualClose = false;
  private connectionId?: string;

  constructor(config: WebSocketConfig) {
    this.config = {
      reconnectAttempts: 5,
      reconnectInterval: 3000,
      heartbeatInterval: 30000,
      ...config
    };

    this.maxReconnectAttempts = this.config.reconnectAttempts || 5;
    this.reconnectInterval = this.config.reconnectInterval || 3000;
    this.heartbeatInterval = this.config.heartbeatInterval || 30000;
  }

  /**
   * 连接WebSocket
   */
  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.isManualClose = false;
        this.updateConnectionStatus('connecting');

        // 构建WebSocket URL
        const wsUrl = this.buildWebSocketUrl();

        this.ws = new WebSocket(wsUrl, this.config.protocols);

        this.ws.onopen = () => {
          this.onOpen();
          resolve();
        };

        this.ws.onmessage = (event) => {
          this.onMessage(event);
        };

        this.ws.onclose = (event) => {
          this.onClose(event);
        };

        this.ws.onerror = (event) => {
          this.onError(new Error('WebSocket connection error'));
          reject(new Error('WebSocket connection error'));
        };

      } catch (error) {
        this.onError(error as Error);
        reject(error);
      }
    });
  }

  /**
   * 断开连接
   */
  disconnect(): void {
    this.isManualClose = true;
    this.clearTimers();

    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.close(1000, 'Manual disconnect');
    }

    this.ws = null;
    this.updateConnectionStatus('disconnected', 'Manual disconnect');
  }

  /**
   * 发送消息
   */
  send(message: WebSocketMessage): boolean {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket not connected, message not sent:', message);
      return false;
    }

    try {
      this.ws.send(JSON.stringify(message));
      return true;
    } catch (error) {
      console.error('Failed to send WebSocket message:', error);
      this.onError(error as Error);
      return false;
    }
  }

  /**
   * 订阅事件
   */
  subscribe(
    eventTypes: string[],
    filters?: Record<string, any>,
    subscriptionType?: string
  ): boolean {
    return this.send({
      type: 'subscribe',
      data: {
        subscription_type: subscriptionType || 'specific_event',
        event_types: eventTypes,
        filters: filters || {}
      }
    });
  }

  /**
   * 取消订阅事件
   */
  unsubscribe(eventTypes: string[]): boolean {
    return this.send({
      type: 'unsubscribe',
      data: {
        event_types: eventTypes
      }
    });
  }

  /**
   * 发送心跳
   */
  sendHeartbeat(): boolean {
    return this.send({ type: 'heartbeat' });
  }

  /**
   * 获取统计信息
   */
  getStats(): boolean {
    return this.send({ type: 'get_stats' });
  }

  /**
   * 获取订阅信息
   */
  getSubscriptions(): boolean {
    return this.send({ type: 'get_subscriptions' });
  }

  /**
   * 添加事件处理器
   */
  addEventHandler(eventType: string, handler: EventHandler): void {
    if (!this.eventHandlers.has(eventType)) {
      this.eventHandlers.set(eventType, new Set());
    }
    this.eventHandlers.get(eventType)!.add(handler);
  }

  /**
   * 移除事件处理器
   */
  removeEventHandler(eventType: string, handler: EventHandler): void {
    const handlers = this.eventHandlers.get(eventType);
    if (handlers) {
      handlers.delete(handler);
      if (handlers.size === 0) {
        this.eventHandlers.delete(eventType);
      }
    }
  }

  /**
   * 添加连接状态处理器
   */
  addConnectionStatusHandler(handler: ConnectionStatusHandler): void {
    this.connectionStatusHandlers.add(handler);
  }

  /**
   * 移除连接状态处理器
   */
  removeConnectionStatusHandler(handler: ConnectionStatusHandler): void {
    this.connectionStatusHandlers.delete(handler);
  }

  /**
   * 添加错误处理器
   */
  addErrorHandler(handler: ErrorHandler): void {
    this.errorHandlers.add(handler);
  }

  /**
   * 移除错误处理器
   */
  removeErrorHandler(handler: ErrorHandler): void {
    this.errorHandlers.delete(handler);
  }

  /**
   * 获取连接状态
   */
  getConnectionStatus(): 'connecting' | 'connected' | 'disconnected' {
    if (!this.ws) return 'disconnected';

    switch (this.ws.readyState) {
      case WebSocket.CONNECTING: return 'connecting';
      case WebSocket.OPEN: return 'connected';
      case WebSocket.CLOSING:
      case WebSocket.CLOSED:
      default: return 'disconnected';
    }
  }

  /**
   * 获取连接ID
   */
  getConnectionId(): string | undefined {
    return this.connectionId;
  }

  private buildWebSocketUrl(): string {
    const url = new URL(this.config.url);

    // 添加查询参数
    if (this.config.userId) {
      url.searchParams.set('user_id', this.config.userId);
    }
    if (this.config.sessionId) {
      url.searchParams.set('session_id', this.config.sessionId);
    }
    if (this.config.token) {
      url.searchParams.set('token', this.config.token);
    }

    return url.toString();
  }

  private onOpen(): void {
    console.log('WebSocket connected');
    this.reconnectAttempts = 0;
    this.updateConnectionStatus('connected');
    this.startHeartbeat();
  }

  private onMessage(event: MessageEvent): void {
    try {
      const data = JSON.parse(event.data);

      // 处理连接状态消息
      if (data.event_type === 'connection_status') {
        this.handleConnectionStatusMessage(data);
        return;
      }

      // 触发事件处理器
      const realtimeEvent: RealtimeEvent = data;
      this.triggerEventHandlers(realtimeEvent);

    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
    }
  }

  private onClose(event: CloseEvent): void {
    console.log('WebSocket disconnected:', event.code, event.reason);
    this.clearTimers();
    this.updateConnectionStatus('disconnected', `Connection closed: ${event.reason}`);

    // 自动重连（除非是手动关闭）
    if (!this.isManualClose && this.reconnectAttempts < this.maxReconnectAttempts) {
      this.scheduleReconnect();
    }
  }

  private onError(error: Error): void {
    console.error('WebSocket error:', error);
    this.triggerErrorHandlers(error);
  }

  private handleConnectionStatusMessage(data: any): void {
    if (data.data.connection_id) {
      this.connectionId = data.data.connection_id;
    }

    this.updateConnectionStatus('connected', data.data.message, data.data);
  }

  private triggerEventHandlers(event: RealtimeEvent): void {
    const handlers = this.eventHandlers.get(event.event_type);
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(event);
        } catch (error) {
          console.error('Error in event handler:', error);
        }
      });
    }
  }

  private triggerErrorHandlers(error: Error): void {
    this.errorHandlers.forEach(handler => {
      try {
        handler(error);
      } catch (handlerError) {
        console.error('Error in error handler:', handlerError);
      }
    });
  }

  private updateConnectionStatus(
    status: ConnectionStatus['status'],
    message?: string,
    data?: any
  ): void {
    const statusData: ConnectionStatus = {
      status,
      connectionId: this.connectionId,
      userId: this.config.userId,
      message,
      timestamp: new Date().toISOString(),
      ...data
    };

    this.connectionStatusHandlers.forEach(handler => {
      try {
        handler(statusData);
      } catch (error) {
        console.error('Error in connection status handler:', error);
      }
    });
  }

  private startHeartbeat(): void {
    this.clearTimers();
    this.heartbeatTimer = setInterval(() => {
      this.sendHeartbeat();
    }, this.heartbeatInterval);
  }

  private clearTimers(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = undefined;
    }
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = undefined;
    }
  }

  private scheduleReconnect(): void {
    this.reconnectAttempts++;
    console.log(`Scheduling reconnect attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);

    this.reconnectTimer = setTimeout(() => {
      this.updateConnectionStatus('connecting', `Reconnecting... (attempt ${this.reconnectAttempts})`);
      this.connect().catch(error => {
        console.error('Reconnect failed:', error);
      });
    }, this.reconnectInterval);
  }
}

/**
 * 创建WebSocket服务实例的便捷函数
 */
export function createWebSocketService(config: WebSocketConfig): WebSocketService {
  // 确保URL以ws://或wss://开头
  let url = config.url;
  if (!url.startsWith('ws://') && !url.startsWith('wss://')) {
    // 如果是HTTP/HTTPS URL，转换为WebSocket URL
    if (url.startsWith('http://')) {
      url = url.replace('http://', 'ws://');
    } else if (url.startsWith('https://')) {
      url = url.replace('https://', 'wss://');
    } else {
      // 默认使用ws://
      url = `ws://${url}`;
    }
  }

  return new WebSocketService({ ...config, url });
}

/**
 * 预设的WebSocket配置
 */
export const WEBSOCKET_ENDPOINTS = {
  // 通用WebSocket端点
  GENERAL: '/api/v1/realtime/ws',

  // 预测专用WebSocket端点
  PREDICTIONS: '/api/v1/realtime/ws/predictions',

  // 比赛专用WebSocket端点
  MATCHES: '/api/v1/realtime/ws/matches'
} as const;

/**
 * 事件类型常量
 */
export const EVENT_TYPES = {
  CONNECTION_STATUS: 'connection_status',
  PREDICTION_CREATED: 'prediction_created',
  PREDICTION_UPDATED: 'prediction_updated',
  PREDICTION_COMPLETED: 'prediction_completed',
  MATCH_STARTED: 'match_started',
  MATCH_SCORE_CHANGED: 'match_score_changed',
  MATCH_STATUS_CHANGED: 'match_status_changed',
  MATCH_ENDED: 'match_ended',
  ODDS_UPDATED: 'odds_updated',
  ODDS_SIGNIFICANT_CHANGE: 'odds_significant_change',
  SYSTEM_ALERT: 'system_alert',
  SYSTEM_STATUS: 'system_status',
  USER_SUBSCRIPTION_CHANGED: 'user_subscription_changed',
  DATA_REFRESH: 'data_refresh',
  ANALYTICS_UPDATED: 'analytics_updated'
} as const;