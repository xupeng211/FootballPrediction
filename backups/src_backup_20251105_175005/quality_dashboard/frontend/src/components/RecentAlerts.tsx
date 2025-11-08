import React, { useState, useEffect } from 'react';
import { Card, List, Tag, Button, Empty, Space, Badge } from 'antd';
import {
  WarningOutlined,
  ExclamationCircleOutlined,
  InfoCircleOutlined,
  CloseCircleOutlined,
  BellOutlined
} from '@ant-design/icons';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import 'dayjs/locale/zh-cn';

dayjs.extend(relativeTime);
dayjs.locale('zh-cn');

interface Alert {
  id: string;
  timestamp: string;
  level: 'info' | 'warning' | 'error' | 'critical';
  message: string;
  source: string;
  details: Record<string, any>;
  acknowledged?: boolean;
}

const RecentAlerts: React.FC = () => {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 30000); // 每30秒更新一次
    return () => clearInterval(interval);
  }, []);

  const fetchAlerts = async () => {
    try {
      const response = await fetch('/api/quality/alerts?limit=10');
      const data = await response.json();

      // 模拟告警数据（实际应该从API获取）
      const mockAlerts: Alert[] = generateMockAlerts();
      setAlerts(mockAlerts);
    } catch (error) {
      console.error('获取告警数据失败:', error);
      // 使用模拟数据
      const mockAlerts: Alert[] = generateMockAlerts();
      setAlerts(mockAlerts);
    } finally {
      setLoading(false);
    }
  };

  const generateMockAlerts = (): Alert[] => {
    const now = new Date();
    return [
      {
        id: '1',
        timestamp: new Date(now.getTime() - 5 * 60 * 1000).toISOString(),
        level: 'warning',
        message: '测试覆盖率下降至84.4%',
        source: 'coverage_monitor',
        details: { current_coverage: 84.4, threshold: 85.0, drop: 2.1 },
        acknowledged: false
      },
      {
        id: '2',
        timestamp: new Date(now.getTime() - 15 * 60 * 1000).toISOString(),
        level: 'info',
        message: '改进引擎完成第6个周期',
        source: 'improvement_engine',
        details: { cycle_number: 6, improvement: '+0.3', duration: '2m 15s' },
        acknowledged: true
      },
      {
        id: '3',
        timestamp: new Date(now.getTime() - 45 * 60 * 1000).toISOString(),
        level: 'warning',
        message: '发现3个新的Ruff警告',
        source: 'code_quality',
        details: { file_count: 3, warnings: ['E741', 'F841', 'W503'] },
        acknowledged: false
      },
      {
        id: '4',
        timestamp: new Date(now.getTime() - 2 * 60 * 60 * 1000).toISOString(),
        level: 'info',
        message: '质量分数提升至9.84',
        source: 'quality_monitor',
        details: { previous_score: 9.6, current_score: 9.84, improvement: '+2.5%' },
        acknowledged: true
      },
      {
        id: '5',
        timestamp: new Date(now.getTime() - 4 * 60 * 60 * 1000).toISOString(),
        level: 'critical',
        message: '安全扫描发现高风险漏洞',
        source: 'security_scan',
        details: { vulnerability: 'CVE-2023-1234', severity: 'high', package: 'requests' },
        acknowledged: false
      }
    ];
  };

  const getAlertIcon = (level: Alert['level']) => {
    switch (level) {
      case 'critical':
        return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
      case 'error':
        return <ExclamationCircleOutlined style={{ color: '#ff7875' }} />;
      case 'warning':
        return <WarningOutlined style={{ color: '#faad14' }} />;
      case 'info':
      default:
        return <InfoCircleOutlined style={{ color: '#1890ff' }} />;
    }
  };

  const getAlertColor = (level: Alert['level']) => {
    switch (level) {
      case 'critical':
        return 'red';
      case 'error':
        return 'orange';
      case 'warning':
        return 'gold';
      case 'info':
      default:
        return 'blue';
    }
  };

  const getAlertStatus = (alert: Alert) => {
    if (alert.acknowledged) {
      return 'default';
    }
    return getAlertColor(alert.level);
  };

  const getRelativeTime = (timestamp: string) => {
    return dayjs(timestamp).fromNow();
  };

  const acknowledgeAlert = (alertId: string) => {
    setAlerts(prev =>
      prev.map(alert =>
        alert.id === alertId ? { ...alert, acknowledged: true } : alert
      )
    );
  };

  const dismissAlert = (alertId: string) => {
    setAlerts(prev => prev.filter(alert => alert.id !== alertId));
  };

  const unacknowledgedCount = alerts.filter(alert => !alert.acknowledged).length;

  return (
    <Card
      title={
        <Space>
          <BellOutlined />
          <span>最近告警</span>
          {unacknowledgedCount > 0 && (
            <Badge count={unacknowledgedCount} size="small" />
          )}
        </Space>
      }
      className="recent-alerts-card"
      extra={
        <Button size="small" type="text" onClick={fetchAlerts}>
          刷新
        </Button>
      }
    >
      {alerts.length === 0 ? (
        <Empty
          description="暂无告警"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      ) : (
        <List
          size="small"
          dataSource={alerts}
          renderItem={(alert) => (
            <List.Item
              className={`alert-item alert-${alert.level}`}
              actions={[
                !alert.acknowledged && (
                  <Button
                    size="small"
                    type="text"
                    onClick={() => acknowledgeAlert(alert.id)}
                  >
                    确认
                  </Button>
                ),
                <Button
                  size="small"
                  type="text"
                  danger
                  onClick={() => dismissAlert(alert.id)}
                >
                  忽略
                </Button>
              ]}
            >
              <List.Item.Meta
                avatar={getAlertIcon(alert.level)}
                title={
                  <Space>
                    <span style={{ fontSize: '13px' }}>{alert.message}</span>
                    <Tag
                      color={getAlertStatus(alert)}
                      size="small"
                      style={{ fontSize: '10px' }}
                    >
                      {alert.level.toUpperCase()}
                    </Tag>
                  </Space>
                }
                description={
                  <div>
                    <div style={{ fontSize: '12px', color: '#999', marginBottom: '4px' }}>
                      {alert.source} • {getRelativeTime(alert.timestamp)}
                    </div>
                    {!alert.acknowledged && (
                      <div style={{ fontSize: '11px', color: '#faad14' }}>
                        待处理
                      </div>
                    )}
                  </div>
                }
              />
            </List.Item>
          )}
        />
      )}
    </Card>
  );
};

export default RecentAlerts;