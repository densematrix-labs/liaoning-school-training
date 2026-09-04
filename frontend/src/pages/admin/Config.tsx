import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, getErrorMessage } from '../../lib/api'

export default function AdminConfig() {
  const queryClient = useQueryClient()
  const abilities = useQuery({ queryKey: ['admin-abilities'], queryFn: async () => (await api.get('/api/v1/admin/abilities')).data })
  const labs = useQuery({ queryKey: ['admin-labs'], queryFn: async () => (await api.get('/api/v1/admin/labs')).data })
  const projects = useQuery({ queryKey: ['admin-projects'], queryFn: async () => (await api.get('/api/v1/admin/projects')).data })
  const access = useQuery({ queryKey: ['admin-access'], queryFn: async () => (await api.get('/api/v1/admin/access-control')).data })
  const history = useQuery({ queryKey: ['admin-sync-history'], queryFn: async () => (await api.get('/api/v1/admin/sync/history')).data })
  const sync = useMutation({
    mutationFn: async () => (await api.post('/api/v1/admin/sync')).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-sync-history'] }),
  })

  return <div className="space-y-7">
    <header><p className="eyebrow">SYSTEM CONFIGURATION</p><h1 className="page-title">规则、能力与权限配置</h1><p className="mt-2 text-sm text-text-muted">所有规则修改均生成版本号，可选择样例成绩重算并查看前后差异</p></header>
    <ProjectConfiguration projects={projects.data || []} abilities={abilities.data || []} />
    <div className="grid gap-6 xl:grid-cols-2">
      <AbilityConfiguration abilities={abilities.data || []} />
      <LabConfiguration labs={labs.data || []} />
    </div>
    <AccessControl data={access.data} />
    <section className="railway-card overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-railway-600/50 p-5"><div><p className="eyebrow">MOCK SYNC AUDIT</p><h2 className="section-heading">演示数据同步闭环</h2><p className="mt-1 text-xs text-text-muted">模拟增量、去重、异常隔离和重复执行；不连接校方 MySQL</p></div><button onClick={() => sync.mutate()} disabled={sync.isPending} className="btn-primary">{sync.isPending ? '执行中…' : '执行一次 Mock 同步'}</button></div>
      {sync.error && <ErrorBox error={sync.error} />}
      <div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm"><thead className="bg-railway-800/70 text-xs text-text-muted"><tr><th className="p-3">任务</th><th>读取</th><th>新增</th><th>跳过</th><th>异常</th><th>状态</th><th>操作</th></tr></thead><tbody>{history.data?.map((item: any) => <tr key={item.id} className="border-t border-railway-600/40"><td className="p-3"><p className="font-mono text-xs text-text-secondary">{item.id.slice(0, 12)}</p><p className="text-xs text-text-muted">{new Date(item.started_at).toLocaleString('zh-CN')}</p></td><td>{item.read_count}</td><td className="text-status-success">{item.success_count}</td><td>{item.skipped_count}</td><td className="text-status-warning">{item.error_count}</td><td>{item.status === 'completed' ? '完成' : item.status}</td><td><button className="railway-button !px-2 !py-1 text-xs" disabled={!item.error_count} onClick={() => downloadExceptions(item.id)}>导出异常</button></td></tr>)}</tbody></table></div>
    </section>
  </div>
}

function ProjectConfiguration({ projects, abilities }: { projects: any[]; abilities: any[] }) {
  const queryClient = useQueryClient()
  const [projectId, setProjectId] = useState('')
  const project = projects.find((item) => item.id === projectId) || projects[0]
  const [steps, setSteps] = useState<any[]>([])
  const [mapping, setMapping] = useState<Record<string, string[]>>({})
  const [scoreId, setScoreId] = useState('')
  const [recalcResult, setRecalcResult] = useState<any>(null)
  useEffect(() => { if (projects.length && !projectId) setProjectId(projects[0].id) }, [projects, projectId])
  useEffect(() => { if (project) { setSteps(structuredClone(project.steps || [])); setMapping(structuredClone(project.ability_mapping || {})); setScoreId(project.sample_scores?.[0]?.id || ''); setRecalcResult(null) } }, [project?.id])
  const subAbilities = useMemo(() => abilities.flatMap((major) => (major.sub_abilities || []).map((sub: any) => ({ ...sub, major_name: major.name }))), [abilities])
  const save = useMutation({
    mutationFn: async () => (await api.put(`/api/v1/admin/projects/${project.id}/configuration`, { steps, ability_mapping: mapping })).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-projects'] }),
  })
  const recalc = useMutation({
    mutationFn: async () => (await api.post(`/api/v1/admin/projects/${project.id}/recalculate`, { score_id: scoreId || null })).data,
    onSuccess: (data) => { setRecalcResult(data); queryClient.invalidateQueries({ queryKey: ['admin-projects'] }) },
  })
  const changeStep = (index: number, key: string, value: string | number) => setSteps((current) => current.map((item, idx) => idx === index ? { ...item, [key]: value } : item))
  const toggleMapping = (stepId: string, abilityId: string) => setMapping((current) => ({ ...current, [stepId]: (current[stepId] || []).includes(abilityId) ? (current[stepId] || []).filter((id) => id !== abilityId) : [...(current[stepId] || []), abilityId] }))
  return <section className="railway-card overflow-hidden">
    <div className="grid gap-4 border-b border-railway-600/50 p-5 lg:grid-cols-[1fr_280px]"><div><p className="eyebrow">SCORING TRACEABILITY</p><h2 className="section-heading">评分规则与步骤—能力映射</h2><p className="mt-1 text-xs text-text-muted">步骤通过/未通过得分 → 总分 → 能力画像；映射修改后可重算验证</p></div><select className="input-field" value={project?.id || ''} onChange={(e) => setProjectId(e.target.value)}>{projects.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></div>
    {project && <div className="space-y-5 p-5">
      <div className="space-y-3">{steps.map((step, index) => <div key={step.id} className="rounded border border-railway-600/60 bg-railway-800/35 p-4"><div className="grid gap-3 lg:grid-cols-[1.2fr_120px_120px]"><label className="text-xs text-text-muted">步骤名称<input className="input-field mt-1" value={step.name || ''} onChange={(e) => changeStep(index, 'name', e.target.value)} /></label><label className="text-xs text-text-muted">通过得分<input className="input-field mt-1" type="number" min="1" value={step.score ?? 0} onChange={(e) => changeStep(index, 'score', Number(e.target.value))} /></label><label className="text-xs text-text-muted">未通过得分<input className="input-field mt-1" type="number" min="0" value={step.failed_score ?? 0} onChange={(e) => changeStep(index, 'failed_score', Number(e.target.value))} /></label></div><div className="mt-3 flex flex-wrap gap-2">{subAbilities.map((ability) => <button type="button" key={ability.id} onClick={() => toggleMapping(String(step.id), ability.id)} className={(mapping[String(step.id)] || []).includes(ability.id) ? 'rounded border border-accent-cyan bg-accent-electric/20 px-2 py-1 text-xs text-accent-cyan' : 'rounded border border-railway-500 px-2 py-1 text-xs text-text-muted'}>{ability.major_name} / {ability.name}</button>)}</div></div>)}</div>
      <div className="flex flex-wrap items-end gap-3"><button className="btn-primary" disabled={save.isPending} onClick={() => save.mutate()}>{save.isPending ? '保存中…' : '保存规则与映射'}</button><label className="min-w-72 flex-1 text-xs text-text-muted">样例成绩<select className="input-field mt-1" value={scoreId} onChange={(e) => setScoreId(e.target.value)}>{project.sample_scores?.map((item: any) => <option key={item.id} value={item.id}>{item.student_id.slice(0, 8)} · 当前 {item.total_score} 分</option>)}</select></label><button className="railway-button" disabled={!scoreId || recalc.isPending} onClick={() => recalc.mutate()}>{recalc.isPending ? '重算中…' : '重算并比对'}</button></div>
      {(save.error || recalc.error) && <ErrorBox error={save.error || recalc.error} />}
      {save.data && <div className="alert-success rounded p-3 text-sm">{save.data.message} · 规则版本 v{save.data.rule_version} · 总分 {save.data.max_score}</div>}
      {recalcResult && <div className="grid gap-3 rounded border border-accent-blue/35 bg-accent-electric/10 p-4 sm:grid-cols-4"><Metric label="重算数量" value={recalcResult.recalculated_count} /><Metric label="原始总分" value={recalcResult.sample?.before_total ?? '—'} /><Metric label="重算总分" value={recalcResult.sample?.after_total ?? '—'} /><Metric label="规则版本" value={`v${recalcResult.sample?.rule_version ?? '—'}`} /></div>}
    </div>}
  </section>
}

function AbilityConfiguration({ abilities }: { abilities: any[] }) {
  const queryClient = useQueryClient()
  const [thresholds, setThresholds] = useState<Record<string, number>>({})
  useEffect(() => setThresholds(Object.fromEntries(abilities.map((item) => [item.id, Math.round(item.graduation_threshold * 100)]))), [abilities])
  const save = useMutation({ mutationFn: async ({ id, value }: { id: string; value: number }) => (await api.put(`/api/v1/admin/abilities/${id}`, { graduation_threshold: value / 100 })).data, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-abilities'] }) })
  return <section className="railway-card overflow-hidden"><div className="border-b border-railway-600/50 p-5"><h2 className="section-heading">能力达标阈值</h2><p className="mt-1 text-xs text-text-muted">影响学生毕业达标判断，不反向修改成绩</p></div><div className="divide-y divide-railway-600/40">{abilities.map((item) => <div key={item.id} className="grid items-center gap-3 p-4 sm:grid-cols-[1fr_110px_auto]"><div><p className="text-sm font-semibold text-text-primary">{item.name}</p><p className="text-xs text-text-muted">{item.sub_abilities?.length || 0} 个子能力</p></div><input className="input-field" type="number" min="0" max="100" value={thresholds[item.id] ?? 0} onChange={(e) => setThresholds((current) => ({ ...current, [item.id]: Number(e.target.value) }))} /><button className="railway-button !px-3 !py-2 text-xs" onClick={() => save.mutate({ id: item.id, value: thresholds[item.id] })}>保存</button></div>)}</div>{save.error && <ErrorBox error={save.error} />}</section>
}

function LabConfiguration({ labs }: { labs: any[] }) {
  const queryClient = useQueryClient()
  const [urls, setUrls] = useState<Record<string, string>>({})
  useEffect(() => setUrls(Object.fromEntries(labs.map((item) => [item.id, item.reference_image_url || '']))), [labs])
  const save = useMutation({ mutationFn: async ({ id, value }: { id: string; value: string }) => (await api.put(`/api/v1/admin/labs/${id}`, { reference_image_url: value })).data, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-labs'] }) })
  return <section className="railway-card overflow-hidden"><div className="border-b border-railway-600/50 p-5"><h2 className="section-heading">实训室标准状态图</h2><p className="mt-1 text-xs text-text-muted">环境检查同时保留标准图、现场图和复核记录</p></div><div className="divide-y divide-railway-600/40">{labs.map((item) => <div key={item.id} className="p-4"><div className="mb-2 flex justify-between"><span className="text-sm font-semibold text-text-primary">{item.name}</span><span className="text-xs text-status-success">● 在线</span></div><div className="flex gap-2"><input className="input-field" value={urls[item.id] || ''} onChange={(e) => setUrls((current) => ({ ...current, [item.id]: e.target.value }))} placeholder="标准状态图片 URL" /><button className="railway-button !px-3 text-xs" onClick={() => save.mutate({ id: item.id, value: urls[item.id] || '' })}>保存</button></div></div>)}</div>{save.error && <ErrorBox error={save.error} />}</section>
}

function AccessControl({ data }: { data: any }) {
  const queryClient = useQueryClient()
  const assign = useMutation({ mutationFn: async ({ classId, teacherId }: { classId: string; teacherId: string }) => (await api.put(`/api/v1/admin/classes/${classId}/teacher`, { teacher_id: teacherId || null })).data, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-access'] }) })
  return <section className="railway-card overflow-hidden"><div className="border-b border-railway-600/50 p-5"><p className="eyebrow">ROLE-BASED ACCESS</p><h2 className="section-heading">账号权限与教师数据范围</h2></div><div className="grid gap-3 border-b border-railway-600/50 p-5 md:grid-cols-3">{data?.role_scopes?.map((item: any) => <div key={item.role} className="rounded border border-railway-600/60 p-3"><p className="font-semibold text-text-primary">{item.label}</p><p className="mt-1 text-xs text-text-muted">{item.scope}</p></div>)}</div><div className="divide-y divide-railway-600/40">{data?.classes?.map((item: any) => <div key={item.id} className="grid items-center gap-3 p-4 md:grid-cols-[1fr_280px]"><div><p className="text-sm text-text-primary">{item.name}</p><p className="text-xs text-text-muted">{item.year} 级 · 当前：{item.teacher_name || '未授权'}</p></div><select className="input-field" value={item.teacher_id || ''} onChange={(e) => assign.mutate({ classId: item.id, teacherId: e.target.value })}><option value="">不授权教师</option>{data.teachers?.map((teacher: any) => <option key={teacher.id} value={teacher.id}>{teacher.name}（{teacher.username}）</option>)}</select></div>)}</div>{assign.error && <ErrorBox error={assign.error} />}</section>
}

function Metric({ label, value }: { label: string; value: any }) { return <div><p className="text-xs text-text-muted">{label}</p><p className="mt-1 font-mono text-xl text-accent-cyan">{value}</p></div> }
function ErrorBox({ error }: { error: any }) { return <div className="alert-warning m-4 rounded p-3 text-sm">{getErrorMessage(error)}</div> }
async function downloadExceptions(taskId: string) { const response = await api.get(`/api/v1/admin/sync/${taskId}/exceptions.csv`, { responseType: 'blob' }); const url = URL.createObjectURL(response.data); const link = document.createElement('a'); link.href = url; link.download = `sync-${taskId}-exceptions.csv`; link.click(); URL.revokeObjectURL(url) }
