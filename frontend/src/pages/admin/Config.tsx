import { useMutation, useQuery } from '@tanstack/react-query'
import { api } from '../../lib/api'

export default function AdminConfig() {
  const abilities = useQuery({ queryKey: ['admin-abilities'], queryFn: async () => (await api.get('/api/v1/admin/abilities')).data })
  const labs = useQuery({ queryKey: ['admin-labs'], queryFn: async () => (await api.get('/api/v1/admin/labs')).data })
  const sync = useMutation({ mutationFn: async () => (await api.post('/api/v1/admin/sync')).data })

  return (
    <div className="space-y-7">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between"><div><p className="eyebrow">SYSTEM CONFIGURATION</p><h2 className="page-title">基础配置</h2><p className="mt-2 text-sm text-text-muted">管理能力体系、实训室和数据接入状态</p></div><button onClick={() => sync.mutate()} disabled={sync.isPending} className="btn-primary">{sync.isPending ? '校验中…' : '校验演示数据库'}</button></div>
      {sync.data && <div className="alert-success rounded p-4 text-sm">{sync.data.message}，当前共 {sync.data.synced_records} 条成绩记录。</div>}
      <div className="grid gap-6 xl:grid-cols-2">
        <section className="railway-card overflow-hidden"><div className="border-b border-railway-600/50 p-5"><h3 className="section-heading">能力体系</h3><p className="mt-1 text-xs text-text-muted">{abilities.data?.length || 0} 个能力大类</p></div><div className="divide-y divide-railway-600/40">{abilities.data?.map((item: any) => <div key={item.id} className="flex items-center justify-between p-4"><div><p className="text-sm font-semibold text-text-primary">{item.name}</p><p className="text-xs text-text-muted">{item.sub_abilities?.length || 0} 个能力点</p></div><span className="font-mono text-accent-cyan">{Math.round(item.graduation_threshold * 100)}%</span></div>)}</div></section>
        <section className="railway-card overflow-hidden"><div className="border-b border-railway-600/50 p-5"><h3 className="section-heading">实训室</h3><p className="mt-1 text-xs text-text-muted">{labs.data?.length || 0} 个已接入空间</p></div><div className="divide-y divide-railway-600/40">{labs.data?.map((item: any) => <div key={item.id} className="flex items-center justify-between p-4"><div><p className="text-sm font-semibold text-text-primary">{item.name}</p><p className="text-xs text-text-muted">{item.building} · 容量 {item.capacity}</p></div><span className="text-xs text-status-success">● {item.status === 'in_use' ? '使用中' : '在线'}</span></div>)}</div></section>
      </div>
    </div>
  )
}
