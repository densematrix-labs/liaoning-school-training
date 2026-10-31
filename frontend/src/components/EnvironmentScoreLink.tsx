import { useQuery } from '@tanstack/react-query'
import { api, getErrorMessage } from '../lib/api'
export default function EnvironmentScoreLink({item}:{item:any}) {
 const s=useQuery({queryKey:['environment-independent-score',item.score_id],queryFn:async()=>(await api.get('/api/v1/scores/'+item.score_id)).data,enabled:!!item.score_id})
 return <section className="rounded border border-accent-cyan/30 p-3 space-y-1 text-xs" aria-label="同次实训独立计分对照"><strong>同次实训：成绩与环境分别处理</strong><p>检查ID：{item.id}</p><p>成绩ID：{item.score_id||'未关联'} · 实训记录：{item.record_reference||'未留存'}</p><p>项目：{item.project_name} · 实训室ID：{item.lab_id}</p>{s.isError?<p role="alert">{getErrorMessage(s.error)}</p>:<p>操作成绩：{s.data?.total_score??'读取中'} / {s.data?.max_score??'…'} · 环境AI原始分：{item.total_score}/100</p>}<p>环境状态：{({confirmed:'已确认',modified:'已修改复核',rejected:'已驳回',needs_review:'无法判读或低置信，待人工复核'} as Record<string,string>)[item.review_status]||'待教师复核'}；环境分不并入操作成绩。</p></section>
}
