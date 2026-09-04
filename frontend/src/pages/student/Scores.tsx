import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../lib/api'
import ScoreEvidenceModal from '../../components/ScoreEvidenceModal'

export default function StudentScores() {
  const [page, setPage] = useState(1)
  const [projectId, setProjectId] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [selectedScore, setSelectedScore] = useState('')
  const projects = useQuery({ queryKey: ['score-projects'], queryFn: async () => (await api.get('/api/v1/scores/projects')).data })
  const scores = useQuery({
    queryKey: ['student-scores', page, projectId, dateFrom, dateTo],
    queryFn: async () => (await api.get('/api/v1/scores/', { params: { page, page_size: 10, project_id: projectId || undefined, date_from: dateFrom || undefined, date_to: dateTo ? `${dateTo}T23:59:59` : undefined } })).data,
  })

  return <div className="space-y-6">
    <header><p className="eyebrow">PERSONAL SCORE LEDGER</p><h1 className="page-title">我的实训成绩</h1><p className="mt-2 text-sm text-text-muted">每一分均可下钻到步骤状态、适用规则和关联能力</p></header>
    <section className="railway-card grid gap-4 p-5 md:grid-cols-3">
      <Field label="实训项目"><select className="input-field" value={projectId} onChange={(e) => { setProjectId(e.target.value); setPage(1) }}><option value="">全部项目</option>{projects.data?.map((item: any) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field>
      <Field label="开始日期"><input className="input-field" type="date" value={dateFrom} onChange={(e) => { setDateFrom(e.target.value); setPage(1) }} /></Field>
      <Field label="结束日期"><input className="input-field" type="date" value={dateTo} onChange={(e) => { setDateTo(e.target.value); setPage(1) }} /></Field>
    </section>
    <div className="grid gap-3">
      {scores.isLoading && <p className="railway-card p-6 text-text-muted">正在加载成绩…</p>}
      {scores.data?.scores.map((score: any) => <button key={score.id} onClick={() => setSelectedScore(score.id)} className="railway-card grid gap-4 p-5 text-left transition hover:border-accent-blue/60 sm:grid-cols-[1fr_auto_auto] sm:items-center"><div><p className="font-semibold text-text-primary">{score.project_name}</p><p className="mt-1 text-xs text-text-muted">{new Date(score.calculated_at).toLocaleString('zh-CN')}</p></div><span className="font-mono text-2xl text-accent-cyan">{score.percentage}</span><span className="text-sm text-accent-blue">查看步骤证据 →</span></button>)}
      {!scores.isLoading && !scores.data?.scores.length && <p className="railway-card p-10 text-center text-text-muted">当前筛选条件下没有成绩记录</p>}
    </div>
    {scores.data?.total > scores.data?.page_size && <div className="flex items-center justify-center gap-3"><button className="railway-button" disabled={page === 1} onClick={() => setPage((value) => Math.max(1, value - 1))}>上一页</button><span className="text-sm text-text-muted">第 {page} 页</span><button className="railway-button" disabled={page * scores.data.page_size >= scores.data.total} onClick={() => setPage((value) => value + 1)}>下一页</button></div>}
    {selectedScore && <ScoreEvidenceModal scoreId={selectedScore} onClose={() => setSelectedScore('')} />}
  </div>
}

function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label className="text-sm text-text-secondary"><span className="mb-2 block">{label}</span>{children}</label> }
