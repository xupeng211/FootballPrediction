/**
 * 实时统计面板组件
 *
 * Realtime Statistics Panel Component
 *
 * 展示WebSocket实时系统的运行统计和性能指标
 * Displays WebSocket real-time system operational statistics and performance metrics
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Progress,
  Typography,
  Space,
  Tag,
  Divider,
  List,
  Badge,
  Tooltip,
  Alert,
  Switch
} from 'antd';
import {
  LineChartOutlined,
  BarChartOutlined,
  ClockCircleOutlined,
  ThunderboltOutlined,
  DatabaseOutlined,
  UserOutlined,
  EyeOutlined,
  TrophyOutlined,
  FireOutlined,
  RocketOutlined
} from '@ant-design/icons';
import { useWebSocket, useRealtimeEvent } from '../hooks/useWebSocket';
import { EVENT_TYPES } from '../services/websocket';

const { Text, Title } = Typography;

interface RealtimeStatsPanelProps {
  userId?: string;
  className?: string;
  refreshInterval?: number;
}

interface SystemStats {
  totalConnections: number;
  activeConnections: number;
  totalSubscriptions: number;
  totalRooms: number;
  messageCount: number;
  errorCount: number;
  uptime: string;
  avgResponseTime: number;
  cpuUsage: number;
  memoryUsage: number;
}

interface EventTypeStats {
  eventType: string;
  count: number;
  last24h: number;
  last7d: number;
  trend: 'up' | 'down' | 'stable';
}

const RealtimeStatsPanel: React.FC<RealtimeStatsPanelProps> = ({
  userId,
  className,
  refreshInterval = 30000
}) => {
  // 状态管理
  const [stats, setStats] = useState<SystemStats>({
    totalConnections: 0,
    activeConnections: 0,
    totalSubscriptions: 0,
    totalRooms: 0,
    messageCount: 0,
    errorCount: 0,
    uptime: '00:00:00',
    avgResponseTime: 0,
    cpuUsage: 0,
    memoryUsage: 0
  });

  const [eventTypeStats, setEventTypeStats] = useState<EventTypeStats[]>([]);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [showDetails, setShowDetails] = useState(false);

  // WebSocket连接
  const ws = useWebSocket({
    userId,
    autoConnect: true
  });

  // 监听统计数据事件
  useRealtimeEvent(EVENT_TYPES.ANALYTICS_UPDATED, (event) => {
    const data = event.data;
    if (data.metric_name) {
      // 更新对应的统计数据
      updateStats(data.metric_name, data.value);
    }
  });

  useRealtimeEvent(EVENT_TYPES.SYSTEM_STATUS, (event) => {
    const data = event.data;
    if (data.websocket) {
      setStats(prev => ({
        ...prev,
        ...data.websocket,
        lastUpdate: new Date().toISOString()
      }));
    }
  });

  // 更新统计数据
  const updateStats = (metricName: string, value: any) => {
    setStats(prev => {
      const updated = { ...prev };

      switch (metricName) {
        case 'total_connections':
          updated.totalConnections = value;
          break;
        case 'active_connections':
          updated.activeConnections = value;
          break;
        case 'total_subscriptions':
          updated.totalSubscriptions = value;
          break;
        case 'total_rooms':
          updated.totalRooms = value;
          break;
        case 'message_count':
          updated.messageCount = value;
          break;
        case 'error_count':
          updated.errorCount = value;
          break;
        case 'avg_response_time':
          updated.avgResponseTime = value;
          break;
        case 'cpu_usage':
          updated.cpuUsage = value;
          break;
        case 'memory_usage':
          updated.memoryUsage = value;
          break;
        default:
          break;
      }

      return updated;
    });
  };

  // 模拟统计数据更新
  useEffect(() => {
    if (!autoRefresh || !ws.isConnected) return;

    const interval = setInterval(() => {
      // 模拟统计数据
      const mockStats: SystemStats = {
        totalConnections: stats.totalConnections + Math.floor(Math.random() * 3),
        activeConnections: Math.max(1, Math.floor(Math.random() * 10)),
        totalSubscriptions: stats.totalSubscriptions + Math.floor(Math.random() * 5),
        totalRooms: Math.max(1, Math.floor(Math.random() * 5)),
        messageCount: stats.messageCount + Math.floor(Math.random() * 10),
        errorCount: Math.max(0, stats.errorCount + (Math.random() < 0.1 ? 1 : 0)),
        uptime: formatUptime(stats.messageCount),
        avgResponseTime: Math.max(10, Math.floor(Math.random() * 100)),
        cpuUsage: Math.max(5, Math.floor(Math.random() * 80)),
        memoryUsage: Math.max(10, Math.floor(Math.random() * 70))
      };

      setStats(mockStats);

      // 更新事件类型统计
      updateEventTypeStats();

    }, refreshInterval);

    return () => clearInterval(interval);
  }, [autoRefresh, ws.isConnected, refreshInterval]);

  const updateEventTypeStats = () => {
    const eventTypes: EventTypeStats[] = [
      {
        eventType: EVENT_TYPES.PREDICTION_CREATED,
        count: Math.floor(Math.random() * 50) + 10,
        last24h: Math.floor(Math.random() * 20) + 5,
        last7d: Math.floor(Math.random() * 100) + 50,
        trend: Math.random() > 0.5 ? 'up' : Math.random() > 0.3 ? 'stable' : 'down'
      },
      {
        eventType: EVENT_TYPES.MATCH_SCORE_CHANGED,
        count: Math.floor(Math.random() * 30) + 5,
        last24h: Math.floor(Math.random() * 15) + 3,
        last7d: Math.floor(Math.random() * 60) + 20,
        trend: Math.random() > 0.4 ? 'up' : Math.random() > 0.5 ? 'stable' : 'down'
      },
      {
        eventType: EVENT_TYPES.ODDS_UPDATED,
        count: Math.floor(Math.random() * 80) + 20,
        last24h: Math.floor(Math.random() * 30) + 10,
        last7d: Math.floor(Math.random() * 150) + 80,
        trend: Math.random() > 0.6 ? 'up' : Math.random() > 0.3 ? 'stable' : 'down'
      },
      {
        eventType: EVENT_TYPES.SYSTEM_ALERT,
        count: Math.floor(Math.random() * 5) + 1,
        last24h: Math.floor(Math.random() * 3),
        last7d: Math.floor(Math.random() * 10) + 5,
        trend: Math.random() > 0.7 ? 'up' : 'stable'
      }
    ];

    setEventTypeStats(eventTypes);
  };

  const formatUptime = (messageCount: number) => {
    const hours = Math.floor(messageCount / 100);
    const minutes = (messageCount % 100);
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:00`;
  };

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'up':
        return <TrophyOutlined style={{ color: '#52c41a' }} />;
      case 'down':
        return <FireOutlined style={{ color: '#f5222d' }} />;
      default:
        return <BarChartOutlined style={{ color: '#faad14' }} />;
    }
  };

  const getTrendColor = (trend: string) => {
    switch (trend) {
      case 'up': return '#52c41a';
      case 'down': return '#f5222d';
      default: return '#faad14';
    }
  };

  const getConnectionStatus = () => {
    if (!ws.isConnected) {
      return { status: 'error', text: '未连接', color: '#f5222d' };
    }
    if (stats.activeConnections === 0) {
      return { status: 'warning', text: '无活跃连接', color: '#faad14' };
    }
    return { status: 'success', text: '正常运行', color: '#52c41a' };
  };

  const getPerformanceStatus = () => {
    const avgResponse = stats.avgResponseTime;
    if (avgResponse > 200) {
      return { status: 'error', text: '响应较慢', color: '#f5222d' };
    }
    if (avgResponse > 100) {
      return { status: 'warning', text: '响应一般', color: '#faad14' };
    }
    return { status: 'success', text: '响应良好', color: '#52c41a' };
  };

  const connectionStatus = getConnectionStatus();
  const performanceStatus = getPerformanceStatus();

  return (
    <div className={className}>
      <Row gutter={[16, 16]}>
        {/* 系统状态概览 */}
        <Col xs={24} sm={24} md={8}>
          <Card
            title={
              <Space>
                <RocketOutlined />
                <span>系统状态</span>
                <Badge status={connectionStatus.status as any} text={connectionStatus.text} />
              </Space>
            }
            extra={
              <Tooltip title="自动刷新">
                <Switch
                  size="small"
                  checked={autoRefresh}
                  onChange={setAutoRefresh}
                  disabled={!ws.isConnected}
                />
              </Tooltip>
            }
            size="small"
          >
            <Space direction="vertical" style={{ width: '100%' }}>
              <Row gutter={16}>
                <Col span={12}>
                  <Statistic
                    title="活跃连接"
                    value={stats.activeConnections}
                    prefix={<UserOutlined />}
                    valueStyle={{ fontSize: '18px', color: connectionStatus.color }}
                  />
                </Col>
                <Col span={12}>
                  <Statistic
                    title="总连接数"
                    value={stats.totalConnections}
                    prefix={<DatabaseOutlined />}
                    valueStyle={{ fontSize: '16px' }}
                  />
                </Col>
              </Row>

              <Row gutter={16}>
                <Col span={12}>
                  <Statistic
                    title="订阅数"
                    value={stats.totalSubscriptions}
                    prefix={<EyeOutlined />}
                    valueStyle={{ fontSize: '16px' }}
                  />
                </Col>
                <Col span={12}>
                  <Statistic
                    title="房间数"
                    value={stats.totalRooms}
                    prefix={<ThunderboltOutlined />}
                    valueStyle={{ fontSize: '16px' }}
                  />
                </Col>
              </Row>

              <Alert
                message={`系统运行时间: ${stats.uptime}`}
                type="info"
                showIcon={false}
                style={{ marginTop: 8 }}
              />
            </Space>
          </Card>
        </Col>

        {/* 性能指标 */}
        <Col xs={24} sm={24} md={8}>
          <Card
            title={
              <Space>
                <LineChartOutlined />
                <span>性能指标</span>
                <Badge status={performanceStatus.status as any} text={performanceStatus.text} />
              </Space>
            }
            size="small"
          >
            <Space direction="vertical" style={{ width: '100%' }}>
              <div>
                <Text type="secondary">平均响应时间</Text>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Progress
                    percent={Math.max(0, 100 - (stats.avgResponseTime / 2))}
                    size="small"
                    style={{ flex: 1 }}
                    strokeColor={performanceStatus.color}
                    showInfo={false}
                  />
                  <Text strong style={{ color: performanceStatus.color }}>
                    {stats.avgResponseTime}ms
                  </Text>
                </div>
              </div>

              <div>
                <Text type="secondary">CPU使用率</Text>
                <Progress
                  percent={stats.cpuUsage}
                  size="small"
                  strokeColor={
                    stats.cpuUsage > 80 ? '#f5222d' :
                    stats.cpuUsage > 50 ? '#faad14' : '#52c41a'
                  }
                  showInfo={true}
                />
              </div>

              <div>
                <Text type="secondary">内存使用率</Text>
                <Progress
                  percent={stats.memoryUsage}
                  size="small"
                  strokeColor={
                    stats.memoryUsage > 80 ? '#f5222d' :
                    stats.memoryUsage > 50 ? '#faad14' : '#52c41a'
                  }
                  showInfo={true}
                />
              </div>

              {showDetails && (
                <div style={{ fontSize: '12px', color: '#666' }}>
                  <div>消息总数: {stats.messageCount}</div>
                  <div>错误次数: {stats.errorCount}</div>
                  <div>错误率: {stats.messageCount > 0 ? ((stats.errorCount / stats.messageCount) * 100).toFixed(2) : 0}%</div>
                </div>
              )}
            </Space>
          </Card>
        </Col>

        {/* 活动统计 */}
        <Col xs={24} sm={24} md={8}>
          <Card
            title={
              <Space>
                <BarChartOutlined />
                <span>活动统计</span>
              </Space>
            }
            size="small"
          >
            <List
              size="small"
              dataSource={eventTypeStats}
              renderItem={(item) => (
                <List.Item>
                  <List.Item.Meta
                    avatar={getTrendIcon(item.trend)}
                    title={
                      <Space>
                        <Text>{item.eventType.replace('_', ' ')}</Text>
                        <Tag color={getTrendColor(item.trend)}>
                          {item.trend === 'up' ? '↑' : item.trend === 'down' ? '↓' : '→'}
                        </Tag>
                      </Space>
                    }
                    description={
                      <Space direction="vertical" size="small">
                        <Text type="secondary">
                          总计: <Text strong>{item.count}</Text>
                        </Text>
                        <Text type="secondary">
                          24h: <Text>{item.last24h}</Text>
                        </Text>
                        <Text type="secondary">
                          7d: <Text>{item.last7d}</Text>
                        </Text>
                      </Space>
                    }
                  />
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default RealtimeStatsPanel;