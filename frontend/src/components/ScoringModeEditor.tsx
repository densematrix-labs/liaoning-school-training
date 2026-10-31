export default function ScoringModeEditor({steps,rules,onChange}:{steps:any[];rules:any;onChange:(s:any[],r:any)=>void}) {
 const total=steps.filter(s=>s.enabled!==false).reduce((n,s)=>n+Number(s.score||0),0)
 return <div aria-label="计分配置" className="grid gap-4 rounded border border-railway-500 p-4 md:grid-cols-2"><label>项目满分<input aria-label="项目总分" className="input-field" readOnly value={Math.round(total*100)/100}/></label><label className="flex items-center gap-2"><input aria-label="评分规则启用" type="checkbox" checked={rules.enabled!==false} onChange={e=>onChange(steps,{...rules,enabled:e.target.checked})}/>{rules.enabled===false?'评分规则已停用':'评分规则已启用'}</label></div>
}
