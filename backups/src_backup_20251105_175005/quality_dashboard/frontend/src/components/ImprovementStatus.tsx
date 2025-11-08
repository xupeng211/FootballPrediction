import React, { useState, useEffect } from 'react';
import { Card, Progress, Statistic, Row, Col, Tag, Space, Button } from 'antd';
import {
  RocketOutlined,
  CheckCircleOutlined,
  SyncOutlined,
  FireOutlined
} from '@ant-design/icons';
import { useWebSocket } from '../contexts/WebSocketContext';
import './ImprovementStatus.css';

interface ImprovementEngineStatus {
  isRunning: boolean;
  pid?: number;
  totalCycles: number;
  successCycles: number;
  averageImprovement: number;
  lastCycleTime: string;
  nextRunTime: string;
}

const ImprovementStatus: React.FC = () => {
  const { metrics } = useWebSocket();
  const [engineStatus, setEngineStatus] = useState<ImprovementEngineStatus>({
    isRunning: false,
    totalCycles: 0,
    successCycles: 0,
    averageImprovement: 0,
    lastCycleTime: '',
    nextRunTime: ''
  });

  useEffect(() => {
    fetchEngineStatus();
    const interval = setInterval(fetchEngineStatus, 10000); // 每10秒检查一次
    return () => clearInterval(interval);
  }, []);

  const fetchEngineStatus = async () => {
    try {
      const response = await fetch('/api/system/status');
      const data = await response.json();

      // 模拟引擎状态数据
      setEngineStatus({
        isRunning: true,
        pid: 5292,
        totalCycles: metrics?.improvement_cycles || 6,
        successCycles: Math.floor((metrics?.improvement_cycles || 6) * 0.33),
        averageImprovement: 4.17,
        lastCycleTime: new Date(Date.now() - 15 * 60 * 1000).toISOString(), // 15分钟前
        nextRunTime: new Date(Date.now() + 15 * 60 * 1000).toISOString() // 15分钟后
      });
    } catch (error) {
      console.error('获取引擎状态失败:', error);
    }
  };

  const successRate = engineStatus.totalCycles > 0
    ? (engineStatus.successCycles / engineStatus.totalCycles) * 100
    : 0;

  const getProgressColor = (rate: number): string => {
    if (rate >= 70) return '#52c41a';
    if (rate >= 50) return '#faad14';
    return '#ff4d4f';
  };

  const getNextRunCountdown = (): string => {
    const now = new Date();
    const nextRun = new Date(engineStatus.nextRunTime);
    const diff = nextRun.getTime() - now.getTime();

    if (diff <= 0) return '运行中...';

    const minutes = Math.floor(diff / (1000 * 60));
    const seconds = Math.floor((diff % (1000 * 60)) / 1000);

    return `${minutes}分${seconds}秒`;
  };

  return (
    <Card
      title={
        <Space>
          <RocketOutlined />
          <span>持续改进引擎</span>
          {engineStatus.isRunning ? (
            <Tag color="green" icon={<SyncOutlined spin />}>
              运行中
            </Tag>
          ) : (
            <Tag color="red" icon={<CheckCircleOutlined />}>
              已停止
            </Tag>
          )}
        </Space>
      }
      className="improvement-status-card"
      extra={
        <Button size="small" type="primary" ghost>
          配置
        </Button>
      }
    >
      <div className="engine-overview">
        <Row gutter={16}>
          <Col span={12}>
            <Statistic
              title="总改进周期"
              value={engineStatus.totalCycles}
              prefix={<FireOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Col>
          <Col span={12}>
            <Statistic
              title="成功率"
              value={successRate}
              precision={1}
              suffix="%"
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: getProgressColor(successRate) }}
            />
          </Col>
        </Row>
      </div>

      <div className="progress-section">
        <div className="progress-item">
          <div className="progress-header">
            <span>改进成功率</span>
            <span className="progress-value">{successRate.toFixed(1)}%</span>
          </div>
          <Progress
            percent={successRate}
            strokeColor={getProgressColor(successRate)}
            size="small"
            showInfo={false}
          />
        </div>

        <div className="progress-item">
          <div className="progress-header">
            <span>平均改进幅度</span>
            <span className="progress-value">+{engineStatus.averageImprovement}</span>
          </div>
          <Progress
            percent={Math.min(100, engineStatus.averageImprovement * 10)}
            strokeColor="#52c41a"
            size="small"
            showInfo={false}
          />
        </div>
      </div>

      <div className="timing-info">
        <div className="timing-item">
          <span className="timing-label">上次运行:</span>
          <span className="timing-value">
            {engineStatus.lastCycleTime
              ? new Date(engineStatus.lastCycleTime).toLocaleString('zh-CN', {
                  month: 'short',
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit'
                })
              : '未知'}
          </span>
        </div>

        <div className="timing-item">
          <span className="timing-label">下次运行:</span>
          <span className="timing-value">
            {getNextRunCountdown()}
          </span>
        </div>
      </div>

      {engineStatus.pid && (
        <div className="engine-details">
          <Space split={<span style={{ color: '#d9d9d9' }}>|</span>}>
            <span>PID: <strong>{engineStatus.pid}</strong></span>
            <span>间隔: <strong>30分钟</strong></span>
            <span>状态: <strong>自动</strong></span>
          </Space>
        </div>
      )}
    </Card>
  );
};

export default ImprovementStatus;