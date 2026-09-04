import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import ReactMarkdown from 'react-markdown'
import { api } from '../../lib/api'
import { useAuthStore } from '../../store/auth'
import { ReportTaskStatus, useReportTask } from '../../lib/useReportTask'

export default function StudentReports() {
  const { user } = useAuthStore()
  const [selected, setSelected] = useState<any>(null)
  const reports = useQuery({ queryKey: ['student-reports'], queryFn: async () => (await api.get('/api/v1/reports/')).data })
  const scores = useQuery({ queryKey: ['student-report-scores'], queryFn: async () => (await api.get('/api/v1/scores/', { params: { page_size: 100 } })).data })
  const [scoreId, setScoreId] = useState('')
  const reportTask = useReportTask((report) => setSelected(report))

  return <div className="space-y-6">
    <header><p className="eyebrow">AI DIAGNOSTIC REPORTS</p><h1 className="page-title">诊断报告</h1><p className="mt-2 text-sm text-text-muted">选择单次实训或汇总阶段成绩，查看任务状态与真实模型结果</p></header>
    <section className="railway-card grid gap-4 p-5 lg:grid-cols-[1fr_auto_auto] lg:items-end">
      <label className="text-sm text-text-secondary"><span className="mb-2 block">单次实训记录</span><select className="input-field" value={scoreId} onChange={(e) => setScoreId(e.target.value)}><option value="">最近一次实训</option>{scores.data?.scores.map((item: any) => <option key={item.id} value={item.id}>{item.project_name} · {item.percentage}分 · {new Date(item.calculated_at).toLocaleDateString('zh-CN')}</option>)}</select></label>
      <button className="btn-secondary" disabled={!user?.student_id || reportTask.create.isPending} onClick={() => reportTask.create.mutate({ student_id: user!.student_id!, report_type: 'single', score_id: scoreId || undefined })}>生成单次报告</button>
      <button className="btn-primary" disabled={!user?.student_id || reportTask.create.isPending} onClick={() => reportTask.create.mutate({ student_id: user!.student_id!, report_type: 'periodic' })}>生成阶段报告</button>
    </section>
    <ReportTaskStatus task={reportTask.task} />
    {reportTask.create.error && <p className="alert-warning rounded p-4">报告任务提交失败</p>}
    <div className="grid gap-5 xl:grid-cols-[340px_1fr]">
      <section className="railway-card overflow-hidden"><div className="border-b border-railway-600/50 p-5"><h2 className="section-heading">历史报告</h2></div><div className="divide-y divide-railway-600/50">{reports.data?.map((item: any) => <button key={item.id} className="w-full p-4 text-left hover:bg-railway-700/40" onClick={() => setSelected(item)}><p className="font-medium text-text-primary">{item.title}</p><p className="mt-1 text-xs text-text-muted">{new Date(item.generated_at).toLocaleString('zh-CN')}</p></button>)}{!reports.data?.length && <p className="p-5 text-sm text-text-muted">暂无诊断报告</p>}</div></section>
      <section className="railway-card min-h-80 p-6">{selected ? <><p className="eyebrow">{selected.report_type === 'single' ? 'SINGLE SESSION' : 'PERIODIC REVIEW'}</p><h2 className="section-heading">{selected.title}</h2><article className="prose prose-invert prose-cyan mt-5 max-w-none text-text-secondary"><ReactMarkdown>{selected.content}</ReactMarkdown></article></> : <div className="flex min-h-72 items-center justify-center text-text-muted">选择历史报告，或生成一份新报告</div>}</section>
    </div>
  </div>
}
