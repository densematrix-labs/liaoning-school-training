import { useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import ReactMarkdown from 'react-markdown'
import { api } from '../../lib/api'
import { ReportTaskStatus, useReportTask } from '../../lib/useReportTask'

export default function TeacherReports() {
  const [params] = useSearchParams()
  const [classId, setClassId] = useState(params.get('class_id') || '')
  const [studentId, setStudentId] = useState('')
  const [scoreId, setScoreId] = useState('')
  const [reportType, setReportType] = useState<'single' | 'periodic'>('single')
  const [historyType, setHistoryType] = useState<'all' | 'single' | 'periodic'>('all')
  const [historyScoreId, setHistoryScoreId] = useState('')
  const [activeReport, setActiveReport] = useState<any>(null)
  const reportSectionRef = useRef<HTMLElement>(null)
  const classes = useQuery({ queryKey: ['teacher-classes'], queryFn: async () => (await api.get('/api/v1/students/classes')).data })
  const students = useQuery({ queryKey: ['class-students', classId], queryFn: async () => (await api.get(`/api/v1/students/classes/${classId}/students`)).data, enabled: Boolean(classId) })
  const scores = useQuery({ queryKey: ['teacher-report-scores', studentId], queryFn: async () => (await api.get(`/api/v1/scores/student/${studentId}`, { params: { page_size: 100 } })).data, enabled: Boolean(studentId) })
  const reports = useQuery({ queryKey: ['teacher-student-reports', studentId], queryFn: async () => (await api.get(`/api/v1/reports/student/${studentId}`)).data, enabled: Boolean(studentId) })
  const showReport = (report: any) => {
    setActiveReport(report)
    window.setTimeout(() => reportSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 0)
  }
  const reportTask = useReportTask(showReport)
  const filteredReports = useMemo(() => (reports.data || []).filter((item: any) => {
    if (historyType !== 'all' && item.report_type !== historyType) return false
    if (historyType === 'single' && historyScoreId && item.score_id !== historyScoreId) return false
    return true
  }), [reports.data, historyType, historyScoreId])
  useEffect(() => { setStudentId(''); setScoreId(''); setHistoryScoreId(''); setActiveReport(null) }, [classId])
  useEffect(() => { setScoreId(''); setHistoryScoreId(''); setActiveReport(null) }, [studentId])
  useEffect(() => { if (reportType === 'periodic') setScoreId('') }, [reportType])
  useEffect(() => { if (historyType !== 'single') setHistoryScoreId('') }, [historyType])

  return <div className="space-y-6">
    <header><p className="eyebrow">TRACEABLE AI DIAGNOSTIC</p><h1 className="page-title">学生诊断报告</h1><p className="mt-2 text-sm text-text-muted">指定学生与实训记录，观察任务从提交到完成，并核对报告引用数据</p></header>
    <section className="railway-card grid gap-4 p-5 md:grid-cols-2 xl:grid-cols-5 xl:items-end">
      <Field label="授权班级"><select className="input-field" value={classId} onChange={(e) => setClassId(e.target.value)}><option value="">选择班级</option>{classes.data?.map((item: any) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field>
      <Field label="学生"><select className="input-field" value={studentId} disabled={!classId} onChange={(e) => setStudentId(e.target.value)}><option value="">选择学生</option>{students.data?.map((item: any) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field>
      <Field label="生成报告类型"><select className="input-field" value={reportType} onChange={(e) => setReportType(e.target.value as any)}><option value="single">单次实训诊断</option><option value="periodic">阶段综合诊断</option></select></Field>
      <Field label="生成依据记录"><select className="input-field" value={scoreId} disabled={reportType !== 'single' || !studentId} onChange={(e) => setScoreId(e.target.value)}><option value="">选择记录</option>{scores.data?.scores.map((item: any) => <option key={item.id} value={item.id}>{item.project_name} · {item.percentage}分</option>)}</select></Field>
      <button className="btn-primary" disabled={!studentId || (reportType === 'single' && !scoreId) || reportTask.create.isPending} onClick={() => reportTask.create.mutate({ student_id: studentId, report_type: reportType, score_id: reportType === 'single' ? scoreId : undefined })}>{reportTask.create.isPending ? '正在生成…' : '生成诊断报告'}</button>
    </section>
    <ReportTaskStatus task={reportTask.task} onView={() => reportTask.task?.report && showReport(reportTask.task.report)} />
    {studentId && <section className="railway-card grid gap-4 p-4 sm:grid-cols-2">
      <Field label="筛选历史报告类型"><select className="input-field" value={historyType} onChange={(e) => setHistoryType(e.target.value as any)}><option value="all">全部报告</option><option value="single">单次实训诊断</option><option value="periodic">阶段综合诊断</option></select></Field>
      <Field label="筛选关联实训记录"><select className="input-field" value={historyScoreId} disabled={historyType !== 'single'} onChange={(e) => setHistoryScoreId(e.target.value)}><option value="">全部单次记录</option>{scores.data?.scores.map((item: any) => <option key={item.id} value={item.id}>{item.project_name} · {item.percentage}分</option>)}</select></Field>
    </section>}
    <div className="grid gap-5 xl:grid-cols-[340px_1fr]">
      <section className="railway-card overflow-hidden"><div className="border-b border-railway-600/50 p-5"><h2 className="section-heading">历史报告</h2><p className="mt-1 text-xs text-text-muted">当前筛选 {filteredReports.length} 条</p></div><div className="divide-y divide-railway-600/50">{filteredReports.map((item: any) => <button key={item.id} className="w-full p-4 text-left hover:bg-railway-700/40" onClick={() => showReport(item)}><p className="font-medium text-text-primary">{item.title}</p><p className="mt-1 text-xs text-text-muted">{item.report_type === 'single' ? '单次实训诊断' : '阶段综合诊断'} · {new Date(item.generated_at).toLocaleString('zh-CN')}</p></button>)}{studentId && !filteredReports.length && <p className="p-5 text-sm text-text-muted">当前筛选条件下没有报告</p>}</div></section>
      <section ref={reportSectionRef} className="railway-card min-h-96 scroll-mt-6 p-6">{activeReport ? <><p className="eyebrow">DATA-BACKED REPORT</p><h2 className="section-heading">{activeReport.title}</h2><p className="mt-2 text-xs text-text-muted">{activeReport.report_type === 'single' ? '单次实训诊断' : '阶段综合诊断'} · {new Date(activeReport.generated_at).toLocaleString('zh-CN')}</p><article className="prose prose-invert prose-cyan mt-5 max-w-none text-text-secondary"><ReactMarkdown>{activeReport.content}</ReactMarkdown></article></> : <div className="flex min-h-80 items-center justify-center text-text-muted">选择历史报告或生成新的诊断报告</div>}</section>
    </div>
  </div>
}

function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label className="text-sm text-text-secondary"><span className="mb-2 block">{label}</span>{children}</label> }
