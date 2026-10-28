import { useState } from 'react'
import { api, getErrorMessage } from '../lib/api'

export default function DatabaseEvidence() {
  const [data,setData]=useState<any>(null)
  const [error,setError]=useState('')
  const [busy,setBusy]=useState(false)
  const check=async()=>{setBusy(true);setError('');try{setData((await api.get('/api/v1/release/source/evidence')).data)}catch(e){setError(getErrorMessage(e))}finally{setBusy(false)}}
  return <section className="railway-card space-y-4 p-5">
    <h2 className="section-heading">数据库联通与来源追溯</h2>
    <button className="btn-primary" disabled={busy} onClick={check}>检查 MySQL 连接与只读权限</button>
    {error&&<p role="alert">{error}</p>}
    {data&&<>
      <div className="grid gap-4 md:grid-cols-4">{[['源数据库',data.source_database.engine+' '+data.source_database.version],['连接状态',data.source_database.connected?'已联通':'失败'],['源账号权限',data.source_database.select_only_grants?'仅 SELECT（已核对授权）':'非纯只读，需处理'],['源记录数',data.source_database.row_count]].map(([label,value])=><div className="rounded border border-accent-cyan/30 p-4" key={label}><p className="text-sm text-text-secondary">{label}</p><p className="mt-2 text-xl">{value}</p></div>)}</div>
      <p>只读中间表：{data.source_database.table}；平台业务库：{data.business_database}（与源 MySQL 分离）</p>
      <h3>源表结构（实际读取）</h3><div className="flex flex-wrap gap-3">{data.source_database.columns.map((c:any)=><span className="rounded border p-2" key={c.name}>{c.name} · {c.type}</span>)}</div>
      <h3>最近增量同步</h3><p>状态：{data.last_run.status||'尚未同步'} · 时间：{data.last_run.time||'—'}</p><p>增量游标：{JSON.stringify(data.last_run.cursor||null)}</p>
      <h3>成绩来源追溯（最近 12 条）</h3>{data.records.map((r:any)=><details className="rounded border border-accent-cyan/20 p-3" key={r.record_id}><summary>{r.source_record_id} · {r.class_name||'班级见学生资料'} · {r.score}/{r.max_score} 分</summary><dl className="mt-3 grid grid-cols-2 gap-2 text-sm"><dt>来源系统</dt><dd>{r.source}</dd><dt>源记录唯一标识</dt><dd>{r.source_record_id}</dd><dt>同步批次</dt><dd>{r.batch_id}</dd><dt>原始完成时间</dt><dd>{r.completed_at}</dd><dt>平台实训记录</dt><dd>{r.record_id}</dd><dt>关联成绩</dt><dd>{r.score_id}</dd></dl></details>)}
    </>}
  </section>
}
