import { useEffect, useMemo, useRef, useState } from 'react'
import replay from '../data/performanceReplay.json'

type ReplayData = {
  title: string
  tested_at: string
  environment: string
  concurrency: number
  duration_seconds: number
  terminal_lines: string[]
}

export default function PerformanceReplay() {
  const data = replay as ReplayData
  const [visibleCount, setVisibleCount] = useState(0)
  const [playing, setPlaying] = useState(true)
  const terminalRef = useRef<HTMLDivElement>(null)
  const lines = useMemo(() => data.terminal_lines || [], [data.terminal_lines])

  useEffect(() => {
    const previousTitle = document.title
    document.title = '只读终端记录｜辽轨智能实训能力评估平台'
    const meta = document.createElement('meta')
    meta.name = 'robots'
    meta.content = 'noindex,nofollow'
    document.head.appendChild(meta)
    return () => { meta.remove(); document.title = previousTitle }
  }, [])

  useEffect(() => {
    if (!playing || visibleCount >= lines.length) return
    const timer = window.setTimeout(() => setVisibleCount((current) => Math.min(current + 1, lines.length)), visibleCount < 3 ? 380 : 150)
    return () => window.clearTimeout(timer)
  }, [lines.length, playing, visibleCount])

  useEffect(() => {
    const terminal = terminalRef.current
    if (!terminal) return
    if (typeof terminal.scrollTo === 'function') terminal.scrollTo({ top: terminal.scrollHeight, behavior: 'smooth' })
    else terminal.scrollTop = terminal.scrollHeight
  }, [visibleCount])

  const replayFromStart = () => {
    setVisibleCount(0)
    setPlaying(true)
  }
  const toggleFullscreen = async () => {
    try {
      if (document.fullscreenElement) await document.exitFullscreen()
      else await document.documentElement.requestFullscreen()
    } catch {
      // 浏览器或嵌入环境不支持全屏时保持只读回放，不触发其他操作。
    }
  }

  return <main className="min-h-screen bg-[#05090f] px-4 py-6 text-slate-100 sm:px-8 lg:px-12">
    <section className="mx-auto flex min-h-[calc(100vh-3rem)] max-w-6xl flex-col overflow-hidden rounded-xl border border-emerald-400/30 bg-[#07110d] shadow-[0_0_60px_rgba(16,185,129,.12)]">
      <header className="flex flex-wrap items-start justify-between gap-4 border-b border-emerald-400/20 bg-[#0b1712] px-5 py-4">
        <div>
          <p className="font-mono text-xs tracking-[.18em] text-emerald-300">READ-ONLY TERMINAL RECORD</p>
          <h1 className="mt-1 text-xl font-semibold text-white">{data.title}</h1>
          <p className="mt-1 text-xs text-slate-400">实际测试时间：{data.tested_at} · {data.environment} · {data.concurrency} 并发 · {data.duration_seconds} 秒</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={() => setPlaying((current) => !current)} className="rounded border border-emerald-400/40 px-3 py-1.5 text-sm text-emerald-200 hover:bg-emerald-400/10">{playing ? '暂停' : '继续'}</button>
          <button type="button" onClick={replayFromStart} className="rounded border border-emerald-400/40 px-3 py-1.5 text-sm text-emerald-200 hover:bg-emerald-400/10">重新播放</button>
          <button type="button" onClick={toggleFullscreen} className="rounded border border-emerald-400/40 px-3 py-1.5 text-sm text-emerald-200 hover:bg-emerald-400/10">全屏</button>
        </div>
      </header>
      <div className="flex items-center gap-2 border-b border-white/5 bg-black/30 px-5 py-2 text-xs text-amber-200"><span className="h-2 w-2 rounded-full bg-amber-300" />只读终端记录 · 自动回放 · 非实时 Shell · 不支持命令输入或任务触发</div>
      <div ref={terminalRef} role="log" aria-label="50 并发测试终端记录" className="min-h-0 flex-1 overflow-y-auto bg-[#050a07] p-5 font-mono text-sm leading-7 text-emerald-200 sm:p-7">
        {lines.slice(0, visibleCount).map((line, index) => <div key={`${index}-${line}`} className={line.startsWith('PASS') ? 'font-semibold text-emerald-300' : line.startsWith('NOTICE') ? 'text-amber-200' : line.startsWith('===') ? 'mt-2 text-cyan-200' : 'whitespace-pre-wrap break-words'}>{line || '\u00a0'}</div>)}
        {visibleCount < lines.length && <span className="inline-block h-5 w-2 animate-pulse bg-emerald-300 align-middle" aria-hidden="true" />}
      </div>
      <footer className="border-t border-emerald-400/15 bg-[#0b1712] px-5 py-3 text-xs text-slate-400">Demo 工程验证，不替代正式验收。正式验收须由双方确认测试环境、标准业务脚本、原始日志和汇总报告。</footer>
    </section>
  </main>
}
