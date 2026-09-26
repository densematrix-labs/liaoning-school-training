import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { motion } from 'framer-motion'
import { useAuthStore } from '../store/auth'
import { getErrorMessage } from '../lib/api'

const demoAccounts = [
  { label: '学生', username: '2023010101', code: 'STUDENT', description: '成绩 · 能力 · 报告' },
  { label: '教师', username: 'T20150012', code: 'TEACHER', description: '班级 · 复核 · 诊断' },
  { label: '管理员', username: 'T20100008', code: 'ADMIN', description: '配置 · 同步 · 运维' },
]

export default function Login() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { login } = useAuthStore()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault(); setError(''); setLoading(true)
    try { await login(username, password); navigate('/') }
    catch (err: any) { setError(getErrorMessage(err, t('login_error'))) }
    finally { setLoading(false) }
  }

  return (
    <div className="grid-bg relative min-h-screen overflow-hidden px-4 py-8 sm:px-6 lg:grid lg:place-items-center lg:px-10">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute left-1/2 top-0 h-[420px] w-[1000px] -translate-x-1/2 rounded-full bg-accent-blue/15 blur-3xl" />
        <div className="absolute -left-24 bottom-0 h-80 w-80 rounded-full border border-accent-cyan/15" />
        <div className="absolute -right-28 top-24 h-96 w-96 rounded-full border border-accent-cyan/10" />
      </div>

      <motion.main initial={false} animate={{ opacity: 1, y: 0 }} className="relative mx-auto grid min-w-0 w-full max-w-full overflow-hidden rounded border border-accent-cyan/55 bg-railway-800/80 shadow-[0_0_60px_rgba(0,200,255,.28),0_32px_80px_rgba(0,20,70,.4)] backdrop-blur-xl lg:max-w-6xl lg:grid-cols-[1.15fr_.85fr]">
        <section className="relative hidden min-h-[660px] overflow-hidden border-r border-accent-cyan/25 p-12 lg:flex lg:flex-col lg:justify-between">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_38%_24%,rgba(100,236,255,.2),transparent_28%),linear-gradient(135deg,rgba(17,103,192,.64),rgba(3,45,105,.92))]" />
          <div className="absolute inset-0 opacity-30 [background-image:linear-gradient(rgba(100,236,255,.12)_1px,transparent_1px),linear-gradient(90deg,rgba(100,236,255,.12)_1px,transparent_1px)] [background-size:28px_28px]" />
          <div className="relative z-10">
            <div className="flex items-center gap-4"><div className="signal-mark" aria-hidden="true"><span /><span /><span /></div><div><p className="font-mono text-[10px] tracking-[.24em] text-accent-cyan">LIAONING RAILWAY · AI LAB</p><p className="mt-1 text-sm text-text-secondary">辽宁铁道职业技术学院</p></div></div>
            <div className="mt-24 max-w-xl">
              <p className="font-mono text-xs tracking-[.22em] text-accent-cyan">INTELLIGENT TRAINING OS</p>
              <h1 className="text-gradient mt-5 text-5xl font-bold leading-[1.16] tracking-[.06em]">智能实训<br />能力评估平台</h1>
              <p className="mt-7 max-w-lg text-base leading-8 text-text-secondary">贯通实训成绩、能力图谱、环境检测与 AI 诊断报告，让每一步操作形成可追溯的成长证据。</p>
            </div>
          </div>
          <div className="relative z-10 grid grid-cols-3 gap-3">
            {[['01', '过程采集'], ['02', '能力计算'], ['03', '智能诊断']].map(([code, label]) => <div key={code} className="border-t border-accent-cyan/50 bg-accent-cyan/5 p-3"><p className="font-mono text-xs text-accent-cyan">{code}</p><p className="mt-2 text-sm text-text-primary">{label}</p></div>)}
          </div>
        </section>

        <section className="relative flex min-h-[660px] min-w-0 flex-col justify-center p-6 sm:p-10 lg:p-12">
          <div className="mb-9 lg:hidden"><div className="flex items-center gap-3"><div className="signal-mark" aria-hidden="true"><span /><span /><span /></div><div><p className="font-mono text-[9px] tracking-[.2em] text-accent-cyan">RAIL TRAINING · AI</p><h1 className="text-lg font-bold text-white">智能实训能力评估平台</h1></div></div></div>
          <div>
            <p className="font-mono text-[10px] tracking-[.24em] text-accent-cyan">SECURE ACCESS</p>
            <h2 className="mt-3 text-3xl font-bold text-white">进入实训工作台</h2>
            <p className="mt-2 text-sm text-text-muted">使用学号或工号登录对应角色空间</p>
          </div>

          <form onSubmit={handleSubmit} className="mt-8 min-w-0 space-y-5">
            <label className="block"><span className="mb-2 block text-sm font-medium text-text-secondary">{t('username')}</span><input type="text" value={username} onChange={(event) => setUsername(event.target.value)} className="railway-input !py-3" placeholder="请输入学号 / 工号" required autoComplete="username" /></label>
            <label className="block"><span className="mb-2 block text-sm font-medium text-text-secondary">{t('password')}</span><input type="password" value={password} onChange={(event) => setPassword(event.target.value)} className="railway-input !py-3" placeholder="请输入密码" required autoComplete="current-password" /></label>
            {error && <motion.div initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} className="rounded border border-status-danger/35 bg-status-danger/10 px-4 py-3 text-sm text-status-danger">{error}</motion.div>}
            <button type="submit" disabled={loading} className="btn-primary w-full !py-3">{loading ? <span className="flex items-center justify-center gap-2"><span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />登录中...</span> : t('login')}</button>
          </form>

          <div className="mt-8 border-t border-accent-cyan/20 pt-6">
            <div className="flex items-center justify-between"><p className="text-xs text-text-muted">演示账号 · 密码均为 123456</p><span className="font-mono text-[9px] text-status-success">● READY</span></div>
            <div className="mt-3 grid min-w-0 grid-cols-3 gap-2">
              {demoAccounts.map((account) => <button key={account.code} type="button" aria-label={account.label} onClick={() => { setUsername(account.username); setPassword('123456') }} className="group min-w-0 overflow-hidden rounded border border-accent-cyan/20 bg-accent-cyan/5 px-2 py-3 text-left transition hover:border-accent-cyan/60 hover:bg-accent-cyan/10"><span className="block truncate text-sm font-semibold text-text-primary">{account.label}</span><span className="mt-1 hidden truncate text-[9px] text-text-muted sm:block">{account.description}</span></button>)}
            </div>
          </div>

          <a href="/dashboard" className="mt-7 flex items-center justify-between rounded border border-accent-cyan/25 bg-railway-900/30 px-4 py-3 text-sm text-text-secondary transition hover:border-accent-cyan/60 hover:text-accent-cyan"><span>无需登录，进入公共数据大屏</span><span aria-hidden="true">→</span></a>
        </section>
      </motion.main>
    </div>
  )
}
