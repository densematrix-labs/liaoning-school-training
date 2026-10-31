import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { api } from '../lib/api'
import ScoreEvidenceModal from './ScoreEvidenceModal'
import ReportDocument from './ReportDocument'
import EnvironmentScoreLink from './EnvironmentScoreLink'

export default function StudentBusinessDetail({ data }: { data: any }) {
  const [scoreId, setScoreId] = useState('')
  const [reportId, setReportId] = useState('')
  const [checkId, setCheckId] = useState('')
  const sid = data.student.id
  const trend = useQuery({queryKey:['detail-trend',sid],queryFn:async()=>(await api.get(`/api/v1/abilities/student/${sid}/trend`)).data})
  const report = useQuery({queryKey:['detail-report',reportId],enabled:!!reportId,queryFn:async()=>(await api.get(`/api/v1/reports/${reportId}`)).data})
  const check = useQuery({queryKey:['detail-check',checkId],enabled:!!checkId,queryFn:async()=>(await api.get(`/api/v1/environment/checks/${checkId}`)).data})
  const download = async () => {const r=await api.get(`/api/v1/reports/${reportId}/download.docx`,{responseType:'blob'}); const u=URL.createObjectURL(r.data); const a=document.createElement('a');a.href=u;a.download='诊断报告.docx';a.click();URL.revokeObjectURL(u)}
  return <div className="space-y-6" aria-label="同一学生业务详情">
    <p>学生：{data.student.name} · {data.student.class_name} · 学号 {data.student.student_no} · 学生ID {sid}</p>
    <section className="railway-card p-5"><h3 className="section-heading">历史成绩与单次步骤展开</h3>{data.score_summary.scores.map((s:any)=><button className="btn-secondary m-2" key={s.id} onClick={()=>setScoreId(s.id)}>{s.project_name} · {s.total_score}/{s.max_score} · 查看步骤明细</button>)}</section>
    <section className="railway-card p-5" aria-label="学生能力变化"><h3 className="section-heading">能力变化趋势</h3><div className="h-80"><ResponsiveContainer><LineChart data={(trend.data?.points||[]).map((p:any)=>({...p.abilities,date:new Date(p.date).toLocaleDateString('zh-CN')}))}><XAxis dataKey="date"/><YAxis domain={[0,100]}/><Tooltip/><Legend/>{trend.data?.abilities?.map((a:any,i:number)=><Line key={a.id} isAnimationActive={false} dataKey={a.id} name={a.name} strokeWidth={2.5} strokeDasharray={['','6 4','2 3','12 3 3 3','3 6','8 4'][i%6]} stroke={['#ffd166','#f69d47','#ff69b4','#fff0da','#a9ff68','#dab3ff'][i%6]}/>)}</LineChart></ResponsiveContainer></div></section>
    <section className="railway-card p-5" aria-label="学生环境结果"><h3 className="section-heading">环境检查结果</h3>{data.environment_checks.map((x:any)=><button className="btn-secondary m-2" key={x.id} onClick={()=>setCheckId(x.id)}>{x.checked_at} · AI原始{x.total_score}分 · 打开检查 {x.id}</button>)}{check.data&&<div className="mt-4 space-y-3"><EnvironmentScoreLink item={check.data}/><p>检查ID {check.data.id} · 状态 {({pending:'待人工复核',needs_review:'待人工复核',modified:'已修改复核',confirmed:'已确认',rejected:'已驳回'} as any)[check.data.review_status]||'待人工复核'}</p><p>AI原始分 {check.data.total_score} · 最终分 {['confirmed','modified'].includes(check.data.review_status)?check.data.final_score:'待人工复核'}</p><p>{check.data.summary}</p>{Object.entries(check.data.details||{}).map(([k,v]:any)=><p key={k}>{({equipment_placement:'设备摆放',surface_cleanliness:'台面整洁',floor_cleanliness:'地面整洁',environmental_hygiene:'遗留杂物与环境卫生',safety_compliance:'安全规范'} as any)[k]||k}：{v.score}/{v.max_score} · {v.issues?.join('；')}</p>)}<p>复核备注：{check.data.review_note||'尚未复核'}</p></div>}</section>
    <section aria-label="学生诊断正文"><h3 className="section-heading">诊断报告正文</h3>{data.reports.map((r:any)=><button className="btn-secondary m-2" key={r.id} onClick={()=>setReportId(r.id)}>{r.title} · 打开正文</button>)}{report.data&&<ReportDocument report={report.data} onDownload={download}/>}</section>
    {scoreId&&<ScoreEvidenceModal scoreId={scoreId} onClose={()=>setScoreId('')}/>}
  </div>
}
