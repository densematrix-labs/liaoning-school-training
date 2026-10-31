import {useQuery} from '@tanstack/react-query'
import {api} from '../lib/api'
const total=(d:any)=>Object.values(d||{}).reduce((s:number,v:any)=>s+(typeof v?.score==='number'?v.score:0),0)
const status=(s:string)=>({pending:'待人工复核',needs_review:'待人工复核',modified:'已修改复核',confirmed:'已确认',rejected:'已驳回'} as any)[s]||s
export default function EnvironmentReviewHistory({item}:{item:any}){
 const q=useQuery({queryKey:['review-history',item.id,item.reviewed_at],queryFn:async()=>(await api.get(`/api/v1/environment/checks/${item.id}/review-history`)).data})
 return <section className="railway-card space-y-3 p-5" aria-label="环境复核前后历史"><h3 className="section-heading">复核前后与已保存备注</h3><p>检查ID：{item.id} · AI原始 {item.total_score} · 人工最终 {item.reviewed_at?item.final_score:'尚未复核'} · {status(item.review_status||'pending')}</p>{q.data?.map((x:any)=><article className="rounded border border-accent-cyan/30 p-3" key={x.id}><p>审计ID {x.id} · {x.actor_name||x.actor_id} · {x.created_at} UTC</p><p>旧状态：{status(x.before?.status||'pending')} · 旧分数：{total(x.before?.details)}</p><p>新状态：{status(x.after?.status)} · 新分数：{total(x.after?.reviewed_details)}</p><p>已保存备注：{x.after?.note||'无'}</p><p>复核总结：{x.after?.reviewed_summary}</p></article>)}{q.data?.length===0&&<p>尚未产生人工复核记录；原始AI结果保留。</p>}</section>
}
