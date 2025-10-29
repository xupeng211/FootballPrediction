import React, { useState } from 'react';
import {
  Card,
  Select,
  DatePicker,
  Button,
  Space,
  Tooltip,
  Switch,
  Row,
  Col,
} from 'antd';
import {
  LineChartOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import dayjs from 'dayjs';

interface HistoryTrendChartProps {
  matchId?: number;
  teamId?: number;
  height?: number;
}

interface PredictionHistory {
  date: string;
  home_win_prob: number;
  draw_prob: number;
  away_win_prob: number;
  confidence: number;
  prediction: 'home_win' | 'draw' | 'away_win';
  actual_result?: 'home_win' | 'draw' | 'away_win';
  accuracy?: number;
}

const { Option } = Select;
const { RangePicker } = DatePicker;

const HistoryTrendChart: React.FC<HistoryTrendChartProps> = ({
  matchId,
  teamId,
  height = 400,
}) => {
  const [timeRange, setTimeRange] = useState<[dayjs.Dayjs, dayjs.Dayjs]>([
    dayjs().subtract(30, 'day'),
    dayjs(),
  ]);
  const [chartType, setChartType] = useState<'line' | 'bar'>('line');
  const [showAccuracy, setShowAccuracy] = useState<boolean>(true);
  const [loading, setLoading] = useState<boolean>(false);

  // 模拟历史数据
  const generateMockHistoryData = (): PredictionHistory[] => {
    const data: PredictionHistory[] = [];
    const startDate = timeRange[0];
    const endDate = timeRange[1];
    const days = endDate.diff(startDate, 'day');

    for (let i = 0; i <= days; i += 2) { // 每两天一个数据点
      const currentDate = startDate.add(i, 'day');
      const baseProb = 0.4 + Math.random() * 0.2; // 基础概率
      const variance = (Math.random() - 0.5) * 0.2; // 变化量

      const homeWinProb = Math.max(0.1, Math.min(0.8, baseProb + variance));
      const drawProb = Math.max(0.1, Math.min(0.4, 0.25 + (Math.random() - 0.5) * 0.1));
      const awayWinProb = Math.max(0.1, 1 - homeWinProb - drawProb);

      const predictions: ('home_win' | 'draw' | 'away_win')[] = ['home_win', 'draw', 'away_win'];
      const prediction = predictions[Math.floor(Math.random() * predictions.length)];

      const actual_result = Math.random() > 0.3 ? predictions[Math.floor(Math.random() * predictions.length)] : undefined;
      const accuracy = actual_result ? (actual_result === prediction ? 1 : 0) : undefined;

      data.push({
        date: currentDate.format('YYYY-MM-DD'),
        home_win_prob: Math.round(homeWinProb * 100),
        draw_prob: Math.round(drawProb * 100),
        away_win_prob: Math.round(awayWinProb * 100),
        confidence: Math.round((0.6 + Math.random() * 0.3) * 100),
        prediction,
        actual_result,
        accuracy,
      });
    }

    return data;
  };

  const [historyData, setHistoryData] = useState<PredictionHistory[]>(() => generateMockHistoryData());

  // 刷新数据
  const refreshData = () => {
    setLoading(true);
    setTimeout(() => {
      setHistoryData(generateMockHistoryData());
      setLoading(false);
    }, 1000);
  };

  // 获取图表配置
  const getChartOption = () => {
    const dates = historyData.map(item => item.date);
    const homeWinData = historyData.map(item => item.home_win_prob);
    const drawData = historyData.map(item => item.draw_prob);
    const awayWinData = historyData.map(item => item.away_win_prob);
    const confidenceData = historyData.map(item => item.confidence);

    return {
      title: {
        text: '预测概率历史趋势',
        left: 'center',
        textStyle: {
          fontSize: 16,
          fontWeight: 'bold',
        },
      },
      tooltip: {
        trigger: 'axis',
        formatter: (params: any) => {
          const index = params[0].dataIndex;
          const item = historyData[index];
          let result = `<div style="padding: 8px;">
            <div style="font-weight: bold; margin-bottom: 8px;">${item.date}</div>
            <div>主胜: ${item.home_win_prob}%</div>
            <div>平局: ${item.draw_prob}%</div>
            <div>客胜: ${item.away_win_prob}%</div>
            <div>置信度: ${item.confidence}%</div>
            <div>预测: ${item.prediction === 'home_win' ? '主胜' : item.prediction === 'draw' ? '平局' : '客胜'}</div>`;

          if (item.actual_result) {
            const isCorrect = item.accuracy === 1;
            result += `<div style="color: ${isCorrect ? '#52c41a' : '#ff4d4f'};">
              实际结果: ${item.actual_result === 'home_win' ? '主胜' : item.actual_result === 'draw' ? '平局' : '客胜'}
              ${isCorrect ? '✓' : '✗'}
            </div>`;
          }

          result += '</div>';
          return result;
        },
      },
      legend: {
        data: ['主胜概率', '平局概率', '客胜概率', '置信度'],
        top: 30,
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: dates,
        axisLabel: {
          rotate: 45,
          formatter: (value: string) => {
            return dayjs(value).format('MM-DD');
          },
        },
      },
      yAxis: {
        type: 'value',
        name: '概率 (%)',
        min: 0,
        max: 100,
        axisLabel: {
          formatter: '{value}%',
        },
      },
      series: [
        {
          name: '主胜概率',
          type: chartType,
          data: homeWinData,
          itemStyle: { color: '#52c41a' },
          smooth: true,
          lineStyle: {
            width: 2,
          },
        },
        {
          name: '平局概率',
          type: chartType,
          data: drawData,
          itemStyle: { color: '#faad14' },
          smooth: true,
          lineStyle: {
            width: 2,
          },
        },
        {
          name: '客胜概率',
          type: chartType,
          data: awayWinData,
          itemStyle: { color: '#ff4d4f' },
          smooth: true,
          lineStyle: {
            width: 2,
          },
        },
        ...(showAccuracy ? [{
          name: '置信度',
          type: chartType,
          data: confidenceData,
          itemStyle: { color: '#1890ff' },
          smooth: true,
          lineStyle: {
            width: 2,
            type: 'dashed',
          },
        }] : []),
      ],
      // 标记实际结果点
      markPoint: {
        data: historyData
          .filter(item => item.actual_result)
          .map(item => ({
            name: item.actual_result,
            coord: [item.date,
              item.actual_result === 'home_win' ? item.home_win_prob :
              item.actual_result === 'draw' ? item.draw_prob : item.away_win_prob
            ],
            itemStyle: {
              color: item.accuracy === 1 ? '#52c41a' : '#ff4d4f',
            },
            symbol: item.accuracy === 1 ? 'circle' : 'x',
            symbolSize: 10,
          })),
      },
    };
  };

  // 获取准确率统计
  const getAccuracyStats = () => {
    const predictionsWithResults = historyData.filter(item => item.actual_result);
    const correctPredictions = predictionsWithResults.filter(item => item.accuracy === 1);
    const totalPredictions = predictionsWithResults.length;
    const accuracyRate = totalPredictions > 0 ? (correctPredictions.length / totalPredictions) * 100 : 0;

    return {
      total: totalPredictions,
      correct: correctPredictions.length,
      accuracy: accuracyRate.toFixed(1),
    };
  };

  const stats = getAccuracyStats();

  return (
    <Card
      title={
        <Space>
          <LineChartOutlined />
          历史趋势分析
        </Space>
      }
      extra={
        <Space>
          <Select
            value={chartType}
            onChange={setChartType}
            style={{ width: 100 }}
            size="small"
          >
            <Option value="line">折线图</Option>
            <Option value="bar">柱状图</Option>
          </Select>

          <Tooltip title="显示置信度">
            <Switch
              checked={showAccuracy}
              onChange={setShowAccuracy}
              size="small"
            />
          </Tooltip>

          <Button
            icon={<ReloadOutlined />}
            onClick={refreshData}
            loading={loading}
            size="small"
          >
            刷新
          </Button>
        </Space>
      }
    >
      {/* 时间范围选择 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={12}>
          <div>
            <label style={{ marginRight: 8 }}>时间范围:</label>
            <RangePicker
              value={timeRange}
              onChange={(dates) => {
                if (dates && dates[0] && dates[1]) {
                  setTimeRange([dates[0], dates[1]]);
                  refreshData();
                }
              }}
              format="YYYY-MM-DD"
              size="small"
            />
          </div>
        </Col>
        <Col xs={24} sm={12}>
          <div style={{ textAlign: 'right' }}>
            <Space>
              <span>总预测: {stats.total}</span>
              <span style={{ color: '#52c41a' }}>正确: {stats.correct}</span>
              <span style={{ color: '#1890ff' }}>准确率: {stats.accuracy}%</span>
            </Space>
          </div>
        </Col>
      </Row>

      {/* 图表 */}
      <ReactECharts
        option={getChartOption()}
        style={{ height }}
        notMerge={true}
        lazyUpdate={true}
        showLoading={loading}
      />

      {/* 图例说明 */}
      <div style={{ marginTop: 16, padding: '12px', backgroundColor: '#fafafa', borderRadius: '6px' }}>
        <div style={{ fontSize: '12px', color: '#666', lineHeight: '1.5' }}>
          <div><strong>图例说明:</strong></div>
          <div>• 实线: 预测概率变化趋势</div>
          <div>• 虚线: 置信度变化 (可选显示)</div>
          <div>• 绿点: 预测正确的实际结果</div>
          <div>• 红叉: 预测错误的实际结果</div>
          <div>• 准确率: {stats.accuracy}% ({stats.correct}/{stats.total})</div>
        </div>
      </div>
    </Card>
  );
};

export default HistoryTrendChart;