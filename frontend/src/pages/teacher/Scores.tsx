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
  const [studentId, setStudentId] = useState(searchParams.get('student_id') || '')
  const [projectId, setProjectId] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [selectedScore, setSelectedScore] = useState(searchParams.get('score_id') || '')
  const [importCandidate, setImportCandidate] = useState<{ file: File; preview: any } | null>(null)
  const previewImport = useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData()
      form.append('file', file)
      return (await api.post('/api/v1/admin/operations/sync-import/preview', form, { headers: { 'Content-Type': 'multipart/form-data' } })).data
    },
    onSuccess: (preview, file) => setImportCandidate({ file, preview }),
  })
  const importFile = useMutation({
    mutationFn: async ({ file }: { file: File }) => {
      const form = new FormData()
      form.append('file', file)
      await api.post('/api/v1/admin/operations/sync-import', form, { headers: { 'Content-Type': 'multipart/form-data' } })
      return (await api.post('/api/v1/admin/sync')).data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['class-scores'] })
      queryClient.invalidateQueries({ queryKey: ['class-summary'] })
      queryClient.invalidateQueries({ queryKey: ['teacher-report-scores'] })
      queryClient.invalidateQueries({ queryKey: ['admin-sync-history'] })
      setImportCandidate(null)
      if (importInput.current) importInput.current.value = ''
    },
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
  useEffect(() => {
    if (classId !== searchParams.get('class_id')) setStudentId('')
  }, [classId, searchParams])
  const selectedStudent = students.data?.find((item: any) => item.id === studentId)
  const visiblePassRate = scores.data?.scores?.length
    ? Math.round(scores.data.scores.filter((item: any) => item.percentage >= 60).length / scores.data.scores.length * 1000) / 10
    : 0

  return <div className="space-y-6">
    <header><p className="eyebrow">CLASS SCORE EVIDENCE</p><h1 className="page-title">班级成绩总览</h1><p className="mt-2 text-sm text-text-muted">按班级、学生、项目和时间检索，并核对单次成绩汇总证据</p></header>
    <section className="railway-card grid gap-4 p-5 sm:grid-cols-2 xl:grid-cols-5">
      <Field label="班级"><select className="input-field" value={classId} onChange={(e) => setClassId(e.target.value)}><option value="">选择授权班级</option>{classes.data?.map((item: any) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field>
      <Field label="学生"><select className="input-field" value={studentId} disabled={!classId} onChange={(e) => setStudentId(e.target.value)}><option value="">全部学生</option>{students.data?.map((item: any) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field>
      <Field label="实训项目"><select className="input-field" value={projectId} onChange={(e) => setProjectId(e.target.value)}><option value="">全部项目</option>{projects.data?.map((item: any) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field>
      <Field label="开始日期"><input className="input-field" type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} /></Field>
      <Field label="结束日期"><input className="input-field" type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} /></Field>
    </section>
    {classId && <div className="grid gap-3 sm:grid-cols-4"><Metric label={studentId ? '当前学生' : '学生数'} value={studentId ? (selectedStudent?.name || '已选择') : (summary.data?.student_count ?? '—')} /><Metric label="实训记录" value={scores.data?.total ?? '—'} /><Metric label={studentId ? '个人平均' : '班级平均'} value={studentId ? (scores.data?.average_score ?? '—') : (summary.data?.average_score ?? '—')} /><Metric label={studentId ? '个人及格率' : '及格率'} value={`${studentId ? visiblePassRate : (summary.data?.pass_rate ?? '—')}%`} /></div>}
    <CsvImportPanel
      isAdmin={user?.role === 'admin'}
      inputRef={importInput}
      candidate={importCandidate}
      previewPending={previewImport.isPending}
      importPending={importFile.isPending}
      previewError={previewImport.error}
      importError={importFile.error}
      result={importFile.data}
      onSelect={(file) => { setImportCandidate(null); previewImport.mutate(file) }}
      onConfirm={() => importCandidate && importFile.mutate({ file: importCandidate.file })}
      onCancel={() => { setImportCandidate(null); if (importInput.current) importInput.current.value = '' }}
    />
    <div className="flex justify-end"><button className="railway-button" disabled={!classId} onClick={() => downloadClassScores(classId, { student_id: studentId || undefined, project_id: projectId || undefined, date_from: dateFrom || undefined, date_to: dateTo ? `${dateTo}T23:59:59` : undefined })}>导出当前筛选 CSV</button></div>
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

function CsvImportPanel({ isAdmin, inputRef, candidate, previewPending, importPending, previewError, importError, result, onSelect, onConfirm, onCancel }: {
  isAdmin: boolean
  inputRef: React.RefObject<HTMLInputElement>
  candidate: { file: File; preview: any } | null
  previewPending: boolean
  importPending: boolean
  previewError: unknown
  importError: unknown
  result: any
  onSelect: (file: File) => void
  onConfirm: () => void
  onCancel: () => void
}) {
  return <section className="railway-card overflow-hidden">
    <div className="flex flex-wrap items-start justify-between gap-4 border-b border-railway-600/50 p-5">
      <div><p className="eyebrow">CSV IMPORT</p><h2 className="section-heading">批量导入实训记录</h2><p className="mt-1 text-xs text-text-muted">先校验并预览，再确认写入；完成后成绩列表与汇总会自动刷新。</p></div>
      {isAdmin ? <div className="flex flex-wrap gap-2"><button type="button" className="railway-button" onClick={downloadImportTemplate}>下载 CSV 模板</button><input ref={inputRef} className="hidden" type="file" accept=".csv,text/csv" onChange={(event) => { const file = event.target.files?.[0]; if (file) onSelect(file) }} /><button type="button" className="btn-primary" disabled={previewPending || importPending} onClick={() => inputRef.current?.click()}>{previewPending ? '正在校验…' : '选择 CSV 文件'}</button></div> : <span className="rounded border border-status-warning/40 bg-status-warning/10 px-3 py-2 text-xs text-status-warning">仅管理员可执行导入</span>}
    </div>
    <div className="grid gap-3 p-5 text-xs text-text-muted md:grid-cols-4">
      <FieldHint name="source_record_id" description="必填；外部记录唯一编号，用于防重复" />
      <FieldHint name="student_no" description="推荐；学生学号，必须已存在" />
      <FieldHint name="project_name" description="推荐；实训项目名称，必须与系统一致" />
      <FieldHint name="completed_at" description="必填；如 2026-09-17T08:30:00" />
    </div>
    {!isAdmin && <p className="border-t border-railway-600/40 px-5 py-4 text-xs text-text-muted">教师可继续使用右侧导出功能；全校数据写入由管理员在此处完成，避免越权修改其他班级成绩。</p>}
    {(previewError || importError) && <p role="alert" className="alert-warning m-4 rounded p-3 text-sm">{getErrorMessage(previewError || importError, 'CSV 校验或导入失败')}</p>}
    {candidate && <div className="border-t border-railway-600/40 p-5">
      <div className="flex flex-wrap items-center justify-between gap-3"><div><p className="font-medium text-text-primary">{candidate.file.name}</p><p className="mt-1 text-xs text-text-muted">共 {candidate.preview.row_count} 条 · 可导入 {candidate.preview.valid_count} 条 · 异常 {candidate.preview.error_count} 条</p></div><div className="flex gap-2"><button type="button" className="railway-button" disabled={importPending} onClick={onCancel}>取消</button><button type="button" className="btn-primary" disabled={!candidate.preview.can_import || importPending} onClick={onConfirm}>{importPending ? '正在导入并刷新…' : '确认导入并更新成绩'}</button></div></div>
      <div className="mt-4 overflow-x-auto"><table className="w-full min-w-[720px] text-left text-xs"><thead className="bg-railway-800/70 text-text-muted"><tr><th className="p-2">行</th><th>实训记录编号</th><th>学生</th><th>项目</th><th>完成时间</th><th>校验</th></tr></thead><tbody>{candidate.preview.preview?.map((item: any) => <tr key={item.row_number} className="border-t border-railway-600/40"><td className="p-2">{item.row_number}</td><td>{item.source_record_id || '—'}</td><td>{item.student}</td><td>{item.project}</td><td>{item.completed_at || '—'}</td><td className={item.valid ? 'text-status-success' : 'text-status-danger'}>{item.valid ? '通过' : '异常'}</td></tr>)}</tbody></table></div>
      {candidate.preview.errors?.length > 0 && <div className="mt-4 rounded border border-status-warning/35 bg-status-warning/5 p-3"><p className="font-medium text-status-warning">需修正的记录</p><ul className="mt-2 space-y-1 text-xs text-text-secondary">{candidate.preview.errors.map((item: any) => <li key={`${item.row_number}-${item.reason}`}>第 {item.row_number} 行：{item.reason}</li>)}</ul></div>}
    </div>}
    {result && <p className="alert-success m-4 rounded p-3 text-sm">CSV 导入完成：读取 {result.read_count} 条，新增 {result.success_count} 条，跳过 {result.skipped_count} 条，异常 {result.error_count} 条；成绩数据已刷新。</p>}
  </section>
}

function FieldHint({ name, description }: { name: string; description: string }) { return <div className="rounded border border-railway-600/50 bg-railway-800/35 p-3"><code className="text-accent-cyan">{name}</code><p className="mt-1">{description}</p></div> }

async function downloadClassScores(classId: string, params: Record<string, string | undefined>) {
  const response = await api.get(`/api/v1/scores/class/${classId}/export.csv`, { params, responseType: 'blob' })
  const url = URL.createObjectURL(response.data)
  const link = document.createElement('a')
  link.href = url
  link.download = `class-${classId}-scores.csv`
  link.click()
  URL.revokeObjectURL(url)
}

async function downloadImportTemplate() {
  const response = await api.get('/api/v1/admin/operations/sync-import/template.csv', { responseType: 'blob' })
  const url = URL.createObjectURL(response.data)
  const link = document.createElement('a')
  link.href = url
  link.download = '实训记录导入模板.csv'
  link.click()
  URL.revokeObjectURL(url)
}
