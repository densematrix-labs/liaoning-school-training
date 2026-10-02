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
      if(!file||file.size>10*1024*1024)throw new Error('请选择不超过 10MB 的图片')
      const image=await new Promise<string>((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result));reader.onerror=()=>reject(new Error('图片读取失败'));reader.readAsDataURL(file)})
      setTask((await api.post('/api/v1/environment/tasks',{student_id:studentId,score_id:score,lab_id:lab,image_base64:image})).data)
    } catch(e) {setError(getErrorMessage(e))} finally {setBusy(false)}
  }
  return <section className="railway-card space-y-4 p-5"><h2 className="section-heading">上传实训现场图片</h2><p className="text-sm text-text-muted">选择对应实训及实训室。系统与标准图片对比，结果由教师复核；任务失败可重新提交。仅检查图片中可见的环境状态。</p>
    <label>关联实训<select className="input-field" value={score} onChange={e=>setScore(e.target.value)}><option value="">选择已完成实训</option>{scores.data?.scores?.map((x:any)=><option key={x.id} value={x.id}>{x.project_name} · {x.training_completed_at||x.calculated_at}</option>)}</select></label>
    <label>对应实训室<select className="input-field" value={lab} onChange={e=>setLab(e.target.value)}><option value="">选择实训室</option>{labs.data?.map((x:any)=><option key={x.id} value={x.id}>{x.name}</option>)}</select></label>
    <input aria-label="现场图片" type="file" accept="image/png,image/jpeg,image/webp" onChange={e=>setFile(e.target.files?.[0]??null)}/><button className="btn-primary" disabled={!score||!lab||!file||busy} onClick={submit}>提交环境检查</button>
    {error&&<p role="alert">{error}</p>}{task&&<p role="status">处理状态：{status.data?.status||task.status}{status.data?.error_message&&` · ${status.data.error_message}`}{status.data?.status==='completed'&&' · 已生成，请刷新检查记录查看'}</p>}
  </section>
}
