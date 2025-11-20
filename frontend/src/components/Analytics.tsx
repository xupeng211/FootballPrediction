import React, { useState, useEffect, useCallback, lazy, Suspense } from 'react';
import {
  Card,
  Row,
  Col,
  Select,
  DatePicker,
  Button,
  Table,
  Tag,
  Statistic,
  Progress,
  Spin,
  Empty,
  Alert,
} from 'antd';
import {
  BarChartOutlined,
  TrophyOutlined,
  ReloadOutlined,
  LineChartOutlined,
} from '@ant-design/icons';
import { useDispatch } from 'react-redux';
import { AppDispatch } from '../store';
import { fetchMatches } from '../store/slices/matchesSlice';
import { getTeamName } from '../services/api';

// 懒加载ECharts组件
const ReactECharts = lazy(() => import('echarts-for-react').then(module => ({ default: module.default })));
const HistoryTrendChart = lazy(() => import('./HistoryTrendChart'));

const { Option } = Select;
const { RangePicker } = DatePicker;

interface AnalyticsData {
  leaguePerformance: Array<{
    league: string;
    total_matches: number;
    accurate_predictions: number;
    accuracy_rate: number;
    avg_confidence: number;
  }>;
  teamPerformance: Array<{
    team: string;
    matches: number;
    wins: number;
    draws: number;
    losses: number;
    points: number;
  }>;
  predictionTrends: Array<{
    date: string;
    total_predictions: number;
    accuracy_rate: number;
    avg_confidence: number;
  }>;
}

const Analytics: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [analyticsData, setAnalyticsData] = useState<AnalyticsData | null>(null);
  const [filters, setFilters] = useState({
    league: 'all',
    dateRange: null as any,
    team: 'all',
  });

  // 加载分析数据
  const loadAnalyticsData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // 模拟分析数据（实际应该从API获取）
      const mockData: AnalyticsData = {
        leaguePerformance: [
          {
            league: '英超',
            total_matches: 45,
            accurate_predictions: 32,
            accuracy_rate: 0.71,
            avg_confidence: 0.68,
          },
          {
            league: '西甲',
            total_matches: 38,
            accurate_predictions: 28,
            accuracy_rate: 0.74,
            avg_confidence: 0.72,
          },
          {
            league: '德甲',
            total_matches: 32,
            accurate_predictions: 23,
            accuracy_rate: 0.72,
            avg_confidence: 0.70,
          },
          {
            league: '意甲',
            total_matches: 35,
            accurate_predictions: 25,
            accuracy_rate: 0.71,
            avg_confidence: 0.69,
          },
          {
            league: '法甲',
            total_matches: 30,
            accurate_predictions: 21,
            accuracy_rate: 0.70,
            avg_confidence: 0.67,
          },
        ],
        teamPerformance: [
          { team: '曼城', matches: 15, wins: 12, draws: 2, losses: 1, points: 38 },
          { team: '利物浦', matches: 15, wins: 11, draws: 3, losses: 1, points: 36 },
          { team: '切尔西', matches: 15, wins: 10, draws: 3, losses: 2, points: 33 },
          { team: '阿森纳', matches: 15, wins: 9, draws: 4, losses: 2, points: 31 },
          { team: '曼联', matches: 15, wins: 8, draws: 5, losses: 2, points: 29 },
        ],
        predictionTrends: [
          { date: '2025-10-23', total_predictions: 12, accuracy_rate: 0.75, avg_confidence: 0.70 },
          { date: '2025-10-24', total_predictions: 15, accuracy_rate: 0.73, avg_confidence: 0.68 },
          { date: '2025-10-25', total_predictions: 18, accuracy_rate: 0.78, avg_confidence: 0.72 },
          { date: '2025-10-26', total_predictions: 14, accuracy_rate: 0.71, avg_confidence: 0.69 },
          { date: '2025-10-27', total_predictions: 20, accuracy_rate: 0.75, avg_confidence: 0.71 },
          { date: '2025-10-28', total_predictions: 16, accuracy_rate: 0.81, avg_confidence: 0.74 },
          { date: '2025-10-29', total_predictions: 22, accuracy_rate: 0.77, avg_confidence: 0.73 },
        ],
      };

      setAnalyticsData(mockData);
    } catch (err) {
      console.error('加载分析数据失败:', err);
      setError('无法加载分析数据，请检查API连接');
    } finally {
      setLoading(false);
    }
  }, []);

  // 联赛性能图表配置
  const getLeaguePerformanceOption = () => {
    if (!analyticsData) return {};

    return {
      title: {
        text: '联赛预测准确率',
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
        formatter: (params: any) => {
          const data = params[0];
          const league = analyticsData.leaguePerformance.find(l => l.league === data.name);
          if (!league) return '';
          return `
            <strong>${data.name}</strong><br/>
            准确率: ${(league.accuracy_rate * 100).toFixed(1)}%<br/>
            平均置信度: ${(league.avg_confidence * 100).toFixed(1)}%<br/>
            总预测数: ${league.total_matches}
          `;
        },
      },
      xAxis: {
        type: 'category',
        data: analyticsData.leaguePerformance.map(item => item.league),
        axisLabel: {
          rotate: 45,
        },
      },
      yAxis: [
        {
          type: 'value',
          name: '准确率 (%)',
          position: 'left',
          axisLabel: {
            formatter: '{value}%',
          },
        },
        {
          type: 'value',
          name: '置信度 (%)',
          position: 'right',
          axisLabel: {
            formatter: '{value}%',
          },
        },
      ],
      series: [
        {
          name: '准确率',
          type: 'bar',
          data: analyticsData.leaguePerformance.map(item => ({
            value: (item.accuracy_rate * 100).toFixed(1),
            itemStyle: {
              color: '#1890ff',
            },
          })),
        },
        {
          name: '平均置信度',
          type: 'line',
          yAxisIndex: 1,
          data: analyticsData.leaguePerformance.map(item => ({
            value: (item.avg_confidence * 100).toFixed(1),
            itemStyle: {
              color: '#52c41a',
            },
          })),
          smooth: true,
        },
      ],
    };
  };

  // 预测趋势图表配置
  const getPredictionTrendsOption = () => {
    if (!analyticsData) return {};

    return {
      title: {
        text: '预测准确率趋势',
        left: 'center',
        textStyle: {
          fontSize: 16,
          fontWeight: 'bold',
        },
      },
      tooltip: {
        trigger: 'axis',
      },
      legend: {
        top: 'bottom',
      },
      xAxis: {
        type: 'category',
        data: analyticsData.predictionTrends.map(item => item.date),
      },
      yAxis: [
        {
          type: 'value',
          name: '准确率 (%)',
          position: 'left',
          axisLabel: {
            formatter: '{value}%',
          },
        },
        {
          type: 'value',
          name: '预测数量',
          position: 'right',
        },
      ],
      series: [
        {
          name: '准确率',
          type: 'line',
          data: analyticsData.predictionTrends.map(item => item.accuracy_rate * 100),
          smooth: true,
          itemStyle: {
            color: '#1890ff',
          },
          areaStyle: {
            opacity: 0.3,
            color: '#1890ff',
          },
        },
        {
          name: '平均置信度',
          type: 'line',
          data: analyticsData.predictionTrends.map(item => item.avg_confidence * 100),
          smooth: true,
          itemStyle: {
            color: '#52c41a',
          },
        },
        {
          name: '预测数量',
          type: 'bar',
          yAxisIndex: 1,
          data: analyticsData.predictionTrends.map(item => item.total_predictions),
          itemStyle: {
            color: '#faad14',
            opacity: 0.6,
          },
        },
      ],
    };
  };

  
  // 球队积分榜表格列
  const teamRankingColumns = [
    {
      title: '排名',
      key: 'rank',
      render: (_: any, __: any, index: number) => (
        <Tag color={index < 4 ? 'green' : index < 7 ? 'blue' : 'default'}>
          {index + 1}
        </Tag>
      ),
      width: 80,
    },
    {
      title: '球队',
      dataIndex: 'team',
      key: 'team',
      render: (team: any) => getTeamName(team),
    },
    {
      title: '场次',
      dataIndex: 'matches',
      key: 'matches',
      width: 80,
    },
    {
      title: '胜',
      dataIndex: 'wins',
      key: 'wins',
      width: 60,
    },
    {
      title: '平',
      dataIndex: 'draws',
      key: 'draws',
      width: 60,
    },
    {
      title: '负',
      dataIndex: 'losses',
      key: 'losses',
      width: 60,
    },
    {
      title: '积分',
      dataIndex: 'points',
      key: 'points',
      width: 80,
      render: (points: number) => (
        <span style={{ fontWeight: 'bold', color: '#1890ff' }}>{points}</span>
      ),
    },
  ];

  useEffect(() => {
    dispatch(fetchMatches());
    loadAnalyticsData();
  }, [dispatch, filters, loadAnalyticsData]);

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" tip="正在加载分析数据..." />
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
          <Button size="small" onClick={loadAnalyticsData}>
            重试
          </Button>
        }
      />
    );
  }

  if (!analyticsData) {
    return <Empty description="暂无分析数据" />;
  }

  return (
    <div>
      {/* 筛选器 */}
      <Card style={{ marginBottom: 24 }}>
        <Row gutter={[16, 16]} align="middle">
          <Col>
            <span style={{ marginRight: 8 }}>联赛：</span>
            <Select
              value={filters.league}
              onChange={(value) => setFilters({ ...filters, league: value })}
              style={{ width: 120 }}
            >
              <Option value="all">所有联赛</Option>
              <Option value="英超">英超</Option>
              <Option value="西甲">西甲</Option>
              <Option value="德甲">德甲</Option>
              <Option value="意甲">意甲</Option>
              <Option value="法甲">法甲</Option>
            </Select>
          </Col>
          <Col>
            <span style={{ marginRight: 8 }}>日期范围：</span>
            <RangePicker
              value={filters.dateRange}
              onChange={(dates) => setFilters({ ...filters, dateRange: dates })}
            />
          </Col>
          <Col>
            <Button
              icon={<ReloadOutlined />}
              onClick={loadAnalyticsData}
              loading={loading}
            >
              刷新数据
            </Button>
          </Col>
        </Row>
      </Card>

      {/* 统计概览 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="总预测数"
              value={analyticsData.predictionTrends.reduce((sum, item) => sum + item.total_predictions, 0)}
              prefix={<BarChartOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="平均准确率"
              value={(
                analyticsData.predictionTrends.reduce((sum, item) => sum + item.accuracy_rate, 0) /
                analyticsData.predictionTrends.length * 100
              ).toFixed(1)}
              suffix="%"
              prefix={<TrophyOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="覆盖联赛数"
              value={analyticsData.leaguePerformance.length}
              prefix={<LineChartOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 图表区域 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={12}>
          <Card>
            <Suspense fallback={<div style={{ textAlign: 'center', padding: '50px' }}>加载图表...</div>}>
              <ReactECharts
                option={getLeaguePerformanceOption()}
                style={{ height: 400 }}
                notMerge={true}
                lazyUpdate={true}
              />
            </Suspense>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card>
            <Suspense fallback={<div style={{ textAlign: 'center', padding: '50px' }}>加载图表...</div>}>
              <ReactECharts
                option={getPredictionTrendsOption()}
                style={{ height: 400 }}
                notMerge={true}
                lazyUpdate={true}
              />
            </Suspense>
          </Card>
        </Col>
      </Row>

      {/* 历史趋势分析 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={24}>
          <Suspense fallback={<div style={{ textAlign: 'center', padding: '50px' }}>加载历史趋势...</div>}>
            <HistoryTrendChart height={400} />
          </Suspense>
        </Col>
      </Row>

      {/* 联赛性能详细表格 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={24}>
          <Card title="联赛性能分析">
            <Table
              dataSource={analyticsData.leaguePerformance}
              rowKey="league"
              pagination={false}
              size="small"
              columns={[
                {
                  title: '联赛',
                  dataIndex: 'league',
                  key: 'league',
                },
                {
                  title: '总预测数',
                  dataIndex: 'total_matches',
                  key: 'total_matches',
                  width: 120,
                },
                {
                  title: '准确预测数',
                  dataIndex: 'accurate_predictions',
                  key: 'accurate_predictions',
                  width: 120,
                },
                {
                  title: '准确率',
                  key: 'accuracy_rate',
                  width: 150,
                  render: (record: any) => (
                    <div>
                      <Progress
                        percent={record.accuracy_rate * 100}
                        size="small"
                        strokeColor={
                          record.accuracy_rate >= 0.75 ? '#52c41a' :
                          record.accuracy_rate >= 0.70 ? '#faad14' : '#f5222d'
                        }
                      />
                      <span style={{ marginLeft: 8, fontSize: '12px' }}>
                        {(record.accuracy_rate * 100).toFixed(1)}%
                      </span>
                    </div>
                  ),
                },
                {
                  title: '平均置信度',
                  key: 'avg_confidence',
                  width: 150,
                  render: (record: any) => (
                    <div>
                      <Progress
                        percent={record.avg_confidence * 100}
                        size="small"
                        strokeColor="#1890ff"
                      />
                      <span style={{ marginLeft: 8, fontSize: '12px' }}>
                        {(record.avg_confidence * 100).toFixed(1)}%
                      </span>
                    </div>
                  ),
                },
                {
                  title: '评级',
                  key: 'rating',
                  width: 100,
                  render: (record: any) => {
                    if (record.accuracy_rate >= 0.75) {
                      return <Tag color="green">优秀</Tag>;
                    } else if (record.accuracy_rate >= 0.70) {
                      return <Tag color="blue">良好</Tag>;
                    } else {
                      return <Tag color="orange">一般</Tag>;
                    }
                  },
                },
              ]}
            />
          </Card>
        </Col>
      </Row>

      {/* 球队积分榜 */}
      <Row gutter={[16, 16]}>
        <Col span={24}>
          <Card title="球队积分榜 (模拟数据)">
            <Table
              dataSource={analyticsData.teamPerformance}
              rowKey="team"
              pagination={false}
              size="small"
              columns={teamRankingColumns}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Analytics;
