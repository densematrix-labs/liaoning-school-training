import {useState} from 'react'
import {useQuery} from '@tanstack/react-query'
import {api} from '../lib/api'
export default function AbilityHierarchy(){
 const [selected,setSelected]=useState('')
 const {data,isLoading,error}=useQuery({queryKey:['ability-hierarchy'],queryFn:async()=>(await api.get('/api/v1/release/ability-hierarchy')).data})
 const parent=data?.items.find((x:any)=>x.id===selected)||data?.items[0]
 return <section className="railway-card space-y-4 p-5" aria-label="能力体系"><h2 className="section-heading">能力体系</h2>{isLoading&&<p>正在读取…</p>}{error&&<p role="alert">能力体系读取失败</p>}{parent&&<div className="grid gap-5 lg:grid-cols-[1fr_2fr]"><nav aria-label="能力父子名称树" className="space-y-2">{data.items.map((x:any)=><button className="w-full rounded border border-railway-500 p-3 text-left" key={x.id} onClick={()=>setSelected(x.id)}><strong>{x.name}</strong><span className="ml-3">{x.children.length} 项子能力</span></button>)}</nav><div><h3 className="font-semibold">{parent.name} · 达标分 {parent.pass_score} / 100</h3><table className="mt-4 w-full text-left"><thead><tr><th>子能力</th><th>编码</th><th>满分</th><th>状态</th></tr></thead><tbody>{parent.children.map((x:any)=><tr className="border-t border-railway-500" key={x.id}><td className="py-3">{x.name}</td><td>{x.code||'—'}</td><td>{x.full_score}</td><td>{x.enabled?'启用':'停用'}</td></tr>)}</tbody></table></div></div>}</section>
}
