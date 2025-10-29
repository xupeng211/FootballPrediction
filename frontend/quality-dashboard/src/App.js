import React, { useState, useEffect } from 'react';
import { Layout, Card, Row, Col, Typography, Statistic, Alert, Badge, Spin } from 'antd';
import {
  DashboardOutlined,
  AlertOutlined,
  TrendingUpOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  CloseCircleOutlined,
  ApiOutlined,
  DatabaseOutlined,
  CloudServerOutlined
} from '@ant-design/icons';
import './App.css';
import MetricsOverview from './components/MetricsOverview';
import AlertsPanel from './components/AlertsPanel';
import QualityTrendsChart from './components/QualityTrendsChart';
import SystemHealthPanel from './components/SystemHealthPanel';
import { useWebSocket } from './services/websocketService';

const { Header, Content, Sider } = Layout;
const { Title, Text } = Typography;

function App() {
  const [metrics, setMetrics] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [wsConnected, setWsConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [loading, setLoading] = useState(true);

  // 使用WebSocket连接
  const {
    connectionStatus,
    lastMessage,
    sendMessage
  } = useWebSocket('ws://localhost:8001/ws/quality');

  useEffect(() => {
    setWsConnected(connectionStatus === 'Connected');
  }, [connectionStatus]);

  useEffect(() => {
    if (lastMessage) {
      try {
        const data = JSON.parse(lastMessage.data);

        switch (data.type) {
          case 'initial_data':
          case 'metrics_update':
          case 'quality_update':
            setMetrics(data.data);
            setAlerts(data.data.alerts || []);
            setLastUpdate(new Date());
            setLoading(false);
            break;

          case 'new_alerts':
            setAlerts(prev => [...data.alerts, ...prev]);
            break;

          default:
            console.log('未知消息类型:', data.type);
        }
      } catch (error) {
        console.error('解析WebSocket消息失败:', error);
      }
    }
  }, [lastMessage]);

  const getStatusColor = (status) => {
    switch (status) {
      case 'PASSED': return '#52c41a';
      case 'WARNING': return '#faad14';
      case 'FAILED': return '#ff4d4f';
      default: return '#d9d9d9';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'PASSED': return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'WARNING': return <ExclamationCircleOutlined style={{ color: '#faad14' }} />;
      case 'FAILED': return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
      default: return <ApiOutlined style={{ color: '#d9d9d9' }} />;
    }
  };

  const criticalAlerts = alerts.filter(alert => alert.severity === 'critical');
  const warningAlerts = alerts.filter(alert => alert.severity === 'warning');

  if (loading) {
    return (
      <div className="loading-container">
        <Spin size="large" />
        <Text>正在加载实时质量监控数据...</Text>
      </div>
    );
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      {/* 顶部导航栏 */}
      <Header style={{
        background: '#001529',
        padding: '0 24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <DashboardOutlined style={{ fontSize: '24px', color: '#1890ff', marginRight: '12px' }} />
          <Title level={3} style={{ color: 'white', margin: 0 }}>
            实时质量监控面板
          </Title>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          {/* WebSocket连接状态 */}
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <div className={`ws-status-indicator ${wsConnected ? 'connected' : 'disconnected'}`}></div>
            <Text style={{ color: 'white', marginLeft: '8px' }}>
              {wsConnected ? '已连接' : '连接中...'}
            </Text>
          </div>

          {/* 告警数量 */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {criticalAlerts.length > 0 && (
              <Badge count={criticalAlerts.length} style={{ backgroundColor: '#ff4d4f' }}>
                <AlertOutlined style={{ fontSize: '18px', color: '#ff4d4f' }} />
              </Badge>
            )}
            {warningAlerts.length > 0 && (
              <Badge count={warningAlerts.length} style={{ backgroundColor: '#faad14' }}>
                <AlertOutlined style={{ fontSize: '18px', color: '#faad14' }} />
              </Badge>
            )}
          </div>

          {/* 最后更新时间 */}
          {lastUpdate && (
            <Text style={{ color: '#888' }}>
              最后更新: {lastUpdate.toLocaleTimeString()}
            </Text>
          )}
        </div>
      </Header>

      {/* 主内容区 */}
      <Layout>
        <Content style={{ margin: '24px', background: '#f0f2f5' }}>
          {/* 总体状态卡片 */}
          <Card
            style={{ marginBottom: '24px' }}
            title={
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span>质量总览</span>
                {getStatusIcon(metrics?.overall_status)}
              </div>
            }
          >
            <Row gutter={16}>
              <Col span={6}>
                <Statistic
                  title="综合质量分数"
                  value={metrics?.overall_score || 0}
                  precision={2}
                  suffix="/10"
                  valueStyle={{
                    color: getStatusColor(metrics?.overall_status),
                    fontSize: '32px',
                    fontWeight: 'bold'
                  }}
                  prefix={<TrendingUpOutlined />}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="检查门禁数量"
                  value={metrics?.gates_checked || 0}
                  suffix="个"
                  valueStyle={{ color: '#1890ff', fontSize: '32px' }}
                  prefix={<DatabaseOutlined />}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="通过率"
                  value={metrics?.summary?.passed || 0}
                  suffix={`/ ${metrics?.gates_checked || 0}`}
                  valueStyle={{
                    color: '#52c41a',
                    fontSize: '32px'
                  }}
                  prefix={<CheckCircleOutlined />}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="活跃连接"
                  value={metrics?.performance?.active_connections || 0}
                  suffix="个"
                  valueStyle={{ color: '#722ed1', fontSize: '32px' }}
                  prefix={<CloudServerOutlined />}
                />
              </Col>
            </Row>

            {/* 状态描述 */}
            <div style={{ marginTop: '16px' }}>
              <Alert
                message={`系统状态: ${metrics?.overall_status || 'UNKNOWN'}`}
                description={
                  metrics?.overall_status === 'PASSED'
                    ? '所有质量检查均通过，系统运行正常。'
                    : metrics?.overall_status === 'WARNING'
                    ? '发现部分质量问题，建议关注并处理。'
                    : metrics?.overall_status === 'FAILED'
                    ? '发现严重质量问题，需要立即处理。'
                    : '状态未知，请检查监控系统。'
                }
                type={
                  metrics?.overall_status === 'PASSED'
                    ? 'success'
                    : metrics?.overall_status === 'WARNING'
                    ? 'warning'
                    : metrics?.overall_status === 'FAILED'
                    ? 'error'
                    : 'info'
                }
                showIcon
              />
            </div>
          </Card>

          {/* 监控面板网格 */}
          <Row gutter={[16, 16]}>
            {/* 左侧面板 */}
            <Col span={18}>
              {/* 质量指标概览 */}
              <Card
                title="质量指标概览"
                style={{ marginBottom: '16px' }}
                extra={<Badge status={wsConnected ? 'success' : 'error'} text={wsConnected ? '实时' : '离线'} />}
              >
                <MetricsOverview metrics={metrics} />
              </Card>

              {/* 质量趋势图表 */}
              <Card title="质量趋势分析" style={{ marginBottom: '16px' }}>
                <QualityTrendsChart trends={metrics?.trends} />
              </Card>
            </Col>

            {/* 右侧面板 */}
            <Col span={6}>
              {/* 告警面板 */}
              <Card
                title={
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span>活跃告警</span>
                    <Badge count={alerts.length} />
                  </div>
                }
                style={{ marginBottom: '16px' }}
              >
                <AlertsPanel alerts={alerts} />
              </Card>

              {/* 系统健康状态 */}
              <Card title="系统健康">
                <SystemHealthPanel
                  health={metrics?.system_health}
                  performance={metrics?.performance}
                />
              </Card>
            </Col>
          </Row>
        </Content>
      </Layout>
    </Layout>
  );
}

export default App;