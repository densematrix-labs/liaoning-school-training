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
  const importFile = useMutation({
    mutationFn: async (file: File) => { const body = new FormData(); body.append('file', file); return (await api.post('/api/v1/admin/operations/sync-import', body, { headers: { 'Content-Type': 'multipart/form-data' } })).data },
  })

  return <div className="space-y-7">
    <header><p className="eyebrow">基础配置</p><h1 className="page-title">规则、能力与权限配置</h1><p className="mt-2 text-sm text-text-muted">所有规则修改均生成版本号，可选择样例成绩重算并查看前后差异</p></header>
    <ProjectConfiguration projects={projects.data || []} abilities={abilities.data || []} />
    <div className="grid gap-6 xl:grid-cols-2">
      <AbilityConfiguration abilities={abilities.data || []} />
      <LabConfiguration labs={labs.data || []} />
    </div>
    <AccessControl data={access.data} />
    <OperationsPanel />
    <section className="railway-card overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-railway-600/50 p-5"><div><p className="eyebrow">演示工具</p><h2 className="section-heading">演示数据导入与验证</h2><p className="mt-1 text-xs text-text-muted">模拟外部实训记录导入 → 计分 → 能力更新 → 报告/环境任务；仅用于演示与联调验证，不影响核心教学业务操作。</p></div><div className="flex flex-wrap gap-2"><button type="button" className="railway-button" onClick={downloadDemoRows}>下载演示数据</button><label className="railway-button cursor-pointer">{importFile.isPending ? '正在导入…' : '导入演示数据'}<input className="hidden" type="file" accept=".csv,text/csv" disabled={importFile.isPending} onChange={(e) => { const file = e.target.files?.[0]; if (file) importFile.mutate(file); e.currentTarget.value = '' }} /></label><button onClick={() => sync.mutate()} disabled={sync.isPending || importFile.isPending} className="btn-primary">{sync.isPending ? '验证中…' : '执行导入验证'}</button></div></div>
      {(sync.error || importFile.error) && <ErrorBox error={sync.error || importFile.error} />}
      {importFile.data && <div className="alert-success m-4 rounded p-3 text-sm">演示数据已导入：共 {importFile.data.row_count} 条，请点击「执行导入验证」开始处理</div>}
      {sync.data && <div className="alert-success m-4 rounded p-3 text-sm">同步完成：读取 {sync.data.read_count}，新增 {sync.data.success_count}，跳过 {sync.data.skipped_count}，异常 {sync.data.error_count}</div>}
      <div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm"><thead className="bg-railway-800/70 text-xs text-text-muted"><tr><th className="p-3">验证批次</th><th>读取</th><th>新增</th><th>跳过</th><th>异常</th><th>状态</th><th>操作</th></tr></thead><tbody>{history.data?.map((item: any, index: number) => <tr key={item.id} className="border-t border-railway-600/40"><td className="p-3"><p className="text-xs text-text-secondary">第 {history.data.length - index} 批</p><p className="text-xs text-text-muted">{new Date(item.started_at).toLocaleString('zh-CN')}</p></td><td>{item.read_count}</td><td className="text-status-success">{item.success_count}</td><td>{item.skipped_count}</td><td className="text-status-warning">{item.error_count}</td><td>{statusLabel(item.status)}</td><td><button className="railway-button !px-2 !py-1 text-xs" disabled={!item.error_count} onClick={() => downloadExceptions(item.id)}>导出异常</button></td></tr>)}</tbody></table></div>
    </section>
  </div>
}

function OperationsPanel() {
  const queryClient = useQueryClient()
  const status = useQuery({ queryKey: ['operations-status'], queryFn: async () => (await api.get('/api/v1/admin/operations/status')).data })
  const schedule = useQuery({ queryKey: ['sync-schedule'], queryFn: async () => (await api.get('/api/v1/admin/operations/sync-schedule')).data })
  const backups = useQuery({ queryKey: ['backups'], queryFn: async () => (await api.get('/api/v1/admin/operations/backups')).data })
  const logs = useQuery({ queryKey: ['audit-logs'], queryFn: async () => (await api.get('/api/v1/admin/operations/audit-logs', { params: { limit: 20 } })).data })
  const performance = useQuery({ queryKey: ['performance-report'], queryFn: async () => (await api.get('/api/v1/admin/operations/performance-report')).data })
  const [enabled, setEnabled] = useState(true)
  const [frequency, setFrequency] = useState(24)
  const [hour, setHour] = useState(2)
  useEffect(() => { if (schedule.data) { setEnabled(schedule.data.enabled); setFrequency(schedule.data.frequency_hours); setHour(schedule.data.hour) } }, [schedule.data])
  const save = useMutation({ mutationFn: async () => (await api.put('/api/v1/admin/operations/sync-schedule', { enabled, frequency_hours: frequency, hour })).data, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['sync-schedule'] }) })
  const backup = useMutation({ mutationFn: async () => (await api.post('/api/v1/admin/operations/backups')).data, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['backups'] }) })
  return <section className="railway-card overflow-hidden">
    <div className="border-b border-railway-600/50 p-5"><p className="eyebrow">系统运行与数据安全</p><h2 className="section-heading">数据更新计划、服务状态与备份</h2></div>
    <div className="grid gap-5 p-5 xl:grid-cols-3">
      <div className="space-y-3"><h3 className="font-semibold text-text-primary">实训数据自动更新</h3><label className="flex items-center gap-2 text-sm text-text-secondary"><input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />启用定时更新</label><label className="text-xs text-text-muted">更新间隔（小时）<input className="input-field mt-1" type="number" min="1" max="168" value={frequency} onChange={(e) => setFrequency(Number(e.target.value))} /></label><label className="text-xs text-text-muted">每日首选时刻<input className="input-field mt-1" type="number" min="0" max="23" value={hour} onChange={(e) => setHour(Number(e.target.value))} /></label><button className="btn-primary" onClick={() => save.mutate()}>保存更新计划</button></div>
      <div className="space-y-3"><h3 className="font-semibold text-text-primary">数据备份</h3><button className="railway-button w-full" onClick={() => backup.mutate()}>立即生成数据备份</button><p className="text-xs text-text-muted">演示数据入口位于下方「演示数据导入与验证」。已留存 {backups.data?.length || 0} 个备份；恢复校验使用临时副本，不覆盖线上数据。</p></div>
      <div className="space-y-3"><h3 className="font-semibold text-text-primary">服务状态</h3>{status.data && <><StatusLine name="平台服务" value={status.data.application.status} /><StatusLine name="业务数据" value={status.data.database.status} /><StatusLine name="最近更新" value={status.data.sync.status} /><StatusLine name="智能分析" value={status.data.ai.status} /></>}</div>
    </div>
    {performance.data && <PerformanceReport data={performance.data} />}
    <div className="border-t border-railway-600/50 p-5"><h3 className="font-semibold text-text-primary">近期操作记录</h3><div className="mt-3 space-y-2">{logs.data?.map((item: any) => <div key={item.id} className="grid gap-2 rounded bg-railway-800/50 p-3 text-xs md:grid-cols-[150px_1fr_1fr_auto]"><span>{new Date(item.created_at).toLocaleString('zh-CN')}</span><span>{item.actor_name || '系统'}</span><span>{auditLabel(item.action)} · {objectLabel(item.object_type)}</span><span className="text-status-success">{statusLabel(item.result)}</span></div>)}</div></div>
    {(save.error || backup.error) && <ErrorBox error={save.error || backup.error} />}
  </section>
}

function PerformanceReport({ data }: { data: any }) {
  return <div className="border-t border-railway-600/50 p-5">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div><p className="eyebrow">性能验收记录</p><h3 className="section-heading">50 并发性能验收</h3><p className="mt-1 text-xs text-text-muted">{data.environment} · {new Date(data.verified_at).toLocaleString('zh-CN')}</p></div>
      <span className={data.passed ? 'rounded border border-status-success/40 bg-status-success/10 px-3 py-1 text-sm text-status-success' : 'rounded border border-status-warning/40 bg-status-warning/10 px-3 py-1 text-sm text-status-warning'}>{data.passed ? '验收通过' : '未通过'}</span>
    </div>
    <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
      <Metric label="并发用户" value={data.concurrent_users} />
      <Metric label="持续时间" value={`${data.duration_seconds} 秒`} />
      <Metric label="请求总量" value={data.total_requests} />
      <Metric label="请求成功率" value={`${data.success_rate}%`} />
      <Metric label="测试版本" value={data.source_commit} />
    </div>
    <div className="mt-4 grid gap-3 md:grid-cols-2">
      <PerformanceLine item={data.basic} />
      <PerformanceLine item={data.aggregate} />
    </div>
    <p className="mt-3 text-xs text-text-muted">{data.note}</p>
  </div>
}

function PerformanceLine({ item }: { item: any }) { return <div className="rounded border border-railway-600/60 bg-railway-800/45 p-4"><div className="flex items-center justify-between gap-3"><span className="text-sm text-text-secondary">{item.label}</span><span className={item.passed ? 'text-status-success' : 'text-status-warning'}>{item.passed ? '通过' : '未通过'}</span></div><p className="mt-2 font-mono text-2xl text-accent-cyan">P95 {item.p95_seconds} 秒</p><p className="mt-1 text-xs text-text-muted">目标 ≤ {item.target_seconds} 秒</p></div> }

function StatusLine({ name, value }: { name: string; value: string }) { return <div className="flex justify-between border-b border-railway-600/50 pb-2 text-sm"><span className="text-text-muted">{name}</span><span className="text-status-success">● {statusLabel(value)}</span></div> }

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
    <div className="grid gap-4 border-b border-railway-600/50 p-5 lg:grid-cols-[1fr_280px]"><div><p className="eyebrow">评分追溯</p><h2 className="section-heading">评分规则与步骤—能力映射</h2><p className="mt-1 text-xs text-text-muted">步骤通过/未通过得分 → 总分 → 能力画像；映射修改后可重算验证</p></div><select className="input-field" value={project?.id || ''} onChange={(e) => setProjectId(e.target.value)}>{projects.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></div>
    {project && <div className="space-y-5 p-5">
      <div className="space-y-3">{steps.map((step, index) => <div key={step.id} className="rounded border border-railway-600/60 bg-railway-800/35 p-4"><div className="grid gap-3 lg:grid-cols-[1.2fr_120px_120px]"><label className="text-xs text-text-muted">步骤名称<input className="input-field mt-1" value={step.name || ''} onChange={(e) => changeStep(index, 'name', e.target.value)} /></label><label className="text-xs text-text-muted">通过得分<input className="input-field mt-1" type="number" min="1" value={step.score ?? 0} onChange={(e) => changeStep(index, 'score', Number(e.target.value))} /></label><label className="text-xs text-text-muted">未通过得分<input className="input-field mt-1" type="number" min="0" value={step.failed_score ?? 0} onChange={(e) => changeStep(index, 'failed_score', Number(e.target.value))} /></label></div><div className="mt-3 flex flex-wrap gap-2">{subAbilities.map((ability) => <button type="button" key={ability.id} onClick={() => toggleMapping(String(step.id), ability.id)} className={(mapping[String(step.id)] || []).includes(ability.id) ? 'rounded border border-accent-cyan bg-accent-electric/20 px-2 py-1 text-xs text-accent-cyan' : 'rounded border border-railway-500 px-2 py-1 text-xs text-text-muted'}>{ability.major_name} / {ability.name}</button>)}</div></div>)}</div>
      <div className="flex flex-wrap items-end gap-3"><button className="btn-primary" disabled={save.isPending} onClick={() => save.mutate()}>{save.isPending ? '保存中…' : '保存规则与映射'}</button><label className="min-w-72 flex-1 text-xs text-text-muted">样例成绩<select className="input-field mt-1" value={scoreId} onChange={(e) => setScoreId(e.target.value)}>{project.sample_scores?.map((item: any) => <option key={item.id} value={item.id}>{item.student_name || '学生'}（{item.student_no || '学号待确认'}） · {item.class_name || '班级待确认'} · {item.project_name || project.name} · {new Date(item.completed_at || item.calculated_at).toLocaleString('zh-CN')} · {item.total_score}/{item.max_score || project.max_score} 分</option>)}</select></label><button className="railway-button" disabled={!scoreId || recalc.isPending} onClick={() => recalc.mutate()}>{recalc.isPending ? '重算中…' : '重算并比对'}</button></div>
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
  const assign = useMutation({ mutationFn: async ({ teacherId, classIds }: { teacherId: string; classIds: string[] }) => (await api.put(`/api/v1/admin/teachers/${teacherId}/classes`, { class_ids: classIds })).data, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-access'] }) })
  const assignedIds = (teacher: any) => teacher.class_ids || data?.classes?.filter((item: any) => (item.teacher_ids || [item.teacher_id]).includes(teacher.id)).map((item: any) => item.id) || []
  const toggle = (teacher: any, classId: string) => {
    const current = assignedIds(teacher)
    const classIds = current.includes(classId) ? current.filter((id: string) => id !== classId) : [...current, classId]
    assign.mutate({ teacherId: teacher.id, classIds })
  }
  return <section className="railway-card overflow-hidden"><div className="border-b border-railway-600/50 p-5"><p className="eyebrow">账号权限</p><h2 className="section-heading">教师与班级数据范围</h2><p className="mt-1 text-xs text-text-muted">同一教师可管理多个班级，同一班级也可由多名教师共同管理。</p></div><div className="grid gap-3 border-b border-railway-600/50 p-5 md:grid-cols-3">{data?.role_scopes?.map((item: any) => <div key={item.role} className="rounded border border-railway-600/60 p-3"><p className="font-semibold text-text-primary">{item.label}</p><p className="mt-1 text-xs text-text-muted">{item.scope}</p></div>)}</div><div className="divide-y divide-railway-600/40">{data?.teachers?.map((teacher: any) => <div key={teacher.id} className="grid gap-3 p-4 lg:grid-cols-[220px_1fr]"><div><p className="text-sm font-semibold text-text-primary">{teacher.name}</p><p className="text-xs text-text-muted">{teacher.username} · 已授权 {assignedIds(teacher).length} 个班级</p></div><div className="flex flex-wrap gap-2">{data.classes?.map((item: any) => { const checked = assignedIds(teacher).includes(item.id); return <label key={item.id} className={checked ? 'cursor-pointer rounded border border-accent-cyan bg-accent-electric/15 px-3 py-2 text-xs text-accent-cyan' : 'cursor-pointer rounded border border-railway-500 px-3 py-2 text-xs text-text-muted'}><input className="mr-2" type="checkbox" checked={checked} disabled={assign.isPending} onChange={() => toggle(teacher, item.id)} />{item.name}</label> })}</div></div>)}</div>{assign.error && <ErrorBox error={assign.error} />}</section>
}

function Metric({ label, value }: { label: string; value: any }) { return <div><p className="text-xs text-text-muted">{label}</p><p className="mt-1 font-mono text-xl text-accent-cyan">{value}</p></div> }
function ErrorBox({ error }: { error: any }) { return <div className="alert-warning m-4 rounded p-3 text-sm">{getErrorMessage(error)}</div> }
async function downloadExceptions(taskId: string) { const response = await api.get(`/api/v1/admin/sync/${taskId}/exceptions.csv`, { responseType: 'blob' }); const url = URL.createObjectURL(response.data); const link = document.createElement('a'); link.href = url; link.download = '导入异常明细.csv'; link.click(); URL.revokeObjectURL(url) }
async function downloadDemoRows() { const response = await api.get('/api/v1/admin/sync/demo-data.csv', { responseType: 'blob' }); const url = URL.createObjectURL(response.data); const link = document.createElement('a'); link.href = url; link.download = '演示实训数据.csv'; link.click(); URL.revokeObjectURL(url) }

function statusLabel(value: string) {
  return ({ completed: '已完成', running: '处理中', pending: '待处理', failed: '失败', healthy: '正常', configured: '已配置', not_configured: '未配置', not_run: '尚未执行', success: '成功', imported: '已导入' } as Record<string, string>)[value] || '未知状态'
}
function auditLabel(value: string) {
  return ({ update_sync_schedule: '更新数据计划', create_backup: '创建备份', verify_backup: '校验备份', stage_sync_import: '导入演示数据', update_teacher_classes: '调整教师班级授权', create_class: '创建班级', create_account: '创建账号' } as Record<string, string>)[value] || '业务配置变更'
}
function objectLabel(value: string) {
  return ({ system_setting: '系统设置', backup: '数据备份', sync_import: '数据导入', teacher_scope: '教师权限', class: '班级', user: '账号', training_project: '实训项目' } as Record<string, string>)[value] || '业务数据'
}
