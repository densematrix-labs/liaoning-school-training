import { useRef, useState, type InputHTMLAttributes } from 'react'

export default function ChineseFileInput({ onChange, className = '', ...props }: InputHTMLAttributes<HTMLInputElement>) {
  const input = useRef<HTMLInputElement>(null)
  const [name, setName] = useState('')
  return <span className={`inline-flex max-w-full items-center gap-3 ${className}`}>
    <input {...props} ref={input} type="file" className="sr-only" onChange={event => {
      setName(Array.from(event.target.files || []).map(file => file.name).join('、'))
      onChange?.(event)
    }} />
    <button type="button" className="btn-secondary shrink-0" disabled={props.disabled} onClick={() => input.current?.click()}>选择文件</button>
    <span className="min-w-0 break-all text-sm" aria-live="polite">{name || '未选择文件'}</span>
  </span>
}
