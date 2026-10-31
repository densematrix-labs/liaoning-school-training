import { useState } from 'react'
import { api, getErrorMessage } from '../lib/api'

const value = (v: any) => v === null || v === undefined || v === '' ? '未采集 / 未留存，无法判断' : typeof v === 'boolean' ? v ? '通过' : '未通过' : String(v)
const category: Record<string, string> = {equipment_placement: '器材摆放', surface_cleanliness: '台面整洁', safety_compliance: '安全规范', environmental_hygiene: '环境卫生'}
export default function ReportSources({reportId}: {reportId: string}) {
  const [data, setData] = useState<any>(null)
  const [error, setError] = useState('')
  const [open, setOpen] = useState(false)
  const load = async () => { setOpen(true); setData(null); setError(''); try { setData((await api.get(`/api/v1/reports/${reportId}/sources`)).data) } catch(e) { setError(getErrorMessage(e)) } }
  return <div className="px-6 py-5">
    <button className="btn-secondary" onClick={load}>查看同一报告的源数据对照</button>
    {open && <section role="dialog" aria-label="报告源数据对照" className="fixed inset-0 z-50 overflow-y-auto bg-railway-900 p-6 text-text-primary">
      <div className="mx-auto max-w-[1600px] space-y-5">
        <div className="flex items-center justify-between"><h2 className="section-heading">报告源数据对照</h2><button className="btn-secondary" onClick={() => setOpen(false)}>关闭对照</button></div>
        {error && <p role="alert">{error}</p>}{!data && !error && <p>正在读取授权范围内的源记录…</p>}
        {data && <>
          <header className="railway-card space-y-2 p-4"><strong>{data.student_name} · {data.report_reference}</strong><p>生成时间 UTC：{data.generated_at} · 报告ID：{data.report_id}</p>{data.records.map((r:any) => <p className="text-xs" key={r.score_id}>关联记录 {r.record_reference} · 实训时间 UTC {r.completed_at} · 成绩ID {r.score_id}</p>)}</header>
          <section aria-label="报告学生成绩逐步骤对照" className="railway-card p-4"><h3 className="section-heading mb-3">学生、成绩与逐步骤：报告输入快照 ↔ 当前源数据</h3><table className="w-full text-left text-sm"><thead><tr><th>字段 / 步骤</th><th>报告生成时输入</th><th>当前业务源数据</th><th>逐项核对</th></tr></thead><tbody>{data.rows.map((r:any,i:number) => <tr className="border-b border-railway-600/40" key={i}><td className="py-1">{r.field}</td><td>{value(r.report_input)}</td><td>{value(r.source)}</td><td>{r.status}</td></tr>)}</tbody></table></section>
          <section aria-label="报告全部能力源数据对照" className="railway-card p-4"><h3 className="section-heading mb-3">全部大类能力：名称、达成结果、阈值及状态</h3><p className="mb-2 text-xs">{data.student_name} · {data.report_reference} · 当前画像参与 {data.history_scope?.selected_records ?? '未留存'} 条历史；{data.history_scope?.date_from} 至 {data.history_scope?.date_to}。</p><table className="w-full text-left text-sm"><thead><tr><th>能力名称</th><th>报告得分 / 达标分</th><th>当前得分 / 达标分</th><th>达标状态</th><th>核对</th></tr></thead><tbody>{data.abilities.map((r:any) => <tr className="border-b border-railway-600/40" key={r.name}><td className="py-2">{r.name}</td><td>{value(r.value)} / {value(r.threshold)}</td><td>{value(r.source_value)} / {value(r.source_threshold)}</td><td>{r.status}</td><td>{r.comparison}</td></tr>)}</tbody></table>{!data.abilities.length && <p>能力数据未采集，无法判断达成情况。</p>}</section>
          <section aria-label="报告关联环境检查源数据" className="railway-card space-y-3 p-4"><h3 className="section-heading">环境检查：报告输入与同成绩关联记录</h3><p>{data.environment_status}</p><p>报告输入：{data.input_environment.length ? data.input_environment.map((r:any) => `${value(r.total_score)} 分 · ${r.review_status}`).join('；') : '无关联环境数据，无法判断是否达标'}</p>{data.environment.map((r:any) => <div key={r.id} className="grid gap-4 md:grid-cols-[260px_1fr]"><div>{r.image && <img className="max-h-56 w-full object-contain" src={r.image} alt="同成绩环境检查原始上传图"/>}</div><div><p>检查ID：{r.id}</p><p>关联成绩ID：{r.score_id}</p><p>检查时间 UTC：{r.checked_at} · 源结果 {value(r.score)} 分 · {r.review_status}</p><p>{r.summary}</p>{Object.entries(r.details || {}).filter(([k,v]:any) => !k.startsWith("__") && v && typeof v === "object" && !Array.isArray(v)).map(([k,v]:any) => <p className="text-xs" key={k}>{category[k] || k}：{value(v.score)} 分；{(v.issues || []).join('；')}</p>)}</div></div>)}</section>
        </>}
      </div>
    </section>}
  </div>
}
