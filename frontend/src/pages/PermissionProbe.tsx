import {useState} from 'react'
import {api} from '../lib/api'
import {useAuthStore} from '../store/auth'
export default function PermissionProbe(){
 const {user}=useAuthStore();const [path,setPath]=useState('/api/v1/scores/'),[result,setResult]=useState<any>(null),[busy,setBusy]=useState(false)
 const run=async()=>{if(!path.startsWith('/api/v1/')||path.startsWith('//'))return;setBusy(true);try{const r=await api.get(path);setResult({http_status:r.status,request_id:r.headers['x-request-id'],body:r.data})}catch(e:any){setResult({http_status:e.response?.status,request_id:e.response?.headers?.['x-request-id'],body:e.response?.data||'请求失败'})}finally{setBusy(false)}}
 return <section className="railway-card space-y-4 p-6"><h1 className="page-title">角色与数据范围 · 只读接口核验</h1><p>只读接口访问验证。</p><p>当前登录：{user?.name} · 角色：{user?.role} · 账号ID：{user?.id}</p><label>请求路径及参数<input aria-label="接口核验路径" className="input-field" value={path} onChange={e=>setPath(e.target.value)}/></label><button className="btn-primary" disabled={busy} onClick={run}>{busy?'正在请求':'执行只读请求'}</button>{result&&<div aria-label="接口实测返回"><p>GET {path}</p><p>HTTP {result.http_status} · 请求ID {result.request_id}</p><pre className="mt-3 max-h-[65vh] overflow-auto whitespace-pre-wrap break-all rounded border border-accent-cyan/30 p-4 text-sm">{JSON.stringify(result.body,null,2)}</pre></div>}</section>
}
