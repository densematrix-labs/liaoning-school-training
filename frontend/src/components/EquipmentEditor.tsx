export default function EquipmentEditor({value,onChange}:{value:any,onChange:(items:string[])=>void}) {
  let rows:any[]=[];try{rows=typeof value==='string'?JSON.parse(value||'[]'):value||[]}catch{rows=[]}
  return <div className="space-y-2" aria-label="设备清单列表">{rows.map((v:any,i:number)=><div className="flex gap-2" key={i}><input aria-label={`设备${i+1}`} className="input-field" value={typeof v==='string'?v:v.name||''} onChange={e=>onChange(rows.map((x:any,j:number)=>j===i?e.target.value:x))}/><button type="button" className="btn-secondary" onClick={()=>onChange(rows.filter((_:any,j:number)=>j!==i))}>移除</button></div>)}<button type="button" className="btn-secondary" onClick={()=>onChange([...rows,''])}>添加设备</button></div>
}
