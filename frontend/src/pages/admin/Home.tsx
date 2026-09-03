import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../../lib/api'
import { useAuthStore } from '../../store/auth'

export default function AdminHome() {
  const { user } = useAuthStore()
  const { data, isLoading, error } = useQuery({
    queryKey: ['admin-overview'],
    queryFn: async () => (await api.get('/api/v1/admin/overview')).data,
  })
  return (
    <div className="space-y-7">
      <section className="role-intro admin-intro">
        <div><p className="eyebrow">ADMIN WORKSPACE · {user?.username}</p><h2>{user?.name}，系统运行正常</h2><p>全校数据范围 · 基础配置与同步管理</p></div>
        <Link to="/admin/config" className="btn-primary">进入基础配置</Link>
      </section>
      {error && <div className="alert-danger p-4">管理数据加载失败，请重新登录后再试。</div>}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <Metric label="学生档案" value={isLoading ? '—' : data?.students} unit="人" />
        <Metric label="班级" value={isLoading ? '—' : data?.classes} unit="个" />
        <Metric label="成绩记录" value={isLoading ? '—' : data?.scores} unit="条" />
        <Metric label="能力大类" value={isLoading ? '—' : data?.abilities} unit="项" />
        <Metric label="实训室" value={isLoading ? '—' : data?.labs} unit="间" />
        <Metric label="AI 报告" value={isLoading ? '—' : data?.reports} unit="份" />
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <section className="railway-card p-6"><p className="eyebrow">DATA PIPELINE</p><h3 className="section-heading">数据服务</h3><div className="mt-5 space-y-3 text-sm"><Status name="业务数据库" value={data?.database || '连接中'} /><Status name="种子数据" value={`${data?.scores || 0} 条成绩已入库`} /><Status name="同步状态" value={data?.sync_status || '检查中'} /></div></section>
        <section className="railway-card p-6"><p className="eyebrow">ACCESS CONTROL</p><h3 className="section-heading">权限边界</h3><ul className="mt-5 space-y-3 text-sm text-text-secondary"><li>学生：仅本人数据</li><li>教师：本人负责班级</li><li>管理员：全校数据与系统配置</li></ul></section>
      </div>
    </div>
  )
}

function Metric({ label, value, unit }: { label: string; value: string | number; unit?: string }) { return <div className="metric-strip"><p>{label}</p><strong className="text-status-danger">{value ?? '—'}</strong>{unit && <span>{unit}</span>}</div> }
function Status({ name, value }: { name: string; value: string }) { return <div className="flex justify-between border-b border-railway-600/50 pb-3"><span className="text-text-muted">{name}</span><span className="text-status-success">● {value}</span></div> }
