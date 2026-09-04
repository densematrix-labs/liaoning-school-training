import { useEffect, useState } from 'react'
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
  const [activeReport, setActiveReport] = useState<any>(null)
  const classes = useQuery({ queryKey: ['teacher-classes'], queryFn: async () => (await api.get('/api/v1/students/classes')).data })
  const students = useQuery({ queryKey: ['class-students', classId], queryFn: async () => (await api.get(`/api/v1/students/classes/${classId}/students`)).data, enabled: Boolean(classId) })
  const scores = useQuery({ queryKey: ['teacher-report-scores', studentId], queryFn: async () => (await api.get(`/api/v1/scores/student/${studentId}`, { params: { page_size: 100 } })).data, enabled: Boolean(studentId) })
  const reports = useQuery({ queryKey: ['teacher-student-reports', studentId], queryFn: async () => (await api.get(`/api/v1/reports/student/${studentId}`)).data, enabled: Boolean(studentId) })
  const reportTask = useReportTask((report) => setActiveReport(report))
  useEffect(() => { setStudentId(''); setScoreId(''); setActiveReport(null) }, [classId])
  useEffect(() => { setScoreId(''); setActiveReport(null) }, [studentId])

  return <div className="space-y-6">
    <header><p className="eyebrow">TRACEABLE AI DIAGNOSTIC</p><h1 className="page-title">学生诊断报告</h1><p className="mt-2 text-sm text-text-muted">指定学生与实训记录，观察任务从提交到完成，并核对报告引用数据</p></header>
    <section className="railway-card grid gap-4 p-5 md:grid-cols-2 xl:grid-cols-5 xl:items-end">
      <Field label="授权班级"><select className="input-field" value={classId} onChange={(e) => setClassId(e.target.value)}><option value="">选择班级</option>{classes.data?.map((item: any) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field>
      <Field label="学生"><select className="input-field" value={studentId} disabled={!classId} onChange={(e) => setStudentId(e.target.value)}><option value="">选择学生</option>{students.data?.map((item: any) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field>
      <Field label="报告类型"><select className="input-field" value={reportType} onChange={(e) => setReportType(e.target.value as any)}><option value="single">单次实训诊断</option><option value="periodic">阶段综合诊断</option></select></Field>
      <Field label="单次实训记录"><select className="input-field" value={scoreId} disabled={reportType !== 'single' || !studentId} onChange={(e) => setScoreId(e.target.value)}><option value="">选择记录</option>{scores.data?.scores.map((item: any) => <option key={item.id} value={item.id}>{item.project_name} · {item.percentage}分</option>)}</select></Field>
      <button className="btn-primary" disabled={!studentId || (reportType === 'single' && !scoreId) || reportTask.create.isPending} onClick={() => reportTask.create.mutate({ student_id: studentId, report_type: reportType, score_id: reportType === 'single' ? scoreId : undefined })}>提交生成任务</button>
    </section>
    <ReportTaskStatus task={reportTask.task} />
    <div className="grid gap-5 xl:grid-cols-[340px_1fr]">
      <section className="railway-card overflow-hidden"><div className="border-b border-railway-600/50 p-5"><h2 className="section-heading">报告记录</h2></div><div className="divide-y divide-railway-600/50">{reports.data?.map((item: any) => <button key={item.id} className="w-full p-4 text-left hover:bg-railway-700/40" onClick={() => setActiveReport(item)}><p className="font-medium text-text-primary">{item.title}</p><p className="mt-1 text-xs text-text-muted">{new Date(item.generated_at).toLocaleString('zh-CN')}</p></button>)}{studentId && !reports.data?.length && <p className="p-5 text-sm text-text-muted">该学生暂无报告</p>}</div></section>
      <section className="railway-card min-h-96 p-6">{activeReport ? <><p className="eyebrow">DATA-BACKED REPORT</p><h2 className="section-heading">{activeReport.title}</h2><article className="prose prose-invert prose-cyan mt-5 max-w-none text-text-secondary"><ReactMarkdown>{activeReport.content}</ReactMarkdown></article></> : <div className="flex min-h-80 items-center justify-center text-text-muted">选择历史报告或提交新的生成任务</div>}</section>
    </div>
  </div>
}

function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label className="text-sm text-text-secondary"><span className="mb-2 block">{label}</span>{children}</label> }
