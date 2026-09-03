import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import ReactMarkdown from 'react-markdown'
import { api, getErrorMessage } from '../../lib/api'

interface ClassInfo {
  id: string
  name: string
  student_count: number
}

interface Student {
  id: string
  student_no: string
  name: string
}

interface Report {
  id: string
  title: string
  content: string
  report_type: 'single' | 'periodic'
  generated_at: string
  model?: string
}

export default function TeacherReports() {
  const [searchParams] = useSearchParams()
  const [selectedClass, setSelectedClass] = useState(searchParams.get('class_id') || '')
  const [selectedStudent, setSelectedStudent] = useState('')
  const [reportType, setReportType] = useState<'single' | 'periodic'>('single')
  const [generatedReport, setGeneratedReport] = useState<Report | null>(null)

  const { data: classes = [] } = useQuery<ClassInfo[]>({
    queryKey: ['teacher-classes'],
    queryFn: async () => (await api.get('/api/v1/students/classes')).data,
  })

  const { data: students = [], isFetching: studentsLoading } = useQuery<Student[]>({
    queryKey: ['class-students', selectedClass],
    queryFn: async () => (await api.get(`/api/v1/students/classes/${selectedClass}/students`)).data,
    enabled: Boolean(selectedClass),
  })

  const { data: reports = [] } = useQuery<Report[]>({
    queryKey: ['teacher-student-reports', selectedStudent],
    queryFn: async () => (await api.get(`/api/v1/reports/student/${selectedStudent}`)).data,
    enabled: Boolean(selectedStudent),
  })

  useEffect(() => {
    setGeneratedReport(null)
  }, [selectedClass, selectedStudent])

  const generateMutation = useMutation({
    mutationFn: async () => (await api.post('/api/v1/reports/generate', {
      student_id: selectedStudent,
      report_type: reportType,
    })).data as Report,
    onSuccess: (report) => setGeneratedReport(report),
  })

  const activeReport = generatedReport || reports[0]
  const errorMessage = generateMutation.error
    ? getErrorMessage(generateMutation.error, '模型服务暂时不可用，请稍后重试')
    : ''

  return (
    <div className="space-y-6">
      <section className="role-intro teacher-intro">
        <div>
          <p className="eyebrow">AI DIAGNOSTIC</p>
          <h2>学生诊断报告</h2>
          <p>基于真实成绩与能力数据生成，教师可在授权班级范围内查看</p>
        </div>
      </section>

      <section className="railway-card p-6">
        <div className="grid gap-4 lg:grid-cols-[1fr_1fr_1fr_auto] lg:items-end">
          <Field label="班级">
            <select value={selectedClass} onChange={(event) => { setSelectedClass(event.target.value); setSelectedStudent('') }} className="input-field">
              <option value="">选择负责班级</option>
              {classes.map((item) => <option key={item.id} value={item.id}>{item.name}（{item.student_count}人）</option>)}
            </select>
          </Field>
          <Field label="学生">
            <select value={selectedStudent} onChange={(event) => setSelectedStudent(event.target.value)} className="input-field" disabled={!selectedClass || studentsLoading}>
              <option value="">{studentsLoading ? '加载中…' : '选择学生'}</option>
              {students.map((item) => <option key={item.id} value={item.id}>{item.name}（{item.student_no}）</option>)}
            </select>
          </Field>
          <Field label="报告类型">
            <select value={reportType} onChange={(event) => setReportType(event.target.value as 'single' | 'periodic')} className="input-field">
              <option value="single">最近一次实训诊断</option>
              <option value="periodic">阶段综合诊断</option>
            </select>
          </Field>
          <button onClick={() => generateMutation.mutate()} disabled={!selectedStudent || generateMutation.isPending} className="btn-primary min-w-32">
            {generateMutation.isPending ? '模型分析中…' : '生成报告'}
          </button>
        </div>
        {errorMessage && <p role="alert" className="mt-4 rounded-md border border-status-danger/40 bg-status-danger/10 p-3 text-sm text-status-danger">{errorMessage}</p>}
      </section>

      {selectedStudent ? (
        <div className="grid gap-6 xl:grid-cols-[320px_1fr]">
          <section className="railway-card overflow-hidden">
            <div className="border-b border-railway-600/50 p-5"><p className="eyebrow">REPORT HISTORY</p><h3 className="section-heading">历史报告</h3></div>
            <div className="divide-y divide-railway-600/40">
              {reports.map((report) => (
                <button key={report.id} onClick={() => setGeneratedReport(report)} className="w-full p-4 text-left transition-colors hover:bg-railway-700/40">
                  <p className="font-medium text-text-primary">{report.title}</p>
                  <p className="mt-1 text-xs text-text-muted">{new Date(report.generated_at).toLocaleString('zh-CN')}</p>
                </button>
              ))}
              {!reports.length && <p className="p-5 text-sm text-text-muted">该学生尚未生成报告</p>}
            </div>
          </section>

          <section className="railway-card min-h-80 p-6">
            {activeReport ? (
              <>
                <div className="mb-5 border-b border-railway-600/50 pb-4">
                  <p className="eyebrow">{activeReport.report_type === 'single' ? 'SINGLE SESSION' : 'PERIODIC REVIEW'}</p>
                  <h3 className="section-heading">{activeReport.title}</h3>
                  <p className="mt-1 text-xs text-text-muted">模型：{activeReport.model || 'DenseMatrix LLM Proxy'}</p>
                </div>
                <article className="prose prose-invert prose-cyan max-w-none text-text-secondary"><ReactMarkdown>{activeReport.content}</ReactMarkdown></article>
              </>
            ) : <div className="flex min-h-64 items-center justify-center text-text-muted">选择报告类型后生成第一份诊断</div>}
          </section>
        </div>
      ) : (
        <section className="railway-card p-12 text-center"><p className="font-display text-lg text-text-primary">请先选择班级和学生</p><p className="mt-2 text-sm text-text-muted">报告只使用该学生已入库的成绩和能力数据</p></section>
      )}
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block text-sm font-medium text-text-secondary"><span className="mb-2 block">{label}</span>{children}</label>
}
