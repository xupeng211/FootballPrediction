import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';

interface QualityMetrics {
  timestamp: string;
  overall_score: number;
  coverage_percentage: number;
  code_quality_score: number;
  security_score: number;
  ruff_errors: number;
  mypy_errors: number;
  file_count: number;
  tests_run: number;
  tests_passed: number;
  improvement_cycles: number;
  success_rate: number;
}

interface WebSocketContextType {
  metrics: QualityMetrics | null;
  isConnected: boolean;
  lastUpdate: string | null;
  triggerQualityCheck: () => Promise<void>;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

interface WebSocketProviderProps {
  children: ReactNode;
}

export const WebSocketProvider: React.FC<WebSocketProviderProps> = ({ children }) => {
  const [metrics, setMetrics] = useState<QualityMetrics | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<string | null>(null);
  const [ws, setWs] = useState<WebSocket | null>(null);

  useEffect(() => {
    const connectWebSocket = () => {
      try {
        const websocket = new WebSocket('ws://localhost:8001/ws');

        websocket.onopen = () => {
          console.log('WebSocket连接已建立');
          setIsConnected(true);
        };

        websocket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            setMetrics(data);
            setLastUpdate(new Date().toISOString());
          } catch (error) {
            console.error('解析WebSocket消息失败:', error);
          }
        };

        websocket.onclose = () => {
          console.log('WebSocket连接已关闭');
          setIsConnected(false);
          // 5秒后尝试重连
          setTimeout(connectWebSocket, 5000);
        };

        websocket.onerror = (error) => {
          console.error('WebSocket错误:', error);
          setIsConnected(false);
        };

        setWs(websocket);

        return () => {
          websocket.close();
        };
      } catch (error) {
        console.error('创建WebSocket连接失败:', error);
        // 5秒后尝试重连
        setTimeout(connectWebSocket, 5000);
      }
    };

    connectWebSocket();

    // 页面卸载时关闭连接
    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, []);

  const triggerQualityCheck = async (): Promise<void> => {
    try {
      const response = await fetch('/api/quality/trigger-check', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        console.log('质量检查已触发');
      } else {
        console.error('触发质量检查失败');
      }
    } catch (error) {
      console.error('触发质量检查时发生错误:', error);
    }
  };

  const contextValue: WebSocketContextType = {
    metrics,
    isConnected,
    lastUpdate,
    triggerQualityCheck,
  };

  return (
    <WebSocketContext.Provider value={contextValue}>
      {children}
    </WebSocketContext.Provider>
  );
};

export const useWebSocket = (): WebSocketContextType => {
  const context = useContext(WebSocketContext);
  if (context === undefined) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
};
