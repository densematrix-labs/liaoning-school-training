import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../lib/api'

interface Score {
  id: string
  student_name: string
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

interface ClassInfo {
  id: string
  name: string
}

interface ClassSummary {
  student_count: number
  average_score: number
  pass_rate: number
  training_count: number
}

export default function TeacherScores() {
  const { t } = useTranslation()
  const [searchParams] = useSearchParams()
  const classId = searchParams.get('class_id')
  const [page, setPage] = useState(1)
  const [selectedClass, setSelectedClass] = useState(classId || '')
  
  const { data: classes } = useQuery<ClassInfo[]>({
    queryKey: ['teacher-classes'],
    queryFn: async () => {
      const res = await api.get('/api/v1/students/classes')
      return res.data
    },
  })
  
  const { data: summary } = useQuery<ClassSummary>({
    queryKey: ['class-summary', selectedClass],
    queryFn: async () => {
      const res = await api.get(`/api/v1/scores/class/${selectedClass}/summary`)
      return res.data
    },
    enabled: !!selectedClass,
  })
  
  const { data: scores, isLoading } = useQuery<ScoreList>({
    queryKey: ['class-scores', selectedClass, page],
    queryFn: async () => {
      const res = await api.get(`/api/v1/scores/class/${selectedClass}`, {
        params: { page, page_size: 20 },
      })
      return res.data
    },
    enabled: !!selectedClass,
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold text-gradient">{t('nav.score_summary')}</h1>
          <p className="text-text-muted mt-1">查看班级学生的实训成绩</p>
        </div>
        
        <select
          value={selectedClass}
          onChange={(e) => { setSelectedClass(e.target.value); setPage(1); }}
          className="input-field w-64"
        >
          <option value="">选择班级</option>
          {classes?.map(cls => (
            <option key={cls.id} value={cls.id}>{cls.name}</option>
          ))}
        </select>
      </div>
      
      {selectedClass && summary && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="card-stat">
              <div className="text-3xl mb-2">👥</div>
              <p className="font-display text-2xl font-bold text-accent-cyan">{summary.student_count}</p>
              <p className="text-sm text-text-muted">学生数</p>
            </div>
            <div className="card-stat">
              <div className="text-3xl mb-2">📊</div>
              <p className="font-display text-2xl font-bold text-accent-cyan">{summary.training_count}</p>
              <p className="text-sm text-text-muted">实训次数</p>
            </div>
            <div className="card-stat">
              <div className="text-3xl mb-2">🎯</div>
              <p className="font-display text-2xl font-bold text-accent-cyan">{summary.average_score}</p>
              <p className="text-sm text-text-muted">平均分</p>
            </div>
            <div className="card-stat">
              <div className="text-3xl mb-2">✅</div>
              <p className="font-display text-2xl font-bold text-status-success">{summary.pass_rate}%</p>
              <p className="text-sm text-text-muted">及格率</p>
            </div>
          </div>
          
          <div className="glass-panel overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-accent-blue/20">
                  <th className="text-left p-4 font-display font-semibold text-text-secondary">学生</th>
                  <th className="text-left p-4 font-display font-semibold text-text-secondary">实训项目</th>
                  <th className="text-left p-4 font-display font-semibold text-text-secondary">得分</th>
                  <th className="text-left p-4 font-display font-semibold text-text-secondary">状态</th>
                  <th className="text-left p-4 font-display font-semibold text-text-secondary">时间</th>
                </tr>
              </thead>
              <tbody>
                {scores?.scores.map((score, index) => (
                  <motion.tr
                    key={score.id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: index * 0.03 }}
                    className="border-b border-railway-700/50 hover:bg-railway-700/20"
                  >
                    <td className="p-4 font-semibold text-text-primary">{score.student_name}</td>
                    <td className="p-4 text-text-secondary">{score.project_name}</td>
                    <td className="p-4">
                      <span className={`font-mono font-bold ${score.percentage >= 60 ? 'text-accent-cyan' : 'text-status-danger'}`}>
                        {score.percentage}
                      </span>
                    </td>
                    <td className="p-4">
                      <span className={`px-2 py-1 rounded text-xs font-semibold ${score.percentage >= 60 ? 'bg-status-success/20 text-status-success' : 'bg-status-danger/20 text-status-danger'}`}>
                        {score.percentage >= 60 ? '通过' : '未通过'}
                      </span>
                    </td>
                    <td className="p-4 text-text-muted text-sm">
                      {new Date(score.calculated_at).toLocaleDateString('zh-CN')}
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
      
      {!selectedClass && (
        <div className="glass-panel p-12 text-center">
          <div className="text-6xl mb-4">📊</div>
          <h3 className="font-display text-xl font-semibold text-text-primary mb-2">请选择班级</h3>
          <p className="text-text-muted">选择班级后查看成绩汇总</p>
        </div>
      )}
      
      {isLoading && selectedClass && (
        <div className="flex items-center justify-center h-64">
          <div className="w-12 h-12 border-4 border-accent-blue/30 border-t-accent-blue rounded-full animate-spin" />
        </div>
      )}
    </div>
  )
}
