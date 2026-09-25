import ReactMarkdown from 'react-markdown'

export default function ReportDocument({
  report,
  onDownload,
}: {
  report: any
  onDownload?: () => void
}) {
  if (!report) {
    return <div className="flex min-h-[520px] items-center justify-center px-8 text-center text-sm text-text-muted">选择一份历史报告，或生成新的诊断报告</div>
  }

  const generatedAt = report.generated_at ? new Date(report.generated_at).toLocaleString('zh-CN') : '—'
  const reportLabel = report.report_type === 'single' ? '单次实训诊断' : '阶段综合诊断'

  return (
    <article className="report-shell">
      <header className="report-cover">
        <div className="report-cover-grid" aria-hidden="true" />
        <div className="relative z-10">
          <div className="flex flex-wrap items-start justify-between gap-5">
            <div>
              <p className="eyebrow !text-accent-cyan">AI DIAGNOSTIC DOSSIER</p>
              <h2 className="mt-3 max-w-3xl font-display text-2xl font-semibold leading-tight text-text-primary md:text-3xl">{report.title}</h2>
            </div>
            <div className="report-seal"><span>AI</span><small>分析归档</small></div>
          </div>
          <div className="mt-8 flex flex-wrap gap-2 text-xs">
            <span className="report-chip">{reportLabel}</span>
            <span className="report-chip">生成时间 {generatedAt}</span>
            {report.score_id && <span className="report-chip">关联实训 {String(report.score_id).slice(-8)}</span>}
            {report.source && <span className="report-chip">模型来源 {report.source}</span>}
          </div>
          {onDownload && <button className="railway-button mt-5" onClick={onDownload}>下载 Word</button>}
        </div>
      </header>
      <div className="report-body">
        <div className="report-document">
          <ReactMarkdown>{report.content || '报告内容为空'}</ReactMarkdown>
        </div>
      </div>
      <footer className="report-footer">
        <span>智能实训能力评估平台</span>
        <span>报告编号 · {String(report.id || '').slice(-12) || '—'}</span>
      </footer>
    </article>
  )
}
