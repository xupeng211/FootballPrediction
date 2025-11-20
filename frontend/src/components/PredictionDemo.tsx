import React from 'react';
import { Card, Row, Col, Typography, Space } from 'antd';
import PredictionChart from './PredictionChart';

const { Title, Text } = Typography;

const PredictionDemo: React.FC = () => {
  // 模拟预测数据 - 符合SRS要求
  const mockPrediction = {
    home_win_prob: 0.58,
    draw_prob: 0.23,
    away_win_prob: 0.19,
    confidence: 0.85,
    prediction: 'home_win' as const,
    match_id: 12345,
    ev: 0.12,
    suggestion: '投注主胜'
  };

  return (
    <div style={{ padding: '20px' }}>
      <Title level={2}>预测图表演示</Title>

      <Row gutter={[16, 16]}>
        <Col span={12}>
          <Card title="使用简单接口 (符合SRS任务要求)" style={{ height: '400px' }}>
            <PredictionChart
              home_prob={0.6}
              draw_prob={0.25}
              away_prob={0.15}
              title="曼城 vs 切尔西预测"
              height={300}
            />
          </Card>
        </Col>

        <Col span={12}>
          <Card title="使用PredictionResponse接口 (兼容现有代码)" style={{ height: '400px' }}>
            <PredictionChart
              prediction={mockPrediction}
              title={mockPrediction.suggestion}
              height={300}
            />
          </Card>
        </Col>
      </Row>

      <Row style={{ marginTop: '20px' }}>
        <Col span={24}>
          <Card title="数据说明">
            <Space direction="vertical" size="small">
              <Text>• <strong>主胜概率</strong>: 60% (绿色) - 推荐投注</Text>
              <Text>• <strong>平局概率</strong>: 25% (灰色)</Text>
              <Text>• <strong>客胜概率</strong>: 15% (红色)</Text>
              <Text>• <strong>置信度</strong>: 85%</Text>
              <Text>• <strong>期望收益</strong>: 12%</Text>
            </Space>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default PredictionDemo;