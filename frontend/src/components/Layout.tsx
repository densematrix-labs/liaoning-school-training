import { motion } from 'framer-motion'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import clsx from 'clsx'
import { useAuthStore } from '../store/auth'
import { roleMenus } from '../lib/roleAccess'

const roleMeta = {
  student: { label: '学生', scope: '仅限本人数据', accent: 'text-accent-cyan', code: 'STUDENT' },
  teacher: { label: '教师', scope: '所带班级数据', accent: 'text-status-warning', code: 'TEACHER' },
  admin: { label: '管理员', scope: '全校管理权限', accent: 'text-status-danger', code: 'ADMIN' },
}

export default function Layout() {
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()
  if (!user) return null

  const role = roleMeta[user.role]
  const links = roleMenus[user.role]
  const handleLogout = () => { logout(); navigate('/login') }

  return (
    <div className="min-h-screen bg-railway-900 grid-bg">
      <header className="fixed inset-x-0 top-0 z-50 border-b border-accent-cyan/50 bg-railway-700/95 shadow-[0_0_32px_rgba(0,200,255,.22)] backdrop-blur-xl">
        <div className="grid h-20 grid-cols-[1fr_auto] items-center gap-4 px-4 lg:grid-cols-[260px_1fr_300px] lg:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <div className="signal-mark" aria-hidden="true"><span /><span /><span /></div>
            <div className="min-w-0">
              <p className="font-mono text-[9px] tracking-[.2em] text-accent-cyan">RAIL TRAINING · AI</p>
              <p className="truncate text-xs font-medium text-text-secondary">辽宁铁道职业技术学院</p>
            </div>
          </div>

          <div className="hidden text-center lg:block">
            <h1 className="text-gradient font-display text-2xl font-bold tracking-[.16em]">智能实训能力评估平台</h1>
            <div className="system-title-decoration mt-1"><span className="h-1.5 w-1.5 rotate-45 bg-accent-cyan shadow-[0_0_8px_#64ecff]" /></div>
          </div>

          <div className="flex items-center justify-end gap-3">
            <NavLink to="/dashboard" className="hidden rounded border border-accent-cyan/40 bg-accent-electric/10 px-3 py-1.5 text-xs font-semibold text-accent-cyan transition hover:bg-accent-cyan/15 sm:block">公共大屏</NavLink>
            <div className="hidden border-l border-accent-cyan/30 pl-3 text-right sm:block">
              <div className="flex items-center justify-end gap-2"><span className="text-sm font-semibold text-text-primary">{user.name}</span><span className={clsx('role-badge', role.accent)}>{role.label}</span></div>
              <p className="text-[10px] text-text-muted">{user.class_name || role.scope}</p>
            </div>
            <button onClick={handleLogout} className="railway-button !px-3 !py-1.5 text-xs">退出</button>
          </div>
        </div>
        <nav className="flex gap-1 overflow-x-auto border-t border-accent-cyan/20 bg-railway-900/35 px-3 py-2 lg:hidden">
          {links.map((link) => <MenuLink key={link.to} {...link} compact />)}
        </nav>
      </header>

      <aside className="fixed bottom-0 left-0 top-20 z-40 hidden w-64 border-r border-accent-cyan/35 bg-railway-800/85 shadow-[8px_0_30px_rgba(0,30,80,.2)] backdrop-blur-xl lg:block">
        <div className="border-b border-accent-cyan/25 p-5">
          <div className="flex items-start justify-between gap-3">
            <div><p className="font-mono text-[9px] uppercase tracking-[.22em] text-text-muted">{role.code} CONSOLE</p><p className={clsx('mt-2 font-display text-xl font-bold tracking-wide', role.accent)}>{role.label}工作区</p></div>
            <span className="mt-1 h-2 w-2 rounded-full bg-status-success shadow-[0_0_10px_#39e58c]" />
          </div>
          <p className="mt-1 text-xs text-text-muted">{role.scope}</p>
        </div>
        <p className="px-5 pb-2 pt-5 font-mono text-[9px] tracking-[.22em] text-text-muted">FUNCTION MODULES</p>
        <nav className="space-y-1 px-3">
          {links.map((link, index) => (
            <motion.div key={link.to} initial={{ opacity: 0, x: -12 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: index * 0.04 }}>
              <MenuLink {...link} />
            </motion.div>
          ))}
        </nav>
        <div className="absolute bottom-5 left-5 right-5 rounded border border-status-success/30 bg-status-success/5 p-3">
          <div className="flex items-center gap-2"><span className="h-1.5 w-1.5 rounded-full bg-status-success shadow-[0_0_8px_#39e58c]" /><p className="text-xs text-status-success">数据服务在线</p></div>
          <p className="mt-1 font-mono text-[9px] text-text-muted">SQLITE · LLM PROXY · VISION</p>
        </div>
      </aside>

      <main className="px-4 pb-10 pt-36 sm:px-6 lg:ml-64 lg:px-8 lg:pt-28">
        <div className="mx-auto max-w-[1500px]">
          <div className="mb-5 flex items-start gap-2 rounded border border-status-warning/25 bg-status-warning/5 px-4 py-2 text-xs text-text-secondary">
            <span className="font-mono text-status-warning">DEMO</span><span>演示环境：实训项目名称、成绩及其计算出的能力结果均为模拟数据，非校方确认数据。</span>
          </div>
          <Outlet />
        </div>
      </main>
    </div>
  )
}

function MenuLink({ to, label, icon, compact = false }: { to: string; label: string; icon: string; compact?: boolean }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) => clsx(
        'group flex shrink-0 items-center gap-3 border transition-all',
        compact ? 'rounded px-3 py-2 text-xs' : 'rounded px-4 py-3 text-sm',
        isActive
          ? 'border-accent-cyan/60 bg-accent-electric/20 text-white shadow-[0_0_16px_rgba(0,200,255,.18)]'
          : 'border-transparent text-text-secondary hover:border-accent-cyan/25 hover:bg-accent-cyan/5 hover:text-white',
      )}
    >
      <span className="font-mono text-base text-accent-cyan transition group-hover:drop-shadow-[0_0_6px_#64ecff]">{icon}</span>
      <span className="font-medium">{label}</span>
    </NavLink>
  )
}
