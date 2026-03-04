import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../stores/auth'
import clsx from 'clsx'

export default function MainLayout() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const navItems = user?.role === 'student' ? [
    { path: '/student', label: '概览', end: true },
    { path: '/student/records', label: '实训记录' },
    { path: '/student/ability', label: '能力图谱' },
    { path: '/student/reports', label: '诊断报告' },
  ] : user?.role === 'admin' ? [
    { path: '/admin', label: '能力管理', end: true },
    { path: '/admin/labs', label: '实训室管理' },
    { path: '/admin/mappings', label: '映射管理' },
    { path: '/teacher', label: '班级管理' },
  ] : [
    { path: '/teacher', label: '班级概览', end: true },
  ]

  return (
    <div className="min-h-screen bg-railway-900 grid-bg">
      <header className="bg-railway-800/90 border-b border-railway-600/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-accent-electric/20 border border-accent-blue/50 flex items-center justify-center">
                <svg className="w-6 h-6 text-accent-blue" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              </div>
              <div>
                <h1 className="text-lg font-semibold text-text-primary">辽轨实训平台</h1>
                <p className="text-xs text-text-muted">智能能力评估系统</p>
              </div>
            </div>

            <nav className="hidden md:flex items-center gap-1">
              {navItems.map((item) => (
                <NavLink key={item.path} to={item.path} end={item.end}
                  className={({ isActive }) => clsx(
                    'px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200',
                    isActive ? 'bg-accent-electric/20 text-accent-blue border border-accent-blue/30' : 'text-text-secondary hover:text-text-primary hover:bg-railway-700/50'
                  )}>
                  {item.label}
                </NavLink>
              ))}
            </nav>

            <div className="flex items-center gap-4">
              <NavLink to="/dashboard" className="text-text-secondary hover:text-accent-blue transition-colors text-sm">大屏展示</NavLink>
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-full bg-railway-600 flex items-center justify-center text-sm font-medium">{user?.name?.[0] || 'U'}</div>
                <div className="hidden sm:block">
                  <p className="text-sm font-medium text-text-primary">{user?.name}</p>
                  <p className="text-xs text-text-muted capitalize">{user?.role}</p>
                </div>
              </div>
              <button onClick={handleLogout} className="text-text-muted hover:text-status-danger transition-colors">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8"><Outlet /></main>

      <footer className="border-t border-railway-700/50 py-6 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center text-text-muted text-sm">
          <p>© 2026 辽宁铁道职业技术学院 · 智能实训能力评估平台</p>
          <p className="mt-1 text-xs">技术支持：DenseMatrix AI</p>
        </div>
      </footer>
    </div>
  )
}
