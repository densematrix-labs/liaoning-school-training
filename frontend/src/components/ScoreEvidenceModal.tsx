import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'

export default function ScoreEvidenceModal({ scoreId, onClose }: { scoreId: string; onClose: () => void }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['score-detail', scoreId],
    queryFn: async () => (await api.get(`/api/v1/scores/${scoreId}`)).data,
  })

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center bg-railway-900/90 p-3 backdrop-blur-sm" onClick={onClose}>
      <section className="glass-panel-bright max-h-[92vh] w-full max-w-5xl overflow-y-auto" onClick={(event) => event.stopPropagation()}>
        <header className="sticky top-0 z-10 flex items-start justify-between border-b border-railway-600/60 bg-railway-800/95 p-5 backdrop-blur">
          <div><p className="eyebrow">TRACEABLE SCORE EVIDENCE</p><h2 className="section-heading">单次实训成绩证据</h2></div>
          <button className="railway-button" onClick={onClose}>关闭</button>
        </header>
        {isLoading && <p className="p-8 text-text-muted">正在读取步骤证据…</p>}
        {error && <p className="m-6 alert-warning p-4">成绩明细加载失败</p>}
        {data && (
          <div className="space-y-6 p-5 sm:p-7">
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              <Metric label="学生" value={data.student_name || '—'} />
              <Metric label="班级" value={data.class_name || '—'} />
              <Metric label="实训项目" value={data.project_name || '—'} />
              <Metric label="总成绩" value={`${data.total_score}/${data.max_score}`} />
              <Metric label="源记录" value={data.source_record_id || '—'} compact />
              <Metric label="实训时间" value={data.source_completed_at ? new Date(data.source_completed_at).toLocaleString('zh-CN') : '—'} compact />
            </div>
            <div className={data.reconciliation_ok ? 'alert-success rounded p-4 text-sm' : 'alert-warning rounded p-4 text-sm'}>
              步骤汇总 {data.steps_total} 分，记录总分 {data.total_score} 分：{data.reconciliation_ok ? '核对一致' : '核对不一致'}
            </div>
            <div className="space-y-3">
              {data.details.map((step: any, index: number) => (
                <article key={step.step_id} className="rounded-lg border border-railway-600/60 bg-railway-800/55 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div><p className="text-xs text-text-muted">步骤 {index + 1} · {step.step_id}</p><h3 className="mt-1 font-semibold text-text-primary">{step.step_name}</h3></div>
                    <div className="text-right"><span className={step.passed ? 'text-status-success' : 'text-status-danger'}>{step.source_status}</span><p className="font-mono text-lg text-accent-cyan">{step.score}/{step.max_score}</p></div>
                  </div>
                  <div className="mt-4 grid gap-3 text-sm md:grid-cols-3">
                    <Info label="适用规则" value={`通过 ${step.applied_rule?.passed_score ?? step.max_score} 分 / 未通过 ${step.applied_rule?.failed_score ?? 0} 分`} />
                    <Info label="规则版本" value={`v${step.applied_rule?.rule_version ?? 1}`} />
                    <Info label="关联能力" value={step.related_ability_names?.join('、') || '未配置'} />
                  </div>
                  {step.reason && <p className="mt-3 text-xs text-status-warning">记录说明：{step.reason}</p>}
                </article>
              ))}
            </div>
          </div>
        )}
      </section>
    </div>
  )
}

function Metric({ label, value, compact = false }: { label: string; value: string; compact?: boolean }) {
  return <div className="metric-strip"><p>{label}</p><strong className={compact ? '!text-xs !leading-5 break-words text-accent-cyan' : '!text-xl !leading-tight break-words text-accent-cyan'}>{value}</strong></div>
}

function Info({ label, value }: { label: string; value: string }) {
  return <div><p className="text-xs uppercase tracking-wider text-text-muted">{label}</p><p className="mt-1 text-text-secondary">{value}</p></div>
}
