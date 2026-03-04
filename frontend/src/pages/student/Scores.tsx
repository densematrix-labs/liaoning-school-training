import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../lib/api'

interface Score {
  id: string
  project_id: string
  project_name: string
  total_score: number
  max_score: number
  percentage: number
  calculated_at: string
}

interface ScoreList {
  scores: Score[]
  total: number
  page: number
  page_size: number
  average_score: number | null
}

function ScoreCard({ score, index }: { score: Score; index: number }) {
  const isPassed = score.percentage >= 60
  const isExcellent = score.percentage >= 85
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      className="glass-panel p-5 hover:shadow-glow-sm transition-all duration-300 group"
    >
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="font-display text-lg font-semibold text-text-primary group-hover:text-accent-cyan transition-colors">
            {score.project_name || '实训项目'}
          </h3>
          <p className="text-sm text-text-muted mt-1">
            {new Date(score.calculated_at).toLocaleDateString('zh-CN', {
              year: 'numeric',
              month: 'long',
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit',
            })}
          </p>
        </div>
        
        {/* Score badge */}
        <div className={`px-4 py-2 rounded-lg font-display text-2xl font-bold
          ${isExcellent ? 'bg-status-success/20 text-status-success' :
            isPassed ? 'bg-accent-blue/20 text-accent-cyan' :
            'bg-status-danger/20 text-status-danger'}`}
        >
          {score.percentage}
        </div>
      </div>
      
      {/* Progress bar */}
      <div className="h-2 bg-railway-700 rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${score.percentage}%` }}
          transition={{ duration: 0.8, delay: index * 0.05 + 0.2 }}
          className={`h-full rounded-full
            ${isExcellent ? 'bg-gradient-to-r from-status-success to-accent-cyan' :
              isPassed ? 'bg-gradient-to-r from-accent-electric to-accent-blue' :
              'bg-gradient-to-r from-status-danger to-status-warning'}`}
        />
      </div>
      
      {/* Score details */}
      <div className="flex items-center justify-between mt-3 text-sm">
        <span className="text-text-muted">
          得分: <span className="font-mono text-text-primary">{score.total_score} / {score.max_score}</span>
        </span>
        <span className={`font-semibold
          ${isPassed ? 'text-status-success' : 'text-status-danger'}`}
        >
          {isPassed ? '✓ 通过' : '✗ 未通过'}
        </span>
      </div>
    </motion.div>
  )
}

export default function StudentScores() {
  const { t } = useTranslation()
  const [page, setPage] = useState(1)
  
  const { data, isLoading } = useQuery<ScoreList>({
    queryKey: ['student-scores', page],
    queryFn: async () => {
      const res = await api.get('/api/v1/scores/', { params: { page, page_size: 10 } })
      return res.data
    },
  })
  
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-12 h-12 border-4 border-accent-blue/30 border-t-accent-blue rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold text-gradient">
            {t('student.score_history')}
          </h1>
          <p className="text-text-muted mt-1">
            共 {data?.total || 0} 条实训记录
          </p>
        </div>
        
        {/* Average score */}
        {data?.average_score && (
          <div className="glass-panel px-6 py-4 text-center">
            <p className="text-sm text-text-muted mb-1">平均分</p>
            <p className="font-display text-3xl font-bold text-accent-cyan">
              {data.average_score}
            </p>
          </div>
        )}
      </div>
      
      {/* Score list */}
      <div className="grid gap-4">
        {data?.scores.map((score, index) => (
          <ScoreCard key={score.id} score={score} index={index} />
        ))}
      </div>
      
      {/* Empty state */}
      {(!data?.scores || data.scores.length === 0) && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="glass-panel p-12 text-center"
        >
          <div className="text-6xl mb-4">📊</div>
          <h3 className="font-display text-xl font-semibold text-text-primary mb-2">
            暂无实训记录
          </h3>
          <p className="text-text-muted">
            完成实训后，成绩将显示在这里
          </p>
        </motion.div>
      )}
      
      {/* Pagination */}
      {data && data.total > data.page_size && (
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="btn-secondary !px-4 !py-2 disabled:opacity-50"
          >
            上一页
          </button>
          <span className="px-4 text-text-muted">
            第 {page} 页，共 {Math.ceil(data.total / data.page_size)} 页
          </span>
          <button
            onClick={() => setPage(p => p + 1)}
            disabled={page >= Math.ceil(data.total / data.page_size)}
            className="btn-secondary !px-4 !py-2 disabled:opacity-50"
          >
            下一页
          </button>
        </div>
      )}
    </div>
  )
}
