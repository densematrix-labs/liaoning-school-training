import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { motion } from 'framer-motion'
import { useAuthStore } from '../store/auth'
import clsx from 'clsx'

const TrainIcon = () => (
  <svg viewBox="0 0 24 24" fill="currentColor" className="w-8 h-8">
    <path d="M12 2C8 2 4 2.5 4 6v9.5C4 17.43 5.57 19 7.5 19L6 20.5v.5h2.23l2-2H14l2 2h2v-.5L16.5 19c1.93 0 3.5-1.57 3.5-3.5V6c0-3.5-4-4-8-4zM7.5 17c-.83 0-1.5-.67-1.5-1.5S6.67 14 7.5 14s1.5.67 1.5 1.5S8.33 17 7.5 17zm3.5-6H6V6h5v5zm2 0V6h5v5h-5zm3.5 6c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5z"/>
  </svg>
)

export default function Layout() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()
  
  const handleLogout = () => {
    logout()
    navigate('/login')
  }
  
  const toggleLang = () => {
    i18n.changeLanguage(i18n.language === 'zh' ? 'en' : 'zh')
  }
  
  const studentLinks = [
    { to: '/scores', label: t('nav.my_scores'), icon: '📊' },
    { to: '/ability', label: t('nav.ability_map'), icon: '🎯' },
    { to: '/reports', label: t('nav.reports'), icon: '📋' },
    { to: '/env-check', label: t('nav.env_check'), icon: '📷' },
  ]
  
  const teacherLinks = [
    { to: '/classes', label: t('nav.class_manage'), icon: '👥' },
    { to: '/class-scores', label: t('nav.score_summary'), icon: '📈' },
    { to: '/batch-reports', label: t('nav.batch_report'), icon: '📑' },
  ]
  
  const links = user?.role === 'teacher' || user?.role === 'admin' 
    ? [...studentLinks, ...teacherLinks]
    : studentLinks

  return (
    <div className="min-h-screen bg-railway-900 bg-grid noise-overlay">
      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-50 glass-panel-bright border-b border-accent-blue/30">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            {/* Logo */}
            <motion.div 
              className="flex items-center gap-4"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
            >
              <div className="text-accent-blue">
                <TrainIcon />
              </div>
              <div>
                <h1 className="font-display text-xl font-bold text-gradient">
                  {t('app_name')}
                </h1>
                <p className="text-xs text-text-muted font-body">
                  辽宁铁道职业技术学院
                </p>
              </div>
            </motion.div>
            
            {/* User Info & Actions */}
            <div className="flex items-center gap-6">
              {/* Dashboard Link */}
              <NavLink
                to="/dashboard"
                className="text-accent-cyan hover:text-accent-blue transition-colors text-sm font-semibold"
              >
                {t('nav.dashboard')}
              </NavLink>
              
              {/* Language Toggle */}
              <button
                onClick={toggleLang}
                className="px-3 py-1 text-sm border border-accent-blue/40 rounded-md hover:bg-accent-blue/10 transition-all"
              >
                {i18n.language === 'zh' ? 'EN' : '中文'}
              </button>
              
              {/* User */}
              <div className="flex items-center gap-3">
                <div className="text-right">
                  <p className="text-sm font-semibold text-text-primary">{user?.name}</p>
                  <p className="text-xs text-text-muted">
                    {user?.role === 'student' ? user?.class_name : '教师'}
                  </p>
                </div>
                <button
                  onClick={handleLogout}
                  className="btn-secondary !px-4 !py-2 text-sm"
                >
                  {t('logout')}
                </button>
              </div>
            </div>
          </div>
        </div>
      </header>
      
      {/* Sidebar + Content */}
      <div className="flex pt-20">
        {/* Sidebar */}
        <aside className="fixed left-0 top-20 bottom-0 w-64 glass-panel border-r border-accent-blue/20 overflow-y-auto">
          <nav className="p-4 space-y-2">
            {links.map((link, index) => (
              <motion.div
                key={link.to}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
              >
                <NavLink
                  to={link.to}
                  className={({ isActive }) =>
                    clsx(
                      'flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-300',
                      'font-body text-sm font-medium',
                      isActive
                        ? 'bg-gradient-to-r from-accent-electric/20 to-accent-blue/10 text-accent-cyan border-l-2 border-accent-cyan shadow-glow-sm'
                        : 'text-text-secondary hover:text-text-primary hover:bg-railway-700/50'
                    )
                  }
                >
                  <span className="text-lg">{link.icon}</span>
                  <span>{link.label}</span>
                </NavLink>
              </motion.div>
            ))}
          </nav>
          
          {/* Decorative element */}
          <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-railway-900 to-transparent pointer-events-none" />
        </aside>
        
        {/* Main Content */}
        <main className="flex-1 ml-64 p-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
          >
            <Outlet />
          </motion.div>
        </main>
      </div>
    </div>
  )
}
