import React, { useState } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Button,
  Tag,
  Tooltip,
  Alert,
  Space,
  Progress,
  Table,
  Modal,
  InputNumber,
  Switch,
} from 'antd';
import {
  DollarCircleOutlined,
  TrophyOutlined,
  ExclamationCircleOutlined,
  InfoCircleOutlined,
  CalculatorOutlined,
  StarOutlined,
  LineChartOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { PredictionResponse } from '../services/api';

interface BettingRecommendationProps {
  prediction: PredictionResponse;
  odds?: {
    home_win: number;
    draw: number;
    away_win: number;
  };
  bankroll?: number;
}

interface BettingStrategy {
  name: string;
  description: string;
  kellyFraction: number;
  riskLevel: 'low' | 'medium' | 'high';
}

const BettingRecommendation: React.FC<BettingRecommendationProps> = ({
  prediction,
  odds,
  bankroll = 1000,
}) => {
  const [selectedStrategy, setSelectedStrategy] = useState<string>('kelly');
  const [customBankroll, setCustomBankroll] = useState<number>(bankroll);
  const [showDetails, setShowDetails] = useState<boolean>(false);

  // 计算期望收益 (EV)
  const calculateEV = (probability: number, decimalOdds: number): number => {
    return (probability * decimalOdds) - 1;
  };

  // 计算凯利准则投注比例
  const calculateKellyFraction = (probability: number, decimalOdds: number): number => {
    const kelly = (probability * decimalOdds - 1) / (decimalOdds - 1);
    return Math.max(0, Math.min(kelly, 0.25)); // 限制最大投注比例为25%
  };

  // 获取投注策略
  const getBettingStrategies = (): BettingStrategy[] => {
    if (!odds) return [];

    const homeWinEV = calculateEV(prediction.home_win_prob, odds.home_win);
    const drawEV = calculateEV(prediction.draw_prob, odds.draw);
    const awayWinEV = calculateEV(prediction.away_win_prob, odds.away_win);

    const bestEV = Math.max(homeWinEV, drawEV, awayWinEV);
    const bestOutcome = bestEV === homeWinEV ? 'home_win' :
                      bestEV === drawEV ? 'draw' : 'away_win';

    const bestOdds = bestOutcome === 'home_win' ? odds.home_win :
                     bestOutcome === 'draw' ? odds.draw : odds.away_win;
    const bestProb = bestOutcome === 'home_win' ? prediction.home_win_prob :
                    bestOutcome === 'draw' ? prediction.draw_prob : prediction.away_win_prob;

    return [
      {
        name: 'kelly',
        description: '凯利准则 - 数学最优投注比例',
        kellyFraction: calculateKellyFraction(bestProb, bestOdds),
        riskLevel: 'medium',
      },
      {
        name: 'conservative',
        description: '保守策略 - 凯利准则的50%',
        kellyFraction: calculateKellyFraction(bestProb, bestOdds) * 0.5,
        riskLevel: 'low',
      },
      {
        name: 'aggressive',
        description: '激进策略 - 凯利准则的150%',
        kellyFraction: calculateKellyFraction(bestProb, bestOdds) * 1.5,
        riskLevel: 'high',
      },
      {
        name: 'fixed',
        description: '固定比例 - 总资金的5%',
        kellyFraction: 0.05,
        riskLevel: 'low',
      },
    ];
  };

  // 获取推荐投注
  const getRecommendation = () => {
    if (!odds) return null;

    const homeWinEV = calculateEV(prediction.home_win_prob, odds.home_win);
    const drawEV = calculateEV(prediction.draw_prob, odds.draw);
    const awayWinEV = calculateEV(prediction.away_win_prob, odds.away_win);

    const outcomes = [
      { name: 'home_win', label: '主胜', ev: homeWinEV, prob: prediction.home_win_prob, odds: odds.home_win },
      { name: 'draw', label: '平局', ev: drawEV, prob: prediction.draw_prob, odds: odds.draw },
      { name: 'away_win', label: '客胜', ev: awayWinEV, prob: prediction.away_win_prob, odds: odds.away_win },
    ];

    // 找到EV最高的结果
    const bestOutcome = outcomes.reduce((best, current) =>
      current.ev > best.ev ? current : best
    );

    return bestOutcome;
  };

  // 获取风险等级
  const getRiskLevel = (ev: number): { level: string; color: string; icon: React.ReactNode } => {
    if (ev > 0.15) {
      return { level: '低风险', color: 'green', icon: <StarOutlined /> };
    } else if (ev > 0.05) {
      return { level: '中风险', color: 'orange', icon: <ExclamationCircleOutlined /> };
    } else if (ev > 0) {
      return { level: '高风险', color: 'red', icon: <ExclamationCircleOutlined /> };
    } else {
      return { level: '不推荐', color: 'default', icon: <ExclamationCircleOutlined /> };
    }
  };

  // 获取投注建议表格数据
  const getBettingTableData = () => {
    if (!odds) return [];

    return [
      {
        key: 'home_win',
        outcome: '主胜',
        probability: `${Math.round(prediction.home_win_prob * 100)}%`,
        odds: odds.home_win.toFixed(2),
        ev: calculateEV(prediction.home_win_prob, odds.home_win).toFixed(3),
        recommendation: getRecommendation()?.name === 'home_win' ? '推荐' : '',
      },
      {
        key: 'draw',
        outcome: '平局',
        probability: `${Math.round(prediction.draw_prob * 100)}%`,
        odds: odds.draw.toFixed(2),
        ev: calculateEV(prediction.draw_prob, odds.draw).toFixed(3),
        recommendation: getRecommendation()?.name === 'draw' ? '推荐' : '',
      },
      {
        key: 'away_win',
        outcome: '客胜',
        probability: `${Math.round(prediction.away_win_prob * 100)}%`,
        odds: odds.away_win.toFixed(2),
        ev: calculateEV(prediction.away_win_prob, odds.away_win).toFixed(3),
        recommendation: getRecommendation()?.name === 'away_win' ? '推荐' : '',
      },
    ];
  };

  // 计算投注收益图表配置
  const getProfitChartOption = () => {
    if (!odds) return {};

    const outcomes = ['主胜', '平局', '客胜'];
    const probabilities = [
      prediction.home_win_prob,
      prediction.draw_prob,
      prediction.away_win_prob,
    ];
    const oddsValues = [odds.home_win, odds.draw, odds.away_win];

    return {
      title: {
        text: '投注收益分析',
        left: 'center',
        textStyle: { fontSize: 16, fontWeight: 'bold' },
      },
      tooltip: {
        trigger: 'axis',
        formatter: (params: any) => {
          const index = params[0].dataIndex;
          const outcome = outcomes[index];
          const prob = probabilities[index];
          const odd = oddsValues[index];
          const ev = calculateEV(prob, odd);
          return `${outcome}<br/>
                  概率: ${(prob * 100).toFixed(1)}%<br/>
                  赔率: ${odd.toFixed(2)}<br/>
                  期望收益: ${ev.toFixed(3)}`;
        },
      },
      xAxis: {
        type: 'category',
        data: outcomes,
      },
      yAxis: {
        type: 'value',
        name: '期望收益 (EV)',
        axisLabel: {
          formatter: '{value}',
        },
      },
      series: [
        {
          name: '期望收益',
          type: 'bar',
          data: outcomes.map((outcome, index) => {
            const ev = calculateEV(probabilities[index], oddsValues[index]);
            return {
              value: ev,
              itemStyle: {
                color: ev > 0 ? '#52c41a' : '#ff4d4f',
              },
            };
          }),
          label: {
            show: true,
            position: 'top',
            formatter: (params: any) => params.value.toFixed(3),
          },
        },
      ],
    };
  };

  const recommendation = getRecommendation();
  const strategies = getBettingStrategies();
  const selectedStrategyData = strategies.find(s => s.name === selectedStrategy);
  const riskInfo = recommendation ? getRiskLevel(recommendation.ev) : null;

  const tableColumns = [
    {
      title: '结果',
      dataIndex: 'outcome',
      key: 'outcome',
    },
    {
      title: '概率',
      dataIndex: 'probability',
      key: 'probability',
    },
    {
      title: '赔率',
      dataIndex: 'odds',
      key: 'odds',
    },
    {
      title: '期望收益',
      dataIndex: 'ev',
      key: 'ev',
      render: (ev: string) => (
        <span style={{ color: parseFloat(ev) > 0 ? '#52c41a' : '#ff4d4f' }}>
          {parseFloat(ev) > 0 ? '+' : ''}{ev}
        </span>
      ),
    },
    {
      title: '推荐',
      dataIndex: 'recommendation',
      key: 'recommendation',
      render: (rec: string) => rec && <Tag color="green">{rec}</Tag>,
    },
  ];

  if (!odds) {
    return (
      <Alert
        message="缺少赔率数据"
        description="无法生成投注建议，请提供赔率信息"
        type="warning"
        showIcon
      />
    );
  }

  return (
    <div className="betting-recommendation">
      {/* 推荐概览 */}
      <Card
        title={
          <Space>
            <DollarCircleOutlined />
            投注建议分析
          </Space>
        }
        extra={
          <Button
            icon={<InfoCircleOutlined />}
            onClick={() => setShowDetails(true)}
          >
            详细分析
          </Button>
        }
        style={{ marginBottom: 16 }}
      >
        <Row gutter={[16, 16]}>
          <Col xs={24} md={8}>
            <Statistic
              title="推荐投注"
              value={recommendation?.label || '-'}
              prefix={<TrophyOutlined />}
              valueStyle={{
                color: recommendation && recommendation.ev > 0 ? '#52c41a' : '#ff4d4f'
              }}
            />
          </Col>
          <Col xs={24} md={8}>
            <Statistic
              title="期望收益 (EV)"
              value={recommendation?.ev.toFixed(3) || '0.000'}
              precision={3}
              valueStyle={{
                color: recommendation && recommendation.ev > 0 ? '#52c41a' : '#ff4d4f'
              }}
              prefix={recommendation && recommendation.ev > 0 ? '+' : ''}
            />
          </Col>
          <Col xs={24} md={8}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ marginBottom: 8 }}>
                {riskInfo?.icon} {riskInfo?.level}
              </div>
              <Tag color={riskInfo?.color}>
                {prediction?.confidence ?
                  `置信度: ${Math.round(prediction.confidence * 100)}%` :
                  '低置信度'
                }
              </Tag>
            </div>
          </Col>
        </Row>

        {recommendation && recommendation.ev > 0 && (
          <Alert
            message="投注建议"
            description={
              <div>
                <p>基于数学模型分析，建议<strong>{recommendation.label}</strong>。</p>
                <p>当前期望收益为 <strong>{recommendation.ev.toFixed(3)}</strong>，属于{riskInfo?.level}投注机会。</p>
                <p>建议采用凯利准则进行资金管理，单次投注不超过总资金的25%。</p>
              </div>
            }
            type="success"
            showIcon
            style={{ marginTop: 16 }}
          />
        )}

        {recommendation && recommendation.ev <= 0 && (
          <Alert
            message="不推荐投注"
            description={
              <div>
                <p>当前所有选项的期望收益都小于等于0，不建议进行投注。</p>
                <p>建议等待更有利的赔率机会或寻找其他比赛。</p>
              </div>
            }
            type="warning"
            showIcon
            style={{ marginTop: 16 }}
          />
        )}
      </Card>

      {/* 投注策略选择 */}
      <Card title="投注策略" style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]} align="middle">
          <Col xs={24} md={12}>
            <div>
              <div style={{ marginBottom: 16 }}>
                <strong>总资金:</strong>
              </div>
              <InputNumber
                value={customBankroll}
                onChange={(value) => setCustomBankroll(value || 1000)}
                min={100}
                max={100000}
                step={100}
                prefix="¥"
                style={{ width: '100%' }}
              />
            </div>
          </Col>
          <Col xs={24} md={12}>
            <div>
              <div style={{ marginBottom: 16 }}>
                <strong>投注策略:</strong>
              </div>
              <select
                value={selectedStrategy}
                onChange={(e) => setSelectedStrategy(e.target.value)}
                style={{ width: '100%', padding: '8px' }}
              >
                {strategies.map(strategy => (
                  <option key={strategy.name} value={strategy.name}>
                    {strategy.description}
                  </option>
                ))}
              </select>
            </div>
          </Col>
        </Row>

        {selectedStrategyData && (
          <div style={{ marginTop: 16 }}>
            <Row gutter={[16, 16]}>
              <Col xs={24} md={8}>
                <Statistic
                  title="建议投注额"
                  value={customBankroll * selectedStrategyData.kellyFraction}
                  precision={2}
                  prefix="¥"
                  valueStyle={{ color: '#1890ff' }}
                />
              </Col>
              <Col xs={24} md={8}>
                <Statistic
                  title="投注比例"
                  value={selectedStrategyData.kellyFraction * 100}
                  precision={1}
                  suffix="%"
                  valueStyle={{ color: '#52c41a' }}
                />
              </Col>
              <Col xs={24} md={8}>
                <div style={{ textAlign: 'center' }}>
                  <Tag color={
                    selectedStrategyData.riskLevel === 'low' ? 'green' :
                    selectedStrategyData.riskLevel === 'medium' ? 'orange' : 'red'
                  }>
                    {selectedStrategyData.riskLevel === 'low' ? '低风险' :
                     selectedStrategyData.riskLevel === 'medium' ? '中风险' : '高风险'}
                  </Tag>
                </div>
              </Col>
            </Row>
          </div>
        )}
      </Card>

      {/* 收益分析图表 */}
      <Card title="期望收益分析" style={{ marginBottom: 16 }}>
        <ReactECharts
          option={getProfitChartOption()}
          style={{ height: 300 }}
          notMerge={true}
          lazyUpdate={true}
        />
      </Card>

      {/* 详细分析模态框 */}
      <Modal
        title="详细投注分析"
        visible={showDetails}
        onCancel={() => setShowDetails(false)}
        footer={null}
        width={800}
      >
        <Table
          columns={tableColumns}
          dataSource={getBettingTableData()}
          pagination={false}
          size="small"
          style={{ marginBottom: 16 }}
        />

        <Alert
          message="重要提醒"
          description={
            <ul>
              <li>投注有风险，决策需谨慎</li>
              <li>凯利准则假设概率估计准确</li>
              <li>建议分散投注，避免集中风险</li>
              <li>长期来看，只有正EV的投注才能盈利</li>
              <li>请根据自身风险承受能力调整投注策略</li>
            </ul>
          }
          type="info"
          showIcon
        />
      </Modal>
    </div>
  );
};

export default BettingRecommendation;