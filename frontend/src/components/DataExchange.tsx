import {useState} from 'react'
import {api,getErrorMessage} from '../lib/api'
export default function DataExchange(){
 const [sid,setSid]=useState(''),[error,setError]=useState('')
 const get=async(kind:string)=>{try{const r=await api.get(`/api/v1/release/business-export/${kind}.csv`,{params:{student_id:sid||undefined},responseType:'blob'});const u=URL.createObjectURL(r.data);const a=document.createElement('a');a.href=u;a.download=kind+'.csv';a.click();URL.revokeObjectURL(u);setError('')}catch(e){setError(getErrorMessage(e))}}
 return <section className="railway-card space-y-4 p-5"><h2 className="section-heading">业务数据导出</h2><label>能力评价导出的学生ID<input aria-label="导出学生范围" className="input-field" value={sid} onChange={e=>setSid(e.target.value)}/></label><div className="flex flex-wrap gap-3">{[['steps','步骤定义'],['mappings','步骤能力映射'],['evaluations','能力评价结果'],['report-summaries','报告摘要']].map(([k,n])=><button className="btn-secondary" key={k} disabled={k==='evaluations'&&!sid} onClick={()=>get(k)}>导出{n} CSV</button>)}</div>{error&&<p role="alert">{error}</p>}</section>
}
