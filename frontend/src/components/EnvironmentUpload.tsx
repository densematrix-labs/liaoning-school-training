import ChineseFileInput from './ChineseFileInput'
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api, getErrorMessage } from '../lib/api'

export default function EnvironmentUpload({studentId}:{studentId:string}) {
  const [score,setScore]=useState(''),[lab,setLab]=useState(''),[file,setFile]=useState<File|null>(null)
  const [task,setTask]=useState<any>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false)
  const scores=useQuery({queryKey:['upload-scores',studentId],queryFn:async()=>(await api.get(`/api/v1/scores/student/${studentId}`,{params:{page_size:100}})).data,enabled:!!studentId})
  const labs=useQuery({queryKey:['upload-labs'],queryFn:async()=>(await api.get('/api/v1/environment/labs')).data})
  const status=useQuery({queryKey:['uploaded-environment-task',task?.id],queryFn:async()=>(await api.get(`/api/v1/environment/tasks/${task.id}`)).data,enabled:!!task?.id,refetchInterval:q=>['completed','failed'].includes((q.state.data as any)?.status)?false:2000})
  const submit=async()=>{
    setBusy(true);setError('')
    try {
      if(!file||file.size>10*1024*1024)throw new Error('图片大小校验失败：请选择不超过 10MB 的图片')
      if(!['image/jpeg','image/png','image/webp'].includes(file.type))throw new Error('图片格式校验失败：仅支持 JPEG、PNG、WebP')
      const image=await new Promise<string>((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result));reader.onerror=()=>reject(new Error('图片读取失败'));reader.readAsDataURL(file)})
      setTask((await api.post('/api/v1/environment/tasks',{student_id:studentId,score_id:score,lab_id:lab,image_base64:image})).data)
    } catch(e) {setError(e instanceof Error && !(e as any).response ? e.message : getErrorMessage(e))} finally {setBusy(false)}
  }
  return <section className="railway-card space-y-4 p-5"><h2 className="section-heading">上传实训现场图片</h2>
    {(scores.isError||labs.isError)&&<p role="alert">加载实训记录或实训室失败：{getErrorMessage(scores.error||labs.error)}<button type="button" className="btn-secondary ml-2" onClick={()=>{scores.refetch();labs.refetch()}}>重新加载</button></p>}
    <label>关联实训<select className="input-field" value={score} onChange={e=>setScore(e.target.value)}><option value="">选择已完成实训</option>{scores.data?.scores?.map((x:any)=><option key={x.id} value={x.id}>{x.project_name} · {x.training_completed_at||x.calculated_at}</option>)}</select></label>
    <label>对应实训室<select className="input-field" value={lab} onChange={e=>setLab(e.target.value)}><option value="">选择实训室</option>{labs.data?.map((x:any)=><option key={x.id} value={x.id}>{x.name}</option>)}</select></label>
    <ChineseFileInput aria-label="现场图片" type="file" accept="image/png,image/jpeg,image/webp" onChange={e=>setFile(e.target.files?.[0]??null)}/><button className="btn-primary" disabled={!score||!lab||!file||busy} onClick={submit}>提交环境检查</button>
    {error&&<p role="alert">{error}</p>}{task&&<div role="status" className="space-y-2 rounded border border-accent-cyan/30 p-4"><p>处理状态：{({pending:'已提交，等待处理',running:'正在分析',completed:'处理完成，已生成检查结果',failed:'处理失败，记录已保留'} as Record<string,string>)[status.data?.status||task.status] || task.status}{status.data?.error_message&&` · ${status.data.error_message}`}</p><p className="break-all text-xs">任务ID：{task.id}{status.data?.check_id&&` · 检查ID：${status.data.check_id}`}</p>{status.data?.status==='completed'&&status.data?.result&&<><p>AI 原始结果：{status.data.result.total_score}/100 · 待教师复核，不等同于人工最终结论</p><p className="text-sm">{status.data.result.summary}</p></>}</div>}
  </section>
}
