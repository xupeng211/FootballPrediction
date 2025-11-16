/**
 * 实时仪表板组件 - 足球预测系统
 *
 * Realtime Dashboard Component - Football Prediction System
 *
 * 显示实时连接状态、统计数据和事件信息
 * Displays real-time connection status, statistics, and event information
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Badge,
  Tag,
  List,
  Typography,
  Alert,
  Button,
  Space,
  Tooltip,
  Progress,
  Spin,
  Empty,
  Switch
} from 'antd';
import {
  WifiOutlined,
  DisconnectOutlined,
  ReloadOutlined,
  EyeOutlined,
  DatabaseOutlined,
  UserOutlined,
  BellOutlined,
  SettingOutlined
} from '@ant-design/icons';
import { useWebSocket, useConnectionStatus } from '../hooks/useWebSocket';
import { EVENT_TYPES } from '../services/websocket';

const { Text, Title } = Typography;

interface RealtimeDashboardProps {
  userId?: string;
  className?: string;
  height?: number | string;
}

interface EventHistoryItem {
  id: string;
  eventType: string;
  data: any;
  timestamp: string;
  formattedTime: string;
}

const RealtimeDashboard: React.FC<RealtimeDashboardProps> = ({
  userId,
  className,
  height = 600
}) => {
  const [autoScroll, setAutoScroll] = useState(true);
  const [eventHistory, setEventHistory] = useState<EventHistoryItem[]>([]);
  const [showDetails, setShowDetails] = useState(false);

  // WebSocket连接
  const ws = useWebSocket({
    userId,
    autoConnect: true,
    reconnectAttempts: 5,
    reconnectInterval: 3000
  });

  const connectionStatus = useConnectionStatus();

  // 监听实时事件
  useEffect(() => {
    if (ws.service) {
      const handleEvent = (event: any) => {
        const historyItem: EventHistoryItem = {
          id: `${event.timestamp}-${Math.random()}`,
          eventType: event.event_type,
          data: event.data,
          timestamp: event.timestamp,
          formattedTime: new Date(event.timestamp).toLocaleTimeString()
        };

        setEventHistory(prev => {
          const newHistory = [historyItem, ...prev];
          return autoScroll ? newHistory.slice(0, 50) : newHistory.slice(0, 100);
        });
      };

      // 订阅所有系统事件
      ws.service.addEventHandler(EVENT_TYPES.CONNECTION_STATUS, handleEvent);
      ws.service.addEventHandler(EVENT_TYPES.SYSTEM_ALERT, handleEvent);
      ws.service.addEventHandler(EVENT_TYPES.USER_SUBSCRIPTION_CHANGED, handleEvent);
      ws.service.addEventHandler(EVENT_TYPES.ANALYTICS_UPDATED, handleEvent);
      ws.service.addEventHandler(EVENT_TYPES.PREDICTION_CREATED, handleEvent);
      ws.service.addEventHandler(EVENT_TYPES.MATCH_SCORE_CHANGED, handleEvent);
      ws.service.addEventHandler(EVENT_TYPES.ODDS_UPDATED, handleEvent);

      return () => {
        if (ws.service) {
          ws.service.removeEventHandler(EVENT_TYPES.CONNECTION_STATUS, handleEvent);
          ws.service.removeEventHandler(EVENT_TYPES.SYSTEM_ALERT, handleEvent);
          ws.service.removeEventHandler(EVENT_TYPES.USER_SUBSCRIPTION_CHANGED, handleEvent);
          ws.service.removeEventHandler(EVENT_TYPES.ANALYTICS_UPDATED, handleEvent);
          ws.service.removeEventHandler(EVENT_TYPES.PREDICTION_CREATED, handleEvent);
          ws.service.removeEventHandler(EVENT_TYPES.MATCH_SCORE_CHANGED, handleEvent);
          ws.service.removeEventHandler(EVENT_TYPES.ODDS_UPDATED, handleEvent);
        }
      };
    }
  }, [ws.service, autoScroll]);

  // 手动连接/断开
  const toggleConnection = () => {
    if (ws.isConnected) {
      ws.disconnect();
    } else {
      ws.connect();
    }
  };

  // 刷新统计数据
  const refreshStats = () => {
    ws.getStats();
    ws.getSubscriptions();
  };

  // 清空事件历史
  const clearHistory = () => {
    setEventHistory([]);
  };

  // 获取事件类型标签颜色
  const getEventTypeColor = (eventType: string) => {
    const colorMap: Record<string, string> = {
      [EVENT_TYPES.CONNECTION_STATUS]: 'blue',
      [EVENT_TYPES.SYSTEM_ALERT]: 'red',
      [EVENT_TYPES.SYSTEM_STATUS]: 'green',
      [EVENT_TYPES.PREDICTION_CREATED]: 'purple',
      [EVENT_TYPES.PREDICTION_UPDATED]: 'purple',
      [EVENT_TYPES.MATCH_STARTED]: 'orange',
      [EVENT_TYPES.MATCH_SCORE_CHANGED]: 'orange',
      [EVENT_TYPES.MATCH_ENDED]: 'orange',
      [EVENT_TYPES.ODDS_UPDATED]: 'cyan',
      [EVENT_TYPES.USER_SUBSCRIPTION_CHANGED]: 'geekblue',
      [EVENT_TYPES.ANALYTICS_UPDATED]: 'lime'
    };
    return colorMap[eventType] || 'default';
  };

  // 格式化事件数据
  const formatEventData = (data: any) => {
    try {
      return JSON.stringify(data, null, 2);
    } catch {
      return String(data);
    }
  };

  // 获取连接状态文本
  const getConnectionStatusText = () => {
    if (!connectionStatus.status) return '未连接';
    switch (connectionStatus.status as unknown as string) {
      case 'connected': return '已连接';
      case 'connecting': return '连接中...';
      case 'disconnected': return '已断开';
      case 'error': return '连接错误';
      default: return String(connectionStatus.status);
    }
  };

  // 获取连接状态颜色
  const getConnectionStatusColor = () => {
    if (!connectionStatus.status) return 'default';
    switch (connectionStatus.status as unknown as string) {
      case 'connected': return 'success';
      case 'connecting': return 'processing';
      case 'disconnected': return 'default';
      case 'error': return 'error';
      default: return 'default';
    }
  };

  return (
    <div className={className} style={{ height }}>
      <Row gutter={[16, 16]} style={{ height: '100%' }}>
        {/* 连接状态卡片 */}
        <Col xs={24} sm={24} md={8}>
          <Card
            title={
              <Space>
                <WifiOutlined />
                <span>连接状态</span>
                <Badge
                  status={getConnectionStatusColor() as any}
                  text={getConnectionStatusText()}
                />
              </Space>
            }
            extra={
              <Space>
                <Tooltip title={ws.isConnected ? "断开连接" : "重新连接"}>
                  <Button
                    type={ws.isConnected ? "default" : "primary"}
                    size="small"
                    icon={ws.isConnected ? <DisconnectOutlined /> : <ReloadOutlined />}
                    onClick={toggleConnection}
                    loading={(connectionStatus?.status as unknown as string) === 'connecting'}
                  />
                </Tooltip>
                <Tooltip title="刷新统计">
                  <Button
                    size="small"
                    icon={<ReloadOutlined />}
                    onClick={refreshStats}
                    disabled={!ws.isConnected}
                  />
                </Tooltip>
              </Space>
            }
            size="small"
          >
            <Space direction="vertical" style={{ width: '100%' }}>
              {/* 连接信息 */}
              <div>
                <Text type="secondary">连接ID:</Text>
                <Text code copyable>
                  {connectionStatus.status?.connectionId || 'N/A'}
                </Text>
              </div>

              <div>
                <Text type="secondary">用户ID:</Text>
                <Text code>{userId || 'N/A'}</Text>
              </div>

              {connectionStatus.status?.timestamp && (
                <div>
                  <Text type="secondary">连接时间:</Text>
                  <Text>{new Date(connectionStatus.status.timestamp).toLocaleString()}</Text>
                </div>
              )}

              {/* 连接状态进度条 */}
              <div>
                <Text type="secondary">连接质量:</Text>
                <Progress
                  percent={ws.isConnected ? 100 : 0}
                  status={ws.isConnected ? "success" : "exception"}
                  size="small"
                  showInfo={false}
                />
              </div>
            </Space>
          </Card>
        </Col>

        {/* 统计信息卡片 */}
        <Col xs={24} sm={24} md={8}>
          <Card
            title={
              <Space>
                <DatabaseOutlined />
                <span>实时统计</span>
              </Space>
            }
            size="small"
          >
            {ws.stats ? (
              <Space direction="vertical" style={{ width: '100%' }}>
                <Statistic
                  title="总连接数"
                  value={ws.stats.total_connections}
                  prefix={<UserOutlined />}
                  valueStyle={{ fontSize: '16px' }}
                />

                <Statistic
                  title="活跃用户"
                  value={ws.stats.total_users}
                  prefix={<UserOutlined />}
                  valueStyle={{ fontSize: '16px' }}
                />

                <Statistic
                  title="房间数量"
                  value={ws.stats.total_rooms}
                  prefix={<EyeOutlined />}
                  valueStyle={{ fontSize: '16px' }}
                />

                <Statistic
                  title="订阅数量"
                  value={ws.stats.total_subscriptions}
                  prefix={<BellOutlined />}
                  valueStyle={{ fontSize: '16px' }}
                />
              </Space>
            ) : (
              <Empty
                description={ws.isConnected ? "加载统计信息中..." : "请先连接"}
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            )}
          </Card>
        </Col>

        {/* 事件历史卡片 */}
        <Col xs={24} sm={24} md={8}>
          <Card
            title={
              <Space>
                <BellOutlined />
                <span>事件历史</span>
                <Badge count={eventHistory.length} showZero />
              </Space>
            }
            extra={
              <Space>
                <Tooltip title="自动滚动">
                  <Switch
                    size="small"
                    checked={autoScroll}
                    onChange={setAutoScroll}
                  />
                </Tooltip>
                <Tooltip title="显示详情">
                  <Button
                    size="small"
                    type={showDetails ? "primary" : "default"}
                    icon={<SettingOutlined />}
                    onClick={() => setShowDetails(!showDetails)}
                  />
                </Tooltip>
                <Tooltip title="清空历史">
                  <Button
                    size="small"
                    icon={<ReloadOutlined />}
                    onClick={clearHistory}
                    disabled={eventHistory.length === 0}
                  />
                </Tooltip>
              </Space>
            }
            size="small"
            bodyStyle={{ maxHeight: 300, overflow: 'auto' }}
          >
            {eventHistory.length > 0 ? (
              <List
                size="small"
                dataSource={eventHistory}
                renderItem={(item) => (
                  <List.Item style={{ padding: '4px 0' }}>
                    <div style={{ width: '100%' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Tag color={getEventTypeColor(item.eventType)}>
                          {item.eventType}
                        </Tag>
                        <Text type="secondary" style={{ fontSize: '11px' }}>
                          {item.formattedTime}
                        </Text>
                      </div>
                      {showDetails && (
                        <pre
                          style={{
                            fontSize: '10px',
                            margin: '4px 0',
                            padding: '4px',
                            background: '#f5f5f5',
                            borderRadius: '4px',
                            maxHeight: '60px',
                            overflow: 'auto',
                            whiteSpace: 'pre-wrap'
                          }}
                        >
                          {formatEventData(item.data)}
                        </pre>
                      )}
                    </div>
                  </List.Item>
                )}
              />
            ) : (
              <Empty
                description={ws.isConnected ? "等待事件..." : "请先连接"}
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            )}
          </Card>
        </Col>

        {/* 错误提示 */}
        {ws.error && (
          <Col span={24}>
            <Alert
              message="连接错误"
              description={ws.error.message}
              type="error"
              showIcon
              closable
            />
          </Col>
        )}
      </Row>
    </div>
  );
};

export default RealtimeDashboard;
