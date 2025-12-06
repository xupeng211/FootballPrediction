/**
 * WebSocket React Hook - 足球预测系统实时通信
 *
 * WebSocket React Hook - Football Prediction System Real-time Communication
 *
 * 提供React组件中使用的WebSocket功能
 * Provides WebSocket functionality for React components
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import {
  WebSocketService,
  WebSocketConfig,
  RealtimeEvent,
  ConnectionStatus,
  EventHandler,
  WebSocketStats,
  WEBSOCKET_ENDPOINTS,
  EVENT_TYPES
} from '../services/websocket';

export interface UseWebSocketOptions extends Partial<WebSocketConfig> {
  autoConnect?: boolean;
  endpoint?: keyof typeof WEBSOCKET_ENDPOINTS | string;
}

export interface UseWebSocketReturn {
  service: WebSocketService | null;
  isConnected: boolean;
  connectionStatus: ConnectionStatus | null;
  stats: WebSocketStats | null;
  error: Error | null;
  connect: () => Promise<void>;
  disconnect: () => void;
  subscribe: (eventTypes: string[], filters?: Record<string, any>) => boolean;
  unsubscribe: (eventTypes: string[]) => boolean;
  sendHeartbeat: () => boolean;
  getStats: () => boolean;
  getSubscriptions: () => boolean;
  lastEvent: RealtimeEvent | null;
}

/**
 * WebSocket React Hook
 */
export function useWebSocket(options: UseWebSocketOptions = {}): UseWebSocketReturn {
  const {
    autoConnect = true,
    endpoint = 'GENERAL',
    userId,
    sessionId,
    token,
    reconnectAttempts = 5,
    reconnectInterval = 3000,
    heartbeatInterval = 30000
  } = options;

  // 状态管理
  const [service, setService] = useState<WebSocketService | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus | null>(null);
  const [stats, setStats] = useState<WebSocketStats | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [lastEvent, setLastEvent] = useState<RealtimeEvent | null>(null);

  // Refs to avoid stale closures
  const serviceRef = useRef<WebSocketService | null>(null);
  const mountedRef = useRef(true);

  // 构建WebSocket URL
  const buildWebSocketUrl = useCallback(() => {
    // 优先使用指定的WebSocket URL
    const wsBaseUrl = process.env.REACT_APP_WS_URL ||
      process.env.REACT_APP_API_URL ||
      (typeof window !== 'undefined' ? window.location.origin : 'http://localhost:8000');

    const wsUrl = wsBaseUrl.replace(/^http/, 'ws');
    const endpointPath = typeof endpoint === 'string'
      ? endpoint
      : WEBSOCKET_ENDPOINTS[endpoint];

    const fullUrl = `${wsUrl}${endpointPath}`;

    // 验证URL格式
    try {
      new URL(fullUrl);
      console.log('Connecting to WebSocket:', fullUrl);
      return fullUrl;
    } catch (error) {
      console.warn('Invalid WebSocket URL constructed:', fullUrl, error);
      // 返回一个安全的默认URL
      return 'ws://localhost:8000/api/v1/realtime/ws';
    }
  }, [endpoint]);

  // 创建WebSocket服务
  const createService = useCallback(() => {
    const config: WebSocketConfig = {
      url: buildWebSocketUrl(),
      userId,
      sessionId,
      token,
      reconnectAttempts,
      reconnectInterval,
      heartbeatInterval
    };

    const wsService = new WebSocketService(config);

    // 设置事件处理器
    wsService.addConnectionStatusHandler((status) => {
      if (mountedRef.current) {
        setIsConnected(status.status === 'connected');
        setConnectionStatus(status);
        setError(null);
      }
    });

    wsService.addErrorHandler((err) => {
      if (mountedRef.current) {
        setError(err);
      }
    });

    wsService.addEventHandler(EVENT_TYPES.SYSTEM_STATUS, (event) => {
      if (mountedRef.current && event.data.websocket) {
        setStats(event.data.websocket);
      }
    });

    // 通用事件处理器
    wsService.addEventHandler('*', (event) => {
      if (mountedRef.current) {
        setLastEvent(event);
      }
    });

    return wsService;
  }, [buildWebSocketUrl, userId, sessionId, token, reconnectAttempts, reconnectInterval, heartbeatInterval]);

  // 连接WebSocket
  const connect = useCallback(async () => {
    if (!serviceRef.current) {
      const wsService = createService();
      serviceRef.current = wsService;
      setService(wsService);
    }

    if (serviceRef.current) {
      try {
        await serviceRef.current.connect();
      } catch (err) {
        if (mountedRef.current) {
          console.warn('WebSocket connection failed, falling back to HTTP polling:', err);
          setError(err as Error);
          // 不阻止应用运行，只是记录错误
        }
      }
    }
  }, [createService]);

  // 断开连接
  const disconnect = useCallback(() => {
    if (serviceRef.current) {
      serviceRef.current.disconnect();
    }
  }, []);

  // 订阅事件
  const subscribe = useCallback((eventTypes: string[], filters?: Record<string, any>) => {
    return serviceRef.current?.subscribe(eventTypes, filters) || false;
  }, []);

  // 取消订阅
  const unsubscribe = useCallback((eventTypes: string[]) => {
    return serviceRef.current?.unsubscribe(eventTypes) || false;
  }, []);

  // 发送心跳
  const sendHeartbeat = useCallback(() => {
    return serviceRef.current?.sendHeartbeat() || false;
  }, []);

  // 获取统计信息
  const getStats = useCallback(() => {
    return serviceRef.current?.getStats() || false;
  }, []);

  // 获取订阅信息
  const getSubscriptions = useCallback(() => {
    return serviceRef.current?.getSubscriptions() || false;
  }, []);

  // 初始化和清理
  useEffect(() => {
    mountedRef.current = true;

    // 检查是否应该禁用WebSocket（用于不支持WebSocket的后端）
    const disableWebSocket = process.env.REACT_APP_DISABLE_WS === 'true';

    if (autoConnect && !disableWebSocket) {
      connect();
    } else if (disableWebSocket) {
      console.info('WebSocket is disabled via REACT_APP_DISABLE_WS=true');
      setConnectionStatus({
        status: 'disconnected',
        message: 'WebSocket disabled',
        timestamp: new Date().toISOString()
      });
    }

    return () => {
      mountedRef.current = false;
      if (serviceRef.current) {
        serviceRef.current.disconnect();
      }
    };
  }, [autoConnect, connect]);

  return {
    service,
    isConnected,
    connectionStatus,
    stats,
    error,
    connect,
    disconnect,
    subscribe,
    unsubscribe,
    sendHeartbeat,
    getStats,
    getSubscriptions,
    lastEvent
  };
}

/**
 * 专门用于预测事件的Hook
 */
export function usePredictionsWebSocket(matchIds?: number[], minConfidence?: number) {
  const result = useWebSocket({
    endpoint: 'PREDICTIONS',
    autoConnect: true
  });

  // 自动订阅预测事件
  useEffect(() => {
    if (result.isConnected) {
      const eventTypes = [
        EVENT_TYPES.PREDICTION_CREATED,
        EVENT_TYPES.PREDICTION_UPDATED,
        EVENT_TYPES.PREDICTION_COMPLETED
      ];

      const filters: Record<string, any> = {};
      if (matchIds && matchIds.length > 0) {
        filters.match_ids = matchIds;
      }
      if (minConfidence) {
        filters.min_confidence = minConfidence;
      }

      result.subscribe(eventTypes, filters);
    }
  }, [result.isConnected, matchIds, minConfidence, result.subscribe]);

  return result;
}

/**
 * 专门用于比赛事件的Hook
 */
export function useMatchesWebSocket(matchIds?: number[], leagues?: string[]) {
  const result = useWebSocket({
    endpoint: 'MATCHES',
    autoConnect: true
  });

  // 自动订阅比赛事件
  useEffect(() => {
    if (result.isConnected) {
      const eventTypes = [
        EVENT_TYPES.MATCH_STARTED,
        EVENT_TYPES.MATCH_SCORE_CHANGED,
        EVENT_TYPES.MATCH_STATUS_CHANGED,
        EVENT_TYPES.MATCH_ENDED
      ];

      const filters: Record<string, any> = {};
      if (matchIds && matchIds.length > 0) {
        filters.match_ids = matchIds;
      }
      if (leagues && leagues.length > 0) {
        filters.leagues = leagues;
      }

      result.subscribe(eventTypes, filters);
    }
  }, [result.isConnected, matchIds, leagues, result.subscribe]);

  return result;
}

/**
 * 通用实时事件Hook
 */
export function useRealtimeEvent<T = any>(
  eventType: string,
  handler: (event: RealtimeEvent & { data: T }) => void,
  dependencies: any[] = []
) {
  const ws = useWebSocket();

  useEffect(() => {
    if (ws.service) {
      const wrappedHandler: EventHandler = (event) => {
        if (event.event_type === eventType) {
          handler(event as RealtimeEvent & { data: T });
        }
      };

      ws.service.addEventHandler(eventType, wrappedHandler);

      return () => {
        ws.service?.removeEventHandler(eventType, wrappedHandler);
      };
    }
  }, [ws.service, eventType, handler, ...dependencies]);

  return ws;
}

/**
 * 连接状态Hook
 */
export function useConnectionStatus() {
  const ws = useWebSocket();
  return {
    isConnected: ws.isConnected,
    status: ws.connectionStatus,
    error: ws.error,
    reconnect: ws.connect
  };
}
