import React from 'react';
import { Card, Statistic, Progress, Badge, Space } from 'antd';
import {
  TrophyOutlined,
  CodeOutlined,
  SecurityScanOutlined,
  BugOutlined
} from '@ant-design/icons';
import { useWebSocket } from '../contexts/WebSocketContext';
import './QualityScoreCard.css';

interface QualityScoreCardProps {
  title?: string;
}

const QualityScoreCard: React.FC<QualityScoreCardProps> = ({ title = "质量评分" }) => {
  const { metrics, isConnected, lastUpdate } = useWebSocket();

  const getScoreColor = (score: number): string => {
    if (score >= 9.5) return '#52c41a'; // 优秀 - 绿色
    if (score >= 8.5) return '#1890ff'; // 良好 - 蓝色
    if (score >= 7.0) return '#faad14'; // 中等 - 黄色
    return '#ff4d4f'; // 需要改进 - 红色
  };

  const getScoreStatus = (score: number): 'success' | 'normal' | 'exception' => {
    if (score >= 9.0) return 'success';
    if (score >= 8.0) return 'normal';
    return 'exception';
  };

  const getScoreLevel = (score: number): string => {
    if (score >= 9.5) return 'A+ 优秀';
    if (score >= 9.0) return 'A  良好';
    if (score >= 8.5) return 'B+ 不错';
    if (score >= 8.0) return 'B  合格';
    if (score >= 7.0) return 'C  需要改进';
    return 'D  急需改进';
  };

  if (!metrics) {
    return (
      <Card
        title={title}
        extra={<Badge status="default" text="无数据" />}
        className="quality-score-card"
      >
        <div style={{ textAlign: 'center', padding: '20px' }}>
          <TrophyOutlined style={{ fontSize: '48px', color: '#d9d9d9' }} />
          <p style={{ marginTop: '16px', color: '#999' }}>等待质量数据...</p>
        </div>
      </Card>
    );
  }

  return (
    <Card
      title={title}
      extra={
        <Space>
          <Badge
            status={isConnected ? 'processing' : 'error'}
            text={isConnected ? '实时' : '离线'}
          />
          {lastUpdate && (
            <span style={{ fontSize: '12px', color: '#999' }}>
              {new Date(lastUpdate).toLocaleTimeString()}
            </span>
          )}
        </Space>
      }
      className="quality-score-card"
    >
      <div className="score-display">
        <Statistic
          title="综合质量分数"
          value={metrics.overall_score}
          precision={2}
          valueStyle={{
            color: getScoreColor(metrics.overall_score),
            fontSize: '36px',
            fontWeight: 'bold'
          }}
          prefix={<TrophyOutlined />}
          suffix="/ 10"
        />

        <div className="score-level">
          <Badge
            status={getScoreStatus(metrics.overall_score)}
            text={getScoreLevel(metrics.overall_score)}
          />
        </div>
      </div>

      <div className="metrics-breakdown">
        <Space direction="vertical" style={{ width: '100%' }}>
          <div className="metric-item">
            <div className="metric-header">
              <CodeOutlined /> 代码质量
              <span className="metric-score">{metrics.code_quality_score.toFixed(1)}</span>
            </div>
            <Progress
              percent={metrics.code_quality_score * 10}
              strokeColor={getScoreColor(metrics.code_quality_score)}
              showInfo={false}
              size="small"
            />
          </div>

          <div className="metric-item">
            <div className="metric-header">
              <SecurityScanOutlined /> 安全评分
              <span className="metric-score">{metrics.security_score.toFixed(1)}</span>
            </div>
            <Progress
              percent={metrics.security_score * 10}
              strokeColor={getScoreColor(metrics.security_score)}
              showInfo={false}
              size="small"
            />
          </div>

          <div className="metric-item">
            <div className="metric-header">
              <BugOutlined /> 测试覆盖率
              <span className="metric-score">{metrics.coverage_percentage.toFixed(1)}%</span>
            </div>
            <Progress
              percent={metrics.coverage_percentage}
              strokeColor={getScoreColor(metrics.coverage_percentage / 10)}
              showInfo={false}
              size="small"
            />
          </div>
        </Space>
      </div>

      <div className="error-summary">
        <Space split={<span style={{ color: '#d9d9d9' }}>|</span>}>
          <span>Ruff错误: <strong>{metrics.ruff_errors}</strong></span>
          <span>MyPy错误: <strong>{metrics.mypy_errors}</strong></span>
          <span>测试通过: <strong>{metrics.tests_passed}/{metrics.tests_run}</strong></span>
        </Space>
      </div>
    </Card>
  );
};

export default QualityScoreCard;
