import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../../lib/api'
import { useAuthStore } from '../../store/auth'

export default function TeacherHome() {
  const { user } = useAuthStore()
  const { data: classes, isLoading } = useQuery({
    queryKey: ['teacher-home-classes'],
    queryFn: async () => (await api.get('/api/v1/students/classes')).data,
  })
  const studentCount = classes?.reduce((sum: number, item: any) => sum + item.student_count, 0) ?? 0

  return (
    <div className="space-y-7">
      <section className="role-intro teacher-intro">
        <div><p className="eyebrow">TEACHER WORKSPACE · {user?.username}</p><h2>{user?.name}老师，教学数据已就绪</h2><p>仅展示您负责班级的学生、成绩和报告数据</p></div>
        <Link to="/class-scores" className="btn-primary">查看班级成绩</Link>
      </section>
      <div className="grid gap-4 sm:grid-cols-3">
        <Metric label="负责班级" value={classes?.length ?? '—'} unit="个" />
        <Metric label="覆盖学生" value={studentCount || '—'} unit="人" />
        <Metric label="核心任务" value="成绩分析" />
      </div>
      <section className="railway-card overflow-hidden">
        <div className="flex items-center justify-between border-b border-railway-600/50 p-6"><div><p className="eyebrow">AUTHORIZED CLASSES</p><h3 className="section-heading">我的班级</h3></div><Link to="/classes" className="text-sm text-accent-blue">全部班级 →</Link></div>
        <div className="divide-y divide-railway-600/40">
          {isLoading && <p className="p-6 text-text-muted">正在加载教学数据…</p>}
          {classes?.map((item: any) => (
            <div key={item.id} className="grid gap-4 p-5 sm:grid-cols-[1fr_auto_auto] sm:items-center">
              <div><p className="font-semibold text-text-primary">{item.name}</p><p className="mt-1 text-xs text-text-muted">{item.major_name}</p></div>
              <span className="font-mono text-accent-cyan">{item.student_count} 名学生</span>
              <div className="flex gap-2"><Link to={`/class-scores?class_id=${item.id}`} className="railway-button text-xs">成绩</Link><Link to={`/batch-reports?class_id=${item.id}`} className="railway-button text-xs">报告</Link></div>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}

function Metric({ label, value, unit }: { label: string; value: string | number; unit?: string }) {
  return <div className="metric-strip"><p>{label}</p><strong className="text-status-warning">{value}</strong>{unit && <span>{unit}</span>}</div>
}
