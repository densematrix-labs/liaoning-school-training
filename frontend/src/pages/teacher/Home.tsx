import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import AbilityRadar from '../../components/AbilityRadar'
import { api } from '../../lib/api'
import { useAuthStore } from '../../store/auth'

export default function TeacherHome() {
  const { user } = useAuthStore()
  const [classId, setClassId] = useState('')
  const classes = useQuery({ queryKey: ['teacher-home-classes'], queryFn: async () => (await api.get('/api/v1/students/classes')).data })
  const overview = useQuery({ queryKey: ['teacher-home-overview', classId], queryFn: async () => (await api.get(`/api/v1/students/classes/${classId}/overview`)).data, enabled: Boolean(classId) })
  useEffect(() => { if (!classId && classes.data?.length) setClassId(classes.data[0].id) }, [classes.data, classId])
  const selectedClass = classes.data?.find((item: any) => item.id === classId)
  const riskStudents = (overview.data?.students || []).filter((item: any) => item.graduation_risk).slice(0, 5)

  return <div className="space-y-6">
    <section className="role-intro teacher-intro">
      <div><p className="eyebrow">TEACHER COMMAND CENTER · {user?.username}</p><h2>{user?.name}老师，教学态势已更新</h2><p>以能力雷达为核心，快速识别班级共性短板和学生毕业风险</p></div>
      <div className="flex gap-2"><Link to={`/classes${classId ? `?class_id=${classId}` : ''}`} className="railway-button">进入班级分析</Link><Link to={`/batch-reports${classId ? `?class_id=${classId}` : ''}`} className="btn-primary">诊断报告</Link></div>
    </section>

    <section className="railway-card flex flex-wrap items-end justify-between gap-4 p-5">
      <Field label="当前班级"><select className="input-field min-w-64" value={classId} onChange={(e) => setClassId(e.target.value)}><option value="">选择班级</option>{classes.data?.map((item: any) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field>
      <div className="text-right"><p className="text-xs text-text-muted">专业方向</p><p className="mt-1 text-sm text-text-primary">{selectedClass?.major_name || '—'}</p></div>
    </section>

    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
      <Metric label="班级学生" value={overview.data?.student_count ?? '—'} unit="人" />
      <Metric label="实训记录" value={overview.data?.training_count ?? '—'} unit="次" />
      <Metric label="平均成绩" value={overview.data?.average_score ?? '—'} unit="分" />
      <Metric label="毕业达标" value={overview.data?.graduation_ready_count ?? '—'} unit="人" tone="good" />
      <Metric label="毕业风险" value={overview.data?.graduation_not_ready_count ?? '—'} unit="人" tone="warn" />
      <Metric label="达标率" value={overview.data ? `${overview.data.graduation_ready_rate}%` : '—'} />
    </div>

    <div className="grid items-start gap-5 xl:grid-cols-[1.15fr_.85fr]">
      <AbilityRadar items={overview.data?.ability_distribution || []} title={`${selectedClass?.name || '班级'} · 能力雷达`} description="班级平均能力与各维度毕业标准对照" />
      <div className="space-y-5">
        <section className="railway-card p-5"><div className="flex items-center justify-between"><div><p className="eyebrow">SCORE DISTRIBUTION</p><h2 className="section-heading">成绩分布</h2></div><Link to={`/class-scores?class_id=${classId}`} className="text-xs text-accent-blue">查看明细 →</Link></div><div className="mt-5 space-y-4">{overview.data?.score_distribution.map((item: any) => { const max = Math.max(...overview.data.score_distribution.map((entry: any) => entry.count), 1); return <div key={item.label} className="grid grid-cols-[70px_1fr_42px] items-center gap-3 text-sm"><span className="text-text-secondary">{item.label}</span><div className="h-2 overflow-hidden rounded bg-railway-700"><div className="h-full rounded bg-gradient-to-r from-accent-electric to-accent-cyan" style={{ width: `${item.count / max * 100}%` }} /></div><span className="text-right font-mono text-accent-cyan">{item.count}</span></div> })}{!overview.data?.score_distribution.length && <p className="text-sm text-text-muted">暂无成绩数据</p>}</div></section>
        <section className="railway-card overflow-hidden"><div className="border-b border-railway-600/50 p-5"><p className="eyebrow">GRADUATION RISK</p><h2 className="section-heading">优先关注学生</h2></div><div className="divide-y divide-railway-600/50">{riskStudents.map((item: any) => <div key={item.id} className="flex items-center justify-between gap-3 p-4"><div><p className="font-medium text-text-primary">{item.name}</p><p className="text-xs text-text-muted">{item.training_count} 次实训 · 均分 {item.average_score}</p></div><div className="text-right"><p className="font-mono text-status-warning">{item.graduation_progress}%</p><p className="text-[10px] text-text-muted">毕业达标进度</p></div></div>)}{!riskStudents.length && <p className="p-5 text-sm text-text-muted">当前班级暂无毕业风险学生</p>}</div></section>
      </div>
    </div>
  </div>
}

function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label className="text-sm text-text-secondary"><span className="mb-2 block">{label}</span>{children}</label> }
function Metric({ label, value, unit, tone }: { label: string; value: string | number; unit?: string; tone?: 'good' | 'warn' }) { return <div className="metric-strip"><p>{label}</p><strong className={tone === 'good' ? 'text-status-success' : tone === 'warn' ? 'text-status-warning' : 'text-accent-cyan'}>{value}</strong>{unit && <span>{unit}</span>}</div> }
