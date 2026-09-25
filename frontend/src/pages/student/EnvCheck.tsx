import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../lib/api'

const categoryNames: Record<string, string> = {
  equipment_placement: '器材归位',
  surface_cleanliness: '台面整洁',
  safety_compliance: '安全规范',
  environmental_hygiene: '环境卫生',
}

export default function EnvironmentCheckPage() {
  const queryClient = useQueryClient()
  const [classId, setClassId] = useState('')
  const [studentId, setStudentId] = useState('')
  const [result, setResult] = useState<any>(null)
  const [reviewDetails, setReviewDetails] = useState<any>({})
  const [reviewSuggestions, setReviewSuggestions] = useState<string[]>([])
  const [reviewSuggestionsComment, setReviewSuggestionsComment] = useState('')
  const [reviewSummary, setReviewSummary] = useState('')
  const [note, setNote] = useState('')

  const classes = useQuery({ queryKey: ['environment-classes'], queryFn: async () => (await api.get('/api/v1/students/classes')).data })
  const students = useQuery({ queryKey: ['environment-students', classId], queryFn: async () => (await api.get(`/api/v1/students/classes/${classId}/students`)).data, enabled: Boolean(classId) })
  const history = useQuery({ queryKey: ['environment-history', studentId], queryFn: async () => (await api.get(`/api/v1/environment/history/${studentId}`)).data, enabled: Boolean(studentId) })
  const review = useMutation({
    mutationFn: async (status: 'confirmed' | 'modified' | 'rejected') => (await api.post(`/api/v1/environment/checks/${result.id}/review`, { status, reviewed_details: reviewDetails, reviewed_suggestions: reviewSuggestions, reviewed_suggestions_comment: reviewSuggestionsComment, reviewed_summary: reviewSummary, note })).data,
    onSuccess: (data) => { setResult(data); queryClient.invalidateQueries({ queryKey: ['environment-history', studentId] }) },
  })

  useEffect(() => {
    if (!classId && classes.data?.length) setClassId(classes.data[0].id)
  }, [classes.data, classId])
  useEffect(() => {
    if (classId && !studentId && students.data?.length) setStudentId(students.data[0].id)
  }, [classId, students.data, studentId])
  useEffect(() => {
    if (!result && history.data?.length) setResult(history.data[0])
  }, [history.data, result])
  useEffect(() => {
    if (!result) return
    const details = structuredClone(result.reviewed_details || result.details || {})
    delete details.__suggestions__
    setReviewDetails(details)
    setReviewSuggestions(result.reviewed_suggestions?.length ? result.reviewed_suggestions : result.suggestions || [])
    setReviewSuggestionsComment(result.reviewed_suggestions_comment || '')
    setReviewSummary(result.reviewed_summary || result.summary || '')
    setNote(result.review_note || '')
  }, [result?.id, result?.reviewed_at])

  const pendingCount = (history.data || []).filter((item: any) => !item.review_status).length
  const selectedStudent = students.data?.find((item: any) => item.id === studentId)
  const manualScore = Object.values(reviewDetails || {}).reduce((sum: number, value: any) => sum + (Number(value?.score) || 0), 0)

  return <div className="space-y-6">
    <header className="role-intro teacher-intro">
      <div><p className="eyebrow">AUTOMATED ENVIRONMENT REVIEW</p><h1 className="page-title">实训环境自动检测</h1><p>实训结束 → 摄像头抓拍 → AI 对比标准状态 → 教师复核；教师端不再手动发起检测</p></div>
      <div className="flex gap-6 text-right"><HeaderMetric label="检测记录" value={studentId ? history.data?.length || 0 : '—'} /><HeaderMetric label="待复核" value={studentId ? pendingCount : '—'} warn={pendingCount > 0} /></div>
    </header>

    <section className="railway-card p-5">
      <div className="grid gap-4 md:grid-cols-[1fr_1fr_1.4fr] md:items-end">
        <Field label="授权班级"><select className="input-field" value={classId} onChange={(e) => { setClassId(e.target.value); setStudentId(''); setResult(null) }}><option value="">选择班级</option>{classes.data?.map((item: any) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field>
        <Field label="学生"><select className="input-field" value={studentId} disabled={!classId} onChange={(e) => { setStudentId(e.target.value); setResult(null) }}><option value="">选择学生</option>{students.data?.map((item: any) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field>
        <div className="rounded border border-accent-blue/25 bg-accent-electric/5 px-4 py-3 text-xs text-text-secondary"><span className="text-accent-cyan">自动触发规则：</span>每条实训完成记录携带现场抓拍后，系统自动创建检测任务并关联实训成绩；本页只处理查看与复核。</div>
      </div>
    </section>

    {!studentId && <section className="railway-card p-12 text-center"><div className="mx-auto grid h-16 w-16 place-content-center rounded-full border border-accent-blue/30 bg-accent-electric/10 font-mono text-xl text-accent-cyan">AUTO</div><h2 className="mt-5 section-heading">选择班级和学生查看自动检测记录</h2><p className="mt-2 text-sm text-text-muted">无需上传图片或点击生成，检测结果由实训完成事件自动写入。</p></section>}

    {studentId && <div className="grid items-start gap-5 xl:grid-cols-[320px_minmax(0,1fr)]">
      <section className="railway-card overflow-hidden xl:sticky xl:top-28">
        <div className="border-b border-railway-600/50 p-5"><p className="eyebrow">AUTO CHECK ARCHIVE</p><h2 className="section-heading">{selectedStudent?.name || '学生'} · 检测记录</h2><p className="mt-1 text-xs text-text-muted">按实训结束时间倒序生成</p></div>
        <div className="max-h-[690px] divide-y divide-railway-600/50 overflow-y-auto">{history.data?.map((item: any) => <button key={item.id} onClick={() => setResult(item)} className={`w-full p-4 text-left transition hover:bg-railway-700/50 ${result?.id === item.id ? 'bg-accent-electric/10' : ''}`}><div className="flex items-start justify-between gap-3"><div><p className="font-medium text-text-primary">{item.lab_name}</p><p className="mt-1 font-mono text-[10px] text-text-muted">{new Date(item.checked_at).toLocaleString('zh-CN')}</p></div><span className={item.review_status ? 'text-xs text-status-success' : 'text-xs text-status-warning'}>{reviewLabel(item.review_status)}</span></div><div className="mt-3 flex items-end justify-between"><span className="text-xs text-text-muted">{item.review_status ? '教师最终分' : 'AI 原始分'}</span><span className="font-mono text-2xl text-accent-cyan">{item.final_score ?? item.total_score}</span></div></button>)}{!history.isLoading && !history.data?.length && <p className="p-5 text-sm text-text-muted">该学生暂无自动检测记录；请确认实训完成数据已携带现场抓拍。</p>}</div>
      </section>

      {result ? <div className="space-y-5">
        <section className="railway-card overflow-hidden"><div className="flex flex-wrap items-center justify-between gap-4 border-b border-railway-600/50 p-5"><div><p className="eyebrow">AUTOMATED CHECK · {String(result.id).slice(-8)}</p><h2 className="section-heading">AI 检测结果与教师复核</h2><p className="mt-1 text-xs text-text-muted">{result.lab_name} · 自动生成于 {new Date(result.checked_at).toLocaleString('zh-CN')}</p></div><div className="text-right"><span className="font-mono text-4xl text-accent-cyan">{result.review_status ? (result.final_score ?? manualScore) : result.total_score}</span><p className="text-[10px] text-text-muted">{result.review_status ? '教师最终分' : 'AI 原始分'} / 100</p></div></div><div className="grid gap-px bg-railway-600/40 md:grid-cols-4">{Object.entries(result.details || {}).map(([key, value]: any) => <ResultMetric key={key} name={categoryNames[key] || key} value={value} />)}</div></section>

        <div className="grid gap-5 lg:grid-cols-2"><ImageEvidence title="标准状态" src={result.reference_image_url} badge="REFERENCE" /><ImageEvidence title="实训结束抓拍" src={result.uploaded_image_url} badge="AUTO CAPTURE" /></div>

        <div className="grid gap-5 2xl:grid-cols-[.9fr_1.1fr]">
          <section className="railway-card p-5"><p className="eyebrow">AI ORIGINAL RESULT</p><h3 className="section-heading">AI 原始判断</h3><p className="mt-4 leading-7 text-text-secondary">{result.summary}</p><div className="mt-5 space-y-3">{Object.entries(result.details || {}).map(([key, value]: any) => <div key={key} className="rounded border border-railway-600/60 bg-railway-700/30 p-3"><div className="flex justify-between gap-3"><span className="text-text-primary">{categoryNames[key] || key}</span><span className="font-mono text-accent-cyan">{value.score}/{value.max_score}</span></div><p className="mt-2 text-xs text-text-muted">{value.issues?.join('；') || '未发现问题'}</p></div>)}</div>{result.suggestions?.length > 0 && <div className="mt-5 rounded border border-accent-blue/30 bg-accent-electric/5 p-4"><p className="text-xs font-semibold text-accent-cyan">AI 整改建议</p><ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-text-secondary">{result.suggestions.map((item: string) => <li key={item}>{item}</li>)}</ul></div>}</section>

          <section className="railway-card p-5"><div className="flex items-end justify-between gap-3"><div><p className="eyebrow">HUMAN REVIEW</p><h3 className="section-heading">教师复核</h3></div><p className="font-mono text-sm text-accent-cyan">复核分 {manualScore}/100</p></div><label className="mt-4 block text-sm text-text-secondary">复核总结<textarea className="input-field mt-2 min-h-20" value={reviewSummary} onChange={(e) => setReviewSummary(e.target.value)} /></label><div className="mt-4 space-y-3">{Object.entries(reviewDetails || {}).map(([key, value]: any) => <div key={key} className="rounded border border-railway-600/60 p-3"><div className="flex items-center justify-between gap-3"><span>{categoryNames[key] || key}</span><label className="text-xs text-text-muted">人工分数 <input className="ml-2 w-20 rounded border border-railway-500 bg-railway-800 px-2 py-1 text-right text-text-primary" type="number" min="0" max={value.max_score} value={value.score} onChange={(e) => setReviewDetails((current: any) => ({ ...current, [key]: { ...current[key], score: Number(e.target.value) } }))} /></label></div><p className="mt-2 text-xs text-text-muted">{value.issues?.join('；') || '未发现问题'}</p><label className="mt-3 block text-xs text-text-muted">教师意见<textarea className="input-field mt-1 min-h-16" value={value.comment || ''} onChange={(e) => setReviewDetails((current: any) => ({ ...current, [key]: { ...current[key], comment: e.target.value } }))} placeholder="填写本检查项的复核意见" /></label></div>)}</div><div className="mt-3 rounded border border-railway-600/60 p-3"><p className="font-medium text-text-primary">建议措施</p>{reviewSuggestions.length > 0 ? <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-text-muted">{reviewSuggestions.map((item) => <li key={item}>{item}</li>)}</ul> : <p className="mt-2 text-xs text-text-muted">AI 未提供建议措施</p>}<label className="mt-3 block text-xs text-text-muted">教师意见<textarea className="input-field mt-1 min-h-16" value={reviewSuggestionsComment} onChange={(e) => setReviewSuggestionsComment(e.target.value)} placeholder="可对建议措施补充意见；此项不计分" /></label></div><label className="mt-4 block text-sm text-text-secondary">整体复核备注<textarea className="input-field mt-2 min-h-20" value={note} onChange={(e) => setNote(e.target.value)} placeholder="填写整体修改原因或复核意见" /></label><div className="mt-4 grid gap-2 sm:grid-cols-3"><button className="railway-button" disabled={review.isPending} onClick={() => review.mutate('confirmed')}>确认 AI 结果</button><button className="btn-primary" disabled={review.isPending} onClick={() => review.mutate('modified')}>保存人工复核</button><button className="rounded border border-status-danger/50 px-3 py-2 text-sm text-status-danger" disabled={review.isPending} onClick={() => review.mutate('rejected')}>驳回并保存</button></div>{result.reviewed_at && <p className="mt-4 text-xs text-text-muted">最近复核：{result.reviewer_name || '—'} · {new Date(result.reviewed_at).toLocaleString('zh-CN')} · {result.review_note || '无备注'}</p>}</section>
        </div>
      </div> : <section className="railway-card flex min-h-[500px] items-center justify-center text-text-muted">选择一条自动检测记录进行复核</section>}
    </div>}
  </div>
}

function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label className="text-sm text-text-secondary"><span className="mb-2 block">{label}</span>{children}</label> }
function HeaderMetric({ label, value, warn = false }: { label: string; value: string | number; warn?: boolean }) { return <div><p className="text-[10px] uppercase tracking-widest text-text-muted">{label}</p><strong className={`mt-1 block font-mono text-2xl ${warn ? 'text-status-warning' : 'text-accent-cyan'}`}>{value}</strong></div> }
function ImageEvidence({ title, src, badge }: { title: string; src?: string; badge: string }) { return <section className="railway-card overflow-hidden"><div className="flex items-center justify-between border-b border-railway-600/50 p-4"><span className="text-sm font-semibold text-text-primary">{title}</span><span className="font-mono text-[9px] text-accent-cyan">{badge}</span></div><div className="aspect-video bg-railway-800">{src ? <img className="h-full w-full object-cover" src={src} alt={title} /> : <div className="flex h-full items-center justify-center text-text-muted">无图片</div>}</div></section> }
function ResultMetric({ name, value }: { name: string; value: any }) { const percentage = value.max_score ? value.score / value.max_score * 100 : 0; return <div className="bg-railway-800/95 p-4"><p className="text-xs text-text-muted">{name}</p><div className="mt-2 flex items-end justify-between"><strong className="font-mono text-xl text-text-primary">{value.score}<span className="text-xs text-text-muted">/{value.max_score}</span></strong><span className={percentage >= 80 ? 'text-[10px] text-status-success' : 'text-[10px] text-status-warning'}>{percentage >= 80 ? '规范' : '需关注'}</span></div><div className="mt-2 h-1 overflow-hidden rounded bg-railway-700"><div className={percentage >= 80 ? 'h-full bg-status-success' : 'h-full bg-status-warning'} style={{ width: `${percentage}%` }} /></div></div> }
function reviewLabel(status?: string) { return ({ confirmed: '已确认', modified: '已修改复核', rejected: '已驳回', pending: '待复核' } as Record<string, string>)[status || 'pending'] || status }
