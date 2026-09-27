import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
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
    threshold: number
    ready_count: number
    not_ready_count: number
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
  graduation_summary: {
    total_students: number
    evaluated_students: number
    ready_count: number
    risk_count: number
    ready_rate: number
  }
  score_distribution: Array<{ label: string; count: number }>
  updated_at: string
}

interface RealtimeActivity {
  id: string
  student_name: string
  student_id: string
  class_name: string
  project_name: string
  status: string
  score: number | null
  passed: boolean | null
  timestamp: string | null
}

interface AlertInfo {
  type: string
  level: string
  message: string
  student_id: string | null
  student_name: string | null
  timestamp: string
}

const scoreColors = ['#ff6674', '#ffc04a', '#36c8ff', '#64ecff', '#39e58c']

function AnimatedNumber({ value, suffix = '' }: { value: number; suffix?: string }) {
  const [display, setDisplay] = useState(0)

  useEffect(() => {
    const duration = 700
    const steps = 24
    const increment = value / steps
    const factor = Number.isInteger(value) ? 1 : 10
    let current = 0
    const timer = window.setInterval(() => {
      current += increment
      if (current >= value) {
        setDisplay(value)
        window.clearInterval(timer)
      } else {
        setDisplay(Math.floor(current * factor) / factor)
      }
    }, duration / steps)
    return () => window.clearInterval(timer)
  }, [value])

  return <span>{display.toLocaleString()}{suffix}</span>
}

function MetricCard({ code, label, value, suffix = '', tone = 'cyan' }: {
  code: string
  label: string
  value: number
  suffix?: string
  tone?: 'cyan' | 'green' | 'amber' | 'red'
}) {
  return (
    <div className={`dashboard-metric dashboard-metric-${tone}`}>
      <div className="dashboard-metric-head"><span>{code}</span><i aria-hidden="true" /></div>
      <strong><AnimatedNumber value={value} suffix={suffix} /></strong>
      <p>{label}</p>
    </div>
  )
}

function PanelTitle({ code, title, meta }: { code: string; title: string; meta?: string }) {
  return (
    <div className="dashboard-panel-title">
      <div><span>{code}</span><h2>{title}</h2></div>
      {meta && <p>{meta}</p>}
    </div>
  )
}

function formatTime(value: string | null) {
  if (!value) return '--:--'
  return new Date(value).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false })
}

export default function Dashboard() {
  const [time, setTime] = useState(new Date())
  const wsRef = useRef<WebSocket | null>(null)

  const { data, isLoading, refetch } = useQuery<DashboardData>({
    queryKey: ['dashboard'],
    queryFn: async () => (await api.get('/api/v1/dashboard/')).data,
    refetchInterval: 30000,
  })
  const { data: activities = [] } = useQuery<RealtimeActivity[]>({
    queryKey: ['dashboard-realtime'],
    queryFn: async () => (await api.get('/api/v1/dashboard/realtime?limit=6')).data,
    refetchInterval: 30000,
  })
  const { data: alerts = [] } = useQuery<AlertInfo[]>({
    queryKey: ['dashboard-alerts'],
    queryFn: async () => (await api.get('/api/v1/dashboard/alerts?limit=4')).data,
    refetchInterval: 30000,
  })

  useEffect(() => {
    const timer = window.setInterval(() => setTime(new Date()), 1000)
    return () => window.clearInterval(timer)
  }, [])

  useEffect(() => {
    const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/v1/dashboard/ws`
    try {
      wsRef.current = new WebSocket(wsUrl)
      wsRef.current.onmessage = () => refetch()
      wsRef.current.onerror = () => undefined
    } catch {
      // The 30-second query interval remains as the fallback.
    }
    return () => wsRef.current?.close()
  }, [refetch])

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-railway-900">
        <div className="text-center"><div className="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-4 border-accent-blue/30 border-t-accent-blue" /><p className="text-text-muted">数据加载中</p></div>
      </div>
    )
  }

  const realtime = data?.realtime || { active_students: 0, today_trainings: 0, average_score: 0, pass_rate: 0 }
  const graduation = data?.graduation_summary || { total_students: 0, evaluated_students: 0, ready_count: 0, risk_count: 0, ready_rate: 0 }
  const ranking = data?.class_ranking.slice(0, 5) || []
  const maxRankingScore = Math.max(...ranking.map(item => item.average_score), 100)
  const radarData = data?.ability_distribution.map(item => ({
    ability: item.ability_name.length > 5 ? `${item.ability_name.slice(0, 5)}…` : item.ability_name,
    value: item.avg,
    threshold: item.threshold,
  })) || []
  const trendData = data?.trend.slice(-7).map(item => ({ date: item.date.slice(5), score: item.average_score, count: item.training_count })) || []
  const hasTrendData = trendData.some(item => item.count > 0 || item.score > 0)
  const scoreDistribution = data?.score_distribution || []
  const labs = data?.lab_status || []
  const inUseLabs = labs.filter(lab => lab.status === 'in_use').length
  const maintenanceLabs = labs.filter(lab => lab.status === 'maintenance')
  const belowTargetAbilities = (data?.ability_distribution || []).filter(item => item.avg < item.threshold)
  const riskNotices = [
    ...(graduation.risk_count > 0 ? [{ key: 'graduation', level: 'danger', message: `${graduation.risk_count} 名学生存在毕业达标风险` }] : []),
    ...maintenanceLabs.map(lab => ({ key: `lab-${lab.lab_id}`, level: 'warning', message: `${lab.lab_name}处于维护状态` })),
    ...belowTargetAbilities.map(item => ({ key: `ability-${item.ability_id}`, level: 'warning', message: `${item.ability_name}均值低于达标线 ${item.threshold}` })),
    ...alerts.map(alert => ({ key: `api-${alert.type}-${alert.student_id}-${alert.timestamp}`, level: alert.level, message: alert.message })),
  ].slice(0, 5)

  return (
    <div className="dashboard-screen bg-grid noise-overlay">
      <header className="dashboard-header">
        <div className="dashboard-brand">
          <div className="signal-mark" aria-hidden="true"><span /><span /><span /></div>
          <div><p>PUBLIC DATA CENTER · REALTIME</p><h1>智能实训能力评估平台</h1><small>辽宁铁道职业技术学院 · 实时数据监控大屏</small></div>
        </div>
        <div className="dashboard-clock">
          <div><strong>{time.toLocaleTimeString('zh-CN', { hour12: false })}</strong><span>{time.toLocaleDateString('zh-CN', { weekday: 'long', month: 'long', day: 'numeric' })}</span></div>
          <Link to="/" className="btn-secondary !px-3 !py-1.5">返回系统</Link>
        </div>
      </header>

      <section className="dashboard-metrics" aria-label="核心指标">
        <MetricCard code="LIVE" label="当前在训学生" value={realtime.active_students} />
        <MetricCard code="TODAY" label="今日实训次数" value={realtime.today_trainings} />
        <MetricCard code="AVG" label="今日平均分" value={realtime.average_score} />
        <MetricCard code="PASS" label="今日合格率" value={realtime.pass_rate} suffix="%" tone="green" />
        <MetricCard code="READY" label="毕业达标学生" value={graduation.ready_count} tone="green" />
        <MetricCard code="RISK" label="毕业风险预警" value={graduation.risk_count} tone={graduation.risk_count ? 'red' : 'green'} />
      </section>

      <main className="dashboard-main-grid">
        <div className="dashboard-column dashboard-column-left">
          <section className="dashboard-panel dashboard-live-panel">
            <PanelTitle code="LIVE FEED" title="实时实训动态" meta={`${inUseLabs}/${labs.length} 实训室运行`} />
            <div className="dashboard-lab-rail">
              {labs.slice(0, 4).map(lab => {
                const usage = lab.capacity ? Math.round(lab.current_students / lab.capacity * 100) : 0
                return <div key={lab.lab_id} className="dashboard-lab-item"><div><span className={`status-dot status-${lab.status}`} /><strong>{lab.lab_name}</strong><small>{lab.current_students}/{lab.capacity}</small></div><i><b style={{ width: `${usage}%` }} /></i></div>
              })}
            </div>
            <div className="dashboard-feed">
              {activities.length ? activities.slice(0, 5).map((activity, index) => (
                <motion.div key={activity.id} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: index * .05 }} className="dashboard-feed-row">
                  <time>{formatTime(activity.timestamp)}</time>
                  <div><strong>{activity.student_name}</strong><span>{activity.class_name} · {activity.project_name}</span></div>
                  <em className={activity.passed === false ? 'is-danger' : activity.status === 'in_progress' ? 'is-live' : 'is-success'}>{activity.status === 'in_progress' ? '进行中' : activity.score == null ? '已完成' : `${activity.score}分`}</em>
                </motion.div>
              )) : <div className="dashboard-empty"><span>SYNC</span><p>暂无今日实训记录，等待数据接入</p></div>}
            </div>
          </section>

          <section className="dashboard-panel dashboard-alert-panel">
            <PanelTitle code="ALERT" title="异常与毕业风险" meta={`${riskNotices.length} 条关注事项`} />
            <div className="dashboard-risk-summary">
              <div><strong>{graduation.ready_rate}%</strong><span>整体毕业达标率</span></div>
              <i><b style={{ width: `${graduation.ready_rate}%` }} /></i>
              <p><span>已达标 {graduation.ready_count}</span><em>风险 {graduation.risk_count}</em></p>
            </div>
            <div className="dashboard-alert-metrics">
              <div><strong>{graduation.risk_count}</strong><span>风险学生</span></div>
              <div><strong>{belowTargetAbilities.length}</strong><span>待提升能力</span></div>
              <div><strong>{maintenanceLabs.length}</strong><span>设备维护</span></div>
            </div>
            <div className="dashboard-alert-list">
              {riskNotices.length ? riskNotices.map(notice => <div key={notice.key} className={`dashboard-alert dashboard-alert-${notice.level}`}><i aria-hidden="true" /><span>{notice.message}</span></div>) : <div className="dashboard-alert dashboard-alert-success"><i aria-hidden="true" /><span>当前无异常预警，系统运行平稳</span></div>}
            </div>
          </section>
        </div>

        <div className="dashboard-column dashboard-column-center">
          <section className="dashboard-panel dashboard-ranking-panel">
            <PanelTitle code="CLASS" title="班级对比" meta="平均成绩 / 累计实训" />
            <div className="dashboard-ranking">
              {ranking.map((item, index) => <div key={item.class_id} className="dashboard-rank-row"><span className={`rank-number rank-${index + 1}`}>{item.rank}</span><div><p><strong>{item.class_name}</strong><small>{item.training_count} 次实训</small><em>{item.average_score}</em></p><i><b style={{ width: `${item.average_score / maxRankingScore * 100}%` }} /></i></div></div>)}
            </div>
          </section>

          <section className="dashboard-panel dashboard-analysis-panel">
            <PanelTitle code="SCORE" title="成绩分布与近七日趋势" meta="全量成绩 / 日均分" />
            <div className={`dashboard-dual-chart${hasTrendData ? '' : ' dashboard-dual-chart--trend-empty'}`}>
              <div><h3>成绩分布</h3><ResponsiveContainer width="100%" height="100%"><BarChart data={scoreDistribution} margin={{ top: 8, right: 4, left: -24, bottom: 0 }}><CartesianGrid stroke="rgba(100,236,255,.12)" vertical={false} /><XAxis dataKey="label" tick={{ fill: '#9bc7ed', fontSize: 10 }} axisLine={false} tickLine={false} /><YAxis allowDecimals={false} tick={{ fill: '#86aed2', fontSize: 9 }} axisLine={false} tickLine={false} /><Tooltip contentStyle={{ backgroundColor: '#063d82', border: '1px solid rgba(100,236,255,.5)', borderRadius: 4 }} /><Bar dataKey="count" radius={[3, 3, 0, 0]}>{scoreDistribution.map((entry, index) => <Cell key={entry.label} fill={scoreColors[index] || '#64ecff'} />)}</Bar></BarChart></ResponsiveContainer></div>
              <div className="dashboard-trend-card"><h3>近七日平均分</h3>{hasTrendData ? <ResponsiveContainer width="100%" height="100%"><AreaChart data={trendData} margin={{ top: 8, right: 5, left: -25, bottom: 0 }}><defs><linearGradient id="dashboardScoreGradient" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#64ecff" stopOpacity={.4} /><stop offset="95%" stopColor="#00c8ff" stopOpacity={0} /></linearGradient></defs><CartesianGrid stroke="rgba(100,236,255,.12)" vertical={false} /><XAxis dataKey="date" tick={{ fill: '#9bc7ed', fontSize: 9 }} axisLine={false} tickLine={false} /><YAxis domain={[0, 100]} tick={{ fill: '#86aed2', fontSize: 9 }} axisLine={false} tickLine={false} /><Tooltip contentStyle={{ backgroundColor: '#063d82', border: '1px solid rgba(100,236,255,.5)', borderRadius: 4 }} /><Area type="monotone" dataKey="score" stroke="#64ecff" strokeWidth={2} fill="url(#dashboardScoreGradient)" /></AreaChart></ResponsiveContainer> : <div className="dashboard-chart-empty"><span>NO DATA</span><p>近七日暂无实训记录</p></div>}</div>
            </div>
          </section>
        </div>

        <div className="dashboard-column dashboard-column-right">
          <section className="dashboard-panel dashboard-radar-panel">
            <PanelTitle code="ABILITY" title="能力雷达" meta="平均能力 / 毕业标准" />
            <div className="dashboard-radar-chart"><ResponsiveContainer width="100%" height="100%"><RadarChart data={radarData} outerRadius="85%"><PolarGrid stroke="rgba(100,236,255,.3)" /><PolarAngleAxis dataKey="ability" tick={{ fill: '#c7e6ff', fontSize: 9 }} /><PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: '#86aed2', fontSize: 7 }} /><Radar name="毕业标准" dataKey="threshold" stroke="#ffc04a" fill="#ffc04a" fillOpacity={.05} strokeDasharray="4 4" /><Radar name="平均能力" dataKey="value" stroke="#64ecff" fill="#00c8ff" fillOpacity={.28} /><Tooltip contentStyle={{ backgroundColor: '#063d82', border: '1px solid rgba(100,236,255,.5)', borderRadius: 4 }} /></RadarChart></ResponsiveContainer></div>
            <div className="dashboard-chart-legend"><span><i className="legend-cyan" />平均能力</span><span><i className="legend-amber" />毕业标准</span></div>
          </section>

          <section className="dashboard-panel dashboard-ability-panel">
            <PanelTitle code="TARGET" title="能力达标情况" meta={`${graduation.evaluated_students}/${graduation.total_students} 已评估`} />
            <div className="dashboard-ability-list">
              {data?.ability_distribution.map(item => {
                const achieved = item.avg >= item.threshold
                return <div key={item.ability_id} className="dashboard-ability-row"><p><strong>{item.ability_name}</strong><span className={achieved ? 'is-success' : 'is-danger'}>{achieved ? '达标' : '待提升'}</span><em>{item.avg}<small> / {item.threshold}</small></em></p><i><b className={achieved ? 'is-success' : 'is-warning'} style={{ width: `${Math.min(100, item.avg)}%` }} /><mark style={{ left: `${Math.min(100, item.threshold)}%` }} /></i><small>达标 {item.ready_count} 人 · 未达标 {item.not_ready_count} 人</small></div>
              })}
            </div>
          </section>
        </div>
      </main>

      <footer className="dashboard-footer"><div><i />系统运行正常 <span>数据更新 {data?.updated_at ? new Date(data.updated_at).toLocaleTimeString('zh-CN', { hour12: false }) : '--:--:--'}</span></div><p>GEARBOX CONTROL UI · Powered by DenseMatrix AI</p></footer>
    </div>
  )
}
