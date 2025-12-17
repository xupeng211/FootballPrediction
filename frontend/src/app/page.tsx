'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { MatchList } from '@/components/match-list'
import { PredictionDialog } from '@/components/prediction-dialog'
import { Activity, TrendingUp, Clock, Shield, AlertCircle, CheckCircle, RefreshCw, ListFilter } from 'lucide-react'
import { apiClient, generateMockMatches, MatchWithPrediction, SystemHealth } from '@/lib/api'

export default function Home() {
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null)
  const [matches, setMatches] = useState<MatchWithPrediction[]>([])
  const [selectedMatch, setSelectedMatch] = useState<MatchWithPrediction | null>(null)
  const [loading, setLoading] = useState({
    health: true,
    matches: true
  })
  const [error, setError] = useState<string | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)

  useEffect(() => {
    checkBackendHealth()
    loadMatches()
  }, [])

  const checkBackendHealth = async () => {
    try {
      setLoading(prev => ({ ...prev, health: true }))
      const response = await apiClient.getHealth()
      setSystemHealth(response)
      setError(null)
    } catch (err) {
      console.error('Health check failed:', err)
      setError(err instanceof Error ? err.message : '未知错误')
      setSystemHealth(null)
    } finally {
      setLoading(prev => ({ ...prev, health: false }))
    }
  }

  const loadMatches = async () => {
    try {
      setLoading(prev => ({ ...prev, matches: true }))

      // 尝试从真实API获取数据
      const realMatches = await apiClient.getMatches({ limit: 20 })

      if (realMatches.length > 0) {
        // 为每场比赛获取预测数据
        const matchsWithPredictions = await Promise.all(
          realMatches.map(async (match) => {
            try {
              const prediction = await apiClient.getPrediction(match.id)
              return { ...match, prediction }
            } catch {
              // 如果获取预测失败，返回没有预测的比赛
              return match
            }
          })
        )
        setMatches(matchsWithPredictions)
      } else {
        // 如果没有真实数据，使用mock数据
        console.log('No real matches found, using mock data')
        const mockMatches = generateMockMatches(12)
        setMatches(mockMatches)
      }
    } catch (err) {
      console.error('Failed to load matches:', err)
      // API失败时使用mock数据
      console.log('API failed, using mock data')
      const mockMatches = generateMockMatches(12)
      setMatches(mockMatches)
    } finally {
      setLoading(prev => ({ ...prev, matches: false }))
    }
  }

  const handleMatchClick = (match: MatchWithPrediction) => {
    setSelectedMatch(match)
    setDialogOpen(true)
  }

  const StatusBadge = ({ healthy, label }: { healthy: boolean; label: string }) => (
    <Badge variant={healthy ? "default" : "destructive"} className="flex items-center gap-1">
      {healthy ? (
        <CheckCircle className="w-3 h-3" />
      ) : (
        <AlertCircle className="w-3 h-3" />
      )}
      {label}
    </Badge>
  )

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800">
      <div className="container mx-auto px-4 py-8">
        {/* 头部 */}
        <div className="text-center mb-10">
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-4">
            ⚽ 足球预测仪表盘
          </h1>
          <p className="text-lg text-gray-600 dark:text-gray-300 max-w-2xl mx-auto">
            基于机器学习的足球比赛结果预测系统，提供准确的比赛分析和预测
          </p>
        </div>

        {/* 系统状态卡片 */}
        <Card className="mb-8">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Activity className="w-5 h-5 text-blue-600" />
                <CardTitle>系统状态</CardTitle>
              </div>
              <Button
                onClick={checkBackendHealth}
                disabled={loading.health}
                variant="outline"
                size="sm"
              >
                {loading.health ? (
                  <>
                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    检查中...
                  </>
                ) : (
                  <>
                    <RefreshCw className="w-4 h-4 mr-2" />
                    刷新状态
                  </>
                )}
              </Button>
            </div>
            <CardDescription>
              实时监控系统组件健康状态
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loading.health ? (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                <span className="ml-2">检查系统健康状态...</span>
              </div>
            ) : error ? (
              <div className="text-center py-8">
                <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
                <p className="text-red-600 font-medium">无法连接到后端服务</p>
                <p className="text-gray-500 text-sm mt-1">{error}</p>
                <Button onClick={checkBackendHealth} className="mt-4">
                  重新连接
                </Button>
              </div>
            ) : systemHealth ? (
              <div className="space-y-4">
                {/* 总体状态 */}
                <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                  <div className="flex items-center gap-2">
                    <Shield className="w-5 h-5" />
                    <span className="font-medium">系统整体状态</span>
                  </div>
                  <StatusBadge
                    healthy={systemHealth.status === 'healthy'}
                    label={systemHealth.status === 'healthy' ? '健康' : '异常'}
                  />
                </div>

                {/* 组件状态 */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium text-sm">数据库</span>
                      <StatusBadge
                        healthy={systemHealth.checks.database.healthy}
                        label={systemHealth.checks.database.healthy ? '正常' : '异常'}
                      />
                    </div>
                    <p className="text-xs text-gray-500">
                      响应时间: {systemHealth.checks.database.response_time_ms}ms
                    </p>
                  </div>

                  <div className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium text-sm">Redis缓存</span>
                      <StatusBadge
                        healthy={systemHealth.checks.redis.healthy}
                        label={systemHealth.checks.redis.healthy ? '正常' : '异常'}
                      />
                    </div>
                    <p className="text-xs text-gray-500">
                      响应时间: {systemHealth.checks.redis.response_time_ms}ms
                    </p>
                  </div>

                  <div className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium text-sm">文件系统</span>
                      <StatusBadge
                        healthy={systemHealth.checks.filesystem.healthy}
                        label={systemHealth.checks.filesystem.healthy ? '正常' : '异常'}
                      />
                    </div>
                    <p className="text-xs text-gray-500">
                      响应时间: {systemHealth.checks.filesystem.response_time_ms}ms
                    </p>
                  </div>
                </div>
              </div>
            ) : null}
          </CardContent>
        </Card>

        {/* 比赛列表 */}
        <div className="space-y-6">
          {/* 比赛列表头部 */}
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                比赛预测
              </h2>
              <p className="text-gray-600 dark:text-gray-300">
                基于AI算法的足球比赛结果预测分析
              </p>
            </div>
            <div className="flex items-center gap-3">
              <Button
                onClick={loadMatches}
                disabled={loading.matches}
                variant="outline"
                size="sm"
              >
                {loading.matches ? (
                  <>
                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    刷新中...
                  </>
                ) : (
                  <>
                    <RefreshCw className="w-4 h-4 mr-2" />
                    刷新比赛
                  </>
                )}
              </Button>
              <Button variant="outline" size="sm">
                <ListFilter className="w-4 h-4 mr-2" />
                筛选
              </Button>
            </div>
          </div>

          {/* 比赛列表内容 */}
          <MatchList
            matches={matches}
            loading={loading.matches}
            onMatchClick={handleMatchClick}
          />
        </div>

        {/* 功能卡片 */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mt-12">
          <Card className="hover:shadow-lg transition-shadow">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-green-600" />
                比赛预测
              </CardTitle>
              <CardDescription>
                使用先进的机器学习模型预测比赛结果
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-gray-600 mb-4">
                基于历史数据、球队状态、伤病情况等多维度因素进行分析
              </p>
              <Button className="w-full" disabled>
                即将开放
              </Button>
            </CardContent>
          </Card>

          <Card className="hover:shadow-lg transition-shadow">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity className="w-5 h-5 text-blue-600" />
                数据分析
              </CardTitle>
              <CardDescription>
                深度分析球队表现和统计数据
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-gray-600 mb-4">
                提供详细的球队对比、历史战绩和趋势分析
              </p>
              <Button className="w-full" disabled>
                即将开放
              </Button>
            </CardContent>
          </Card>

          <Card className="hover:shadow-lg transition-shadow">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="w-5 h-5 text-purple-600" />
                模型管理
              </CardTitle>
              <CardDescription>
                监控和管理机器学习模型性能
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-gray-600 mb-4">
                实时跟踪模型准确率，支持模型版本管理
              </p>
              <Button className="w-full" disabled>
                即将开放
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* 预测详情弹窗 */}
      <PredictionDialog
        match={selectedMatch}
        open={dialogOpen}
        onOpenChange={setDialogOpen}
      />
    </div>
  )
}