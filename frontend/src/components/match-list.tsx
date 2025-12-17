'use client'

import { useState } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { MatchWithPrediction, PredictionResult } from '@/lib/api'
import { Calendar, MapPin, TrendingUp, Eye } from 'lucide-react'

interface MatchListProps {
  matches: MatchWithPrediction[]
  onMatchClick?: (match: MatchWithPrediction) => void
  loading?: boolean
}

interface MatchCardProps {
  match: MatchWithPrediction
  onClick?: () => void
}

function getRecommendationBadge(recommendation: string) {
  switch (recommendation) {
    case 'HOME_WIN':
      return <Badge variant="default" className="bg-green-600 hover:bg-green-700">主胜</Badge>
    case 'DRAW':
      return <Badge variant="secondary" className="bg-yellow-600 hover:bg-yellow-700">平局</Badge>
    case 'AWAY_WIN':
      return <Badge variant="destructive" className="bg-red-600 hover:bg-red-700">客胜</Badge>
    default:
      return <Badge variant="outline">未知</Badge>
  }
}

function getStatusBadge(status: string) {
  switch (status) {
    case 'upcoming':
      return <Badge variant="outline" className="text-blue-600 border-blue-600">即将开始</Badge>
    case 'live':
      return <Badge className="bg-red-600 hover:bg-red-700 animate-pulse">进行中</Badge>
    case 'finished':
      return <Badge variant="secondary">已结束</Badge>
    default:
      return <Badge variant="outline">未知</Badge>
  }
}

function PredictionBar({ prediction }: { prediction: PredictionResult }) {
  const { predictions } = prediction

  return (
    <div className="space-y-2">
      <div className="flex justify-between text-xs text-gray-600">
        <span>主胜 {predictions.home_win}%</span>
        <span>平局 {predictions.draw}%</span>
        <span>客胜 {predictions.away_win}%</span>
      </div>
      <div className="flex h-2 overflow-hidden rounded-full bg-gray-200">
        <div
          className="bg-green-500"
          style={{ width: `${predictions.home_win}%` }}
        />
        <div
          className="bg-yellow-500"
          style={{ width: `${predictions.draw}%` }}
        />
        <div
          className="bg-red-500"
          style={{ width: `${predictions.away_win}%` }}
        />
      </div>
    </div>
  )
}

function MatchCard({ match, onClick }: MatchCardProps) {
  const matchDate = new Date(match.match_date)
  const formattedDate = matchDate.toLocaleDateString('zh-CN', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })

  return (
    <Card
      className="hover:shadow-lg transition-all duration-200 cursor-pointer border-l-4 border-l-blue-600 hover:border-l-blue-800"
      onClick={onClick}
    >
      <CardContent className="p-6">
        {/* 比赛头部信息 */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-4 text-sm text-gray-600">
            <div className="flex items-center gap-1">
              <Calendar className="w-4 h-4" />
              <span>{formattedDate}</span>
            </div>
            <div className="flex items-center gap-1">
              <MapPin className="w-4 h-4" />
              <span>{match.venue || match.league}</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {getStatusBadge(match.status)}
            <Button variant="ghost" size="sm" className="p-1">
              <Eye className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {/* 球队信息 */}
        <div className="grid grid-cols-3 gap-4 items-center mb-4">
          {/* 主队 */}
          <div className="text-center">
            <div className="font-semibold text-lg mb-1">{match.home_team.name}</div>
            <div className="text-sm text-gray-500">{match.home_team.short_name}</div>
          </div>

          {/* VS */}
          <div className="text-center">
            <div className="text-gray-400 font-semibold">VS</div>
          </div>

          {/* 客队 */}
          <div className="text-center">
            <div className="font-semibold text-lg mb-1">{match.away_team.name}</div>
            <div className="text-sm text-gray-500">{match.away_team.short_name}</div>
          </div>
        </div>

        {/* 预测信息 */}
        {match.prediction && (
          <div className="border-t pt-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-blue-600" />
                <span className="font-medium text-sm">AI 预测</span>
                <span className="text-xs text-gray-500">
                  置信度: {match.prediction.confidence}%
                </span>
              </div>
              {getRecommendationBadge(match.prediction.recommendation)}
            </div>

            <PredictionBar prediction={match.prediction} />
          </div>
        )}

        {/* 如果没有预测数据 */}
        {!match.prediction && (
          <div className="border-t pt-4">
            <div className="text-center text-gray-500 text-sm">
              <TrendingUp className="w-4 h-4 mx-auto mb-2 opacity-50" />
              预测数据生成中...
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export function MatchList({ matches, onMatchClick, loading = false }: MatchListProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {Array.from({ length: 6 }, (_, i) => (
          <Card key={i} className="animate-pulse">
            <CardContent className="p-6">
              <div className="h-4 bg-gray-200 rounded mb-4 w-32"></div>
              <div className="h-6 bg-gray-200 rounded mb-2"></div>
              <div className="h-4 bg-gray-200 rounded mb-4"></div>
              <div className="h-4 bg-gray-200 rounded"></div>
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  if (matches.length === 0) {
    return (
      <Card>
        <CardContent className="p-12 text-center">
          <TrendingUp className="w-12 h-12 mx-auto mb-4 text-gray-400" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">暂无比赛数据</h3>
          <p className="text-gray-500">
            当前没有可用的比赛预测数据，请稍后重试。
          </p>
        </CardContent>
      </Card>
    )
  }

  // 按日期分组比赛
  const groupedMatches = matches.reduce((groups, match) => {
    const date = new Date(match.match_date).toDateString()
    if (!groups[date]) {
      groups[date] = []
    }
    groups[date].push(match)
    return groups
  }, {} as Record<string, MatchWithPrediction[]>)

  const sortedDates = Object.keys(groupedMatches).sort((a, b) =>
    new Date(a).getTime() - new Date(b).getTime()
  )

  return (
    <div className="space-y-8">
      {sortedDates.map((date) => {
        const dateObj = new Date(date)
        const formattedDate = dateObj.toLocaleDateString('zh-CN', {
          year: 'numeric',
          month: 'long',
          day: 'numeric',
          weekday: 'long'
        })

        return (
          <div key={date}>
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              {formattedDate}
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {groupedMatches[date].map((match) => (
                <MatchCard
                  key={match.id}
                  match={match}
                  onClick={() => onMatchClick?.(match)}
                />
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}