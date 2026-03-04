import { useEffect, useState, useRef } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { motion, AnimatePresence } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
} from 'recharts'
import { api } from '../lib/api'

interface DashboardData {
  realtime: {
    active_students: number
    today_trainings: number
    average_score: number
    pass_rate: number
  }
  class_ranking: Array<{
    class_id: string
    class_name: string
    average_score: number
    training_count: number
    rank: number
  }>
  ability_distribution: Array<{
    ability_id: string
    ability_name: string
    avg: number
    distribution: number[]
  }>
  trend: Array<{
    date: string
    training_count: number
    average_score: number
    pass_rate: number
  }>
  lab_status: Array<{
    lab_id: string
    lab_name: string
    status: string
    current_students: number
    capacity: number
  }>
  updated_at: string
}

// Animated counter component
function AnimatedNumber({ value, suffix = '' }: { value: number; suffix?: string }) {
  const [display, setDisplay] = useState(0)
  
  useEffect(() => {
    const duration = 1000
    const steps = 30
    const increment = value / steps
    let current = 0
    
    const timer = setInterval(() => {
      current += increment
      if (current >= value) {
        setDisplay(value)
        clearInterval(timer)
      } else {
        setDisplay(Math.floor(current))
      }
    }, duration / steps)
    
    return () => clearInterval(timer)
  }, [value])
  
  return (
    <span className="font-display text-4xl font-bold text-gradient tabular-nums">
      {display.toLocaleString()}{suffix}
    </span>
  )
}

// Stat card component
function StatCard({ 
  icon, 
  label, 
  value, 
  suffix = '',
  delay = 0 
}: { 
  icon: string
  label: string
  value: number
  suffix?: string
  delay?: number 
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.5 }}
      className="card-stat relative overflow-hidden group"
    >
      {/* Glow effect */}
      <div className="absolute inset-0 bg-gradient-to-br from-accent-blue/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
      
      {/* Icon */}
      <div className="text-4xl mb-3">{icon}</div>
      
      {/* Value */}
      <AnimatedNumber value={value} suffix={suffix} />
      
      {/* Label */}
      <p className="text-text-muted text-sm mt-2 font-body">{label}</p>
      
      {/* Corner decoration */}
      <div className="absolute top-0 right-0 w-8 h-8">
        <div className="absolute top-0 right-0 w-full h-0.5 bg-gradient-to-l from-accent-blue/50 to-transparent" />
        <div className="absolute top-0 right-0 w-0.5 h-full bg-gradient-to-b from-accent-blue/50 to-transparent" />
      </div>
    </motion.div>
  )
}

// Lab status indicator
function LabStatusCard({ lab }: { lab: DashboardData['lab_status'][0] }) {
  const statusColors: Record<string, string> = {
    available: 'bg-status-success',
    in_use: 'bg-status-warning',
    maintenance: 'bg-status-danger',
  }
  
  const statusLabels: Record<string, string> = {
    available: '空闲',
    in_use: '使用中',
    maintenance: '维护中',
  }
  
  const usage = (lab.current_students / lab.capacity) * 100
  
  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      className="glass-panel p-4 relative overflow-hidden"
    >
      {/* Status indicator */}
      <div className="flex items-center justify-between mb-3">
        <h4 className="font-display text-sm font-semibold text-text-primary">{lab.lab_name}</h4>
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${statusColors[lab.status] || statusColors.available} animate-pulse`} />
          <span className="text-xs text-text-muted">
            {statusLabels[lab.status] || statusLabels.available}
          </span>
        </div>
      </div>
      
      {/* Usage bar */}
      <div className="h-2 bg-railway-700 rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${usage}%` }}
          transition={{ duration: 1, delay: 0.5 }}
          className="h-full bg-gradient-to-r from-accent-electric to-accent-cyan"
        />
      </div>
      
      {/* Stats */}
      <div className="flex justify-between mt-2 text-xs">
        <span className="text-accent-cyan font-mono">{lab.current_students} / {lab.capacity}</span>
        <span className="text-text-muted">{usage.toFixed(0)}%</span>
      </div>
    </motion.div>
  )
}

export default function Dashboard() {
  const { t } = useTranslation()
  const [time, setTime] = useState(new Date())
  const wsRef = useRef<WebSocket | null>(null)
  
  // Fetch dashboard data
  const { data, isLoading, refetch } = useQuery<DashboardData>({
    queryKey: ['dashboard'],
    queryFn: async () => {
      const res = await api.get('/api/v1/dashboard/')
      return res.data
    },
    refetchInterval: 30000, // Refetch every 30 seconds
  })
  
  // Update time every second
  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])
  
  // WebSocket for realtime updates
  useEffect(() => {
    const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/v1/dashboard/ws`
    
    try {
      wsRef.current = new WebSocket(wsUrl)
      
      wsRef.current.onmessage = () => {
        refetch()
      }
      
      wsRef.current.onerror = () => {
        // Fallback to polling
      }
    } catch {
      // WebSocket not available, use polling
    }
    
    return () => {
      wsRef.current?.close()
    }
  }, [refetch])
  
  // Prepare radar data
  const radarData = data?.ability_distribution.map(a => ({
    ability: a.ability_name.slice(0, 4),
    value: a.avg,
    fullMark: 100,
  })) || []
  
  // Prepare trend data (last 7 days)
  const trendData = data?.trend.slice(-7).map(t => ({
    date: t.date.slice(5), // MM-DD
    score: t.average_score,
    count: t.training_count,
  })) || []

  if (isLoading) {
    return (
      <div className="min-h-screen bg-railway-900 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-accent-blue/30 border-t-accent-blue rounded-full animate-spin mx-auto mb-4" />
          <p className="text-text-muted">{t('loading')}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-railway-900 bg-grid noise-overlay p-6 overflow-hidden">
      {/* Header */}
      <header className="mb-6">
        <div className="flex items-center justify-between">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex items-center gap-4"
          >
            <div className="w-12 h-12 bg-gradient-to-br from-accent-blue to-accent-cyan rounded-xl flex items-center justify-center shadow-glow-md">
              <svg viewBox="0 0 24 24" fill="currentColor" className="w-8 h-8 text-white">
                <path d="M12 2C8 2 4 2.5 4 6v9.5C4 17.43 5.57 19 7.5 19L6 20.5v.5h2.23l2-2H14l2 2h2v-.5L16.5 19c1.93 0 3.5-1.57 3.5-3.5V6c0-3.5-4-4-8-4zM7.5 17c-.83 0-1.5-.67-1.5-1.5S6.67 14 7.5 14s1.5.67 1.5 1.5S8.33 17 7.5 17zm3.5-6H6V6h5v5zm2 0V6h5v5h-5zm3.5 6c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5z"/>
              </svg>
            </div>
            <div>
              <h1 className="font-display text-3xl font-bold text-gradient tracking-wide">
                智能实训能力评估平台
              </h1>
              <p className="text-text-muted text-sm">辽宁铁道职业技术学院 · 实时数据监控大屏</p>
            </div>
          </motion.div>
          
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex items-center gap-6"
          >
            {/* Time display */}
            <div className="text-right">
              <p className="font-mono text-2xl font-bold text-accent-cyan">
                {time.toLocaleTimeString('zh-CN', { hour12: false })}
              </p>
              <p className="text-text-muted text-sm">
                {time.toLocaleDateString('zh-CN', { weekday: 'long', month: 'long', day: 'numeric' })}
              </p>
            </div>
            
            {/* Back button */}
            <Link
              to="/"
              className="btn-secondary !py-2"
            >
              返回系统
            </Link>
          </motion.div>
        </div>
      </header>
      
      {/* Main Grid */}
      <div className="grid grid-cols-12 gap-4">
        {/* Left Column - Stats & Ranking */}
        <div className="col-span-3 space-y-4">
          {/* Realtime Stats */}
          <div className="grid grid-cols-2 gap-4">
            <StatCard
              icon="👥"
              label={t('dashboard.active_students')}
              value={data?.realtime.active_students || 0}
              delay={0}
            />
            <StatCard
              icon="📊"
              label={t('dashboard.today_trainings')}
              value={data?.realtime.today_trainings || 0}
              delay={0.1}
            />
            <StatCard
              icon="🎯"
              label={t('dashboard.average_score')}
              value={data?.realtime.average_score || 0}
              suffix=""
              delay={0.2}
            />
            <StatCard
              icon="✅"
              label={t('dashboard.pass_rate')}
              value={data?.realtime.pass_rate || 0}
              suffix="%"
              delay={0.3}
            />
          </div>
          
          {/* Class Ranking */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="glass-panel p-5"
          >
            <h3 className="font-display text-lg font-semibold text-accent-cyan mb-4 flex items-center gap-2">
              <span>🏆</span>
              {t('dashboard.class_ranking')}
            </h3>
            
            <div className="space-y-3">
              {data?.class_ranking.slice(0, 5).map((cls, index) => (
                <motion.div
                  key={cls.class_id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.5 + index * 0.1 }}
                  className="flex items-center gap-3 p-3 bg-railway-700/30 rounded-lg hover:bg-railway-700/50 transition-colors"
                >
                  {/* Rank badge */}
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center font-display font-bold
                    ${index === 0 ? 'bg-yellow-500/20 text-yellow-400' : 
                      index === 1 ? 'bg-gray-400/20 text-gray-300' :
                      index === 2 ? 'bg-orange-500/20 text-orange-400' :
                      'bg-railway-600 text-text-muted'}`}
                  >
                    {cls.rank}
                  </div>
                  
                  <div className="flex-1">
                    <p className="font-semibold text-text-primary text-sm">{cls.class_name}</p>
                    <p className="text-xs text-text-muted">{cls.training_count} 次实训</p>
                  </div>
                  
                  <div className="text-right">
                    <p className="font-mono font-bold text-accent-cyan">{cls.average_score}</p>
                    <p className="text-xs text-text-muted">平均分</p>
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </div>
        
        {/* Center Column - Charts */}
        <div className="col-span-6 space-y-4">
          {/* Ability Radar */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.3 }}
            className="glass-panel p-5"
          >
            <h3 className="font-display text-lg font-semibold text-accent-cyan mb-4 flex items-center gap-2">
              <span>🎯</span>
              {t('dashboard.ability_dist')}
            </h3>
            
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={radarData}>
                  <PolarGrid stroke="#234069" />
                  <PolarAngleAxis 
                    dataKey="ability" 
                    tick={{ fill: '#8eb8e5', fontSize: 12 }}
                  />
                  <PolarRadiusAxis 
                    angle={30} 
                    domain={[0, 100]} 
                    tick={{ fill: '#5d7a9c', fontSize: 10 }}
                  />
                  <Radar
                    name="能力值"
                    dataKey="value"
                    stroke="#00d4ff"
                    fill="#00d4ff"
                    fillOpacity={0.3}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </motion.div>
          
          {/* Trend Chart */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.4 }}
            className="glass-panel p-5"
          >
            <h3 className="font-display text-lg font-semibold text-accent-cyan mb-4 flex items-center gap-2">
              <span>📈</span>
              {t('dashboard.trend')}
            </h3>
            
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trendData}>
                  <defs>
                    <linearGradient id="scoreGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#00d4ff" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#00d4ff" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <XAxis 
                    dataKey="date" 
                    tick={{ fill: '#8eb8e5', fontSize: 11 }}
                    axisLine={{ stroke: '#234069' }}
                  />
                  <YAxis 
                    tick={{ fill: '#5d7a9c', fontSize: 11 }}
                    axisLine={{ stroke: '#234069' }}
                    domain={[0, 100]}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#111d32',
                      border: '1px solid #234069',
                      borderRadius: '8px',
                    }}
                    labelStyle={{ color: '#8eb8e5' }}
                  />
                  <Area
                    type="monotone"
                    dataKey="score"
                    stroke="#00d4ff"
                    strokeWidth={2}
                    fill="url(#scoreGradient)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </motion.div>
        </div>
        
        {/* Right Column - Lab Status */}
        <div className="col-span-3 space-y-4">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="glass-panel p-5"
          >
            <h3 className="font-display text-lg font-semibold text-accent-cyan mb-4 flex items-center gap-2">
              <span>🏭</span>
              {t('dashboard.lab_status')}
            </h3>
            
            <div className="space-y-3">
              <AnimatePresence>
                {data?.lab_status.map((lab, index) => (
                  <motion.div
                    key={lab.lab_id}
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.6 + index * 0.1 }}
                  >
                    <LabStatusCard lab={lab} />
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          </motion.div>
          
          {/* Distribution Bar Chart */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.7 }}
            className="glass-panel p-5"
          >
            <h3 className="font-display text-lg font-semibold text-accent-cyan mb-4">
              能力达标分布
            </h3>
            
            <div className="h-40">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={data?.ability_distribution.map(a => ({
                    name: a.ability_name.slice(0, 2),
                    value: a.avg,
                  }))}
                  layout="vertical"
                >
                  <XAxis type="number" domain={[0, 100]} tick={{ fill: '#5d7a9c', fontSize: 10 }} />
                  <YAxis type="category" dataKey="name" tick={{ fill: '#8eb8e5', fontSize: 10 }} width={30} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#111d32',
                      border: '1px solid #234069',
                      borderRadius: '8px',
                    }}
                  />
                  <Bar 
                    dataKey="value" 
                    fill="#00d4ff" 
                    radius={[0, 4, 4, 0]}
                    background={{ fill: '#16263f' }}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </motion.div>
        </div>
      </div>
      
      {/* Bottom status bar */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.8 }}
        className="mt-4 glass-panel p-3 flex items-center justify-between text-sm"
      >
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-status-success animate-pulse" />
            <span className="text-text-muted">系统运行正常</span>
          </div>
          <div className="text-text-muted">
            数据更新: {data?.updated_at ? new Date(data.updated_at).toLocaleTimeString() : '-'}
          </div>
        </div>
        
        <div className="flex items-center gap-4 text-text-muted">
          <span>Version 1.0.0</span>
          <span>|</span>
          <span>Powered by DenseMatrix AI</span>
        </div>
      </motion.div>
    </div>
  )
}
