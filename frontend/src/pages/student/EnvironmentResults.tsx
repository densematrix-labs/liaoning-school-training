import { useQuery } from '@tanstack/react-query'
import { api } from '../../lib/api'
import { useAuthStore } from '../../store/auth'

export default function StudentEnvironmentResults() {
  const { user } = useAuthStore()
  const history = useQuery({
    queryKey: ['my-environment-results', user?.student_id],
    queryFn: async () => (await api.get(`/api/v1/environment/history/${user!.student_id}`)).data,
    enabled: Boolean(user?.student_id),
  })
  return <div className="space-y-6">
    <header><p className="eyebrow">ENVIRONMENT REVIEW</p><h1 className="page-title">环境检查结果</h1><p className="mt-2 text-sm text-text-muted">仅查看本人记录；上传与人工复核由教师完成</p></header>
    <section className="railway-card overflow-hidden">
      <div className="divide-y divide-railway-600/50">
        {history.data?.map((item: any) => <article key={item.id} className="grid gap-4 p-5 lg:grid-cols-[160px_1fr_auto]">
          <img className="h-28 w-40 rounded object-cover" src={item.uploaded_image_url} alt="实训现场" />
          <div><p className="font-semibold text-text-primary">{item.lab_name || '实训室环境检查'}</p><p className="mt-1 text-sm text-text-secondary">{item.reviewed_summary || item.summary}</p><p className="mt-2 text-xs text-text-muted">{new Date(item.checked_at).toLocaleString('zh-CN')} · 最终状态：{item.review_status || '待教师复核'}</p>{item.review_note && <p className="mt-2 text-xs text-status-warning">教师备注：{item.review_note}</p>}</div>
          <div className="text-right"><div className="font-mono text-3xl text-accent-cyan">{item.final_score ?? item.total_score}<span className="text-sm text-text-muted">/100</span></div><p className="text-[10px] text-text-muted">{item.review_status ? '人工最终分' : 'AI 原始分'}</p></div>
        </article>)}
        {!history.isLoading && !history.data?.length && <p className="p-6 text-sm text-text-muted">暂无环境检查记录</p>}
      </div>
    </section>
  </div>
}
