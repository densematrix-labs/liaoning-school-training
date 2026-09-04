import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, getErrorMessage } from '../../lib/api'

const categoryNames: Record<string, string> = {
  equipment_placement: '器材归位',
  surface_cleanliness: '台面整洁',
  safety_compliance: '安全规范',
  environmental_hygiene: '环境卫生',
}

export default function EnvironmentCheckPage() {
  const queryClient = useQueryClient()
  const fileInput = useRef<HTMLInputElement>(null)
  const [classId, setClassId] = useState('')
  const [studentId, setStudentId] = useState('')
  const [labId, setLabId] = useState('')
  const [scoreId, setScoreId] = useState('')
  const [image, setImage] = useState('')
  const [result, setResult] = useState<any>(null)
  const [reviewDetails, setReviewDetails] = useState<any>({})
  const [reviewSummary, setReviewSummary] = useState('')
  const [note, setNote] = useState('')
  const [taskId, setTaskId] = useState('')

  const classes = useQuery({ queryKey: ['environment-classes'], queryFn: async () => (await api.get('/api/v1/students/classes')).data })
  const students = useQuery({ queryKey: ['environment-students', classId], queryFn: async () => (await api.get(`/api/v1/students/classes/${classId}/students`)).data, enabled: Boolean(classId) })
  const labs = useQuery({ queryKey: ['environment-labs'], queryFn: async () => (await api.get('/api/v1/environment/labs')).data })
  const scores = useQuery({ queryKey: ['environment-scores', studentId], queryFn: async () => (await api.get(`/api/v1/scores/student/${studentId}`, { params: { page_size: 100 } })).data, enabled: Boolean(studentId) })
  const history = useQuery({ queryKey: ['environment-history', studentId], queryFn: async () => (await api.get(`/api/v1/environment/history/${studentId}`)).data, enabled: Boolean(studentId) })
  const check = useMutation({
    mutationFn: async () => (await api.post('/api/v1/environment/tasks', { student_id: studentId, lab_id: labId, score_id: scoreId || undefined, image_base64: image })).data,
    onSuccess: (data) => setTaskId(data.id),
  })
  const task = useQuery({
    queryKey: ['environment-task', taskId],
    queryFn: async () => (await api.get(`/api/v1/environment/tasks/${taskId}`)).data,
    enabled: Boolean(taskId),
    refetchInterval: (query) => ['pending', 'running'].includes((query.state.data as any)?.status) ? 800 : false,
  })
  const review = useMutation({
    mutationFn: async (status: 'confirmed' | 'modified' | 'rejected') => (await api.post(`/api/v1/environment/checks/${result.id}/review`, { status, reviewed_details: reviewDetails, reviewed_summary: reviewSummary, note })).data,
    onSuccess: (data) => { setResult(data); queryClient.invalidateQueries({ queryKey: ['environment-history', studentId] }) },
  })
  useEffect(() => {
    if (!result) return
    setReviewDetails(structuredClone(result.reviewed_details || result.details || {}))
    setReviewSummary(result.reviewed_summary || result.summary || '')
    setNote(result.review_note || '')
  }, [result?.id, result?.reviewed_at])
  useEffect(() => {
    if (task.data?.status === 'completed' && task.data.result) {
      setResult(task.data.result)
      queryClient.invalidateQueries({ queryKey: ['environment-history', studentId] })
    }
  }, [task.data?.status, task.data?.check_id])

  const loadFile = (file?: File) => {
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => setImage(String(reader.result || ''))
    reader.readAsDataURL(file)
  }
  const reset = () => { setImage(''); setResult(null); setTaskId(''); setReviewDetails({}); setReviewSummary(''); setNote(''); if (fileInput.current) fileInput.current.value = '' }

  return <div className="space-y-6">
    <header><p className="eyebrow">ENVIRONMENT EVIDENCE & REVIEW</p><h1 className="page-title">环境图片检查与人工复核</h1><p className="mt-2 text-sm text-text-muted">标准图与现场图智能对比，AI 原始结果和人工复核结果分别留存</p></header>
    <section className="railway-card grid gap-4 p-5 sm:grid-cols-2 xl:grid-cols-4">
      <Field label="授权班级"><select className="input-field" value={classId} onChange={(e) => { setClassId(e.target.value); setStudentId(''); reset() }}><option value="">选择班级</option>{classes.data?.map((item: any) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field>
      <Field label="关联学生"><select className="input-field" value={studentId} disabled={!classId} onChange={(e) => { setStudentId(e.target.value); setScoreId(''); reset() }}><option value="">选择学生</option>{students.data?.map((item: any) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field>
      <Field label="实训室与标准图"><select className="input-field" value={labId} onChange={(e) => setLabId(e.target.value)}><option value="">选择实训室</option>{labs.data?.map((item: any) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field>
      <Field label="关联实训记录"><select className="input-field" value={scoreId} disabled={!studentId} onChange={(e) => setScoreId(e.target.value)}><option value="">不关联</option>{scores.data?.scores.map((item: any) => <option key={item.id} value={item.id}>{item.project_name} · {item.percentage}分</option>)}</select></Field>
    </section>

    {!result && <div className="grid gap-5 xl:grid-cols-[1.1fr_.9fr]">
      <section className="railway-card p-5"><h2 className="section-heading">创建检查任务</h2><input ref={fileInput} className="hidden" type="file" accept="image/jpeg,image/png,image/webp" onChange={(e) => loadFile(e.target.files?.[0])} /><button onClick={() => fileInput.current?.click()} className="mt-5 flex aspect-video w-full items-center justify-center overflow-hidden rounded-lg border-2 border-dashed border-railway-500 bg-railway-800/40">{image ? <img src={image} alt="现场图片预览" className="h-full w-full object-cover" /> : <span className="text-text-muted">点击上传 JPG/PNG/WebP 现场图片（最大 10MB）</span>}</button><button className="btn-primary mt-4 w-full" disabled={!studentId || !labId || !image || check.isPending || ['pending', 'running'].includes(task.data?.status)} onClick={() => check.mutate()}>{check.isPending ? '正在提交…' : '发起智能检查'}</button>{taskId && <div className={task.data?.status === 'failed' ? 'alert-warning mt-4 rounded p-3 text-sm' : 'alert-success mt-4 rounded p-3 text-sm'}>任务状态：{taskLabel(task.data?.status)}{task.data?.error_message && <p className="mt-1">{task.data.error_message}</p>}</div>}{check.error && <p className="alert-warning mt-4 rounded p-3 text-sm">{getErrorMessage(check.error, '环境检查任务提交失败')}</p>}</section>
      <section className="railway-card overflow-hidden"><div className="border-b border-railway-600/50 p-5"><h2 className="section-heading">历史检查记录</h2></div><div className="divide-y divide-railway-600/50">{history.data?.map((item: any) => <button key={item.id} onClick={() => setResult(item)} className="grid w-full gap-2 p-4 text-left hover:bg-railway-700/40 sm:grid-cols-[1fr_auto]"><div><p className="text-text-primary">{item.lab_name}</p><p className="text-xs text-text-muted">{new Date(item.checked_at).toLocaleString('zh-CN')}</p></div><div className="text-right"><p className="font-mono text-accent-cyan">AI {item.total_score}分</p><p className={item.review_status ? 'text-xs text-status-success' : 'text-xs text-status-warning'}>{reviewLabel(item.review_status)}</p></div></button>)}{studentId && !history.data?.length && <p className="p-5 text-sm text-text-muted">该学生暂无环境检查记录</p>}</div></section>
    </div>}

    {result && <div className="space-y-5">
      <section className="railway-card flex flex-wrap items-center justify-between gap-4 p-5"><div><p className="eyebrow">CHECK {result.id}</p><h2 className="section-heading">AI 原始结果与人工复核</h2><p className="mt-1 text-xs text-text-muted">{result.lab_name} · {new Date(result.checked_at).toLocaleString('zh-CN')}</p></div><div className="flex items-center gap-4"><span className="font-mono text-3xl text-accent-cyan">{result.total_score}</span><span className={result.review_status ? 'text-status-success' : 'text-status-warning'}>{reviewLabel(result.review_status)}</span><button className="railway-button" onClick={reset}>返回列表</button></div></section>
      <div className="grid gap-5 xl:grid-cols-2"><ImageEvidence title="标准状态图片" src={result.reference_image_url} /><ImageEvidence title="现场图片" src={result.uploaded_image_url} /></div>
      <div className="grid gap-5 xl:grid-cols-2">
        <section className="railway-card p-5"><p className="eyebrow">IMMUTABLE AI RESULT</p><h3 className="section-heading">AI 原始检查结果</h3><p className="mt-3 text-text-secondary">{result.summary}</p><div className="mt-5 space-y-3">{Object.entries(result.details || {}).map(([key, value]: any) => <ResultRow key={key} name={categoryNames[key] || key} value={value} />)}</div>{result.suggestions?.length > 0 && <div className="mt-4 rounded border border-accent-blue/30 p-3"><p className="text-xs font-semibold text-accent-cyan">建议措施</p><ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-text-secondary">{result.suggestions.map((item: string) => <li key={item}>{item}</li>)}</ul></div>}</section>
        <section className="railway-card p-5"><p className="eyebrow">HUMAN REVIEW</p><h3 className="section-heading">人工复核结果</h3><label className="mt-4 block text-sm text-text-secondary">复核总结<textarea className="input-field mt-2 min-h-20" value={reviewSummary} onChange={(e) => setReviewSummary(e.target.value)} /></label><div className="mt-4 space-y-3">{Object.entries(reviewDetails || {}).map(([key, value]: any) => <div key={key} className="rounded border border-railway-600/60 p-3"><div className="flex items-center justify-between gap-3"><span>{categoryNames[key] || key}</span><label className="text-xs text-text-muted">复核分数 <input className="ml-2 w-20 rounded border border-railway-500 bg-railway-800 px-2 py-1 text-right text-text-primary" type="number" min="0" max={value.max_score} value={value.score} onChange={(e) => setReviewDetails((current: any) => ({ ...current, [key]: { ...current[key], score: Number(e.target.value) } }))} /></label></div><p className="mt-2 text-xs text-text-muted">{value.issues?.join('；') || '未发现问题'}</p></div>)}</div><label className="mt-4 block text-sm text-text-secondary">复核备注<textarea className="input-field mt-2 min-h-20" value={note} onChange={(e) => setNote(e.target.value)} placeholder="填写修改原因或复核意见" /></label><div className="mt-4 grid gap-2 sm:grid-cols-3"><button className="railway-button" disabled={review.isPending} onClick={() => review.mutate('confirmed')}>确认 AI 结果</button><button className="btn-primary" disabled={review.isPending} onClick={() => review.mutate('modified')}>保存修改结果</button><button className="rounded border border-status-danger/50 px-3 py-2 text-sm text-status-danger" disabled={review.isPending} onClick={() => review.mutate('rejected')}>驳回转人工</button></div>{result.reviewed_at && <p className="mt-4 text-xs text-text-muted">最近复核：{result.reviewer_name || '—'} · {new Date(result.reviewed_at).toLocaleString('zh-CN')} · {result.review_note || '无备注'}</p>}</section>
      </div>
    </div>}
  </div>
}

function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label className="text-sm text-text-secondary"><span className="mb-2 block">{label}</span>{children}</label> }
function ImageEvidence({ title, src }: { title: string; src?: string }) { return <section className="railway-card overflow-hidden"><div className="border-b border-railway-600/50 p-4 text-sm font-semibold text-text-primary">{title}</div><div className="aspect-video bg-railway-800">{src ? <img className="h-full w-full object-cover" src={src} alt={title} /> : <div className="flex h-full items-center justify-center text-text-muted">无图片</div>}</div></section> }
function ResultRow({ name, value }: { name: string; value: any }) { return <div className="rounded bg-railway-800/60 p-3"><div className="flex justify-between"><span className="text-text-secondary">{name}</span><span className="font-mono text-accent-cyan">{value.score}/{value.max_score}</span></div><p className="mt-2 text-xs text-text-muted">{value.issues?.join('；') || '未发现问题'}</p></div> }
function reviewLabel(status?: string) { return ({ confirmed: '已确认', modified: '已修改复核', rejected: '已驳回', pending: '待复核' } as Record<string, string>)[status || 'pending'] || status }
function taskLabel(status?: string) { return ({ pending: '已提交', running: 'AI 分析中', completed: '检查完成', failed: '检查失败' } as Record<string, string>)[status || 'pending'] || status }
