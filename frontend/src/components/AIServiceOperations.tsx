import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api, getErrorMessage } from '../lib/api'

const time = (value?: string) => value ? value.replace('T', ' ').replace(/\.\d+$/, '') + ' UTC' : '未留存'

export default function AIServiceOperations() {
  const [result, setResult] = useState('')
  const [probing, setProbing] = useState(false)
  const [error, setError] = useState('')
  const { data, isLoading, error: loadError, refetch } = useQuery({queryKey:['ai-service-operations', result], queryFn: async () => (await api.get('/api/v1/release/ai-operations', {params:{result: result || undefined}})).data})
  const maintenance = data?.maintenance
  const probe = async () => { setProbing(true); setError(''); try { await api.post('/api/v1/release/connectivity'); await refetch() } catch (e) { setError(getErrorMessage(e)) } finally { setProbing(false) } }
  return <>
    <section className="railway-card space-y-4 p-5" aria-label="AI调用管理记录">
      <h2 className="section-heading">AI 调用管理记录</h2>
      <div className="flex flex-wrap items-center gap-4"><span>成功：{data?.counts.success ?? 0} 条 · 失败：{data?.counts.failed ?? 0} 条</span><label className="text-sm">调用结果<select className="input-field" aria-label="AI调用结果筛选" value={result} onChange={e => setResult(e.target.value)}><option value="">全部</option><option value="success">成功</option><option value="failed">失败</option></select></label><button className="btn-secondary" onClick={() => refetch()}>刷新调用与维护记录</button></div>
      {(loadError || error) && <p role="alert">{error || '记录读取失败'}</p>}{isLoading && <p>正在读取实际调用记录…</p>}
      <div className="overflow-x-auto"><table className="w-full min-w-[720px] text-left text-sm"><thead><tr className="border-b border-railway-600 text-text-muted"><th className="p-2">调用时间 UTC</th><th>用途</th><th>结果</th><th>审计记录 ID</th></tr></thead><tbody>{data?.calls.map((row: any) => <tr key={row.id} className="border-b border-railway-600/40"><td className="p-2">{time(row.created_at)}</td><td>{row.kind}</td><td className={row.result === 'success' ? 'text-status-success' : 'text-status-warning'}>{row.result === 'success' ? '成功' : '失败'}{row.reason && <p className="text-xs">{row.reason}</p>}</td><td className="max-w-60 break-all font-mono text-xs">{row.id}</td></tr>)}</tbody></table></div>
      {data && !data.calls.length && <p>当前筛选未检索到调用记录。</p>}
    </section>
    <section className="railway-card space-y-4 p-5" aria-label="AI服务运行维护状态">
      <h2 className="section-heading">AI 服务运行维护状态</h2>
      <div className="grid gap-4 md:grid-cols-2"><Card title="业务数据库" value={maintenance?.database === 'connected' ? '连接正常' : '未取得正常结果'} detail={`状态读取：${time(data?.checked_at)}`}/><Card title="任务处理心跳" value={!maintenance ? '正在读取' : maintenance.worker.stale ? '心跳超时' : '心跳正常'} detail={`最近心跳：${time(maintenance?.worker.heartbeat)}`}/><Card title="最近加密备份" value={maintenance?.last_backup.status === 'completed' ? '已完成' : maintenance?.last_backup.status || '未留存备份结果'} detail={`备份时间：${time(maintenance?.last_backup.time)}`}/><Card title="服务连接检查" value={!maintenance?.connectivity.time ? '尚无检查记录' : maintenance.connectivity.ai?.reachable ? '服务连接正常' : 'AI 连通检查未通过'} detail={`检查时间：${time(maintenance?.connectivity.time)}`}/></div>
      <p className="text-sm">备份异常记录：{maintenance?.backup_error.time ? time(maintenance.backup_error.time) + ' · ' + maintenance.backup_error.status : '未检索到'} · 同步异常记录：{maintenance?.sync_error.time ? time(maintenance.sync_error.time) + ' · ' + maintenance.sync_error.reason : '未检索到'}</p>
      <button className="btn-primary" disabled={probing} onClick={probe}>{probing ? '正在检查…' : '检查服务连接'}</button>
    </section>
  </>
}

function Card({ title, value, detail }: { title: string; value: string; detail: string }) { return <article className="rounded border border-accent-cyan/30 p-4"><p className="text-sm text-text-muted">{title}</p><strong className="mt-2 block text-lg text-accent-cyan">{value}</strong><p className="mt-2 text-xs text-text-secondary">{detail}</p></article> }
