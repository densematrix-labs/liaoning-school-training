import { useEffect, useRef, useState } from 'react'

export type SyncException = {
  id: string
  row_number: number
  source_record_id?: string | null
  reason: string
  raw_data?: Record<string, unknown> | null
}

const fieldLabels: Record<string, string> = {
  source_record_id: '源记录标识', external_id: '源记录标识', student_no: '学号',
  student_index: '学生索引', project_index: '项目索引', project_name: '项目名称',
  project_code: '项目编码', completed_at: '完成时间', step_id: '步骤标识',
  duplicate: '重复标记', invalid: '异常标记',
}

export default function SyncExceptionDetails({ batch, startedAt, exceptions, onClose }: {
  batch: number; startedAt: string; exceptions: SyncException[]; onClose: () => void
}) {
  const [search, setSearch] = useState('')
  const dialogRef = useRef<HTMLDialogElement>(null)
  const searchRef = useRef<HTMLInputElement>(null)
  useEffect(() => {
    const previousFocus = document.activeElement as HTMLElement | null
    dialogRef.current?.showModal()
    searchRef.current?.focus()
    return () => previousFocus?.focus()
  }, [])
  const query = search.trim().toLocaleLowerCase()
  const visible = exceptions.filter(item => `${item.row_number} ${item.source_record_id || ''} ${item.reason} ${JSON.stringify(item.raw_data)}`.toLocaleLowerCase().includes(query))
  return <dialog ref={dialogRef} aria-labelledby="sync-exceptions-title" onCancel={(event) => { event.preventDefault(); onClose() }} className="glass-panel-bright fixed inset-0 !m-auto max-h-[90vh] w-[calc(100%_-_1.5rem)] max-w-5xl overflow-y-auto p-0 text-text-primary backdrop:bg-railway-900/90 backdrop:backdrop-blur-sm">
    <header className="sticky top-0 z-10 flex items-start justify-between gap-3 border-b border-railway-600/60 bg-railway-800 p-5">
      <div><h2 id="sync-exceptions-title" className="section-heading">第 {batch} 批 · 导入异常明细</h2><p className="mt-2 text-sm text-text-muted">{new Date(startedAt).toLocaleString('zh-CN')} · 共 {exceptions.length} 条异常；行号对应原始导入文件（含表头）。</p></div>
      <button type="button" className="railway-button shrink-0" onClick={onClose}>关闭</button>
    </header>
    <div className="space-y-4 p-5">
      <label className="block text-sm text-text-secondary">定位异常记录<input ref={searchRef} className="input-field mt-2 w-full" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="输入行号、源记录标识、学号或失败原因" /></label>
      <p role="status" className="text-sm text-text-muted">显示 {visible.length} / {exceptions.length} 条异常</p>
      {!visible.length && <p className="rounded bg-railway-800 p-4 text-text-secondary">{exceptions.length ? '未找到匹配的异常记录，请调整搜索条件。' : '该批次暂无可展示的异常明细。'}</p>}
      {visible.map(item => <article key={item.id} className="min-w-0 rounded border border-railway-600/60 bg-railway-800/50 p-4">
        <div className="flex flex-wrap items-center justify-between gap-2"><h3 className="font-semibold text-accent-cyan">原始文件第 {item.row_number} 行</h3><span className="break-all text-sm">源记录：{item.source_record_id || '未提供'}</span></div>
        <p className="mt-3 whitespace-pre-wrap break-words text-status-warning">失败原因：{item.reason}</p>
        <details className="mt-4 text-sm"><summary className="cursor-pointer text-accent-cyan">查看原始记录</summary>
          {item.raw_data && Object.keys(item.raw_data).length ? <dl className="mt-3 grid gap-3 sm:grid-cols-2">{Object.entries(item.raw_data).map(([key, value]) => <div key={key} className="min-w-0 rounded bg-railway-900/70 p-3"><dt className="text-text-muted">{fieldLabels[key] || key}</dt><dd className="mt-1 whitespace-pre-wrap break-all text-text-primary">{value === null || value === '' ? '（空）' : typeof value === 'object' ? JSON.stringify(value) : String(value)}</dd></div>)}</dl> : <p className="mt-3 text-text-muted">该记录未保存原始字段，请按源记录标识或行号核对导入文件。</p>}
        </details>
      </article>)}
    </div>
  </dialog>
}
