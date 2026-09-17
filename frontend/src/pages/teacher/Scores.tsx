import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, getErrorMessage } from '../../lib/api'
import ScoreEvidenceModal from '../../components/ScoreEvidenceModal'
import { useAuthStore } from '../../store/auth'

export default function TeacherScores() {
  const { user } = useAuthStore()
  const queryClient = useQueryClient()
  const importInput = useRef<HTMLInputElement>(null)
  const [searchParams] = useSearchParams()
  const [classId, setClassId] = useState(searchParams.get('class_id') || '')
  const [studentId, setStudentId] = useState('')
  const [projectId, setProjectId] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [selectedScore, setSelectedScore] = useState('')
  const importFile = useMutation({
    mutationFn: async (file: File) => { const form = new FormData(); form.append('file', file); return (await api.post('/api/v1/admin/operations/sync-import', form)).data },
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['class-scores'] }); queryClient.invalidateQueries({ queryKey: ['class-summary'] }); if (importInput.current) importInput.current.value = '' },
  })
  const classes = useQuery({ queryKey: ['teacher-classes'], queryFn: async () => (await api.get('/api/v1/students/classes')).data })
  const students = useQuery({ queryKey: ['class-students', classId], queryFn: async () => (await api.get(`/api/v1/students/classes/${classId}/students`)).data, enabled: Boolean(classId) })
  const projects = useQuery({ queryKey: ['score-projects'], queryFn: async () => (await api.get('/api/v1/scores/projects')).data })
  const scores = useQuery({
    queryKey: ['class-scores', classId, studentId, projectId, dateFrom, dateTo],
    queryFn: async () => (await api.get(`/api/v1/scores/class/${classId}`, { params: { page_size: 100, student_id: studentId || undefined, project_id: projectId || undefined, date_from: dateFrom || undefined, date_to: dateTo ? `${dateTo}T23:59:59` : undefined } })).data,
    enabled: Boolean(classId),
  })
  const summary = useQuery({ queryKey: ['class-summary', classId], queryFn: async () => (await api.get(`/api/v1/scores/class/${classId}/summary`)).data, enabled: Boolean(classId) })
  useEffect(() => setStudentId(''), [classId])

  return <div className="space-y-6">
    <header><p className="eyebrow">CLASS SCORE EVIDENCE</p><h1 className="page-title">班级成绩总览</h1><p className="mt-2 text-sm text-text-muted">按班级、学生、项目和时间检索，并核对单次成绩汇总证据</p></header>
    <section className="railway-card grid gap-4 p-5 sm:grid-cols-2 xl:grid-cols-5">
      <Field label="班级"><select className="input-field" value={classId} onChange={(e) => setClassId(e.target.value)}><option value="">选择授权班级</option>{classes.data?.map((item: any) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field>
      <Field label="学生"><select className="input-field" value={studentId} disabled={!classId} onChange={(e) => setStudentId(e.target.value)}><option value="">全部学生</option>{students.data?.map((item: any) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field>
      <Field label="实训项目"><select className="input-field" value={projectId} onChange={(e) => setProjectId(e.target.value)}><option value="">全部项目</option>{projects.data?.map((item: any) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field>
      <Field label="开始日期"><input className="input-field" type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} /></Field>
      <Field label="结束日期"><input className="input-field" type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} /></Field>
    </section>
    {classId && <div className="grid gap-3 sm:grid-cols-4"><Metric label="学生数" value={summary.data?.student_count ?? '—'} /><Metric label="实训记录" value={scores.data?.total ?? '—'} /><Metric label="班级平均" value={summary.data?.average_score ?? '—'} /><Metric label="及格率" value={`${summary.data?.pass_rate ?? '—'}%`} /></div>}
    <div className="flex flex-wrap items-center justify-end gap-3">{user?.role === 'admin' ? <><input ref={importInput} className="hidden" type="file" accept=".csv,text/csv" onChange={(e) => e.target.files?.[0] && importFile.mutate(e.target.files[0])} /><button className="railway-button" disabled={importFile.isPending} onClick={() => importInput.current?.click()}>{importFile.isPending ? '正在导入…' : '导入实训记录 CSV'}</button></> : <span className="text-xs text-text-muted">CSV 导入涉及全校数据写入，仅管理员可执行</span>}<button className="railway-button" disabled={!classId} onClick={() => downloadClassScores(classId, { student_id: studentId || undefined, project_id: projectId || undefined, date_from: dateFrom || undefined, date_to: dateTo ? `${dateTo}T23:59:59` : undefined })}>导出当前筛选 CSV</button></div>
    {importFile.data && <p className="alert-success rounded p-3 text-sm">CSV 导入完成：读取 {importFile.data.read_count} 条，新增 {importFile.data.success_count} 条，跳过 {importFile.data.skipped_count} 条，异常 {importFile.data.error_count} 条。</p>}
    {importFile.error && <p className="alert-warning rounded p-3 text-sm">{getErrorMessage(importFile.error, 'CSV 导入失败')}</p>}
    <section className="space-y-3">
      {scores.data?.scores.map((score: any) => <button key={score.id} onClick={() => setSelectedScore(score.id)} className="railway-card grid w-full gap-3 p-4 text-left hover:border-accent-blue/60 sm:grid-cols-[1fr_1fr_auto_auto] sm:items-center"><div><p className="font-semibold text-text-primary">{score.student_name}</p><p className="text-xs text-text-muted">{score.project_name}</p></div><p className="text-sm text-text-muted">{new Date(score.calculated_at).toLocaleString('zh-CN')}</p><span className="font-mono text-xl text-accent-cyan">{score.percentage}</span><span className="text-sm text-accent-blue">核对明细 →</span></button>)}
      {!classId && <p className="railway-card p-10 text-center text-text-muted">请选择班级开始检索</p>}
      {classId && !scores.isLoading && !scores.data?.scores.length && <p className="railway-card p-10 text-center text-text-muted">当前筛选条件下没有成绩</p>}
    </section>
    {selectedScore && <ScoreEvidenceModal scoreId={selectedScore} onClose={() => setSelectedScore('')} />}
  </div>
}

function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label className="text-sm text-text-secondary"><span className="mb-2 block">{label}</span>{children}</label> }
function Metric({ label, value }: { label: string; value: string | number }) { return <div className="metric-strip"><p>{label}</p><strong className="text-accent-cyan">{value}</strong></div> }

async function downloadClassScores(classId: string, params: Record<string, string | undefined>) {
  const response = await api.get(`/api/v1/scores/class/${classId}/export.csv`, { params, responseType: 'blob' })
  const url = URL.createObjectURL(response.data)
  const link = document.createElement('a')
  link.href = url
  link.download = `class-${classId}-scores.csv`
  link.click()
  URL.revokeObjectURL(url)
}
