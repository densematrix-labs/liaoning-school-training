import { useQuery } from '@tanstack/react-query'
import { api } from '../../lib/api'
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
} from 'recharts'
import { motion } from 'framer-motion'

export default function StudentAbility() {
  const { data: abilityMap, isLoading } = useQuery({
    queryKey: ['studentAbility'],
    queryFn: async () => {
      const res = await api.get('/api/v1/abilities/profile')
      return res.data
    },
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin w-8 h-8 border-2 border-accent-blue border-t-transparent rounded-full" />
      </div>
    )
  }

  const radarData = abilityMap?.radar_data?.map((item: any) => ({
    ...item,
    fullMark: 100,
  })) || []

  const barData = abilityMap?.radar_data || []

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">能力图谱</h1>
        <p className="text-text-muted mt-1">基于实训表现的能力评估分析</p>
      </div>

      {/* Summary Card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="railway-card-glow p-6"
      >
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-medium text-text-primary">综合能力评分</h2>
            <p className="text-text-muted text-sm mt-1">
              最后更新: {abilityMap?.updated_at ? new Date(abilityMap.updated_at).toLocaleString('zh-CN') : '-'}
            </p>
          </div>
          <div className="text-right">
            <p className="stat-value text-4xl">{abilityMap?.total_score || 0}</p>
            <p className="text-sm text-text-muted mt-1">满分 100</p>
          </div>
        </div>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Radar Chart */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2 }}
          className="railway-card p-6"
        >
          <h2 className="section-title mb-4">能力雷达图</h2>
          <div className="h-96">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart cx="50%" cy="50%" outerRadius="70%" data={radarData}>
                <PolarGrid stroke="rgba(0, 212, 255, 0.2)" />
                <PolarAngleAxis
                  dataKey="name"
                  tick={{ fill: '#8eb8e5', fontSize: 12 }}
                />
                <PolarRadiusAxis
                  angle={30}
                  domain={[0, 100]}
                  tick={{ fill: '#5d7a9c', fontSize: 10 }}
                  tickCount={5}
                />
                <Radar
                  name="能力值"
                  dataKey="score"
                  stroke="#00d4ff"
                  fill="#00d4ff"
                  fillOpacity={0.3}
                  strokeWidth={2}
                />
                <Radar
                  name="毕业标准"
                  dataKey="threshold"
                  stroke="#ffaa00"
                  fill="none"
                  strokeWidth={1}
                  strokeDasharray="5 5"
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        {/* Bar Chart */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.3 }}
          className="railway-card p-6"
        >
          <h2 className="section-title mb-4">能力柱状图</h2>
          <div className="h-96">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={barData} layout="vertical" margin={{ left: 80 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(0, 212, 255, 0.1)" />
                <XAxis type="number" domain={[0, 100]} tick={{ fill: '#8eb8e5' }} />
                <YAxis
                  type="category"
                  dataKey="name"
                  tick={{ fill: '#8eb8e5', fontSize: 12 }}
                  width={80}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#111d32',
                    border: '1px solid rgba(0, 212, 255, 0.3)',
                    borderRadius: '8px',
                  }}
                  labelStyle={{ color: '#e8f4ff' }}
                />
                <Bar dataKey="score" radius={[0, 4, 4, 0]}>
                  {barData.map((entry: any, index: number) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={entry.score >= entry.threshold ? '#00ff88' : '#00d4ff'}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </motion.div>
      </div>

      {/* Ability Details */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="railway-card p-6"
      >
        <h2 className="section-title mb-4">能力详情</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {abilityMap?.radar_data?.map((ability: any) => (
            <div
              key={ability.ability_id}
              className={`p-4 rounded-lg border ${
                ability.score >= ability.threshold
                  ? 'bg-status-success/5 border-status-success/20'
                  : 'bg-status-warning/5 border-status-warning/20'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="font-medium text-text-primary">{ability.name}</span>
                <span className={`font-mono font-bold ${
                  ability.score >= ability.threshold ? 'text-status-success' : 'text-status-warning'
                }`}>
                  {ability.score}
                </span>
              </div>
              <div className="h-2 bg-railway-700 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    ability.score >= ability.threshold ? 'bg-status-success' : 'bg-accent-blue'
                  }`}
                  style={{ width: `${ability.score}%` }}
                />
              </div>
              <div className="flex items-center justify-between mt-2 text-xs text-text-muted">
                <span>权重: {(ability.weight * 100).toFixed(0)}%</span>
                <span>达标线: {ability.threshold}</span>
              </div>
            </div>
          ))}
        </div>
      </motion.div>

      {/* Weak Abilities Warning */}
      {abilityMap?.weak_abilities?.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="alert-warning p-4 rounded-lg"
        >
          <div className="flex items-start gap-3">
            <svg className="w-6 h-6 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <div>
              <h3 className="font-medium">薄弱能力提示</h3>
              <p className="text-sm mt-1 opacity-80">
                以下能力低于毕业标准，建议重点加强练习：
                {abilityMap.weak_abilities.map((a: any) => a.name).join('、')}
              </p>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  )
}
