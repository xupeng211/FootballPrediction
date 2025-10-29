/**
 * 告警面板组件
 * Alerts Panel Component
 */

import React, { useState } from 'react';
import { List, Alert, Badge, Tag, Space, Button, Collapse, Tooltip, Empty } from 'antd';
import {
  ExclamationCircleOutlined,
  CloseCircleOutlined,
  WarningOutlined,
  InfoCircleOutlined,
  DeleteOutlined,
  CheckOutlined,
  ClockCircleOutlined,
  BugOutlined,
  SafetyOutlined,
  ThunderboltOutlined,
  ApiOutlined
} from '@ant-design/icons';
import { formatDistanceToNow } from 'date-fns';
import { zhCN } from 'date-fns/locale';

const { Panel } = Collapse;

const AlertsPanel = ({ alerts, onAcknowledge, onDismiss }) => {
  const [expandedAlerts, setExpandedAlerts] = useState([]);

  if (!alerts || alerts.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '20px' }}>
        <CheckOutlined style={{ fontSize: '32px', color: '#52c41a' }} />
        <div style={{ marginTop: '8px', color: '#666' }}>
          暂无活跃告警
        </div>
      </div>
    );
  }

  const getAlertIcon = (severity) => {
    switch (severity) {
      case 'critical':
        return <CloseCircleOutlined style={{ color: '#ff4d4f', fontSize: '16px' }} />;
      case 'warning':
        return <WarningOutlined style={{ color: '#faad14', fontSize: '16px' }} />;
      case 'error':
        return <ExclamationCircleOutlined style={{ color: '#ff7875', fontSize: '16px' }} />;
      case 'info':
        return <InfoCircleOutlined style={{ color: '#1890ff', fontSize: '16px' }} />;
      default:
        return <InfoCircleOutlined style={{ color: '#d9d9d9', fontSize: '16px' }} />;
    }
  };

  const getTypeIcon = (type) => {
    switch (type) {
      case 'quality':
        return <BugOutlined />;
      case 'security':
        return <SafetyOutlined />;
      case 'performance':
        return <ThunderboltOutlined />;
      case 'system':
        return <ApiOutlined />;
      default:
        return <InfoCircleOutlined />;
    }
  };

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'critical': return '#ff4d4f';
      case 'error': return '#ff7875';
      case 'warning': return '#faad14';
      case 'info': return '#1890ff';
      default: return '#d9d9d9';
    }
  };

  const getTypeColor = (type) => {
    switch (type) {
      case 'quality': return '#722ed1';
      case 'security': return '#f5222d';
      case 'performance': return '#fa8c16';
      case 'system': return '#1890ff';
      default: return '#52c41a';
    }
  };

  const formatTimestamp = (timestamp) => {
    try {
      const date = new Date(timestamp);
      return formatDistanceToNow(date, { addSuffix: true, locale: zhCN });
    } catch (error) {
      return '时间未知';
    }
  };

  const handleAcknowledge = (alertId) => {
    if (onAcknowledge) {
      onAcknowledge(alertId);
    }
  };

  const handleDismiss = (alertId) => {
    if (onDismiss) {
      onDismiss(alertId);
    }
  };

  const handleExpandChange = (keys) => {
    setExpandedAlerts(keys);
  };

  // 按严重程度排序告警
  const sortedAlerts = [...alerts].sort((a, b) => {
    const severityOrder = { critical: 4, error: 3, warning: 2, info: 1 };
    const aSeverity = severityOrder[a.severity] || 0;
    const bSeverity = severityOrder[b.severity] || 0;
    return bSeverity - aSeverity;
  });

  const criticalAlerts = sortedAlerts.filter(alert => alert.severity === 'critical');
  const warningAlerts = sortedAlerts.filter(alert => alert.severity === 'warning');
  const otherAlerts = sortedAlerts.filter(alert => !['critical', 'warning'].includes(alert.severity));

  return (
    <div>
      {/* 告警统计 */}
      <div style={{ marginBottom: '16px' }}>
        <Space wrap>
          <Badge count={criticalAlerts.length} style={{ backgroundColor: '#ff4d4f' }}>
            <Tag color="#ff4d4f">严重</Tag>
          </Badge>
          <Badge count={warningAlerts.length} style={{ backgroundColor: '#faad14' }}>
            <Tag color="#faad14">警告</Tag>
          </Badge>
          <Badge count={otherAlerts.length} style={{ backgroundColor: '#1890ff' }}>
            <Tag color="#1890ff">其他</Tag>
          </Badge>
        </Space>
      </div>

      {/* 告警列表 */}
      <Collapse
        activeKey={expandedAlerts}
        onChange={handleExpandChange}
        size="small"
        ghost
      >
        {sortedAlerts.map((alert) => (
          <Panel
            key={alert.id}
            header={
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                width: '100%'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', flex: 1 }}>
                  {getAlertIcon(alert.severity)}
                  <span style={{ marginLeft: '8px', fontSize: '13px', fontWeight: 'bold' }}>
                    {alert.title}
                  </span>
                  <Tag
                    color={getSeverityColor(alert.severity)}
                    size="small"
                    style={{ marginLeft: '8px' }}
                  >
                    {alert.severity.toUpperCase()}
                  </Tag>
                  <Tag
                    color={getTypeColor(alert.type)}
                    size="small"
                    style={{ marginLeft: '4px' }}
                  >
                    {getTypeIcon(alert.type)}
                    <span style={{ marginLeft: '4px' }}>{alert.type}</span>
                  </Tag>
                </div>
                <div style={{ display: 'flex', alignItems: 'center' }}>
                  <ClockCircleOutlined style={{ fontSize: '12px', color: '#999', marginRight: '4px' }} />
                  <span style={{ fontSize: '11px', color: '#999' }}>
                    {formatTimestamp(alert.timestamp)}
                  </span>
                </div>
              </div>
            }
            extra={
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                {alert.active && (
                  <Tooltip title="确认告警">
                    <Button
                      type="text"
                      size="small"
                      icon={<CheckOutlined />}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleAcknowledge(alert.id);
                      }}
                    />
                  </Tooltip>
                )}
                <Tooltip title="忽略告警">
                  <Button
                    type="text"
                    size="small"
                    icon={<DeleteOutlined />}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDismiss(alert.id);
                    }}
                  />
                </Tooltip>
              </div>
            }
          >
            <div style={{ padding: '8px 0' }}>
              {/* 告警消息 */}
              <Alert
                message={alert.title}
                description={alert.message}
                type={
                  alert.severity === 'critical' ? 'error' :
                  alert.severity === 'warning' ? 'warning' :
                  alert.severity === 'error' ? 'error' : 'info'
                }
                showIcon
                style={{ marginBottom: '12px' }}
              />

              {/* 告警详情 */}
              <div style={{ fontSize: '12px', color: '#666' }}>
                <div style={{ marginBottom: '4px' }}>
                  <strong>告警ID:</strong> {alert.id}
                </div>
                <div style={{ marginBottom: '4px' }}>
                  <strong>告警时间:</strong> {new Date(alert.timestamp).toLocaleString()}
                </div>
                <div style={{ marginBottom: '4px' }}>
                  <strong>告警类型:</strong> {alert.type}
                </div>
                <div style={{ marginBottom: '4px' }}>
                  <strong>严重程度:</strong> {alert.severity}
                </div>
                <div style={{ marginBottom: '4px' }}>
                  <strong>状态:</strong> {alert.active ? '活跃' : '已确认'}
                </div>
                {alert.source && (
                  <div style={{ marginBottom: '4px' }}>
                    <strong>来源:</strong> {alert.source}
                  </div>
                )}
                {alert.details && (
                  <details style={{ marginTop: '8px' }}>
                    <summary style={{ cursor: 'pointer', color: '#1890ff' }}>
                      查看详细信息
                    </summary>
                    <div style={{ marginTop: '8px', padding: '8px', backgroundColor: '#f5f5f5', borderRadius: '4px' }}>
                      {typeof alert.details === 'string' ? (
                        <pre style={{ margin: 0, fontSize: '11px', whiteSpace: 'pre-wrap' }}>
                          {alert.details}
                        </pre>
                      ) : (
                        <pre style={{ margin: 0, fontSize: '11px', whiteSpace: 'pre-wrap' }}>
                          {JSON.stringify(alert.details, null, 2)}
                        </pre>
                      )}
                    </div>
                  </details>
                )}
              </div>

              {/* 操作按钮 */}
              <div style={{ marginTop: '12px', textAlign: 'right' }}>
                <Space>
                  {alert.active && (
                    <Button
                      size="small"
                      type="primary"
                      icon={<CheckOutlined />}
                      onClick={() => handleAcknowledge(alert.id)}
                    >
                      确认
                    </Button>
                  )}
                  <Button
                    size="small"
                    danger
                    icon={<DeleteOutlined />}
                    onClick={() => handleDismiss(alert.id)}
                  >
                    忽略
                  </Button>
                </Space>
              </div>
            </div>
          </Panel>
        ))}
      </Collapse>
    </div>
  );
};

export default AlertsPanel;