'use client'

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { MatchWithPrediction, PredictionResult } from '@/lib/api'
import {
  TrendingUp,
  Calendar,
  MapPin,
  Target,
  Brain,
  Clock,
  CheckCircle,
  XCircle,
  MinusCircle,
} from 'lucide-react'

interface PredictionDialogProps {
  match: MatchWithPrediction | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

function getRecommendationInfo(recommendation: string) {
  switch (recommendation) {
    case 'HOME_WIN':
      return {
        label: '推荐主胜',
        icon: <CheckCircle className="w-5 h-5 text-green-600" />,
        color: 'bg-green-100 text-green-800 border-green-200',
        description: '主队获胜概率较高'
      }
    case 'DRAW':
      return {
        label: '推荐平局',
        icon: <MinusCircle className="w-5 h-5 text-yellow-600" />,
        color: 'bg-yellow-100 text-yellow-800 border-yellow-200',
        description: '双方实力相当，可能战平'
      }
    case 'AWAY_WIN':
      return {
        label: '推荐客胜',
        icon: <XCircle className="w-5 h-5 text-red-600" />,
        color: 'bg-red-100 text-red-800 border-red-200',
        description: '客队获胜概率较高'
      }
    default:
      return {
        label: '数据不足',
        icon: <Brain className="w-5 h-5 text-gray-600" />,
        color: 'bg-gray-100 text-gray-800 border-gray-200',
        description: '无法确定预测结果'
      }
  }
}

function PredictionProgressBar({
  label,
  value,
  color
}: {
  label: string
  value: number
  color: string
}) {
  return (
    <div className="space-y-2">
      <div className="flex justify-between items-center">
        <span className="text-sm font-medium">{label}</span>
        <span className="text-sm font-bold">{value}%</span>
      </div>
      <div className="relative">
        <Progress value={value} className="h-3" />
        <div
          className="absolute top-0 left-0 h-3 rounded-full pointer-events-none"
          style={{
            width: `${value}%`,
            backgroundColor: color
          }}
        />
      </div>
    </div>
  )
}

function FeatureList({ features }: { features: string[] }) {
  const featureTranslations: Record<string, string> = {
    'h2h_history': '历史交锋记录',
    'recent_form': '近期状态',
    'home_advantage': '主场优势',
    'injuries': '伤病情况',
    'league_performance': '联赛表现',
    'goals_scored': '进球能力',
    'goals_conceded': '失球情况',
    'venue_factors': '场地因素',
    'weather_conditions': '天气条件',
    'referee_stats': '裁判统计'
  }

  return (
    <div className="grid grid-cols-2 gap-2">
      {features.map((feature, index) => (
        <div key={index} className="flex items-center gap-2 p-2 bg-gray-50 rounded">
          <CheckCircle className="w-4 h-4 text-green-600" />
          <span className="text-sm">
            {featureTranslations[feature] || feature}
          </span>
        </div>
      ))}
    </div>
  )
}

export function PredictionDialog({ match, open, onOpenChange }: PredictionDialogProps) {
  if (!match) return null

  const matchDate = new Date(match.match_date)
  const formattedDate = matchDate.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    weekday: 'long'
  })

  const prediction = match.prediction

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-xl">
            🏆 {match.home_team.name} vs {match.away_team.name}
          </DialogTitle>
          <DialogDescription>
            AI 驱动的足球比赛预测分析
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* 比赛基本信息 */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Calendar className="w-4 h-4" />
                比赛信息
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center gap-2 text-sm">
                <Clock className="w-4 h-4 text-gray-500" />
                <span className="font-medium">时间:</span>
                <span>{formattedDate}</span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <MapPin className="w-4 h-4 text-gray-500" />
                <span className="font-medium">场地:</span>
                <span>{match.venue || match.league}</span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <Target className="w-4 h-4 text-gray-500" />
                <span className="font-medium">联赛:</span>
                <span>{match.league}</span>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant={match.status === 'live' ? 'destructive' : 'outline'}>
                  {match.status === 'upcoming' && '即将开始'}
                  {match.status === 'live' && '进行中'}
                  {match.status === 'finished' && '已结束'}
                </Badge>
              </div>
            </CardContent>
          </Card>

          {/* 预测结果 */}
          {prediction && (
            <>
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base flex items-center gap-2">
                    <Brain className="w-4 h-4" />
                    AI 预测结果
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* 推荐结果 */}
                  <div className={`p-4 rounded-lg border ${getRecommendationInfo(prediction.recommendation).color}`}>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        {getRecommendationInfo(prediction.recommendation).icon}
                        <div>
                          <div className="font-semibold">
                            {getRecommendationInfo(prediction.recommendation).label}
                          </div>
                          <div className="text-sm opacity-75">
                            {getRecommendationInfo(prediction.recommendation).description}
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-2xl font-bold">
                          {prediction.confidence}%
                        </div>
                        <div className="text-sm opacity-75">置信度</div>
                      </div>
                    </div>
                  </div>

                  {/* 概率分布 */}
                  <div className="space-y-4">
                    <h4 className="font-medium flex items-center gap-2">
                      <TrendingUp className="w-4 h-4" />
                      概率分布
                    </h4>

                    <PredictionProgressBar
                      label="主胜"
                      value={prediction.predictions.home_win}
                      color="#10b981"
                    />

                    <PredictionProgressBar
                      label="平局"
                      value={prediction.predictions.draw}
                      color="#f59e0b"
                    />

                    <PredictionProgressBar
                      label="客胜"
                      value={prediction.predictions.away_win}
                      color="#ef4444"
                    />
                  </div>

                  {/* 模型信息 */}
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="font-medium">模型版本:</span>
                      <div className="text-gray-600">{prediction.model_version}</div>
                    </div>
                    <div>
                      <span className="font-medium">生成时间:</span>
                      <div className="text-gray-600">
                        {new Date(prediction.created_at).toLocaleString('zh-CN')}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* 分析特征 */}
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base flex items-center gap-2">
                    <Target className="w-4 h-4" />
                    分析特征
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <FeatureList features={prediction.features_used} />
                </CardContent>
              </Card>
            </>
          )}

          {/* 无预测数据时的提示 */}
          {!prediction && (
            <Card>
              <CardContent className="p-8 text-center">
                <Brain className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  预测数据生成中
                </h3>
                <p className="text-gray-500 mb-4">
                  AI 模型正在分析这场比赛，预测结果即将生成。
                </p>
                <Button variant="outline" disabled>
                  <Brain className="w-4 h-4 mr-2" />
                  分析中...
                </Button>
              </CardContent>
            </Card>
          )}

          {/* 操作按钮 */}
          <div className="flex justify-end gap-3 pt-4 border-t">
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              关闭
            </Button>
            {prediction && (
              <Button>
                <TrendingUp className="w-4 h-4 mr-2" />
                查看详细分析
              </Button>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}