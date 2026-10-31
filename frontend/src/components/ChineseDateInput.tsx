import { useEffect, useRef, useState } from 'react'

type Props = {
  value: string
  onValueChange: (value: string) => void
  type?: 'date' | 'datetime-local'
  className?: string
  'aria-label'?: string
}
const pad = (value: number) => String(value).padStart(2, '0')
function validDate(value: string, time: boolean) {
  if (!(time ? /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/ : /^\d{4}-\d{2}-\d{2}$/).test(value)) return false
  const [year, month, day] = value.slice(0, 10).split('-').map(Number)
  const date = new Date(year, month - 1, day)
  return year >= 1000 && date.getFullYear() === year && date.getMonth() === month - 1 && date.getDate() === day && (!time || (Number(value.slice(11, 13)) < 24 && Number(value.slice(14, 16)) < 60))
}
export default function ChineseDateInput({ value, onValueChange, type = 'date', className = 'input-field', ...props }: Props) {
  const withTime = type === 'datetime-local'
  const [draft, setDraft] = useState(value.replace('T', ' '))
  const [open, setOpen] = useState(false)
  const [error, setError] = useState('')
  const [month, setMonth] = useState(() => new Date((value || new Date().toISOString()).slice(0, 7) + '-01T12:00:00'))
  const root = useRef<HTMLSpanElement>(null)
  useEffect(() => { setDraft(value.replace('T', ' ')); setError('') }, [value])
  useEffect(() => {
    if (!open) return
    const close = (event: MouseEvent) => { if (!root.current?.contains(event.target as Node)) setOpen(false) }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [open])
  const select = (date: string) => {
    const next = date ? date + (withTime ? 'T' + (validDate(value, true) ? value.slice(11, 16) : '00:00') : '') : ''
    onValueChange(next); setDraft(next.replace('T', ' ')); setError(''); setOpen(false)
  }
  const start = new Date(month.getFullYear(), month.getMonth(), 1).getDay()
  const days = new Date(month.getFullYear(), month.getMonth() + 1, 0).getDate()
  return <span ref={root} className="relative inline-block w-full" onKeyDown={event => { if (event.key === 'Escape') setOpen(false) }}>
    <span className="flex items-center gap-1">
      <input {...props} type="text" className={className} value={draft} placeholder={withTime ? '年-月-日 时:分' : '年-月-日'} aria-invalid={!!error} onChange={event => {
        const text = event.target.value
        setDraft(text); setError('')
        const next = text.trim().replace(' ', 'T')
        if (!next || validDate(next, withTime)) onValueChange(next)
      }} onBlur={() => {
        if (draft && !validDate(draft.trim().replace(' ', 'T'), withTime)) setError(withTime ? '请输入有效日期时间，例如 2026-10-30 09:30' : '请输入有效日期，例如 2026-10-30')
      }} />
      <button type="button" className="btn-secondary shrink-0 px-2" aria-label={(props['aria-label'] || '') + '选择日期'} aria-expanded={open} onClick={() => {
        if (!open && value) setMonth(new Date(value.slice(0, 7) + '-01T12:00:00'))
        setOpen(!open)
      }}>日历</button>
    </span>
    {error && <span role="alert" className="block text-sm text-status-danger">{error}</span>}
    {open && <span role="group" aria-label="日期选择" className="absolute left-0 top-full z-50 mt-1 block w-72 rounded-lg border border-railway-600 bg-railway-800 p-3 shadow-xl">
      <span className="mb-3 flex items-center justify-between">
        <button type="button" aria-label="上个月" onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() - 1, 1))}>上一月</button>
        <strong>{month.getFullYear()}年{month.getMonth() + 1}月</strong>
        <button type="button" aria-label="下个月" onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() + 1, 1))}>下一月</button>
      </span>
      <span className="grid grid-cols-7 gap-1 text-center">
        {['日', '一', '二', '三', '四', '五', '六'].map(day => <span key={day}>{day}</span>)}
        {Array.from({ length: start }, (_, index) => <span key={'blank' + index} />)}
        {Array.from({ length: days }, (_, index) => {
          const date = `${month.getFullYear()}-${pad(month.getMonth() + 1)}-${pad(index + 1)}`
          return <button key={date} type="button" aria-label={date} aria-pressed={value.slice(0, 10) === date} className={`rounded p-1 hover:bg-railway-600 ${value.slice(0, 10) === date ? 'bg-railway-600 font-bold' : ''}`} onClick={() => select(date)}>{index + 1}</button>
        })}
      </span>
      <span className="mt-3 flex justify-between">
        <button type="button" onClick={() => select('')}>清空</button>
        <button type="button" onClick={() => { const now = new Date(); select(`${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`) }}>今天</button>
        <button type="button" onClick={() => setOpen(false)}>关闭</button>
      </span>
    </span>}
  </span>
}
