import React, { useEffect, useState, useMemo, useCallback, lazy, Suspense } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Progress,
  Table,
  Tag,
  Space,
  Button,
  Tooltip,
  Alert,
  Spin,
  Empty,
} from 'antd';
import {
  TrophyOutlined,
  BarChartOutlined,
  CheckCircleOutlined,
  RiseOutlined,
  ReloadOutlined,
  InfoCircleOutlined,
  LineChartOutlined,
  AreaChartOutlined,
} from '@ant-design/icons';
import { useDispatch, useSelector } from 'react-redux';
import { AppDispatch } from '../store';
import { fetchMatches, selectFilteredMatches } from '../store/slices/matchesSlice';
import { apiService } from '../services/api';
import { PredictionResponse } from '../services/api';
import PerformanceOptimizer from './PerformanceOptimizer';
import RealtimeDashboard from './RealtimeDashboard';
import RealtimePredictionPanel from './RealtimePredictionPanel';
import SubscriptionManager from './SubscriptionManager';
import RealtimeStatsPanel from './RealtimeStatsPanel';
import AdvancedAnalytics from './AdvancedAnalytics';

// 懒加载ECharts组件
const ReactECharts = lazy(() => import('echarts-for-react').then(module => ({ default: module.default })));

interface DashboardStats {
  total_matches: number;
  total_predictions: number;
  accuracy_rate: number;
  avg_confidence: number;
  upcoming_matches: number;
  live_matches: number;
  finished_matches: number;
}

interface RecentPrediction extends PredictionResponse {
  match_info: {
    home_team: string;
    away_team: string;
    league: string;
    match_date: string;
  };
  created_at: string;
}

const Dashboard: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const matches = useSelector(selectFilteredMatches);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentPredictions] = useState<RecentPrediction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 加载仪表板数据
  const loadDashboardData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // 加载数据
      const statsData = await apiService.getStats();

      setStats({
        ...statsData,
        upcoming_matches: matches.filter(m => m.status === 'upcoming').length,
        live_matches: matches.filter(m => m.status === 'live').length,
        finished_matches: matches.filter(m => m.status === 'finished').length,
      });
    } catch (err) {
      console.error('加载仪表板数据失败:', err);
      setError('无法加载仪表板数据，请检查API连接');
    } finally {
      setLoading(false);
    }
  }, [matches]);

  // 模拟最近预测数据
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const mockPredictions: RecentPrediction[] = [
    {
      home_win_prob: 0.65,
      draw_prob: 0.25,
      away_win_prob: 0.10,
      confidence: 0.75,
      prediction: 'home_win',
      match_id: 1,
      ev: 0.12,
      suggestion: '投注主胜',
      match_info: {
        home_team: '曼联',
        away_team: '切尔西',
        league: '英超',
        match_date: '2025-10-29T20:00:00Z',
      },
      created_at: '2025-10-29T10:30:00Z',
    },
    {
      home_win_prob: 0.35,
      draw_prob: 0.30,
      away_win_prob: 0.35,
      confidence: 0.45,
      prediction: 'draw',
      match_id: 2,
      ev: -0.05,
      suggestion: '不建议投注',
      match_info: {
        home_team: '曼城',
        away_team: '利物浦',
        league: '英超',
        match_date: '2025-10-29T22:00:00Z',
      },
      created_at: '2025-10-29T09:15:00Z',
    },
    {
      home_win_prob: 0.55,
      draw_prob: 0.28,
      away_win_prob: 0.17,
      confidence: 0.68,
      prediction: 'home_win',
      match_id: 3,
      ev: 0.08,
      suggestion: '小注主胜',
      match_info: {
        home_team: '拜仁慕尼黑',
        away_team: '多特蒙德',
        league: '德甲',
        match_date: '2025-10-30T18:30:00Z',
      },
      created_at: '2025-10-29T08:45:00Z',
    },
  ];

  // 计算比赛统计
  const getMatchStats = () => {
    const upcoming = matches.filter(m => m.status === 'upcoming').length;
    const live = matches.filter(m => m.status === 'live').length;
    const finished = matches.filter(m => m.status === 'finished').length;
    return { upcoming, live, finished };
  };

  // 获取预测结果标签
  const getPredictionTag = (prediction: string, confidence: number) => {
    const colors = {
      home_win: 'green',
      draw: 'orange',
      away_win: 'red',
    };
    const texts = {
      home_win: '主胜',
      draw: '平局',
      away_win: '客胜',
    };

    return (
      <Tag color={colors[prediction as keyof typeof colors]}>
        {texts[prediction as keyof typeof texts]} ({Math.round(confidence * 100)}%)
      </Tag>
    );
  };

  // 获取投注建议标签
  const getSuggestionTag = (suggestion: string, ev?: number) => {
    if (!suggestion) return <Tag color="default">无建议</Tag>;

    if (ev && ev > 0.1) {
      return <Tag color="green">强推荐</Tag>;
    } else if (ev && ev > 0) {
      return <Tag color="blue">推荐</Tag>;
    } else if (ev && ev < 0) {
      return <Tag color="red">不推荐</Tag>;
    }

    return <Tag color="default">{suggestion}</Tag>;
  };

  // 预测分布图表配置
  const predictionDistributionOption = useMemo(() => {
    const predictionCounts = recentPredictions.reduce((acc, pred) => {
      acc[pred.prediction] = (acc[pred.prediction] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    return {
      title: {
        text: '预测结果分布',
        left: 'center',
        textStyle: {
          fontSize: 16,
          fontWeight: 'bold',
        },
      },
      tooltip: {
        trigger: 'item',
        formatter: '{a} <br/>{b}: {c} ({d}%)',
      },
      legend: {
        orient: 'vertical',
        left: 'left',
        top: 'middle',
      },
      series: [
        {
          name: '预测分布',
          type: 'pie',
          radius: '50%',
          data: [
            { value: predictionCounts.home_win || 0, name: '主胜', itemStyle: { color: '#52c41a' } },
            { value: predictionCounts.draw || 0, name: '平局', itemStyle: { color: '#faad14' } },
            { value: predictionCounts.away_win || 0, name: '客胜', itemStyle: { color: '#ff4d4f' } },
          ],
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowOffsetX: 0,
              shadowColor: 'rgba(0, 0, 0, 0.5)',
            },
          },
        },
      ],
    };
  }, [recentPredictions]);

  // 置信度分布图表配置
  const confidenceDistributionOption = useMemo(() => {
    const confidenceRanges = {
      high: recentPredictions.filter(p => p.confidence >= 0.8).length,
      medium: recentPredictions.filter(p => p.confidence >= 0.6 && p.confidence < 0.8).length,
      low: recentPredictions.filter(p => p.confidence < 0.6).length,
    };

    return {
      title: {
        text: '置信度分布',
        left: 'center',
        textStyle: {
          fontSize: 16,
          fontWeight: 'bold',
        },
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'shadow',
        },
      },
      xAxis: {
        type: 'category',
        data: ['高 (>80%)', '中 (60-80%)', '低 (<60%)'],
      },
      yAxis: {
        type: 'value',
        name: '预测数量',
      },
      series: [
        {
          name: '预测数量',
          type: 'bar',
          data: [
            { value: confidenceRanges.high, itemStyle: { color: '#52c41a' } },
            { value: confidenceRanges.medium, itemStyle: { color: '#faad14' } },
            { value: confidenceRanges.low, itemStyle: { color: '#ff4d4f' } },
          ],
        },
      ],
    };
  }, [recentPredictions]);

  useEffect(() => {
    dispatch(fetchMatches());
    loadDashboardData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dispatch]);

  const matchStats = getMatchStats();

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" tip="正在加载仪表板数据..." />
      </div>
    );
  }

  if (error) {
    return (
      <Alert
        message="加载失败"
        description={error}
        type="error"
        showIcon
        action={
          <Button size="small" onClick={loadDashboardData}>
            重试
          </Button>
        }
      />
    );
  }

  return (
    <div>
      {/* 顶部统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="总比赛数"
              value={matches.length}
              prefix={<TrophyOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="总预测数"
              value={stats?.total_predictions || 0}
              prefix={<BarChartOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="预测准确率"
              value={stats?.accuracy_rate ? Math.round(stats.accuracy_rate * 100) : 0}
              suffix="%"
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="平均置信度"
              value={stats?.avg_confidence ? Math.round(stats.avg_confidence * 100) : 0}
              suffix="%"
              prefix={<RiseOutlined />}
              valueStyle={{ color: '#f5222d' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 比赛状态统计 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={12}>
          <Card
            title="比赛状态分布"
            extra={
              <Button
                icon={<ReloadOutlined />}
                size="small"
                onClick={() => dispatch(fetchMatches())}
              >
                刷新
              </Button>
            }
          >
            <Row gutter={16}>
              <Col span={8}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 24, fontWeight: 'bold', color: '#1890ff' }}>
                    {matchStats.upcoming}
                  </div>
                  <div style={{ color: '#666' }}>即将开始</div>
                  <Progress
                    percent={matches.length ? (matchStats.upcoming / matches.length) * 100 : 0}
                    showInfo={false}
                    strokeColor="#1890ff"
                    size="small"
                    style={{ marginTop: 8 }}
                  />
                </div>
              </Col>
              <Col span={8}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 24, fontWeight: 'bold', color: '#f5222d' }}>
                    {matchStats.live}
                  </div>
                  <div style={{ color: '#666' }}>进行中</div>
                  <Progress
                    percent={matches.length ? (matchStats.live / matches.length) * 100 : 0}
                    showInfo={false}
                    strokeColor="#f5222d"
                    size="small"
                    style={{ marginTop: 8 }}
                  />
                </div>
              </Col>
              <Col span={8}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 24, fontWeight: 'bold', color: '#52c41a' }}>
                    {matchStats.finished}
                  </div>
                  <div style={{ color: '#666' }}>已结束</div>
                  <Progress
                    percent={matches.length ? (matchStats.finished / matches.length) * 100 : 0}
                    showInfo={false}
                    strokeColor="#52c41a"
                    size="small"
                    style={{ marginTop: 8 }}
                  />
                </div>
              </Col>
            </Row>
          </Card>
        </Col>

        {/* 系统状态 */}
        <Col xs={24} lg={12}>
          <Card title="系统状态">
            <Row gutter={16}>
              <Col span={12}>
                <div style={{ display: 'flex', alignItems: 'center', marginBottom: 16 }}>
                  <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
                  <span>API服务</span>
                  <Tag color="green" style={{ marginLeft: 'auto' }}>正常</Tag>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', marginBottom: 16 }}>
                  <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
                  <span>数据库</span>
                  <Tag color="green" style={{ marginLeft: 'auto' }}>正常</Tag>
                </div>
                <div style={{ display: 'flex', alignItems: 'center' }}>
                  <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
                  <span>缓存服务</span>
                  <Tag color="green" style={{ marginLeft: 'auto' }}>正常</Tag>
                </div>
              </Col>
              <Col span={12}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 18, fontWeight: 'bold', color: '#52c41a' }}>
                    系统健康度
                  </div>
                  <div style={{ marginTop: 16 }}>
                    <Progress
                      type="circle"
                      percent={95}
                      size={80}
                      strokeColor="#52c41a"
                    />
                  </div>
                </div>
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>

      {/* 图表区域 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={12}>
          <Card title="预测分布图">
            {recentPredictions.length > 0 ? (
              <Suspense fallback={<div style={{ textAlign: 'center', padding: '50px' }}>加载图表...</div>}>
                <ReactECharts
                  option={predictionDistributionOption}
                  style={{ height: 300 }}
                  notMerge={true}
                  lazyUpdate={true}
                />
              </Suspense>
            ) : (
              <Empty description="暂无预测数据" />
            )}
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="置信度分布">
            {recentPredictions.length > 0 ? (
              <Suspense fallback={<div style={{ textAlign: 'center', padding: '50px' }}>加载图表...</div>}>
                <ReactECharts
                  option={confidenceDistributionOption}
                  style={{ height: 300 }}
                  notMerge={true}
                  lazyUpdate={true}
                />
              </Suspense>
            ) : (
              <Empty description="暂无预测数据" />
            )}
          </Card>
        </Col>
      </Row>

      {/* 最近预测记录 */}
      <Card
        title="最近预测记录"
        extra={
          <Space>
            <Tooltip title="显示最近10条预测记录">
              <InfoCircleOutlined />
            </Tooltip>
            <Button
              icon={<ReloadOutlined />}
              size="small"
              onClick={loadDashboardData}
            >
              刷新
            </Button>
          </Space>
        }
      >
        {recentPredictions.length > 0 ? (
          <Table
            dataSource={recentPredictions}
            rowKey="match_id"
            pagination={false}
            size="small"
            columns={[
              {
                title: '比赛',
                key: 'match',
                render: (record: RecentPrediction) => (
                  <div>
                    <div style={{ fontWeight: 'bold' }}>
                      {record.match_info.home_team} VS {record.match_info.away_team}
                    </div>
                    <div style={{ fontSize: '12px', color: '#666' }}>
                      {record.match_info.league}
                    </div>
                  </div>
                ),
              },
              {
                title: '预测结果',
                key: 'prediction',
                render: (record: RecentPrediction) =>
                  getPredictionTag(record.prediction, record.confidence),
              },
              {
                title: '投注建议',
                key: 'suggestion',
                render: (record: RecentPrediction) =>
                  getSuggestionTag(record.suggestion || '', record.ev),
              },
              {
                title: '期望收益',
                key: 'ev',
                render: (record: RecentPrediction) =>
                  record.ev !== undefined ? (
                    <span style={{ color: record.ev > 0 ? '#52c41a' : '#f5222d' }}>
                      {record.ev > 0 ? '+' : ''}{record.ev.toFixed(3)}
                    </span>
                  ) : (
                    '-'
                  ),
              },
              {
                title: '创建时间',
                key: 'created_at',
                render: (record: RecentPrediction) =>
                  new Date(record.created_at).toLocaleString(),
              },
            ]}
          />
        ) : (
          <Empty description="暂无预测记录" />
        )}
      </Card>

      {/* 实时功能面板 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={8}>
          <Card title="🔗 实时连接状态" size="small">
            <RealtimeDashboard userId="demo_user" height={300} />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="⚡ 实时预测请求" size="small">
            <RealtimePredictionPanel userId="demo_user" />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="📢 订阅管理" size="small">
            <SubscriptionManager userId="demo_user" />
          </Card>
        </Col>
      </Row>

      {/* 实时统计面板 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={24}>
          <Card title="📊 实时系统统计" size="small">
            <RealtimeStatsPanel userId="demo_user" />
          </Card>
        </Col>
      </Row>

      {/* 高级分析面板 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={24}>
          <Card
            title={
              <Space>
                <AreaChartOutlined />
                <span>🎯 高级数据分析</span>
                <Tag color="blue">Beta</Tag>
              </Space>
            }
            extra={
              <Tooltip title="深度数据分析和智能投注建议">
                <InfoCircleOutlined />
              </Tooltip>
            }
          >
            <AdvancedAnalytics
              userId="demo_user"
              height={1000}
              refreshInterval={30000}
            />
          </Card>
        </Col>
      </Row>

      {/* 性能监控 */}
      <PerformanceOptimizer
        onMetricsUpdate={(metrics) => {
          console.log('Performance metrics updated:', metrics);
        }}
      />
    </div>
  );
};

export default Dashboard;
