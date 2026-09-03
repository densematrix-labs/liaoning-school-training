import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../../lib/api'
import { useAuthStore } from '../../store/auth'

export default function StudentHome() {
  const { user } = useAuthStore()
  const { data: scores } = useQuery({
    queryKey: ['student-home-scores'],
    queryFn: async () => (await api.get('/api/v1/scores/', { params: { page_size: 4 } })).data,
  })
  const { data: ability } = useQuery({
    queryKey: ['student-home-ability'],
    queryFn: async () => (await api.get('/api/v1/abilities/profile')).data,
  })
  const latest = scores?.scores?.[0]

  return (
    <div className="space-y-7">
      <section className="role-intro student-intro">
        <div>
          <p className="eyebrow">STUDENT WORKSPACE · {user?.student_no}</p>
          <h2>{user?.name}，查看你的实训进展</h2>
          <p>{user?.class_name} · {user?.major_name}</p>
        </div>
        <Link to="/reports" className="btn-primary">生成诊断报告</Link>
      </section>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Metric label="已完成实训" value={scores?.total ?? '—'} unit="次" />
        <Metric label="平均成绩" value={scores?.average_score ?? '—'} unit="分" />
        <Metric label="综合能力" value={ability?.total_score ?? '—'} unit="分" />
        <Metric label="毕业能力" value={ability?.graduation_ready ? '已达标' : '提升中'} tone={ability?.graduation_ready ? 'good' : 'warn'} />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.15fr_.85fr]">
        <section className="railway-card p-6">
          <div className="mb-5 flex items-center justify-between">
            <div><p className="eyebrow">LATEST RESULT</p><h3 className="section-heading">最近一次实训</h3></div>
            <Link to="/scores" className="text-sm text-accent-blue">全部成绩 →</Link>
          </div>
          {latest ? (
            <div className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
              <div><p className="text-lg font-semibold text-text-primary">{latest.project_name}</p><p className="mt-2 text-sm text-text-muted">{new Date(latest.calculated_at).toLocaleString('zh-CN')}</p></div>
              <div className="font-display text-5xl font-bold text-accent-cyan">{latest.percentage}<span className="ml-1 text-sm text-text-muted">分</span></div>
            </div>
          ) : <p className="text-text-muted">暂无成绩数据</p>}
        </section>
        <section className="railway-card p-6">
          <div className="mb-5"><p className="eyebrow">ABILITY SIGNAL</p><h3 className="section-heading">能力短板</h3></div>
          <div className="space-y-3">
            {ability?.weak_abilities?.slice(0, 3).map((item: any) => (
              <div key={item.ability_id} className="flex items-center justify-between border-b border-railway-600/50 pb-3">
                <span className="text-sm text-text-secondary">{item.name}</span><span className="font-mono text-status-warning">{item.score}</span>
              </div>
            )) || <p className="text-sm text-text-muted">能力数据加载中</p>}
          </div>
          <Link to="/ability" className="mt-5 inline-block text-sm text-accent-blue">查看能力图谱 →</Link>
        </section>
      </div>
    </div>
  )
}

function Metric({ label, value, unit, tone }: { label: string; value: string | number; unit?: string; tone?: 'good' | 'warn' }) {
  return <div className="metric-strip"><p>{label}</p><strong className={tone === 'good' ? 'text-status-success' : tone === 'warn' ? 'text-status-warning' : 'text-accent-cyan'}>{value}</strong>{unit && <span>{unit}</span>}</div>
}
