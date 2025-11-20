import React from 'react';
import ReactECharts from 'echarts-for-react';

// 兼容现有的PredictionResponse接口
export interface PredictionResponse {
  home_win_prob: number;
  draw_prob: number;
  away_win_prob: number;
  confidence: number;
  prediction: 'home_win' | 'draw' | 'away_win';
  match_id?: number;
  ev?: number; // 期望收益
  suggestion?: string; // 投注建议
}

interface PredictionChartProps {
  // 支持新的简单接口
  home_prob?: number;
  draw_prob?: number;
  away_prob?: number;
  // 支持现有的PredictionResponse接口
  prediction?: PredictionResponse;
  title?: string;
  height?: string | number;
}

const PredictionChart: React.FC<PredictionChartProps> = ({
  home_prob,
  draw_prob,
  away_prob,
  prediction,
  title = '比赛预测结果',
  height = 350
}) => {
  // 兼容两种接口方式
  let homeWinProb: number;
  let drawProb: number;
  let awayWinProb: number;

  if (prediction) {
    // 使用PredictionResponse接口
    homeWinProb = prediction.home_win_prob;
    drawProb = prediction.draw_prob;
    awayWinProb = prediction.away_win_prob;
  } else {
    // 使用简单接口，提供默认值
    homeWinProb = home_prob || 0.6;
    drawProb = draw_prob || 0.25;
    awayWinProb = away_prob || 0.15;
  }

  // 转换为百分比显示
  const homePercent = Math.round(homeWinProb * 100);
  const drawPercent = Math.round(drawProb * 100);
  const awayPercent = Math.round(awayWinProb * 100);

  const option = {
    title: {
      text: title,
      left: 'center',
      textStyle: {
        fontSize: 16,
        fontWeight: 'bold'
      }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      },
      formatter: (params: any) => {
        const data = params[0];
        const resultNames = ['主胜', '平局', '客胜'];
        return `${resultNames[data.dataIndex]}: ${data.value}%`;
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: ['主胜', '平局', '客胜'],
      axisTick: {
        alignWithLabel: true
      }
    },
    yAxis: {
      type: 'value',
      max: 100,
      axisLabel: {
        formatter: '{value}%'
      }
    },
    series: [
      {
        name: '预测概率',
        type: 'bar',
        barWidth: '60%',
        data: [
          {
            value: homePercent,
            itemStyle: {
              color: '#52c41a' // 绿色 - 主胜
            }
          },
          {
            value: drawPercent,
            itemStyle: {
              color: '#8c8c8c' // 灰色 - 平局
            }
          },
          {
            value: awayPercent,
            itemStyle: {
              color: '#ff4d4f' // 红色 - 客胜
            }
          }
        ],
        label: {
          show: true,
          position: 'top',
          formatter: '{c}%',
          fontSize: 14,
          fontWeight: 'bold'
        }
      }
    ]
  };

  return (
    <div style={{
      width: '100%',
      height: typeof height === 'number' ? `${height}px` : height,
      padding: '10px',
      border: '1px solid #f0f0f0',
      borderRadius: '8px',
      backgroundColor: '#fafafa'
    }}>
      <ReactECharts
        option={option}
        style={{ height: '100%', width: '100%' }}
        notMerge={true}
        lazyUpdate={true}
      />
    </div>
  );
};

export default PredictionChart;