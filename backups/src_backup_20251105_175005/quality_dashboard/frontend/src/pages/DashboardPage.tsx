import React, { useState } from 'react';
import { Row, Col, Card, Button, Space, Statistic, Alert, Spin } from 'antd';
import {
  ReloadOutlined,
  ThunderboltOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined
} from '@ant-design/icons';
import QualityScoreCard from '../components/QualityScoreCard';
import QualityTrendChart from '../components/QualityTrendChart';
import ImprovementStatus from '../components/ImprovementStatus';
import RecentAlerts from '../components/RecentAlerts';
import { useWebSocket } from '../contexts/WebSocketContext';
import './DashboardPage.css';

const DashboardPage: React.FC = () => {
  const { metrics, isConnected, lastUpdate, triggerQualityCheck } = useWebSocket();
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await triggerQualityCheck();
    } finally {
      setTimeout(() => setIsRefreshing(false), 2000);
    }
  };

  const getConnectionStatus = () => {
    if (isConnected) {
      return {
        type: 'success' as const,
        message: '实时连接正常',
        icon: <CheckCircleOutlined />
      };
    } else {
      return {
        type: 'warning' as const,
        message: '连接已断开，正在重连...',
        icon: <ExclamationCircleOutlined />
      };
    }
  };

  const connectionStatus = getConnectionStatus();

  if (!metrics) {
    return (
      <div className="dashboard-page">
        <div style={{ textAlign: 'center', padding: '100px 20px' }}>
          <Spin size="large" />
          <h2 style={{ marginTop: '20px', color: '#666' }}>正在加载质量数据...</h2>
          <p style={{ color: '#999' }}>首次加载可能需要几秒钟时间</p>
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard-page">
      {/* 连接状态提示 */}
      <div style={{ marginBottom: '16px' }}>
        <Alert
          message={connectionStatus.message}
          type={connectionStatus.type}
          icon={connectionStatus.icon}
          showIcon
          closable={false}
        />
      </div>

      {/* 顶部操作栏 */}
      <div className="dashboard-header">
        <div className="header-title">
          <h1>质量监控仪表板</h1>
          {lastUpdate && (
            <span className="last-update">
              最后更新: {new Date(lastUpdate).toLocaleString()}
            </span>
          )}
        </div>
        <Space>
          <Button
            type="primary"
            icon={<ThunderboltOutlined />}
            onClick={handleRefresh}
            loading={isRefreshing}
          >
            立即检查
          </Button>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => window.location.reload()}
          >
            刷新页面
          </Button>
        </Space>
      </div>

      {/* 主要内容区域 */}
      <div className="dashboard-content">
        <Row gutter={[16, 16]}>
          {/* 质量评分卡片 */}
          <Col xs={24} lg={8}>
            <QualityScoreCard />
          </Col>

          {/* 改进状态 */}
          <Col xs={24} lg={8}>
            <ImprovementStatus />
          </Col>

          {/* 快速统计 */}
          <Col xs={24} lg={8}>
            <Card title="快速统计" className="stats-card">
              <Row gutter={16}>
                <Col span={12}>
                  <Statistic
                    title="文件数量"
                    value={metrics.file_count}
                    prefix={<span>📁</span>}
                  />
                </Col>
                <Col span={12}>
                  <Statistic
                    title="测试运行"
                    value={metrics.tests_run}
                    prefix={<span>🧪</span>}
                  />
                </Col>
                <Col span={12} style={{ marginTop: '16px' }}>
                  <Statistic
                    title="改进周期"
                    value={metrics.improvement_cycles}
                    prefix={<span>🔄</span>}
                  />
                </Col>
                <Col span={12} style={{ marginTop: '16px' }}>
                  <Statistic
                    title="成功率"
                    value={metrics.success_rate * 100}
                    precision={1}
                    suffix="%"
                    prefix={<span>✅</span>}
                  />
                </Col>
              </Row>
            </Card>
          </Col>

          {/* 质量趋势图表 */}
          <Col xs={24} lg={16}>
            <QualityTrendChart />
          </Col>

          {/* 最近告警 */}
          <Col xs={24} lg={8}>
            <RecentAlerts />
          </Col>
        </Row>
      </div>
    </div>
  );
};

export default DashboardPage;
