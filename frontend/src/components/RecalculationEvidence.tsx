import {useQuery} from '@tanstack/react-query'
import {api} from '../lib/api'
export default function RecalculationEvidence({sample}:{sample:any}){
 const score=useQuery({queryKey:['recalculated-score',sample.score_id,sample.rule_version],queryFn:async()=>(await api.get(`/api/v1/scores/${sample.score_id}`)).data})
 const ability=useQuery({queryKey:['recalculated-ability',sample.student_id,sample.rule_version],queryFn:async()=>(await api.get(`/api/v1/abilities/student/${sample.student_id}`)).data})
 return <section className="railway-card space-y-3 p-4" aria-label="指定记录重算结果依据"><h3 className="section-heading">指定记录新步骤分、适用映射与能力结果</h3><p>成绩ID：{sample.score_id} · 学生ID：{sample.student_id} · 源记录：{sample.source_record_id} · 规则v{sample.rule_version}</p><p>原总分 {sample.before_total} → 新总分 {sample.after_total}/{sample.max_score}</p>{score.data?.details?.map((s:any)=><p key={s.step_id}>{s.step_name} · {s.source_status} · {s.score}/{s.max_score} · 规则v{s.applied_rule?.rule_version} · 关联 {s.related_ability_names?.join('、')}</p>)}<h4>重算后大类能力值</h4>{ability.data?.radar_data?.map((a:any)=><p key={a.ability_id}>{a.name}：{a.score} · 达标阈值{a.threshold} · {a.score>=a.threshold?'达标':'未达标'}</p>)}</section>
}
