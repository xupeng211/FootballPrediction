/**
 * 系统健康状态面板组件
 * System Health Panel Component
 */

import React from 'react';
import { Progress, Statistic, Card, Space, List, Tag, Tooltip } from 'antd';
import {
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  CloseCircleOutlined,
  ApiOutlined,
  DatabaseOutlined,
  CloudServerOutlined,
  ThunderboltOutlined,
  ClockCircleOutlined,
  WarningOutlined
} from '@ant-design/icons';

const SystemHealthPanel = ({ health, performance }) => {
  const getStatusIcon = (status) => {
    switch (status) {
      case 'healthy':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'warning':
        return <ExclamationCircleOutlined style={{ color: '#faad14' }} />;
      case 'unhealthy':
      case 'error':
        return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
      default:
        return <ExclamationCircleOutlined style={{ color: '#d9d9d9' }} />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'healthy': return '#52c41a';
      case 'warning': return '#faad14';
      case 'unhealthy':
      case 'error': return '#ff4d4f';
      default: return '#d9d9d9';
    }
  };

  const getProgressColor = (value, thresholds = { good: 80, warning: 60 }) => {
    if (value >= thresholds.good) return '#52c41a';
    if (value >= thresholds.warning) return '#faad14';
    return '#ff4d4f';
  };

  const formatUptime = (seconds) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
  };

  const healthItems = [
    {
      title: '服务器状态',
      icon: <ApiOutlined />,
      status: health?.server_status || 'unknown',
      description: 'WebSocket服务器运行状态'
    },
    {
      title: '数据库状态',
      icon: <DatabaseOutlined />,
      status: health?.database_status || 'unknown',
      description: 'PostgreSQL数据库连接状态'
    },
    {
      title: 'Redis状态',
      icon: <CloudServerOutlined />,
      status: health?.redis_status || 'unknown',
      description: 'Redis缓存服务状态'
    }
  ];

  return (
    <div>
      {/* 系统健康状态列表 */}
      <List
        size="small"
        dataSource={healthItems}
        renderItem={(item) => (
          <List.Item>
            <List.Item.Meta
              avatar={getStatusIcon(item.status)}
              title={
                <Space>
                  {item.icon}
                  <span style={{ fontSize: '13px' }}>{item.title}</span>
                </Space>
              }
              description={
                <div>
                  <div style={{ fontSize: '11px', color: '#666', marginBottom: '4px' }}>
                    {item.description}
                  </div>
                  <Tag color={getStatusColor(item.status)} size="small">
                    {item.status.toUpperCase()}
                  </Tag>
                </div>
              }
            />
          </List.Item>
        )}
      />

      {/* 性能指标 */}
      {performance && (
        <div style={{ marginTop: '16px' }}>
          <div style={{ marginBottom: '12px', fontSize: '13px', fontWeight: 'bold' }}>
            性能指标
          </div>

          {/* CPU使用率 */}
          <div style={{ marginBottom: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
              <span style={{ fontSize: '11px', color: '#666' }}>CPU使用率</span>
              <span style={{ fontSize: '11px', fontWeight: 'bold' }}>
                {performance.cpu_usage}%
              </span>
            </div>
            <Progress
              percent={performance.cpu_usage}
              strokeColor={getProgressColor(performance.cpu_usage)}
              size="small"
              showInfo={false}
            />
          </div>

          {/* 内存使用率 */}
          <div style={{ marginBottom: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
              <span style={{ fontSize: '11px', color: '#666' }}>内存使用率</span>
              <span style={{ fontSize: '11px', fontWeight: 'bold' }}>
                {performance.memory_usage}%
              </span>
            </div>
            <Progress
              percent={performance.memory_usage}
              strokeColor={getProgressColor(performance.memory_usage)}
              size="small"
              showInfo={false}
            />
          </div>

          {/* 响应时间 */}
          <div style={{ marginBottom: '12px' }}>
            <Tooltip title={`当前响应时间: ${performance.response_time_ms}ms`}>
              <Statistic
                title={<span style={{ fontSize: '11px', color: '#666' }}>响应时间</span>}
                value={performance.response_time_ms}
                suffix="ms"
                valueStyle={{
                  fontSize: '14px',
                  color: getProgressColor(1000 - performance.response_time_ms, { good: 800, warning: 500 })
                }}
                prefix={<ThunderboltOutlined />}
              />
            </Tooltip>
          </div>

          {/* 活跃连接数 */}
          <div>
            <Tooltip title={`当前活跃连接数: ${performance.active_connections}`}>
              <Statistic
                title={<span style={{ fontSize: '11px', color: '#666' }}>活跃连接</span>}
                value={performance.active_connections}
                valueStyle={{
                  fontSize: '14px',
                  color: '#722ed1'
                }}
                prefix={<CloudServerOutlined />}
              />
            </Tooltip>
          </div>
        </div>
      )}

      {/* 系统信息 */}
      <div style={{ marginTop: '16px', padding: '12px', backgroundColor: '#f5f5f5', borderRadius: '4px' }}>
        <div style={{ fontSize: '11px', color: '#666', marginBottom: '8px' }}>
          <strong>系统信息</strong>
        </div>
        <div style={{ fontSize: '10px', color: '#999' }}>
          <div style={{ marginBottom: '2px' }}>
            <ClockCircleOutlined style={{ marginRight: '4px' }} />
            运行时间: {formatUptime(86400)} {/* 示例值，实际应从服务器获取 */}
          </div>
          <div style={{ marginBottom: '2px' }}>
            <ApiOutlined style={{ marginRight: '4px' }} />
            服务版本: v1.0.0
          </div>
          <div>
            <DatabaseOutlined style={{ marginRight: '4px' }} />
            最后更新: {new Date().toLocaleTimeString()}
          </div>
        </div>
      </div>

      {/* 健康度总分 */}
      <div style={{ marginTop: '16px', textAlign: 'center' }}>
        <Progress
          type="circle"
          percent={85} {/* 示例值，实际应根据各组件状态计算 */}
          size={60}
          strokeColor={{
            '0%': '#108ee9',
            '100%': '#87d068',
          }}
          format={() => '85%'}
        />
        <div style={{ marginTop: '8px', fontSize: '11px', color: '#666' }}>
          系统健康度
        </div>
      </div>
    </div>
  );
};

export default SystemHealthPanel;