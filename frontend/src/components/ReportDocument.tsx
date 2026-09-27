import ReactMarkdown from 'react-markdown'
import { Link } from 'react-router-dom'
import { useAuthStore } from '../store/auth'

const internalCodePattern = /\b(?:step|sa|ma)-[a-z0-9-]+\b/gi
const uuidPattern = /\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b/gi
const shortInternalIdPattern = /\b(?=[0-9a-f]{8}\b)(?=[0-9a-f]*[a-f])[0-9a-f]{8}\b/gi
const modelLinePattern = /模型来源|模型供应商|model\s*(?:name|source|provider)|provider|bailian|dashscope|openai|gemini|qwen|\bllm\b/i

export function sanitizeReportText(value: string, studentName = '学生') {
  return (value || '')
    .replace(/匿名学员/g, studentName)
    .replace(/学员-[A-Za-z0-9_-]+/g, studentName)
    .replace(internalCodePattern, '相关业务项')
    .replace(uuidPattern, '内部记录')
    .replace(shortInternalIdPattern, '内部记录')
    .split('\n')
    .filter((line) => !modelLinePattern.test(line))
    .join('\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

export default function ReportDocument({
  report,
  onDownload,
}: {
  report: any
  onDownload?: () => void
}) {
  const { user } = useAuthStore()
  if (!report) {
    return <div className="flex min-h-[520px] items-center justify-center px-8 text-center text-sm text-text-muted">选择一份历史报告，或生成新的诊断报告</div>
  }

  const generatedAt = report.generated_at ? new Date(report.generated_at).toLocaleString('zh-CN') : '—'
  const trainingAt = report.training_completed_at ? new Date(report.training_completed_at).toLocaleString('zh-CN') : ''
  const reportLabel = report.report_type === 'single' ? '单次实训诊断' : '阶段综合诊断'
  const studentName = report.student_name || user?.name || '学生'
  const safeTitle = sanitizeReportText(report.title || reportLabel, studentName)
  const safeContent = sanitizeReportText(report.content || '报告内容为空', studentName)
  const scorePath = report.score_id
    ? user?.role === 'student'
      ? `/scores?score_id=${encodeURIComponent(report.score_id)}`
      : `/class-scores?class_id=${encodeURIComponent(report.class_id || '')}&student_id=${encodeURIComponent(report.student_id || '')}&score_id=${encodeURIComponent(report.score_id)}`
    : ''

  return (
    <article className="report-shell">
      <header className="report-cover">
        <div className="report-cover-grid" aria-hidden="true" />
        <div className="relative z-10">
          <div className="flex flex-wrap items-start justify-between gap-5">
            <div>
              <p className="eyebrow !text-accent-cyan">诊断分析档案</p>
              <h2 className="mt-3 max-w-3xl font-display text-2xl font-semibold leading-tight text-text-primary md:text-3xl">{safeTitle}</h2>
            </div>
            <div className="report-seal"><span>诊断</span><small>分析归档</small></div>
          </div>
          <div className="mt-8 flex flex-wrap gap-2 text-xs">
            <span className="report-chip">{reportLabel}</span>
            <span className="report-chip">生成时间 {generatedAt}</span>
            {scorePath && <Link className="report-chip transition hover:border-accent-cyan hover:text-accent-cyan" to={scorePath}>关联实训 {report.project_name || '查看成绩详情'}{trainingAt ? ` · ${trainingAt}` : ''} →</Link>}
          </div>
          {onDownload && <button className="railway-button mt-5" onClick={onDownload}>下载 Word</button>}
        </div>
      </header>
      <div className="report-body">
        <div className="report-document">
          <ReactMarkdown>{safeContent}</ReactMarkdown>
        </div>
      </div>
      <footer className="report-footer">
        <span>智能实训能力评估平台</span>
        <span>报告编号 · {report.report_reference || '—'}</span>
      </footer>
    </article>
  )
}
