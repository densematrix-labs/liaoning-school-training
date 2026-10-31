import {useQuery} from '@tanstack/react-query'
import {useState} from 'react'
import {api} from '../lib/api'

const names:Record<string,string>={missing_rule:'缺少评分规则',unknown_step:'步骤无法匹配',incomplete_source:'源数据不完整'}
const states:Record<string,string>={exception:'异常',incomplete:'未完成',resolved:'已重新处理'}

export default function ScoringExceptions(){
  const [selected,setSelected]=useState('')
  const {data,isLoading,error,refetch}=useQuery({queryKey:['scoring-exceptions'],queryFn:async()=>(await api.get('/api/v1/release/scoring-exceptions')).data})
  const items=data?.items||[]
  const current=items.find((x:any)=>x.id===selected)
  return <section className="railway-card space-y-4 p-5">
    <h2 className="section-heading">计分异常与正式成绩核验</h2>
    
    <button className="btn-secondary" onClick={()=>refetch()}>刷新核验</button>
    {isLoading&&<p role="status">正在核验…</p>}{error&&<p role="alert">计分异常读取失败，请重试</p>}
    {!isLoading&&!error&&items.length===0&&<p>暂无计分异常记录</p>}
    <div className="space-y-2">{items.map((x:any)=><button key={x.id} className="block w-full rounded border border-railway-600/60 p-3 text-left" onClick={()=>setSelected(x.id)}>
      <strong>{x.source_record_id||'源记录编号缺失'}</strong> · {names[x.code]||x.code} · <span className="text-status-danger">{states[x.current_status]}</span>
    </button>)}</div>
    {current&&<article aria-label="计分异常详情" className="space-y-5 rounded border border-status-danger/50 p-5">
      <h3 className="text-lg font-semibold">{names[current.code]}</h3>
      <dl className="grid gap-4 md:grid-cols-2">{[['源记录 ID',current.source_record_id||'缺失'],['异常记录 ID',current.id],['成绩处理状态',states[current.current_status]],['正式成绩结果',current.formal_result],['正式成绩数量',String(current.formal_score_count)],['检查时间（UTC）',current.checked_at]].map(([label,value])=><div key={label}><dt className="text-xs text-text-muted">{label}</dt><dd className="mt-1 break-all">{value}</dd></div>)}</dl>
      <div className="rounded bg-railway-800/50 p-4"><p className="mt-2 text-status-danger">{current.reason}</p></div>
    </article>}
  </section>
}
