/**
 * 质量指标概览组件
 * Metrics Overview Component
 */

import React from 'react';
import { Progress, Row, Col, Card, Tag, Tooltip, Space, Divider } from 'antd';
import {
  CodeOutlined,
  BugOutlined,
  SafetyOutlined,
  TrophyOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
  InfoCircleOutlined
} from '@ant-design/icons';

const MetricsOverview = ({ metrics }) => {
  if (!metrics) {
    return (
      <div style={{ textAlign: 'center', padding: '40px' }}>
        <InfoCircleOutlined style={{ fontSize: '48px', color: '#d9d9d9' }} />
        <p>暂无质量指标数据</p>
      </div>
    );
  }

  const getGateIcon = (gateName) => {
    if (gateName.includes('代码质量') || gateName.includes('Code Quality')) {
      return <CodeOutlined />;
    } else if (gateName.includes('测试覆盖率') || gateName.includes('Test Coverage')) {
      return <BugOutlined />;
    } else if (gateName.includes('安全') || gateName.includes('Security')) {
      return <SafetyOutlined />;
    } else if (gateName.includes('综合质量') || gateName.includes('Overall Quality')) {
      return <TrophyOutlined />;
    } else if (gateName.includes('技术债务') || gateName.includes('Technical Debt')) {
      return <WarningOutlined />;
    } else {
      return <InfoCircleOutlined />;
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'passed':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'failed':
        return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
      case 'warning':
        return <ExclamationCircleOutlined style={{ color: '#faad14' }} />;
      case 'skipped':
        return <InfoCircleOutlined style={{ color: '#d9d9d9' }} />;
      default:
        return <InfoCircleOutlined style={{ color: '#d9d9d9' }} />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'passed': return '#52c41a';
      case 'failed': return '#ff4d4f';
      case 'warning': return '#faad14';
      case 'skipped': return '#d9d9d9';
      default: return '#d9d9d9';
    }
  };

  const getProgressColor = (score, threshold) => {
    if (score >= threshold) return '#52c41a';
    if (score >= threshold * 0.9) return '#faad14';
    return '#ff4d4f';
  };

  const getPercentage = (score, maxScore = 10) => {
    return Math.min(100, Math.max(0, (score / maxScore) * 100));
  };

  const detailedResults = metrics.detailed_results || [];
  const summary = metrics.summary || {};

  return (
    <div>
      {/* 概览统计 */}
      <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
        <Col span={6}>
          <Card size="small" style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '24px', color: '#52c41a', fontWeight: 'bold' }}>
              {summary.passed || 0}
            </div>
            <div style={{ color: '#666' }}>通过</div>
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '24px', color: '#ff4d4f', fontWeight: 'bold' }}>
              {summary.failed || 0}
            </div>
            <div style={{ color: '#666' }}>失败</div>
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '24px', color: '#faad14', fontWeight: 'bold' }}>
              {summary.warning || 0}
            </div>
            <div style={{ color: '#666' }}>警告</div>
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '24px', color: '#d9d9d9', fontWeight: 'bold' }}>
              {summary.skipped || 0}
            </div>
            <div style={{ color: '#666' }}>跳过</div>
          </Card>
        </Col>
      </Row>

      <Divider />

      {/* 详细门禁结果 */}
      <Row gutter={[16, 16]}>
        {detailedResults.map((gate, index) => (
          <Col span={12} key={index}>
            <Card
              size="small"
              hoverable
              title={
                <Space>
                  {getGateIcon(gate.gate_name)}
                  <span>{gate.gate_name}</span>
                  {getStatusIcon(gate.status)}
                </Space>
              }
              extra={
                <Tooltip title={`当前分数: ${gate.score} / 阈值: ${gate.threshold}`}>
                  <Tag color={getStatusColor(gate.status)}>
                    {gate.status.toUpperCase()}
                  </Tag>
                </Tooltip>
              }
            >
              {/* 进度条 */}
              <div style={{ marginBottom: '12px' }}>
                <Progress
                  percent={getPercentage(gate.score, gate.threshold)}
                  strokeColor={getProgressColor(gate.score, gate.threshold)}
                  format={() => `${gate.score.toFixed(1)}/${gate.threshold}`}
                  size="small"
                />
              </div>

              {/* 详细信息 */}
              <div style={{ fontSize: '12px', color: '#666' }}>
                <div style={{ marginBottom: '4px' }}>
                  <strong>分数:</strong> {gate.score.toFixed(2)} / {gate.threshold}
                </div>
                {gate.duration_ms && (
                  <div style={{ marginBottom: '4px' }}>
                    <strong>耗时:</strong> {gate.duration_ms}ms
                  </div>
                )}
                <div style={{ marginBottom: '4px' }}>
                  <strong>时间:</strong> {new Date(gate.timestamp).toLocaleString()}
                </div>
              </div>

              {/* 消息 */}
              {gate.message && (
                <div style={{
                  marginTop: '8px',
                  padding: '8px',
                  backgroundColor: gate.status === 'failed' ? '#fff2f0' :
                                   gate.status === 'warning' ? '#fffbe6' :
                                   gate.status === 'passed' ? '#f6ffed' : '#f5f5f5',
                  borderRadius: '4px',
                  fontSize: '12px'
                }}>
                  <div style={{ display: 'flex', alignItems: 'flex-start' }}>
                    {getStatusIcon(gate.status)}
                    <span style={{ marginLeft: '8px' }}>{gate.message}</span>
                  </div>
                </div>
              )}

              {/* 额外详情 */}
              {gate.details && Object.keys(gate.details).length > 0 && (
                <details style={{ marginTop: '8px' }}>
                  <summary style={{ cursor: 'pointer', fontSize: '12px', color: '#1890ff' }}>
                    查看详细信息
                  </summary>
                  <div style={{ marginTop: '8px', fontSize: '11px', color: '#666' }}>
                    {Object.entries(gate.details).map(([key, value]) => (
                      <div key={key} style={{ marginBottom: '2px' }}>
                        <strong>{key}:</strong> {JSON.stringify(value)}
                      </div>
                    ))}
                  </div>
                </details>
              )}
            </Card>
          </Col>
        ))}
      </Row>

      {/* 性能指标 */}
      {metrics.performance && (
        <>
          <Divider />
          <Row gutter={[16, 16]}>
            <Col span={6}>
              <Card size="small">
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '18px', color: '#1890ff', fontWeight: 'bold' }}>
                    {metrics.performance.response_time_ms}ms
                  </div>
                  <div style={{ color: '#666', fontSize: '12px' }}>响应时间</div>
                </div>
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small">
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '18px', color: '#52c41a', fontWeight: 'bold' }}>
                    {metrics.performance.cpu_usage}%
                  </div>
                  <div style={{ color: '#666', fontSize: '12px' }}>CPU使用率</div>
                </div>
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small">
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '18px', color: '#faad14', fontWeight: 'bold' }}>
                    {metrics.performance.memory_usage}%
                  </div>
                  <div style={{ color: '#666', fontSize: '12px' }}>内存使用率</div>
                </div>
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small">
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '18px', color: '#722ed1', fontWeight: 'bold' }}>
                    {metrics.performance.active_connections}
                  </div>
                  <div style={{ color: '#666', fontSize: '12px' }}>活跃连接</div>
                </div>
              </Card>
            </Col>
          </Row>
        </>
      )}
    </div>
  );
};

export default MetricsOverview;