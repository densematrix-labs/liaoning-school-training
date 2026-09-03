import { motion } from 'framer-motion'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import clsx from 'clsx'
import { useAuthStore } from '../store/auth'
import { roleMenus } from '../lib/roleAccess'

const roleMeta = {
  student: { label: '学生', scope: '仅限本人数据', accent: 'text-accent-cyan' },
  teacher: { label: '教师', scope: '所带班级数据', accent: 'text-status-warning' },
  admin: { label: '管理员', scope: '全校管理权限', accent: 'text-status-danger' },
}

export default function Layout() {
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()
  if (!user) return null

  const role = roleMeta[user.role]
  const links = roleMenus[user.role]

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-railway-900 grid-bg">
      <header className="fixed inset-x-0 top-0 z-50 border-b border-accent-blue/20 bg-railway-900/95 backdrop-blur-xl">
        <div className="flex h-20 items-center justify-between px-4 lg:px-7">
          <div className="flex min-w-0 items-center gap-3">
            <div className="signal-mark" aria-hidden="true"><span /><span /><span /></div>
            <div className="min-w-0">
              <h1 className="truncate font-display text-sm font-semibold tracking-wide text-text-primary sm:text-lg">智能实训能力评估平台</h1>
              <p className="hidden text-xs text-text-muted sm:block">辽宁铁道职业技术学院 · 数据驾驶舱</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <NavLink to="/dashboard" className="hidden text-xs font-semibold text-accent-blue hover:text-accent-cyan sm:block">大屏展示</NavLink>
            <div className="border-l border-railway-500/60 pl-3 text-right">
              <div className="flex items-center justify-end gap-2">
                <span className="text-sm font-semibold text-text-primary">{user.name}</span>
                <span className={clsx('role-badge', role.accent)}>{role.label}</span>
              </div>
              <p className="text-[11px] text-text-muted">{user.class_name || role.scope}</p>
            </div>
            <button onClick={handleLogout} className="railway-button !px-3 !py-1.5 text-xs">退出</button>
          </div>
        </div>
        <nav className="flex gap-1 overflow-x-auto border-t border-railway-600/40 px-3 py-2 lg:hidden">
          {links.map((link) => <MenuLink key={link.to} {...link} compact />)}
        </nav>
      </header>

      <aside className="fixed bottom-0 left-0 top-20 hidden w-64 border-r border-accent-blue/20 bg-railway-800/85 lg:block">
        <div className="border-b border-railway-600/50 p-5">
          <p className="text-[10px] uppercase tracking-[0.22em] text-text-muted">Current workspace</p>
          <p className={clsx('mt-2 font-display text-lg font-semibold', role.accent)}>{role.label}工作区</p>
          <p className="mt-1 text-xs text-text-muted">{role.scope}</p>
        </div>
        <nav className="space-y-1 p-3">
          {links.map((link, index) => (
            <motion.div key={link.to} initial={{ opacity: 0, x: -12 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: index * 0.04 }}>
              <MenuLink {...link} />
            </motion.div>
          ))}
        </nav>
        <div className="absolute bottom-5 left-5 right-5 border-l-2 border-status-success/70 pl-3">
          <p className="text-xs text-status-success">数据服务在线</p>
          <p className="text-[10px] text-text-muted">SQLite · LLM Proxy</p>
        </div>
      </aside>

      <main className="px-4 pb-10 pt-36 sm:px-6 lg:ml-64 lg:px-8 lg:pt-28">
        <div className="mx-auto max-w-7xl"><Outlet /></div>
      </main>
    </div>
  )
}

function MenuLink({ to, label, icon, compact = false }: { to: string; label: string; icon: string; compact?: boolean }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) => clsx(
        'flex shrink-0 items-center gap-3 border transition-all',
        compact ? 'rounded px-3 py-2 text-xs' : 'rounded-md px-4 py-3 text-sm',
        isActive
          ? 'border-accent-blue/50 bg-accent-electric/15 text-accent-cyan shadow-glow-sm'
          : 'border-transparent text-text-secondary hover:border-railway-500 hover:bg-railway-700/60 hover:text-text-primary',
      )}
    >
      <span className="font-mono text-base text-accent-blue">{icon}</span>
      <span className="font-medium">{label}</span>
    </NavLink>
  )
}
