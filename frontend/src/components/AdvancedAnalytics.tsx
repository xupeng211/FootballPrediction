/**
 * 高级分析组件
 *
 * Advanced Analytics Component
 *
 * 提供深度数据分析功能，包括：
 * - 预测准确率趋势分析
 * - 投注收益分析
 * - 比赛热力图
 * - 实时性能指标监控
 * - 智能投注建议
 * - 风险评估可视化
 */

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Progress,
  Typography,
  Space,
  Tag,
  Button,
  Select,
  DatePicker,
  Switch,
  Tooltip,
  Alert,
  Tabs,
  Table,
  Divider,
  Badge,
  Spin,
  Empty
} from 'antd';
import {
  LineChartOutlined,
  BarChartOutlined,
  PieChartOutlined,
  HeatMapOutlined,
  TrophyOutlined,
  RiseOutlined,
  FireOutlined,
  ThunderboltOutlined,
  EyeOutlined,
  DollarOutlined,
  AimOutlined,
  ExclamationCircleOutlined,
  InfoCircleOutlined,
  RocketOutlined,
  StarOutlined
} from '@ant-design/icons';
import { useWebSocket, useRealtimeEvent } from '../hooks/useWebSocket';
import { EVENT_TYPES } from '../services/websocket';

// 懒加载ECharts组件
const ReactECharts = React.lazy(() => import('echarts-for-react').then(module => ({ default: module.default })));

const { Text, Title } = Typography;
const { RangePicker } = DatePicker;
const { TabPane } = Tabs;

interface AdvancedAnalyticsProps {
  userId?: string;
  className?: string;
  height?: number;
  refreshInterval?: number;
}

interface PredictionTrend {
  date: string;
  accuracy: number;
  confidence: number;
  predictions: number;
  profit: number;
}

interface BettingAnalysis {
  bet_type: string;
  total_bets: number;
  win_rate: number;
  avg_odds: number;
  total_profit: number;
  roi: number;
  risk_level: 'low' | 'medium' | 'high';
}

interface MatchHeatmap {
  league: string;
  match_count: number;
  avg_confidence: number;
  accuracy_rate: number;
  hotness: number;
}

interface PerformanceMetrics {
  response_time: number;
  success_rate: number;
  throughput: number;
  error_rate: number;
  memory_usage: number;
  cpu_usage: number;
}

interface SmartRecommendation {
  match_id: number;
  home_team: string;
  away_team: string;
  recommendation: string;
  confidence: number;
  expected_value: number;
  risk_assessment: 'low' | 'medium' | 'high';
  reasoning: string[];
}

const AdvancedAnalytics: React.FC<AdvancedAnalyticsProps> = ({
  userId,
  className,
  height = 800,
  refreshInterval = 60000
}) => {
  // 状态管理
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('trends');
  const [dateRange, setDateRange] = useState<[any, any] | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [showDetails, setShowDetails] = useState(false);
  const [selectedLeague, setSelectedLeague] = useState<string>('all');
  const [selectedMetric, setSelectedMetric] = useState('accuracy');

  // 数据状态
  const [trendData, setTrendData] = useState<PredictionTrend[]>([]);
  const [bettingAnalysis, setBettingAnalysis] = useState<BettingAnalysis[]>([]);
  const [matchHeatmap, setMatchHeatmap] = useState<MatchHeatmap[]>([]);
  const [performanceMetrics, setPerformanceMetrics] = useState<PerformanceMetrics>({
    response_time: 0,
    success_rate: 0,
    throughput: 0,
    error_rate: 0,
    memory_usage: 0,
    cpu_usage: 0
  });
  const [recommendations, setRecommendations] = useState<SmartRecommendation[]>([]);

  // WebSocket连接
  const ws = useWebSocket({
    userId,
    autoConnect: true
  });

  // 监听实时事件
  useRealtimeEvent(EVENT_TYPES.PREDICTION_CREATED, (event) => {
    // 更新趋势数据
    updateTrendData(event.data);
  });

  useRealtimeEvent(EVENT_TYPES.ANALYTICS_UPDATED, (event) => {
    const { metric_name, value } = event.data;
    updatePerformanceMetrics(metric_name, value);
  });

  useRealtimeEvent(EVENT_TYPES.SYSTEM_ALERT, (event) => {
    // 处理系统告警
    handleSystemAlert(event.data);
  });

  // 更新趋势数据
  const updateTrendData = useCallback((newData: any) => {
    setTrendData(prev => {
      const today = new Date().toISOString().split('T')[0];
      const existingIndex = prev.findIndex(item => item.date === today);

      if (existingIndex >= 0) {
        const updated = [...prev];
        updated[existingIndex] = {
          ...updated[existingIndex],
          predictions: updated[existingIndex].predictions + 1,
          confidence: (updated[existingIndex].confidence + newData.confidence) / 2,
          accuracy: newData.accuracy || updated[existingIndex].accuracy,
          profit: (updated[existingIndex].profit || 0) + (newData.expected_value || 0)
        };
        return updated;
      } else {
        return [...prev, {
          date: today,
          accuracy: newData.accuracy || 0.75,
          confidence: newData.confidence || 0.7,
          predictions: 1,
          profit: newData.expected_value || 0
        }];
      }
    });
  }, []);

  // 更新性能指标
  const updatePerformanceMetrics = useCallback((metricName: string, value: number) => {
    setPerformanceMetrics(prev => {
      const updated = { ...prev };
      switch (metricName) {
        case 'response_time':
          updated.response_time = value;
          break;
        case 'success_rate':
          updated.success_rate = value;
          break;
        case 'throughput':
          updated.throughput = value;
          break;
        case 'error_rate':
          updated.error_rate = value;
          break;
        case 'memory_usage':
          updated.memory_usage = value;
          break;
        case 'cpu_usage':
          updated.cpu_usage = value;
          break;
      }
      return updated;
    });
  }, []);

  // 处理系统告警
  const handleSystemAlert = useCallback((alert: any) => {
    // 可以在这里实现告警处理逻辑
    console.warn('System alert received:', alert);
  }, []);

  // 生成模拟数据
  const generateMockData = useCallback(() => {
    // 生成趋势数据
    const trends: PredictionTrend[] = [];
    const today = new Date();
    for (let i = 29; i >= 0; i--) {
      const date = new Date(today);
      date.setDate(date.getDate() - i);
      trends.push({
        date: date.toISOString().split('T')[0],
        accuracy: 0.65 + Math.random() * 0.25,
        confidence: 0.7 + Math.random() * 0.25,
        predictions: Math.floor(Math.random() * 20) + 5,
        profit: (Math.random() - 0.3) * 10
      });
    }
    setTrendData(trends);

    // 生成投注分析数据
    const betting: BettingAnalysis[] = [
      {
        bet_type: '主胜',
        total_bets: 156,
        win_rate: 0.68,
        avg_odds: 2.15,
        total_profit: 245.50,
        roi: 0.12,
        risk_level: 'medium'
      },
      {
        bet_type: '平局',
        total_bets: 89,
        win_rate: 0.72,
        avg_odds: 3.25,
        total_profit: 156.80,
        roi: 0.18,
        risk_level: 'high'
      },
      {
        bet_type: '客胜',
        total_bets: 134,
        win_rate: 0.61,
        avg_odds: 2.85,
        total_profit: 98.20,
        roi: 0.08,
        risk_level: 'medium'
      },
      {
        bet_type: '大小球',
        total_bets: 201,
        win_rate: 0.75,
        avg_odds: 1.95,
        total_profit: 189.60,
        roi: 0.15,
        risk_level: 'low'
      }
    ];
    setBettingAnalysis(betting);

    // 生成比赛热力图数据
    const heatmap: MatchHeatmap[] = [
      {
        league: '英超',
        match_count: 45,
        avg_confidence: 0.78,
        accuracy_rate: 0.73,
        hotness: 0.85
      },
      {
        league: '西甲',
        match_count: 38,
        avg_confidence: 0.82,
        accuracy_rate: 0.76,
        hotness: 0.79
      },
      {
        league: '德甲',
        match_count: 32,
        avg_confidence: 0.75,
        accuracy_rate: 0.71,
        hotness: 0.73
      },
      {
        league: '意甲',
        match_count: 36,
        avg_confidence: 0.77,
        accuracy_rate: 0.74,
        hotness: 0.76
      },
      {
        league: '法甲',
        match_count: 28,
        avg_confidence: 0.73,
        accuracy_rate: 0.69,
        hotness: 0.68
      }
    ];
    setMatchHeatmap(heatmap);

    // 生成智能推荐
    const smartRecs: SmartRecommendation[] = [
      {
        match_id: 1001,
        home_team: '曼城',
        away_team: '利物浦',
        recommendation: '主胜',
        confidence: 0.82,
        expected_value: 0.15,
        risk_assessment: 'medium',
        reasoning: ['曼城主场优势明显', '利物浦近期状态不佳', '历史交锋曼城占优']
      },
      {
        match_id: 1002,
        home_team: '拜仁慕尼黑',
        away_team: '多特蒙德',
        recommendation: '大球',
        confidence: 0.75,
        expected_value: 0.12,
        risk_assessment: 'low',
        reasoning: ['两队进攻火力强', '防守端存在漏洞', '历史交锋多为进球大战']
      },
      {
        match_id: 1003,
        home_team: '巴黎圣日耳曼',
        away_team: '马赛',
        recommendation: '平局',
        confidence: 0.68,
        expected_value: 0.08,
        risk_assessment: 'high',
        reasoning: ['实力接近', '巴黎主力可能轮换', '马赛客场防守稳健']
      }
    ];
    setRecommendations(smartRecs);

    // 生成性能指标
    setPerformanceMetrics({
      response_time: 45 + Math.random() * 30,
      success_rate: 0.95 + Math.random() * 0.04,
      throughput: 120 + Math.random() * 50,
      error_rate: Math.random() * 0.02,
      memory_usage: 45 + Math.random() * 20,
      cpu_usage: 35 + Math.random() * 25
    });
  }, []);

  // 初始化数据
  useEffect(() => {
    generateMockData();
    setLoading(false);
  }, [generateMockData]);

  // 自动刷新
  useEffect(() => {
    if (!autoRefresh || !ws.isConnected) return;

    const interval = setInterval(() => {
      generateMockData();
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [autoRefresh, ws.isConnected, refreshInterval, generateMockData]);

  // 图表配置 - 预测准确率趋势
  const accuracyTrendOption = useMemo(() => ({
    title: {
      text: '预测准确率趋势',
      left: 'center',
      textStyle: { fontSize: 16, fontWeight: 'bold' }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' }
    },
    legend: {
      data: ['准确率', '置信度', '收益'],
      top: 30
    },
    xAxis: {
      type: 'category',
      data: trendData.map(item => item.date.substring(5))
    },
    yAxis: [
      {
        type: 'value',
        name: '百分比',
        min: 0,
        max: 1,
        axisLabel: { formatter: '{b}%' }
      },
      {
        type: 'value',
        name: '收益',
        position: 'right'
      }
    ],
    series: [
      {
        name: '准确率',
        type: 'line',
        data: trendData.map(item => (item.accuracy * 100).toFixed(1)),
        smooth: true,
        itemStyle: { color: '#52c41a' }
      },
      {
        name: '置信度',
        type: 'line',
        data: trendData.map(item => (item.confidence * 100).toFixed(1)),
        smooth: true,
        itemStyle: { color: '#1890ff' }
      },
      {
        name: '收益',
        type: 'bar',
        yAxisIndex: 1,
        data: trendData.map(item => item.profit.toFixed(2)),
        itemStyle: { color: '#faad14' }
      }
    ]
  }), [trendData]);

  // 图表配置 - 投注收益分析
  const bettingProfitOption = useMemo(() => ({
    title: {
      text: '投注收益分析',
      left: 'center',
      textStyle: { fontSize: 16, fontWeight: 'bold' }
    },
    tooltip: {
      trigger: 'item',
      formatter: '{a} <br/>{b}: {c} ({d}%)'
    },
    legend: {
      orient: 'vertical',
      left: 'left',
      top: 'middle'
    },
    series: [
      {
        name: '收益分布',
        type: 'pie',
        radius: ['40%', '70%'],
        data: bettingAnalysis.map(item => ({
          value: item.total_profit,
          name: item.bet_type,
          itemStyle: {
            color: item.risk_level === 'high' ? '#f5222d' :
                   item.risk_level === 'medium' ? '#faad14' : '#52c41a'
          }
        })),
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        }
      }
    ]
  }), [bettingAnalysis]);

  // 图表配置 - 比赛热力图
  const matchHeatmapOption = useMemo(() => ({
    title: {
      text: '联赛热度分析',
      left: 'center',
      textStyle: { fontSize: 16, fontWeight: 'bold' }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' }
    },
    xAxis: {
      type: 'category',
      data: matchHeatmap.map(item => item.league)
    },
    yAxis: {
      type: 'value',
      name: '热度指数'
    },
    series: [
      {
        name: '热度指数',
        type: 'bar',
        data: matchHeatmap.map(item => ({
          value: item.hotness * 100,
          itemStyle: {
            color: item.hotness > 0.8 ? '#f5222d' :
                   item.hotness > 0.7 ? '#faad14' : '#52c41a'
          }
        }))
      }
    ]
  }), [matchHeatmap]);

  // 获取风险等级颜色
  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'high': return '#f5222d';
      case 'medium': return '#faad14';
      case 'low': return '#52c41a';
      default: return '#d9d9d9';
    }
  };

  // 获取风险等级标签
  const getRiskTag = (risk: string) => {
    const colors = { high: 'red', medium: 'orange', low: 'green' };
    const texts = { high: '高风险', medium: '中风险', low: '低风险' };
    return <Tag color={colors[risk as keyof typeof colors]}>{texts[risk as keyof typeof texts]}</Tag>;
  };

  // 推荐表格列定义
  const recommendationColumns = [
    {
      title: '比赛',
      dataIndex: 'match',
      key: 'match',
      render: (record: SmartRecommendation) => (
        <div>
          <div style={{ fontWeight: 'bold' }}>
            {record.home_team} VS {record.away_team}
          </div>
          <div style={{ fontSize: '12px', color: '#666' }}>
            ID: {record.match_id}
          </div>
        </div>
      )
    },
    {
      title: '推荐',
      dataIndex: 'recommendation',
      key: 'recommendation',
      render: (text: string, record: SmartRecommendation) => (
        <div>
          <Tag color="blue">{text}</Tag>
          <div style={{ fontSize: '12px', color: '#666', marginTop: 4 }}>
            置信度: {(record.confidence * 100).toFixed(1)}%
          </div>
        </div>
      )
    },
    {
      title: '期望收益',
      dataIndex: 'expected_value',
      key: 'expected_value',
      render: (value: number) => (
        <span style={{ color: value > 0 ? '#52c41a' : '#f5222d' }}>
          {value > 0 ? '+' : ''}{value.toFixed(3)}
        </span>
      )
    },
    {
      title: '风险等级',
      dataIndex: 'risk_assessment',
      key: 'risk_assessment',
      render: (risk: string) => getRiskTag(risk)
    },
    {
      title: '分析依据',
      dataIndex: 'reasoning',
      key: 'reasoning',
      render: (reasons: string[]) => (
        <div>
          {reasons.map((reason, index) => (
            <div key={index} style={{ fontSize: '12px', color: '#666' }}>
              • {reason}
            </div>
          ))}
        </div>
      )
    }
  ];

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" tip="正在加载高级分析数据..." />
      </div>
    );
  }

  return (
    <div className={className} style={{ height }}>
      {/* 顶部控制栏 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col>
            <Space>
              <Text>时间范围:</Text>
              <RangePicker
                value={dateRange}
                onChange={setDateRange}
                placeholder={['开始日期', '结束日期']}
              />
            </Space>
          </Col>
          <Col>
            <Space>
              <Text>联赛:</Text>
              <Select
                value={selectedLeague}
                onChange={setSelectedLeague}
                style={{ width: 120 }}
              >
                <Select.Option value="all">全部联赛</Select.Option>
                <Select.Option value="premier">英超</Select.Option>
                <Select.Option value="laliga">西甲</Select.Option>
                <Select.Option value="bundesliga">德甲</Select.Option>
                <Select.Option value="seriea">意甲</Select.Option>
                <Select.Option value="ligue1">法甲</Select.Option>
              </Select>
            </Space>
          </Col>
          <Col>
            <Space>
              <Text>自动刷新:</Text>
              <Switch
                checked={autoRefresh}
                onChange={setAutoRefresh}
                disabled={!ws.isConnected}
              />
              <Badge
                status={ws.isConnected ? 'success' : 'error'}
                text={ws.isConnected ? '已连接' : '未连接'}
              />
            </Space>
          </Col>
          <Col>
            <Button
              type="primary"
              icon={<RocketOutlined />}
              onClick={generateMockData}
            >
              刷新数据
            </Button>
          </Col>
        </Row>
      </Card>

      {/* 主要内容区域 */}
      <Tabs activeKey={activeTab} onChange={setActiveTab}>
        {/* 趋势分析 */}
        <TabPane tab={<span><LineChartOutlined />趋势分析</span>} key="trends">
          <Row gutter={[16, 16]}>
            <Col span={24}>
              <Card title="预测准确率趋势" extra={<Tooltip title="显示最近30天的预测准确率和置信度趋势"><InfoCircleOutlined /></Tooltip>}>
                <ReactECharts
                  option={accuracyTrendOption}
                  style={{ height: 400 }}
                  notMerge={true}
                  lazyUpdate={true}
                />
              </Card>
            </Col>
          </Row>
        </TabPane>

        {/* 投注分析 */}
        <TabPane tab={<span><DollarOutlined />投注分析</span>} key="betting">
          <Row gutter={[16, 16]}>
            <Col xs={24} lg={12}>
              <Card title="投注收益分布">
                <ReactECharts
                  option={bettingProfitOption}
                  style={{ height: 300 }}
                  notMerge={true}
                  lazyUpdate={true}
                />
              </Card>
            </Col>
            <Col xs={24} lg={12}>
              <Card title="投注类型统计">
                <Table
                  dataSource={bettingAnalysis}
                  rowKey="bet_type"
                  size="small"
                  pagination={false}
                  columns={[
                    { title: '投注类型', dataIndex: 'bet_type', key: 'bet_type' },
                    { title: '总投注', dataIndex: 'total_bets', key: 'total_bets' },
                    { title: '胜率', dataIndex: 'win_rate', key: 'win_rate', render: (v) => `${(v * 100).toFixed(1)}%` },
                    { title: 'ROI', dataIndex: 'roi', key: 'roi', render: (v) => `${(v * 100).toFixed(1)}%` },
                    { title: '风险', dataIndex: 'risk_level', key: 'risk_level', render: (v) => getRiskTag(v) }
                  ]}
                />
              </Card>
            </Col>
          </Row>
        </TabPane>

        {/* 联赛热度 */}
        <TabPane tab={<span><HeatMapOutlined />联赛热度</span>} key="heatmap">
          <Row gutter={[16, 16]}>
            <Col span={24}>
              <Card title="联赛热度分析">
                <ReactECharts
                  option={matchHeatmapOption}
                  style={{ height: 350 }}
                  notMerge={true}
                  lazyUpdate={true}
                />
              </Card>
            </Col>
            <Col span={24}>
              <Card title="联赛详细数据">
                <Row gutter={16}>
                  {matchHeatmap.map((league, index) => (
                    <Col xs={24} sm={12} md={8} lg={6} key={index}>
                      <div style={{
                        padding: '16px',
                        border: '1px solid #f0f0f0',
                        borderRadius: '6px',
                        marginBottom: '16px'
                      }}>
                        <div style={{ fontWeight: 'bold', marginBottom: '8px' }}>
                          {league.league}
                        </div>
                        <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>
                          比赛场次: {league.match_count}
                        </div>
                        <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>
                          平均置信度: {(league.avg_confidence * 100).toFixed(1)}%
                        </div>
                        <div style={{ fontSize: '12px', color: '#666', marginBottom: '8px' }}>
                          准确率: {(league.accuracy_rate * 100).toFixed(1)}%
                        </div>
                        <Progress
                          percent={league.hotness * 100}
                          size="small"
                          strokeColor={getRiskColor(league.hotness > 0.8 ? 'high' : league.hotness > 0.7 ? 'medium' : 'low')}
                        />
                      </div>
                    </Col>
                  ))}
                </Row>
              </Card>
            </Col>
          </Row>
        </TabPane>

        {/* 智能推荐 */}
        <TabPane tab={<span><StarOutlined />智能推荐</span>} key="recommendations">
          <Card
            title="AI智能投注推荐"
            extra={
              <Space>
                <Badge count={recommendations.length} showZero>
                  <Button size="small" icon={<ThunderboltOutlined />}>
                    生成新推荐
                  </Button>
                </Badge>
                <Tooltip title="基于机器学习的智能投注建议">
                  <InfoCircleOutlined />
                </Tooltip>
              </Space>
            }
          >
            {recommendations.length > 0 ? (
              <Table
                dataSource={recommendations}
                rowKey="match_id"
                columns={recommendationColumns}
                pagination={false}
                size="small"
              />
            ) : (
              <Empty description="暂无推荐数据" />
            )}
          </Card>
        </TabPane>

        {/* 性能监控 */}
        <TabPane tab={<span><AimOutlined />性能监控</span>} key="performance">
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={12} md={8}>
              <Card size="small">
                <Statistic
                  title="响应时间"
                  value={performanceMetrics.response_time}
                  suffix="ms"
                  prefix={<LineChartOutlined />}
                  valueStyle={{
                    color: performanceMetrics.response_time > 100 ? '#f5222d' : '#52c41a'
                  }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={8}>
              <Card size="small">
                <Statistic
                  title="成功率"
                  value={(performanceMetrics.success_rate * 100).toFixed(2)}
                  suffix="%"
                  prefix={<TrophyOutlined />}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={8}>
              <Card size="small">
                <Statistic
                  title="吞吐量"
                  value={performanceMetrics.throughput}
                  suffix="req/s"
                  prefix={<ThunderboltOutlined />}
                  valueStyle={{ color: '#1890ff' }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={8}>
              <Card size="small">
                <Statistic
                  title="错误率"
                  value={(performanceMetrics.error_rate * 100).toFixed(3)}
                  suffix="%"
                  prefix={<ExclamationCircleOutlined />}
                  valueStyle={{
                    color: performanceMetrics.error_rate > 0.01 ? '#f5222d' : '#52c41a'
                  }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={8}>
              <Card size="small">
                <div>
                  <Text type="secondary">内存使用率</Text>
                  <Progress
                    percent={performanceMetrics.memory_usage}
                    size="small"
                    strokeColor={performanceMetrics.memory_usage > 80 ? '#f5222d' : '#52c41a'}
                  />
                </div>
              </Card>
            </Col>
            <Col xs={24} sm={12} md={8}>
              <Card size="small">
                <div>
                  <Text type="secondary">CPU使用率</Text>
                  <Progress
                    percent={performanceMetrics.cpu_usage}
                    size="small"
                    strokeColor={performanceMetrics.cpu_usage > 80 ? '#f5222d' : '#52c41a'}
                  />
                </div>
              </Card>
            </Col>
          </Row>
        </TabPane>
      </Tabs>

      {/* 底部状态栏 */}
      <Card size="small" style={{ marginTop: 16 }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Space>
              <Text type="secondary">数据更新时间: {new Date().toLocaleString()}</Text>
              <Divider type="vertical" />
              <Badge
                status={ws.isConnected ? 'success' : 'error'}
                text={`WebSocket: ${ws.isConnected ? '已连接' : '未连接'}`}
              />
            </Space>
          </Col>
          <Col>
            <Space>
              <Switch
                checked={showDetails}
                onChange={setShowDetails}
                size="small"
              />
              <Text type="secondary">显示详细信息</Text>
            </Space>
          </Col>
        </Row>
      </Card>
    </div>
  );
};

export default AdvancedAnalytics;
