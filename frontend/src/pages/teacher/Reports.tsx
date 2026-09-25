import { useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import AbilityRadar from '../../components/AbilityRadar'
import ReportDocument from '../../components/ReportDocument'
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
  const ability = useQuery({ queryKey: ['teacher-report-ability', studentId], queryFn: async () => (await api.get(`/api/v1/abilities/student/${studentId}`)).data, enabled: Boolean(studentId) })
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
  const selectedStudent = students.data?.find((item: any) => item.id === studentId)
  useEffect(() => { setStudentId(''); setScoreId(''); setHistoryScoreId(''); setActiveReport(null) }, [classId])
  useEffect(() => { setScoreId(''); setHistoryScoreId(''); setActiveReport(null) }, [studentId])
  useEffect(() => { if (reportType === 'periodic') setScoreId('') }, [reportType])
  useEffect(() => { if (historyType !== 'single') setHistoryScoreId('') }, [historyType])

  return <div className="space-y-6">
    <header className="role-intro teacher-intro">
      <div><p className="eyebrow">AI DIAGNOSTIC WORKBENCH</p><h1 className="page-title">学生诊断工作台</h1><p>能力画像、实训证据与结构化诊断报告在同一屏完成核对</p></div>
      <div className="flex gap-6 text-right"><HeaderMetric label="历史报告" value={studentId ? filteredReports.length : '—'} /><HeaderMetric label="能力达标" value={ability.data ? `${ability.data.graduation_ready_count}/${ability.data.graduation_total_count}` : '—'} /></div>
    </header>

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

    <div className="grid items-start gap-5 xl:grid-cols-[300px_minmax(0,1fr)_360px]">
      <section className="railway-card overflow-hidden xl:sticky xl:top-28">
        <div className="border-b border-railway-600/50 p-5"><p className="eyebrow">REPORT ARCHIVE</p><h2 className="section-heading">{selectedStudent ? `${selectedStudent.name}的报告` : '历史报告'}</h2><p className="mt-1 text-xs text-text-muted">当前筛选 {filteredReports.length} 条</p></div>
        <div className="max-h-[620px] divide-y divide-railway-600/50 overflow-y-auto">{filteredReports.map((item: any) => <button key={item.id} className={`w-full p-4 text-left transition hover:bg-railway-700/50 ${activeReport?.id === item.id ? 'bg-accent-electric/10' : ''}`} onClick={() => showReport(item)}><span className={item.report_type === 'single' ? 'text-[10px] text-accent-cyan' : 'text-[10px] text-status-warning'}>{item.report_type === 'single' ? '单次诊断' : '阶段诊断'}</span><p className="mt-1 font-medium text-text-primary">{item.title}</p><p className="mt-2 font-mono text-[10px] text-text-muted">{new Date(item.generated_at).toLocaleString('zh-CN')}</p></button>)}{studentId && !filteredReports.length && <p className="p-5 text-sm text-text-muted">当前筛选条件下没有报告</p>}{!studentId && <p className="p-5 text-sm text-text-muted">选择班级和学生后载入报告档案</p>}</div>
      </section>

      <section ref={reportSectionRef} className="min-w-0 scroll-mt-28">
        <ReportDocument report={activeReport} onDownload={activeReport ? () => downloadReport(activeReport.id) : undefined} />
      </section>

      <aside className="space-y-5 xl:sticky xl:top-28">
        <AbilityRadar items={ability.data?.radar_data || []} title={selectedStudent ? `${selectedStudent.name} · 能力画像` : '学生能力画像'} description="报告结论应与能力证据和毕业达标线保持一致" compact />
        {ability.data && <section className="railway-card p-5"><p className="eyebrow">DIAGNOSTIC SIGNALS</p><h2 className="section-heading">诊断信号</h2><div className="mt-4 grid gap-3"><Signal label="综合能力" value={`${ability.data.total_score || 0} 分`} tone="cyan" /><Signal label="优势能力" value={ability.data.strongest_ability || '—'} tone="good" /><Signal label="薄弱能力" value={ability.data.weakest_ability || '—'} tone="warn" /></div></section>}
      </aside>
    </div>
  </div>
}

function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label className="text-sm text-text-secondary"><span className="mb-2 block">{label}</span>{children}</label> }
function HeaderMetric({ label, value }: { label: string; value: string | number }) { return <div><p className="text-[10px] uppercase tracking-widest text-text-muted">{label}</p><strong className="mt-1 block font-mono text-2xl text-status-warning">{value}</strong></div> }
function Signal({ label, value, tone }: { label: string; value: string; tone: 'cyan' | 'good' | 'warn' }) { return <div className="rounded border border-railway-600/60 bg-railway-700/35 p-3"><p className="text-[10px] text-text-muted">{label}</p><p className={`mt-1 font-medium ${tone === 'good' ? 'text-status-success' : tone === 'warn' ? 'text-status-warning' : 'text-accent-cyan'}`}>{value}</p></div> }

async function downloadReport(reportId: string) {
  const response = await api.get(`/api/v1/reports/${reportId}/download.doc`, { responseType: 'blob' })
  const url = URL.createObjectURL(response.data)
  const link = document.createElement('a')
  link.href = url
  link.download = `diagnostic-report-${reportId}.doc`
  link.click()
  URL.revokeObjectURL(url)
}
