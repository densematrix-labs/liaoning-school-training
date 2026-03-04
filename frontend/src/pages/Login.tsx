import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '../store/auth'
import { motion } from 'framer-motion'

export default function Login() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { login } = useAuthStore()
  
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      await login(username, password)
      navigate('/')
    } catch (err: any) {
      setError(err.response?.data?.detail || t('login.error'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-railway-900 grid-bg flex items-center justify-center p-4">
      {/* Background decorations */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-accent-electric/5 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-accent-cyan/5 rounded-full blur-3xl" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="relative w-full max-w-md"
      >
        {/* Card */}
        <div className="railway-card-glow p-8">
          {/* Header */}
          <div className="text-center mb-8">
            <div className="w-16 h-16 mx-auto mb-4 rounded-xl bg-accent-electric/20 border border-accent-blue/50 flex items-center justify-center">
              <svg className="w-10 h-10 text-accent-blue" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            <h1 className="text-2xl font-bold text-text-primary mb-2">
              {t('app_name')}
            </h1>
            <p className="text-text-muted text-sm">
              辽宁铁道职业技术学院
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-2">
                {t('login.username')}
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="railway-input"
                placeholder="请输入学号/工号"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-text-secondary mb-2">
                {t('login.password')}
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="railway-input"
                placeholder="请输入密码"
                required
              />
            </div>

            {error && (
              <motion.div
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                className="text-status-danger text-sm bg-status-danger/10 px-4 py-2 rounded-lg"
              >
                {error}
              </motion.div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-accent-electric/30 border border-accent-blue rounded-lg text-accent-blue font-medium hover:bg-accent-electric/40 hover:shadow-glow-sm transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  登录中...
                </span>
              ) : (
                t('login.submit')
              )}
            </button>
          </form>

          {/* Demo accounts */}
          <div className="mt-6 pt-6 border-t border-railway-600/30">
            <p className="text-xs text-text-muted text-center mb-3">演示账号（密码均为 123456）</p>
            <div className="grid grid-cols-3 gap-2 text-xs">
              <button
                type="button"
                onClick={() => { setUsername('2023010101'); setPassword('123456') }}
                className="px-2 py-1.5 rounded bg-railway-700/50 text-text-secondary hover:bg-railway-600/50 transition-colors"
              >
                学生
              </button>
              <button
                type="button"
                onClick={() => { setUsername('T20150012'); setPassword('123456') }}
                className="px-2 py-1.5 rounded bg-railway-700/50 text-text-secondary hover:bg-railway-600/50 transition-colors"
              >
                教师
              </button>
              <button
                type="button"
                onClick={() => { setUsername('T20100008'); setPassword('123456') }}
                className="px-2 py-1.5 rounded bg-railway-700/50 text-text-secondary hover:bg-railway-600/50 transition-colors"
              >
                管理员
              </button>
            </div>
          </div>
        </div>

        {/* Dashboard link */}
        <div className="text-center mt-6">
          <a
            href="/dashboard"
            className="text-text-muted hover:text-accent-blue transition-colors text-sm"
          >
            进入大屏展示 →
          </a>
        </div>
      </motion.div>
    </div>
  )
}
