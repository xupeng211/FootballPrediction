import React, { useEffect, useState } from 'react';
import type { RangePickerProps } from 'antd/es/date-picker';
import {
  Table,
  Tag,
  Button,
  Space,
  Input,
  Select,
  Card,
  Tooltip,
  Badge,
  message,
  Spin,
  Pagination,
  DatePicker,
  Row,
  Col,
  Statistic,
} from 'antd';
import {
  EyeOutlined,
  ThunderboltOutlined,
  ReloadOutlined,
  FilterOutlined,
  ClearOutlined,
} from '@ant-design/icons';
import { useDispatch, useSelector } from 'react-redux';
import { RootState, AppDispatch } from '../store';
import {
  fetchMatches,
  setFilters,
  setPagination,
  selectFilteredMatches,
  selectMatchesLoading,
  selectMatchesFilters,
  selectMatchesPagination,
} from '../store/slices/matchesSlice';
import { MatchData } from '../services/api';
import {
  generatePrediction,
  selectPrediction,
  selectPredictionLoading,
  selectPredictionError,
} from '../store/slices/predictionsSlice';
import PredictionChart from './PredictionChart';
import BettingRecommendation from './BettingRecommendation';

const { Option } = Select;
const { Search } = Input;
const { RangePicker } = DatePicker;

interface MatchListProps {
  onPredictionSelect?: (matchId: number) => void;
}

const MatchList: React.FC<MatchListProps> = ({ onPredictionSelect }) => {
  const dispatch = useDispatch<AppDispatch>();
  const matches = useSelector(selectFilteredMatches);
  const loading = useSelector(selectMatchesLoading);
  const filters = useSelector(selectMatchesFilters);
  const pagination = useSelector(selectMatchesPagination);

  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());

  // 获取比赛列表
  useEffect(() => {
    dispatch(fetchMatches());
  }, [dispatch, filters]);

  // 处理搜索
  const handleSearch = (value: string) => {
    dispatch(setFilters({ search: value }));
  };

  // 处理联赛过滤
  const handleLeagueFilter = (league: string) => {
    dispatch(setFilters({ league: league === 'all' ? undefined : league }));
  };

  // 处理状态过滤
  const handleStatusFilter = (status: string) => {
    dispatch(setFilters({ status: status === 'all' ? undefined : status }));
  };

  // 处理分页变化
  const handlePaginationChange = (page: number, pageSize?: number) => {
    dispatch(setPagination({ currentPage: page, pageSize: pageSize || 20 }));
  };

  // 处理日期范围筛选 - 暂时禁用
  const handleDateRangeFilter = (dates: any) => {
    console.log('日期范围筛选功能暂未实现');
    // TODO: 实现日期范围筛选功能
  };

  // 处理概率范围筛选 - 暂时禁用
  const handleProbabilityFilter = (value: string) => {
    console.log('概率范围筛选功能暂未实现:', value);
    // TODO: 实现概率范围筛选功能
  };

  // 清除所有筛选
  const handleClearFilters = () => {
    dispatch(setFilters({
      search: undefined,
      league: undefined,
      status: undefined,
      // TODO: 添加dateRange和probabilityRange支持
    }));
  };

  // 计算统计信息
  const getStatistics = () => {
    const total = matches.length;
    const upcoming = matches.filter(m => m.status === 'upcoming').length;
    const live = matches.filter(m => m.status === 'live').length;
    const finished = matches.filter(m => m.status === 'finished').length;

    return { total, upcoming, live, finished };
  };

  // 生成预测
  const handleGeneratePrediction = async (matchId: number) => {
    try {
      await dispatch(generatePrediction(matchId)).unwrap();
      message.success('预测生成成功');
    } catch (error) {
      message.error('预测生成失败');
    }
  };

  // 展开预测详情
  const handleExpand = (expanded: boolean, record: MatchData) => {
    const newExpanded = new Set(expandedRows);
    if (expanded) {
      newExpanded.add(record.id);
      // 如果还没有预测，自动生成一个
      handleGeneratePrediction(record.id);
    } else {
      newExpanded.delete(record.id);
    }
    setExpandedRows(newExpanded);
  };

  // 获取状态标签
  const getStatusTag = (status: string) => {
    const statusConfig = {
      upcoming: { color: 'blue', text: '即将开始' },
      live: { color: 'red', text: '进行中' },
      finished: { color: 'default', text: '已结束' },
    };

    const config = statusConfig[status as keyof typeof statusConfig] ||
                   { color: 'default', text: status };

    return <Tag color={config.color}>{config.text}</Tag>;
  };

  // 获取比赛结果
  const getMatchScore = (match: MatchData) => {
    if (match.status === 'finished' && match.home_score !== undefined && match.away_score !== undefined) {
      return `${match.home_score} : ${match.away_score}`;
    }
    return 'VS';
  };

  // 表格列定义
  const columns = [
    {
      title: '比赛信息',
      key: 'match',
      width: 300,
      render: (record: MatchData) => (
        <div>
          <div style={{ fontWeight: 'bold', marginBottom: 4 }}>
            {record.home_team} VS {record.away_team}
          </div>
          <div style={{ color: '#666', fontSize: '12px' }}>
            {record.league} • {new Date(record.match_date).toLocaleString()}
          </div>
        </div>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => getStatusTag(status),
    },
    {
      title: '比分',
      key: 'score',
      width: 80,
      render: (record: MatchData) => (
        <div style={{ textAlign: 'center', fontWeight: 'bold' }}>
          {getMatchScore(record)}
        </div>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (record: MatchData) => {
        // 创建一个内部组件来使用hooks
        return <PredictionActions record={record} onGeneratePrediction={handleGeneratePrediction} onPredictionSelect={onPredictionSelect} />;
      },
    },
  ];

  // 展开行内容（显示预测图表）
  const expandedRowRender = (record: MatchData) => {
    return <ExpandedPredictionContent record={record} />;
  };

  return (
    <Card title="比赛列表"
          extra={
            <Button
              icon={<ReloadOutlined />}
              onClick={() => dispatch(fetchMatches())}
              loading={loading}
            >
              刷新
            </Button>
          }>

      {/* 统计信息 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col xs={6} sm={6}>
          <Card size="small">
            <Statistic
              title="总比赛数"
              value={getStatistics().total}
              prefix={<FilterOutlined />}
            />
          </Card>
        </Col>
        <Col xs={6} sm={6}>
          <Card size="small">
            <Statistic
              title="即将开始"
              value={getStatistics().upcoming}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={6} sm={6}>
          <Card size="small">
            <Statistic
              title="进行中"
              value={getStatistics().live}
              valueStyle={{ color: '#fa8c16' }}
            />
          </Card>
        </Col>
        <Col xs={6} sm={6}>
          <Card size="small">
            <Statistic
              title="已结束"
              value={getStatistics().finished}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 高级过滤器 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <div style={{ marginBottom: 12 }}>
          <Space size="large" wrap>
            <Space>
              <span>🔍 基础筛选:</span>
            </Space>
            <Space wrap>
              {/* 高级筛选 */}
              <span>📅 高级筛选:</span>
              <RangePicker
                placeholder={['开始日期', '结束日期']}
                onChange={handleDateRangeFilter}
                style={{ width: 240 }}
              />

              <Select
                placeholder="预测概率"
                allowClear
                style={{ width: 120 }}
                onChange={handleProbabilityFilter}
              >
                <Option value="all">所有概率</Option>
                <Option value="high">高概率 (60%以上)</Option>
                <Option value="medium">中概率 (40-60%)</Option>
                <Option value="low">低概率 (40%以下)</Option>
              </Select>

              <Button
                icon={<ClearOutlined />}
                onClick={handleClearFilters}
                size="small"
              >
                清除筛选
              </Button>
            </Space>
          </Space>
        </div>
      </Card>

      {/* 基础过滤器 */}
      <div style={{ marginBottom: 16, display: 'flex', gap: 16, alignItems: 'center', flexWrap: 'wrap' }}>
        <Search
          placeholder="搜索球队或联赛"
          allowClear
          style={{ width: 200 }}
          onSearch={handleSearch}
        />

        <Select
          placeholder="选择联赛"
          allowClear
          style={{ width: 150 }}
          onChange={handleLeagueFilter}
          value={filters.league || 'all'}
        >
          <Option value="all">所有联赛</Option>
          <Option value="英超">英超</Option>
          <Option value="西甲">西甲</Option>
          <Option value="德甲">德甲</Option>
          <Option value="意甲">意甲</Option>
          <Option value="法甲">法甲</Option>
          <Option value="欧冠">欧冠</Option>
        </Select>

        <Select
          placeholder="选择状态"
          allowClear
          style={{ width: 120 }}
          onChange={handleStatusFilter}
          value={filters.status || 'all'}
        >
          <Option value="all">所有状态</Option>
          <Option value="upcoming">即将开始</Option>
          <Option value="live">进行中</Option>
          <Option value="finished">已结束</Option>
        </Select>

        <Badge count={matches.length} showZero>
          <span style={{ color: '#666' }}>场比赛</span>
        </Badge>
      </div>

      {/* 比赛表格 */}
      <Table
        columns={columns}
        dataSource={matches}
        rowKey="id"
        loading={loading}
        pagination={false}
        expandable={{
          expandedRowRender,
          expandedRowKeys: Array.from(expandedRows),
          onExpand: handleExpand,
        }}
        scroll={{ x: 800 }}
        size="small"
      />

      {/* 分页 */}
      <div style={{ marginTop: 16, textAlign: 'center' }}>
        <Pagination
          current={pagination.currentPage}
          pageSize={pagination.pageSize}
          total={matches.length}
          showSizeChanger
          showQuickJumper
          showTotal={(total, range) =>
            `第 ${range[0]}-${range[1]} 条，共 ${total} 条记录`
          }
          onChange={handlePaginationChange}
          onShowSizeChange={handlePaginationChange}
        />
      </div>
    </Card>
  );
};

// 预测操作子组件
const PredictionActions: React.FC<{
  record: MatchData;
  onGeneratePrediction: (matchId: number) => void;
  onPredictionSelect?: (matchId: number) => void;
}> = ({ record, onGeneratePrediction, onPredictionSelect }) => {
  const prediction = useSelector((state: RootState) => selectPrediction(state, record.id));
  const loading = useSelector((state: RootState) => selectPredictionLoading(state, record.id));

  return (
    <Space>
      <Tooltip title="查看预测">
        <Button
          type="primary"
          icon={<EyeOutlined />}
          size="small"
          onClick={() => onPredictionSelect?.(record.id)}
        />
      </Tooltip>
      {!prediction && record.status !== 'finished' && (
        <Tooltip title="生成预测">
          <Button
            type="default"
            icon={<ThunderboltOutlined />}
            size="small"
            loading={loading}
            onClick={() => onGeneratePrediction(record.id)}
          />
        </Tooltip>
      )}
    </Space>
  );
};

// 展开的预测内容子组件
const ExpandedPredictionContent: React.FC<{ record: MatchData }> = ({ record }) => {
  const prediction = useSelector((state: RootState) => selectPrediction(state, record.id));
  const loading = useSelector((state: RootState) => selectPredictionLoading(state, record.id));
  const error = useSelector((state: RootState) => selectPredictionError(state, record.id));

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '20px' }}>
        <Spin size="large" tip="正在生成预测..." />
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ textAlign: 'center', padding: '20px', color: '#ff4d4f' }}>
        预测生成失败: {error}
      </div>
    );
  }

  if (!prediction) {
    return (
      <div style={{ textAlign: 'center', padding: '20px', color: '#666' }}>
        暂无预测数据，请点击生成预测按钮
      </div>
    );
  }

  return (
    <div style={{ padding: '20px' }}>
      <div style={{ display: 'flex', gap: '20px', alignItems: 'flex-start', marginBottom: '20px' }}>
        <div style={{ flex: 1 }}>
          <PredictionChart prediction={prediction} height={250} />
        </div>
        <div style={{ flex: 1 }}>
          <Card title="预测详情" size="small">
            <p><strong>推荐结果:</strong>
              <Tag color={prediction.prediction === 'home_win' ? 'green' :
                          prediction.prediction === 'draw' ? 'orange' : 'red'}>
                {prediction.prediction === 'home_win' ? '主胜' :
                 prediction.prediction === 'draw' ? '平局' : '客胜'}
              </Tag>
            </p>
            <p><strong>置信度:</strong> {Math.round(prediction.confidence * 100)}%</p>
            <p><strong>主胜概率:</strong> {Math.round(prediction.home_win_prob * 100)}%</p>
            <p><strong>平局概率:</strong> {Math.round(prediction.draw_prob * 100)}%</p>
            <p><strong>客胜概率:</strong> {Math.round(prediction.away_win_prob * 100)}%</p>
            {prediction.ev !== undefined && (
              <p><strong>期望收益:</strong> {prediction.ev.toFixed(3)}</p>
            )}
            {prediction.suggestion && (
              <p><strong>投注建议:</strong> {prediction.suggestion}</p>
            )}
          </Card>
        </div>
      </div>

      {/* 投注推荐组件 */}
      <BettingRecommendation
        prediction={prediction}
        odds={
          // 模拟赔率数据，实际应该从API获取
          {
            home_win: 1.85,
            draw: 3.40,
            away_win: 4.20,
          }
        }
        bankroll={1000}
      />
    </div>
  );
};

export default MatchList;