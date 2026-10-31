import ChineseDateInput from '../../components/ChineseDateInput'
import { useState } from 'react'
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
  LineChart,
  Line,
  Legend,
} from 'recharts'
import { motion } from 'framer-motion'
import { useAuthStore } from '../../store/auth'

export default function StudentAbility() {
  const { user } = useAuthStore()
  const [selectedAbility, setSelectedAbility] = useState<string>('')
  const [projectId, setProjectId] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const projects = useQuery({queryKey:['ability-projects'],queryFn:async()=>(await api.get('/api/v1/scores/projects')).data})
  const { data: abilityMap, isLoading } = useQuery({
    queryKey: ['studentAbility'],
    queryFn: async () => {
      const res = await api.get('/api/v1/abilities/profile')
      return res.data
    },
  })
  const { data: trend } = useQuery({
    queryKey: ['studentAbilityTrend', user?.student_id, projectId, dateFrom, dateTo],
    queryFn: async () => (await api.get(`/api/v1/abilities/student/${user!.student_id}/trend`, {params:{project_id:projectId||undefined,date_from:dateFrom||undefined,date_to:dateTo?`${dateTo}T23:59:59`:undefined}})).data,
    enabled: Boolean(user?.student_id),
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
  const comparable = barData.filter((item: any) => Number.isFinite(item.score))
  const extremeNames = (maximum: boolean) => {
    if (!comparable.length) return '—'
    const target = (maximum ? Math.max : Math.min)(...comparable.map((item: any) => item.score))
    return comparable.filter((item: any) => item.score === target).map((item: any) => item.name).join('、')
  }
  const selectedAbilityData = barData.find((item: any) => item.ability_id === selectedAbility)
  const selectedSubAbilities = abilityMap?.sub_ability_details?.filter(
    (item: any) => item.major_ability_id === selectedAbility,
  ) || []
  const graduationReadyCount = abilityMap?.graduation_ready_count ?? barData.filter((item: any) => item.score >= item.threshold).length
  const graduationTotalCount = abilityMap?.graduation_total_count ?? barData.length
  const graduationProgress = abilityMap?.graduation_progress ?? (graduationTotalCount ? Math.round(graduationReadyCount / graduationTotalCount * 1000) / 10 : 0)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">能力图谱</h1>

      </div>

      <section className="railway-card p-6">
        <h2 className="section-title mb-4">能力变化趋势</h2>
        <div className="mb-4 grid gap-3 md:grid-cols-3"><label>实训项目<select className="input-field" value={projectId} onChange={e=>setProjectId(e.target.value)}><option value="">全部项目</option>{projects.data?.map((p:any)=><option key={p.id} value={p.id}>{p.name}</option>)}</select></label><label>开始日期<ChineseDateInput type="date" className="input-field" value={dateFrom} onValueChange={value=>setDateFrom(value)}/></label><label>结束日期<ChineseDateInput type="date" className="input-field" value={dateTo} onValueChange={value=>setDateTo(value)}/></label></div>
        {trend?.points?.length===0&&<p role="status" className="text-text-muted">当前筛选范围没有实训记录</p>}
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={(trend?.points || []).map((point: any) => ({ ...point.abilities, date: new Date(point.date).toLocaleDateString('zh-CN') }))}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(100, 236, 255, 0.14)" />
              <XAxis dataKey="date" tick={{ fill: '#bedfff', fontSize: 11 }} />
              <YAxis domain={[0, 100]} tick={{ fill: '#bedfff' }} />
              <Tooltip contentStyle={{ backgroundColor: '#063d82', border: '1px solid rgba(100, 236, 255, 0.5)' }} />
              <Legend />
              {trend?.abilities?.map((ability: any, index: number) => <Line isAnimationActive={false} key={ability.id} type="monotone" dataKey={ability.id} name={ability.name} stroke={['#ffe066', '#ff9f43', '#ff80c0', '#ffffff', '#b8f28b', '#dcadff'][index % 6]} strokeWidth={3} strokeDasharray={[undefined,'8 3','3 3','10 3 2 3','14 4','2 5'][index % 6]} dot={{r:4}} />)}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>

      <div className="grid gap-3 sm:grid-cols-3">
        <Signal label="优势能力" value={extremeNames(true)} tone="good" />
        <Signal label="薄弱能力" value={extremeNames(false)} tone="warn" />
        <Signal label="毕业达标进度" value={`${graduationReadyCount}/${graduationTotalCount}（${graduationProgress}%）· ${abilityMap?.graduation_ready ? '已达标' : '未达标'}`} tone={abilityMap?.graduation_ready ? 'good' : 'warn'} />
      </div>

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
                <PolarGrid stroke="rgba(100, 236, 255, 0.3)" />
                <PolarAngleAxis
                  dataKey="name"
                  tick={{ fill: '#d8efff', fontSize: 12 }}
                />
                <PolarRadiusAxis
                  angle={30}
                  domain={[0, 100]}
                  tick={{ fill: '#86aed2', fontSize: 10 }}
                  tickCount={5}
                />
                <Radar
                  name="能力值"
                  dataKey="score"
                  stroke="#64ecff"
                  fill="#00c8ff"
                  fillOpacity={0.3}
                  strokeWidth={2}
                />
                <Radar
                  name="毕业标准"
                  dataKey="threshold"
                  stroke="#ffc04a"
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
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(100, 236, 255, 0.14)" />
                <XAxis type="number" domain={[0, 100]} tick={{ fill: '#bedfff' }} />
                <YAxis
                  type="category"
                  dataKey="name"
                  tick={{ fill: '#bedfff', fontSize: 12 }}
                  width={80}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#063d82',
                    border: '1px solid rgba(100, 236, 255, 0.5)',
                    borderRadius: '4px',
                  }}
                  labelStyle={{ color: '#f5fbff' }}
                />
                <Bar dataKey="score" radius={[0, 4, 4, 0]}>
                  {barData.map((entry: any, index: number) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={entry.score >= entry.threshold ? '#39e58c' : '#64ecff'}
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
            <button
              key={ability.ability_id}
              type="button"
              onClick={() => setSelectedAbility(ability.ability_id)}
              aria-haspopup="dialog"
              className={`p-4 rounded-lg border ${
                ability.score >= ability.threshold
                  ? 'bg-status-success/5 border-status-success/20'
                  : 'bg-status-warning/5 border-status-warning/20'
              } text-left transition hover:border-accent-blue`}
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

                <span>达标线: {ability.threshold}</span>
                <span className={ability.score >= ability.threshold ? 'text-status-success' : 'text-status-warning'}>{ability.score >= ability.threshold ? '达标' : '未达标'}</span>
              </div>
              <p className="mt-3 text-xs text-accent-blue">查看子能力与成绩依据 →</p>
            </button>
          ))}
        </div>
      </motion.div>


      {selectedAbility && (
        <div
          className="fixed inset-0 z-[90] flex items-center justify-center bg-railway-900/90 p-3 backdrop-blur-sm"
          role="dialog"
          aria-modal="true"
          aria-labelledby="ability-evidence-title"
          onClick={() => setSelectedAbility('')}
        >
          <section
            className="glass-panel-bright max-h-[92vh] w-full max-w-6xl overflow-y-auto"
            onClick={(event) => event.stopPropagation()}
          >
            <header className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-railway-600/50 bg-railway-800/95 p-5 backdrop-blur">
              <div>

                <h2 id="ability-evidence-title" className="section-heading">
                  {selectedAbilityData?.name || '能力'}：子能力与成绩依据
                </h2>
                {selectedAbilityData && (
                  <p className="mt-2 text-sm text-text-secondary">
                    当前能力值 {selectedAbilityData.score} 分 · 毕业达标线 {selectedAbilityData.threshold} 分
                  </p>
                )}
              </div>
              <p className="text-xs text-text-muted">计算时间：{abilityMap?.updated_at ? new Date(abilityMap.updated_at).toLocaleString('zh-CN') : '尚未计算'}</p>
              <button type="button" className="railway-button" onClick={() => setSelectedAbility('')}>关闭</button>
            </header>
            <div className="space-y-4 p-5">
              {abilityMap?.history_scope && <p className="rounded border border-accent-cyan/30 p-3 text-sm">学生：{abilityMap.student_name} · 全部历史 {abilityMap.history_scope.available_records} 次 / 本次计入 {abilityMap.history_scope.selected_records} 次 · {abilityMap.history_scope.date_from?.slice(0, 10)} 至 {abilityMap.history_scope.date_to?.slice(0, 10)}</p>}
              {selectedSubAbilities.map((item: any) => (
                <article key={item.id} className="rounded-lg border border-railway-600/60 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="font-semibold text-text-primary">{item.name}</p>

                    </div>
                    <span className="font-mono text-2xl text-accent-cyan">{item.has_evidence?`${item.score} / ${item.full_score}`:"暂无评价"}</span>
                  </div>
                  <div className="mt-4 space-y-2">
                    {item.evidence?.slice(0, 8).map((evidence: any) => (
                      <div key={`${evidence.score_id}-${evidence.step_id}`} className="grid gap-2 rounded bg-railway-800/60 p-3 text-sm md:grid-cols-[1.2fr_1.4fr_auto]">
                        <div>
                          <p className="text-text-primary">{evidence.project_name}</p>
                          <p className="text-xs text-text-muted">实训记录：{evidence.record_reference || '编号待确认'}</p>
                          <p className="text-xs text-text-muted">完成时间：{evidence.calculated_at?.slice(0, 10) || '未记录'}</p>
                        </div>
                        <p className="text-text-secondary">{evidence.step_name} · {evidence.passed ? '通过' : '未通过'}</p>
                        <span className={evidence.passed ? 'text-status-success' : 'text-status-warning'}>{evidence.score}/{evidence.max_score}</span>
                      </div>
                    ))}
                    {!item.evidence?.length && null}
                  </div>
                </article>
              ))}
              {!selectedSubAbilities.length && null}
            </div>
          </section>
        </div>
      )}

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

function Signal({ label, value, tone }: { label: string; value: string; tone: 'good' | 'warn' }) {
  return <div className="metric-strip"><p>{label}</p><strong className={tone === 'good' ? 'text-status-success' : 'text-status-warning'}>{value}</strong></div>
}
